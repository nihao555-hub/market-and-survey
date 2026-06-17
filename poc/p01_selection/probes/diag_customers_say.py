"""
诊断 Amazon 详情页 "Customers say" / 关键词云的真实结构（2026 版）。
对多个 ASIN 抓全文 + 详细勘察 DOM。
"""
import sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reviews import _fetch_dp_with_review_loaded
from bs4 import BeautifulSoup

# 选高 review 量的真品（更可能有 AI summary）
ASINS = [
    ("B0DGHMNQ5Z", "Apple AirPods 4"),
    ("B0CRTR3PMF", "Soundcore P30i"),
    ("B07RGZ5NKS", "TOZO T6"),
    ("B0C3HCD34R", "Soundcore Q20i"),
]

OUT = Path(__file__).resolve().parents[1] / "reports" / "diag_customers_say.md"
buf = ["# Customers say 区域诊断（2026 版 Amazon DOM）\n"]

for asin, name in ASINS:
    buf.append(f"\n## ASIN={asin} ({name})\n")
    html = _fetch_dp_with_review_loaded(asin, use_proxy=True)
    if not html:
        buf.append(f"- ⚠ 抓不到页面")
        continue
    buf.append(f"- 页面大小: {len(html):,} bytes")

    # 1. 关键字符串扫描
    keywords = [
        "Customers say", "customers-say", "cr-product-insights",
        "cr-summarization", "lighthouse", "review-data-snippet",
        "product-summary", "product-faceouts", "gpt-summarized",
        "cr-insights-widget", "cm_cr_dpinsights", "review-keyword",
        "PRODUCT_INSIGHTS",
    ]
    found_keys = [k for k in keywords if k in html]
    buf.append(f"- 命中关键字: {found_keys or '无'}")

    soup = BeautifulSoup(html, "lxml")

    # 2. 全部 data-hook 列举（找带 review/insight/summary 的）
    hooks = set()
    for el in soup.find_all(attrs={"data-hook": True}):
        hooks.add(el.get("data-hook"))
    relevant = sorted([h for h in hooks if any(k in h.lower() for k in
                       ["review", "insight", "summar", "rating", "popular", "lighthouse"])])
    buf.append(f"- 相关 data-hook ({len(relevant)}):")
    for h in relevant:
        buf.append(f"  - `{h}`")

    # 3. 找含 popular topic / 标签云相关 id
    ids_relevant = []
    for el in soup.find_all(id=True):
        i = el.get("id", "")
        if any(k in i.lower() for k in ["insight", "summar", "lighthouse", "review", "topic"]):
            ids_relevant.append(i)
    buf.append(f"- 相关 id (前 20):")
    for i in sorted(set(ids_relevant))[:20]:
        buf.append(f"  - `{i}`")

    # 4. 实测各候选选择器
    buf.append(f"- 选择器命中数:")
    for sel in [
        "[data-hook='cr-summary-snapshot']",
        "[data-hook*='cr-product-insights']",
        "[data-hook='cr-insights-widget']",
        "[data-hook='cr-helpful-text']",
        "div#cr-summarization",
        "div[id*='product-insights']",
        "div[id*='cr-insights']",
        "section[data-hook='cr-product-insights']",
        "[class*='_lighthouse_']",
        "[class*='cr-product-insights']",
        "div.cr-helpful-button",
        "div[data-hook='review']",
        "[data-hook='review-helpful-question']",
        "div#histogramTable",
    ]:
        n = len(soup.select(sel))
        if n > 0:
            buf.append(f"  - `{sel}`: {n}")

    # 5. 找到的关键 block 完整 dump 头 800 字符
    block = (soup.select_one("[data-hook*='cr-product-insights']")
              or soup.select_one("div[id*='product-insights']")
              or soup.select_one("[data-hook='cr-summary-snapshot']"))
    if block:
        buf.append(f"\n```html\n{str(block)[:1200]}\n```")

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"✅ 写入 {OUT} ({OUT.stat().st_size} bytes)")
