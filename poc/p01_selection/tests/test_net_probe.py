"""连通性预检 / 超时快速失败 / urllib3 2.x 补丁 的最小单测（全部离线，不触网）。"""
import socket
import threading

import pytest

from modules.scraper import tcp_reachable, proxy_reachable
from modules import trends


def _unused_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_tcp_reachable_success():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        assert tcp_reachable("127.0.0.1", port, timeout=1) is True
    finally:
        srv.close()


def test_tcp_reachable_fast_fail_when_closed():
    # 未监听端口必须快速返回 False（快速失败，不挂起）
    assert tcp_reachable("127.0.0.1", _unused_port(), timeout=1) is False


def test_tcp_reachable_unrunnable_host_fast_fail():
    # 不可路由地址也必须在 timeout 内返回 False
    assert tcp_reachable("10.255.255.1", 8001, timeout=0.5) is False


def test_proxy_reachable_parses_auth_url():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        assert proxy_reachable(f"http://user:pass@127.0.0.1:{port}", timeout=1) is True
        assert proxy_reachable(f"http://127.0.0.1:{port}", timeout=1) is True
    finally:
        srv.close()
    assert proxy_reachable("not-a-proxy-url", timeout=0.2) is False


def test_scraperapi_fallback_manual_off(monkeypatch):
    """TRENDS_PROXY_FALLBACK=off（兼容旧人工开关）→ 直接禁用，不做任何网络探测"""
    monkeypatch.setenv("TRENDS_PROXY_FALLBACK", "off")

    def _boom(*a, **k):
        raise AssertionError("人工禁用时不应发起 TCP 探测")

    monkeypatch.setattr("modules.scraper.tcp_reachable", _boom)
    assert trends._scraperapi_proxy_reachable() is False


def test_scraperapi_fallback_auto_default(monkeypatch):
    """默认（未设置开关）→ 自动 3 秒预检，探测结果决定是否走代理"""
    monkeypatch.delenv("TRENDS_PROXY_FALLBACK", raising=False)
    calls = {}

    def _fake(host, port, timeout=3.0):
        calls["args"] = (host, port, timeout)
        return False

    monkeypatch.setattr("modules.scraper.tcp_reachable", _fake)
    assert trends._scraperapi_proxy_reachable() is False
    host, port, timeout = calls["args"]
    assert host == "proxy-server.scraperapi.com" and port == 8001
    assert timeout <= 3.0  # 3 秒连通性检查


def test_scraperapi_trends_skips_when_gateway_unreachable(monkeypatch):
    """网关不可达 → _scraper_api_trends 快速返回空 DataFrame，不实例化 pytrends"""
    monkeypatch.setenv("SCRAPERAPI_KEY", "dummy-key")
    monkeypatch.setattr(trends, "_scraperapi_proxy_reachable", lambda: False)
    df = trends._scraper_api_trends("pet water fountain")
    assert df.empty


def test_urllib3_retry_patch_method_whitelist():
    """urllib3>=2 下 pytrends 的 method_whitelist 用法必须生效（映射到 allowed_methods）"""
    import urllib3
    major = int(urllib3.__version__.split(".")[0])
    trends._patch_urllib3_retry()
    from urllib3.util.retry import Retry
    r = Retry(total=1, backoff_factor=0.3, status_forcelist=[429, 500],
              method_whitelist=frozenset(["GET", "POST"]))
    if major >= 2:
        assert r.allowed_methods == frozenset(["GET", "POST"])
    else:  # 老版本透传，不丢参数
        assert r.method_whitelist == frozenset(["GET", "POST"])
    # 幂等：重复 patch 不报错
    trends._patch_urllib3_retry()
