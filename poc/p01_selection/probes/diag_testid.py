"""用 data-testid 选择器精准定位 Customers say 区域"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reviews import _fetch_dp_with_review_loaded
from bs4 import BeautifulSoup

ASIN = "B0CRTR3PMF"
html = _fetch_dp_with_review_loaded(ASIN, use_proxy=True) or ""
print(f"size: {len(html)}")

soup = BeautifulSoup(html, "lxml")

# 1. 各 testid 命中数
print("\n=== data-testid 选择器命中 ===")
testids_seen = set()
for el in soup.find_all(attrs={"data-testid": True}):
    testids_seen.add(el.get("data-testid"))

# 找含关键字的 testid
relevant_testids = [t for t in testids_seen if any(k in t.lower() for k in
                     ["summary", "aspect", "insight", "topic", "heading", "review", "rating", "popular"])]
for t in sorted(relevant_testids):
    n = len(soup.select(f'[data-testid="{t}"]'))
    print(f"  [data-testid='{t}']: {n}")

# 2. 找 Customers say 标题及其父容器
print("\n=== Customers say 标题父容器 ===")
heading = soup.find("h3", string=lambda s: s and "Customers say" in s) or \
          soup.find("h3", attrs={"data-testid": "heading"})
if heading:
    parent = heading.parent
    print(f"  parent tag: {parent.name}, attrs: {parent.attrs}")
    # 取整个父容器的文本
    print(f"\n  父容器文本（前 1500）:")
    print(parent.get_text(" | ", strip=True)[:1500])

# 3. 找 overall-summary
overall = soup.select_one('[data-testid="overall-summary"]')
if overall:
    print(f"\n=== overall-summary 文本 ===")
    print(overall.get_text(" ", strip=True)[:1500])

# 4. 找 aspect summary（关键词云通常在这）
print("\n=== aspect/topic 候选 ===")
for sel in ['[data-testid*="aspect"]', '[data-testid*="topic"]',
             '[data-testid*="sentiment"]', 'button[data-testid]',
             '[role="button"][data-testid]']:
    nodes = soup.select(sel)
    if nodes:
        print(f"  {sel}: {len(nodes)}")
        for n in nodes[:5]:
            t = n.get_text(strip=True)
            if t:
                print(f"    - {n.get('data-testid'):<35} {t[:80]}")
