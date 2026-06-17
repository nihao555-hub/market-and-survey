"""
解析代理订阅 → 选美国 LA 节点 → 生成 xray 配置 → 启动 xray
启动后本地 HTTP 代理：http://127.0.0.1:10808
SOCKS5 代理：           socks5://127.0.0.1:10809
"""
from __future__ import annotations
import base64, json, ssl, sys, os, time, subprocess, signal
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
XRAY_DIR = ROOT / "bin" / "xray"
XRAY_EXE = XRAY_DIR / "xray.exe"
CFG_PATH = Path(__file__).parent / "xray_config.json"
PID_PATH = Path(__file__).parent / "xray.pid"

URL = "https://47.112.97.173:5000/api/v1/client/subscribe?token=8aeaf258cea053fee69ad74fb481c730"

HTTP_PORT = 10808
SOCKS_PORT = 10809


def b64d(s: str) -> str:
    pad = s + "=" * (-len(s) % 4)
    return base64.b64decode(pad).decode("utf-8", "ignore")


def fetch_subscription() -> list[dict]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(URL, headers={"User-Agent": "v2rayN/6.0"})
    raw = urllib.request.urlopen(req, context=ctx, timeout=30).read().decode("utf-8", "ignore")
    decoded = raw if "://" in raw[:50] else b64d(raw.strip())
    nodes = []
    for line in [l.strip() for l in decoded.splitlines() if l.strip()]:
        if line.startswith("vmess://"):
            try:
                info = json.loads(b64d(line[len("vmess://"):]))
                nodes.append(info)
            except Exception:
                pass
    return nodes


def pick_us(nodes: list[dict]) -> dict | None:
    for n in nodes:
        s = (n.get("ps", "") + " " + n.get("add", "")).lower()
        if any(k in s for k in ["美国", "us-", " us ", "los angeles", "america", "🇺🇸"]):
            return n
    return None


def make_xray_config(node: dict) -> dict:
    """vmess 节点 → xray 入站(http+socks) + 出站(vmess+ws)"""
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {"port": HTTP_PORT, "listen": "127.0.0.1", "protocol": "http",
             "settings": {"timeout": 0}, "tag": "http-in"},
            {"port": SOCKS_PORT, "listen": "127.0.0.1", "protocol": "socks",
             "settings": {"udp": True, "auth": "noauth"}, "tag": "socks-in"},
        ],
        "outbounds": [{
            "protocol": "vmess",
            "settings": {"vnext": [{
                "address": node["add"], "port": int(node["port"]),
                "users": [{"id": node["id"], "alterId": int(node.get("aid", 0)),
                           "security": node.get("scy", "auto")}]
            }]},
            "streamSettings": {
                "network": node.get("net", "tcp"),
                "security": node.get("tls", "none") or "none",
                "wsSettings": {
                    "path": node.get("path", "/"),
                    "headers": {"Host": node.get("host", node["add"])}
                } if node.get("net") == "ws" else None,
                "tlsSettings": {"serverName": node.get("sni") or node.get("host") or node["add"]}
                    if node.get("tls") == "tls" else None,
            },
            "tag": "proxy"
        }, {"protocol": "freedom", "tag": "direct"}],
    }


def start_xray():
    nodes = fetch_subscription()
    print(f"订阅节点 {len(nodes)} 个")
    us = pick_us(nodes)
    if not us:
        print("❌ 找不到美国节点")
        sys.exit(1)
    print(f"✅ 选中：{us.get('ps')}  →  {us['add']}:{us['port']}  net={us.get('net')}")

    cfg = make_xray_config(us)
    # 移除值为 None 的 streamSettings 子项
    ss = cfg["outbounds"][0]["streamSettings"]
    cfg["outbounds"][0]["streamSettings"] = {k: v for k, v in ss.items() if v is not None}
    CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"配置已写入：{CFG_PATH}")

    # 启动 xray（关键：用 DETACHED_PROCESS 让 xray 完全脱离父进程，主脚本退出后仍存活）
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    flags = (DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
    proc = subprocess.Popen(
        [str(XRAY_EXE), "run", "-c", str(CFG_PATH)],
        cwd=str(XRAY_DIR),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    PID_PATH.write_text(str(proc.pid))
    print(f"✅ xray 已启动 PID={proc.pid}（脱离父进程）")
    print(f"   HTTP 代理：http://127.0.0.1:{HTTP_PORT}")
    print(f"   SOCKS5 代理：socks5://127.0.0.1:{SOCKS_PORT}")
    return proc, us


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    proc, node = start_xray()
    print("等待 3 秒让代理就绪...")
    time.sleep(3)
    # 验证：通过代理访问 ifconfig.me 看是不是美国 IP
    import urllib.request as ur
    handler = ur.ProxyHandler({"http": f"http://127.0.0.1:{HTTP_PORT}",
                               "https": f"http://127.0.0.1:{HTTP_PORT}"})
    opener = ur.build_opener(handler)
    try:
        ip = opener.open("https://api.ipify.org?format=json", timeout=20).read().decode()
        print(f"\n🌍 出口 IP: {ip}")
        geo = opener.open(f"https://ipapi.co/{json.loads(ip)['ip']}/json/", timeout=20).read().decode()
        info = json.loads(geo)
        print(f"   国家: {info.get('country_name')}  城市: {info.get('city')}  ISP: {info.get('org')}")
    except Exception as e:
        print(f"⚠ 验证失败：{e}")
        print("  代理可能还在启动，再等几秒重试，或检查节点可用性")
