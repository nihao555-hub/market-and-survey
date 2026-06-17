"""勘察 Amazon 详情页 Customers say 区块的真实选择器"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reviews import _fetch_dp_with_review_loaded
from bs4 import BeautifulSoup

ASIN = "B0DGHMNQ5Z"  # AirPods 4
html = _fetch_dp_with_review_loaded(ASIN, use_proxy=True)
print(f"size: {len(html or '')}")

if html:
    soup = BeautifulSoup(html, "lxml")

    # 1. 找含 "Customers say" 文本的元素
    print("\n=== 'Customers say' 出现位置 ===")
    for el in soup.find_all(string=lambda s: s and "Customers say" in s):
        parent = el.parent
        cls = " ".join(parent.get("class", []))
        dh = parent.get("data-hook", "")
        print(f"  parent <{parent.name} class='{cls[:50]}' hook='{dh}'>: {el.strip()[:150]}")

    # 2. 找带 "insight" 的 hook
    print("\n=== data-hook 含 insight/summary/rating ===")
    for el in soup.find_all(attrs={"data-hook": True}):
        dh = el.get("data-hook", "")
        if any(k in dh.lower() for k in ["insight", "summary", "rating-summary", "popular-topic", "lighthouse"]):
            cls = " ".join(el.get("class", []))
            text = el.get_text(" ", strip=True)[:200]
            print(f"  <{el.name} hook='{dh}' class='{cls[:40]}'>: {text}")

    # 3. 找 popular topics（关键词云）
    print("\n=== 含 cr-pl/customer-attribute/lighthouse 的元素 ===")
    for sel in ["[class*='_lighthouse_']", "[class*='cr-product-insights']",
                 "div[id*='cr-summarization']", "[data-hook*='cr-']",
                 "[class*='product-insights']"]:
        nodes = soup.select(sel)
        if nodes:
            print(f"  {sel}: {len(nodes)}")
            for n in nodes[:3]:
                t = n.get_text(" | ", strip=True)[:200]
                print(f"    {t}")
