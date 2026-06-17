"""1688 真实结构勘察"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch
from bs4 import BeautifulSoup

html = fetch("https://s.1688.com/selloffer/offer_search.htm?keywords=%E8%93%9D%E7%89%99%E8%80%B3%E6%9C%BA",
             use_proxy=False, force_browser=True)
print(f"size: {len(html)}")
Path("poc/01-选品/probes/captured/1688.html").write_text(html, encoding="utf-8")

soup = BeautifulSoup(html, "lxml")
print(f"title: {soup.title.text.strip()[:80]}")

# 找含 ¥ 的元素
import re
prices = re.findall(r'¥\s*\d+\.?\d*', html)
print(f"¥ 出现次数: {len(prices)}, 前 10: {prices[:10]}")

# 找含 "起批" "起订" 的元素
moqs = re.findall(r'\d+[件个套对]起批|\d+件起订|起订量[：: ]?\d+', html)
print(f"MOQ 出现: {len(moqs)}, 前 10: {moqs[:10]}")

# 找商品卡候选
for sel in ["div.offer-card-box", "div[class*='offer-card']",
            "a[href*='offer/']", "li[data-aplus-spm]",
            "div[class*='sm-offer']", "div[data-content='offerResult']"]:
    n = len(soup.select(sel))
    if n > 0:
        print(f"  {sel}: {n}")

# 看页面结构
container = soup.select_one("div[data-content='offerResult']") or soup.select_one("#sm-offer-list")
if container:
    print(f"\n找到容器: {container.name} class={container.get('class')}")
    children = list(container.children)
    print(f"子元素数: {len(children)}")
