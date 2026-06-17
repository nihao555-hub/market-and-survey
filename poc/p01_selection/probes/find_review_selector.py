"""找 Amazon 评论页的真实选择器"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch
from bs4 import BeautifulSoup

# Apple AirPods 4 ASIN（榜单上看到的）
url = "https://www.amazon.com/product-reviews/B0DGHMNQ5Z/?pageNumber=1&filterByStar=critical&sortBy=recent"
html = fetch(url, use_proxy=True, force_browser=True)
print(f"page bytes: {len(html)}")

soup = BeautifulSoup(html, "lxml")
print(f"\n--- 试常见评论选择器 ---")
for sel in ["[data-hook='review']", "li[data-hook='review']", "div[data-hook='review']",
            "div.review", "div[id^='customer_review']", "[data-hook='review-collapsed']"]:
    n = len(soup.select(sel))
    print(f"  {sel}: {n}")

# 找到任何 [data-hook] 节点列出
print("\n--- 含 data-hook 的元素 ---")
seen = set()
for el in soup.find_all(attrs={"data-hook": True}):
    dh = el.get("data-hook")
    if dh in seen: continue
    seen.add(dh)
    if len(seen) <= 30:
        print(f"  data-hook='{dh}'  tag={el.name}")

# 找含至少 50 字的段落
print("\n--- 长文本块（可能是评论body） ---")
count = 0
for el in soup.find_all(["p", "span", "div"]):
    if not el.get_text(strip=True):
        continue
    t = el.get_text(" ", strip=True)
    if 80 < len(t) < 500 and not el.find(True):
        cls = " ".join(el.get("class", []))
        dh = el.get("data-hook", "")
        print(f"  <{el.name} class='{cls[:40]}' data-hook='{dh}'>  {t[:80]}")
        count += 1
        if count >= 8:
            break
