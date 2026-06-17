"""强力突破 Amazon 评论页登录限制的实测"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from botasaurus_driver import Driver
from bs4 import BeautifulSoup

PROXY = "http://127.0.0.1:10808"
ASIN = "B0DGHMNQ5Z"  # Apple AirPods 4 (从 BSR Top 看到的)

# 试 3 种 URL 方案
URLS = [
    ("详情页", f"https://www.amazon.com/dp/{ASIN}"),
    ("评论页主URL", f"https://www.amazon.com/product-reviews/{ASIN}/"),
    ("含 see-all", f"https://www.amazon.com/product-reviews/{ASIN}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"),
]

for label, url in URLS:
    print(f"\n━━━ {label} ━━━ {url}")
    driver = Driver(headless=True, block_images=True, proxy=PROXY)
    try:
        driver.google_get(url, bypass_cloudflare=True)
        driver.sleep(5)
        # 滚动几次
        for _ in range(3):
            driver.run_js("window.scrollBy(0, 1500)")
            driver.sleep(0.8)
        html = driver.page_html
        size = len(html or "")
        print(f"  bytes = {size}")

        soup = BeautifulSoup(html, "lxml")
        title = soup.title.text.strip()[:80] if soup.title else "?"
        print(f"  title: {title!r}")

        # 看是否登录墙
        txt = (html or "")[:5000].lower()
        if "sign-in" in txt or "sign in" in txt or "this site requires javascript" in txt:
            print("  ⚠ 命中登录墙关键词")

        # 多种评论选择器尝试
        for sel in ["[data-hook='review']", "div[data-hook='review-collapsed']",
                    "li[data-hook='review']", "[data-hook='cr-product-insights-summary']",
                    "#cm-cr-dp-review-list", "#cm_cr-review_list",
                    "[data-hook='top-customer-reviews-widget']",
                    "div.review-text-content"]:
            n = len(soup.select(sel))
            if n > 0:
                print(f"  ✅ {sel}: {n}")
        # 检查 ai 摘要
        for sel in ["#product-summary", "[data-hook='cr-summarization-attributes-list']"]:
            el = soup.select_one(sel)
            if el:
                t = el.get_text(" ", strip=True)
                if t:
                    print(f"  📝 {sel}: {t[:120]}")
    finally:
        try: driver.close()
        except Exception: pass
