"""诊断 Walmart 真实 DOM 结构，找到当前能用的 selector"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.scraper import fetch
from scrapling.parser import Adaptor
import re

url = "https://www.walmart.com/search?q=wireless+earbuds"
html = fetch(url, use_proxy=True, force_browser=True)
print(f"HTML 长度: {len(html)}")

# 检测是否是 blocked / robot / press-and-hold 页面
lower = html[:5000].lower()
if "press & hold" in lower or "verify you" in lower or "robot" in lower:
    print("⚠️ 触发 Walmart 反爬墙（press & hold）")
    Path("walmart_blocked.html").write_text(html[:50000], encoding="utf-8")
    print("已存 walmart_blocked.html 前 50KB")
    sys.exit()

# 看真实结构
adp = Adaptor(html, url=url, auto_match=False)

# 试多个 selector
candidates = [
    "div[data-item-id]",
    "div[data-testid='item-stack']",
    "div[data-testid='list-view']",
    "section[data-testid='item-stack']",
    "[data-item-id]",
    "div.mb1",
    "div[role='group']",
    "li[data-testid]",
]

for sel in candidates:
    cards = adp.css(sel)
    if cards:
        print(f"\n✅ {sel} → {len(cards)} 个")
        if len(cards) >= 3:
            c = cards[2]
            txt = c.get_all_text()[:300] if hasattr(c, 'get_all_text') else str(c)[:300]
            print(f"  样本: {txt}")
            break

# 找包含 "$" 的所有元素层级（找价格容器）
print("\n--- 查找含价格 $ 的区块 ---")
for m in re.finditer(r'\$\d+\.?\d*', html[:200000]):
    pos = m.start()
    snippet = html[max(0,pos-200):pos+50]
    # 提取最近的 data-* 属性
    attrs = re.findall(r'data-[\w-]+="[\w-]+"', snippet)
    if attrs:
        print(f"  pos={pos}  ${m.group()[:20]}  {attrs[-3:]}")
        break

# 存全文以便人工检查
Path("walmart_dump.html").write_text(html[:500000], encoding="utf-8")
print("\n已存 walmart_dump.html 前 500KB")
