"""
多国出口代理管理器 — 突破地理拦截类平台（amazon_uk/de/in、shopee_sg 等）。

原理：
- 订阅里有多国节点（英国/德国/印度/新加坡/日本/加拿大/香港/台湾/美国）
- 按国家选节点，为每个国家启动一个独立 xray 实例，监听独立本地端口
- 抓取地理受限平台时，按平台 needs_proxy 字段选对应国家的端口

端口分配（HTTP 入站）：
  US=10808(默认/已有), UK=10820, DE=10821, IN=10822, SG=10823,
  JP=10824, CA=10825, HK=10826, TW=10827, FR→无节点(用 DE 邻近兜底可选)

每个国家实例独立 xray 进程，用 DETACHED 脱离父进程。
"""
from __future__ import annotations
import base64, json, ssl, os, time, socket, subprocess
from pathlib import Path
import urllib.request
from loguru import logger

ROOT = Path(__file__).resolve().parents[3]
XRAY_DIR = ROOT / "bin" / "xray"
XRAY_EXE = XRAY_DIR / "xray.exe"
CFG_DIR = Path(__file__).parent / "country_configs"
CFG_DIR.mkdir(exist_ok=True)

SUB_URL = "https://47.112.97.173:5000/api/v1/client/subscribe?token=8aeaf258cea053fee69ad74fb481c730"

# 国家 → (本地HTTP端口, 节点名关键词列表)
# 注意：仅列出订阅里【真实存在】的节点。无节点的国家不要放进来（否则会误以为能走该国 IP）。
# 实测订阅节点（2026-06）：日本/新加坡/香港/印度/台湾/美国/加拿大/德国/英国。
COUNTRY_PORTS = {
    "US": (10808, ["美国", "us-", "los angeles", "america", "🇺🇸"]),  # 已有默认实例
    "UK": (10820, ["英国", "uk", "london", "🇬🇧", "britain"]),
    "DE": (10821, ["德国", "germany", "frankfurt", "🇩🇪"]),
    "IN": (10822, ["印度", "india", "mumbai", "🇮🇳"]),
    "SG": (10823, ["新加坡", "singapore", "🇸🇬"]),
    "JP": (10824, ["日本", "japan", "tokyo", "🇯🇵"]),
    "CA": (10825, ["加拿大", "canada", "🇨🇦"]),
    "HK": (10826, ["香港", "hong kong", "🇭🇰"]),
    "TW": (10827, ["台湾", "taiwan", "🇹🇼"]),
    # AU/FR/KR/中东/俄/巴/墨 等订阅里无节点 → 不映射，由上层诚实标注"无本地 IP"
}

# 地理受限平台 → 最佳出口国家（只映射到真实存在的节点）。
# 无对应国家节点的平台（coupang-KR / noon-AE / trendyol-TR / ozon-RU / mercadolibre-MX/BR 等）
# 不在此表 → 走默认出口，多半仍被地理封锁，应由 platforms.status=blocked 如实标注。
PLATFORM_COUNTRY = {
    "amazon_uk": "UK",
    "amazon_de": "DE",
    "amazon_fr": "DE",   # 无 FR 节点，用德国邻近兜底（同 EU，可能仍被挡）
    "amazon_in": "IN",
    "shopee_sg": "SG",
    "lazada_sg": "SG",
    "amazon_jp": "JP",
    "rakuten": "JP",
}

_SOCKS_OFFSET = 1000  # socks 端口 = http 端口 + 1000
_nodes_cache: list[dict] | None = None


def _b64d(s: str) -> str:
    pad = s + "=" * (-len(s) % 4)
    return base64.b64decode(pad).decode("utf-8", "ignore")


def fetch_nodes() -> list[dict]:
    """解析订阅，返回 vmess 节点 dict 列表（含 ps 名称）。带缓存。"""
    global _nodes_cache
    if _nodes_cache is not None:
        return _nodes_cache
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(SUB_URL, headers={"User-Agent": "v2rayN/6.0"})
    raw = urllib.request.urlopen(req, context=ctx, timeout=30).read().decode("utf-8", "ignore")
    decoded = raw if "://" in raw[:50] else _b64d(raw.strip())
    nodes = []
    for line in [l.strip() for l in decoded.splitlines() if l.strip()]:
        if line.startswith("vmess://"):
            try:
                nodes.append(json.loads(_b64d(line[len("vmess://"):])))
            except Exception:
                pass
    _nodes_cache = nodes
    return nodes


def pick_node(country: str, nodes: list[dict]) -> dict | None:
    """按国家关键词选节点（选第一个匹配的『优化』节点）。"""
    if country not in COUNTRY_PORTS:
        return None
    _, keywords = COUNTRY_PORTS[country]
    for n in nodes:
        ps = (n.get("ps", "") + " " + n.get("add", "")).lower()
        if any(k.lower() in ps for k in keywords):
            return n
    return None


