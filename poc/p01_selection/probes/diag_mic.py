"""诊断 Made-in-China selector"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.scraper import fetch
from bs4 import BeautifulSoup

url = "https://www.made-in-china.com/products-search/hot-china-products/yoga_mat.html"
html = fetch(url, use_proxy=False, force_browser=True)
print(f"HTML: {len(html)}")

soup = BeautifulSoup(html, "lxml")

# 找含 "US$" 的元素
for sel in ["div.list-node", ".product-item", "[class*='product']", "[class*='Product']",
             "li[class*='product']", "div.searchprodtable", "div.gallery-item",
             "div.J-product-list-item", "[class*='item'][class*='card']"]:
    cards = soup.select(sel)
    if cards:
        print(f"  {sel}: {len(cards)} 个")

# 再找 US$ 文字附近的元素
import re
m = re.search(r'US\$', html)
if m:
    pos = m.start()
    snippet = html[max(0, pos-300):pos+100]
    print(f"\n第一个 US$ 位置: {pos}")
    print(f"附近 html: {snippet}")

Path("mic_dump.html").write_text(html[:500000], encoding="utf-8")
print("\nmic_dump.html 已存")
