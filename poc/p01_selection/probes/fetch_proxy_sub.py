"""获取代理订阅，解析 vmess 节点，筛美国节点"""
import base64, json, ssl, sys
import urllib.request

URL = "https://47.112.97.173:5000/api/v1/client/subscribe?token=8aeaf258cea053fee69ad74fb481c730"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(URL, headers={"User-Agent": "v2rayN/6.0"})
raw = urllib.request.urlopen(req, context=ctx, timeout=30).read().decode("utf-8", "ignore")


def b64dec(s):
    pad = s + "=" * (-len(s) % 4)
    return base64.b64decode(pad).decode("utf-8", "ignore")


# 整体可能也是 base64
decoded = raw
if "://" not in raw[:50]:
    decoded = b64dec(raw.strip())

lines = [l.strip() for l in decoded.splitlines() if l.strip()]
print(f"节点总数: {len(lines)}\n")

# 解析 vmess://<base64-of-json>
nodes = []
for i, line in enumerate(lines):
    if not line.startswith("vmess://"):
        continue
    try:
        body = b64dec(line[len("vmess://"):])
        info = json.loads(body)
        nodes.append({
            "idx": i,
            "ps": info.get("ps", ""),
            "add": info.get("add", ""),
            "port": info.get("port", ""),
            "id": info.get("id", ""),
            "net": info.get("net", ""),
            "type": info.get("type", ""),
            "raw": line,
        })
    except Exception as e:
        print(f"  [{i}] decode err: {e}")

print(f"成功解析 vmess 节点: {len(nodes)}\n")
print("=" * 90)
for n in nodes:
    print(f"  #{n['idx']:>2}  ps={n['ps'][:40]:<42}  {n['add']:<28} :{n['port']:<5} net={n['net']}")

# 筛美国
def is_us(n):
    s = (n["ps"] + " " + n["add"]).lower()
    return any(k in s for k in ["us", "美", "america", "united states",
                                 "los angeles", "san jose", "seattle",
                                 "new york", "dallas", "miami", "chicago",
                                 "🇺🇸"])

us = [n for n in nodes if is_us(n)]
print(f"\n美国节点: {len(us)} 个")
for n in us:
    print(f"  #{n['idx']:>2}  {n['ps']}  →  {n['add']}:{n['port']}  net={n['net']}")