def _make_config(node: dict, http_port: int) -> dict:
    socks_port = http_port + _SOCKS_OFFSET
    ss = {
        "network": node.get("net", "tcp"),
        "security": node.get("tls", "none") or "none",
    }
    if node.get("net") == "ws":
        ss["wsSettings"] = {"path": node.get("path", "/"),
                            "headers": {"Host": node.get("host", node["add"])}}
    if node.get("tls") == "tls":
        ss["tlsSettings"] = {"serverName": node.get("sni") or node.get("host") or node["add"]}
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {"port": http_port, "listen": "127.0.0.1", "protocol": "http",
             "settings": {"timeout": 0}, "tag": "http-in"},
            {"port": socks_port, "listen": "127.0.0.1", "protocol": "socks",
             "settings": {"udp": True, "auth": "noauth"}, "tag": "socks-in"},
        ],
        "outbounds": [{
            "protocol": "vmess",
            "settings": {"vnext": [{
                "address": node["add"], "port": int(node["port"]),
                "users": [{"id": node["id"], "alterId": int(node.get("aid", 0)),
                           "security": node.get("scy", "auto")}]
            }]},
            "streamSettings": ss,
            "tag": "proxy"
        }, {"protocol": "freedom", "tag": "direct"}],
    }


def _is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect((host, port)); s.close(); return True
    except Exception:
        return False


def ensure_country_proxy(country: str, verbose: bool = False) -> str | None:
    """
    确保指定国家的代理实例在跑，返回本地 HTTP 代理 URL（http://127.0.0.1:PORT）。
    若该国家无节点或启动失败，返回 None（调用方应据此报错，不静默回退到 US）。
    """
    country = country.upper()
    if country not in COUNTRY_PORTS:
        logger.warning(f"[multi_country] 无 {country} 国家端口映射")
        return None
    http_port, _ = COUNTRY_PORTS[country]

    # US 用现有默认实例（setup_us_proxy 已管理 10808）
    if country == "US":
        if _is_port_open(http_port):
            return f"http://127.0.0.1:{http_port}"
        # 没起就走 ensure_proxy
        try:
            from proxy.ensure_proxy import ensure_proxy_alive
            if ensure_proxy_alive(verbose=verbose):
                return f"http://127.0.0.1:{http_port}"
        except Exception:
            pass
        return None

    # 已在跑
    if _is_port_open(http_port):
        return f"http://127.0.0.1:{http_port}"

    # 选节点
    nodes = fetch_nodes()
    node = pick_node(country, nodes)
    if not node:
        logger.warning(f"[multi_country] 订阅里找不到 {country} 节点")
        return None

    cfg = _make_config(node, http_port)
    cfg_path = CFG_DIR / f"xray_{country}.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    DETACHED = 0x00000008
    NEW_GROUP = 0x00000200
    flags = (DETACHED | NEW_GROUP) if os.name == "nt" else 0
    subprocess.Popen(
        [str(XRAY_EXE), "run", "-c", str(cfg_path)],
        cwd=str(XRAY_DIR),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=flags, close_fds=True,
    )
    logger.info(f"[multi_country] 启动 {country} 代理（{node.get('ps')}）→ 端口 {http_port}")

    # 等就绪（最多 20 秒）
    for _ in range(20):
        time.sleep(1)
        if _is_port_open(http_port):
            return f"http://127.0.0.1:{http_port}"
    logger.warning(f"[multi_country] {country} 代理 20s 未就绪")
    return None


def get_proxy_for_platform(platform: str, verbose: bool = False) -> str | None:
    """
    给定平台 id，返回最佳出口代理 URL。
    - 地理受限平台 → 对应国家代理（启动失败返回 None）
    - 其他 → US 默认代理
    """
    country = PLATFORM_COUNTRY.get(platform, "US")
    return ensure_country_proxy(country, verbose=verbose)


def verify_country_ip(country: str) -> dict:
    """验证某国家代理的真实出口 IP 国家。"""
    proxy = ensure_country_proxy(country)
    if not proxy:
        return {"country": country, "ok": False, "error": "proxy_not_available"}
    port = COUNTRY_PORTS[country][0]
    try:
        import urllib.request as ur
        handler = ur.ProxyHandler({"http": proxy, "https": proxy})
        opener = ur.build_opener(handler)
        ip = opener.open("https://api.ipify.org", timeout=15).read().decode().strip()
        try:
            geo = json.loads(opener.open(f"https://ipapi.co/{ip}/json/", timeout=15).read().decode())
            cc = geo.get("country_code", "?")
            cn = geo.get("country_name", "?")
        except Exception:
            cc, cn = "?", "?"
        return {"country": country, "ok": True, "proxy": proxy, "exit_ip": ip,
                "exit_country": cc, "exit_country_name": cn,
                "match": cc == country}
    except Exception as e:
        return {"country": country, "ok": False, "error": str(e)[:120]}


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    for c in ["UK", "DE", "IN", "SG"]:
        r = verify_country_ip(c)
        print(json.dumps(r, ensure_ascii=False))
