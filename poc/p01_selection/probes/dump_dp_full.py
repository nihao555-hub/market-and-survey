"""dump 详情页全文找关键词云的位置"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reviews import _fetch_dp_with_review_loaded
from bs4 import BeautifulSoup

ASIN = "B0DGHMNQ5Z"
html = _fetch_dp_with_review_loaded(ASIN, use_proxy=True) or ""
out = Path("poc/01-选品/probes/captured/airpods4_dp_full.html")
out.parent.mkdir(exist_ok=True)
out.write_text(html, encoding="utf-8")
print(f"saved {len(html)} bytes")
print(f"contains 'Customers say': {'Customers say' in html}")
print(f"contains 'cr-product-insights': {'cr-product-insights' in html}")
print(f"contains 'lighthouse': {'lighthouse' in html.lower()}")
print(f"contains 'review-data-snippet': {'review-data-snippet' in html}")
print(f"contains 'cr-summarization': {'cr-summarization' in html}")
print(f"contains 'product-summary': {'product-summary' in html}")
print(f"contains 'review-keyword': {'review-keyword' in html}")

# 找所有以 "say" 结尾的标签内容
import re
for kw in ["Customers say", "Pros mentioned", "Cons mentioned", "What customers say"]:
    matches = re.findall(rf"({re.escape(kw)}[^<]{{0,200}})", html)
    if matches:
        print(f"\n'{kw}' 出现:")
        for m in matches[:3]:
            print(f"  {m[:200]}")
