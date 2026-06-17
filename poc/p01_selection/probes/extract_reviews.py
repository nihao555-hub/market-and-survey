"""从详情页 HTML 提取真实评论"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from botasaurus_driver import Driver
from bs4 import BeautifulSoup

PROXY = "http://127.0.0.1:10808"
ASIN = "B0DGHMNQ5Z"
url = f"https://www.amazon.com/dp/{ASIN}"

driver = Driver(headless=True, block_images=True, proxy=PROXY)
try:
    driver.google_get(url, bypass_cloudflare=True)
    driver.sleep(4)
    # 滚到评论区域促发懒加载
    driver.run_js("""
      const el = document.querySelector('[data-hook=\"reviews-medley-footer\"]') ||
                 document.querySelector('#reviewsMedley') ||
                 document.querySelector('#cm-cr-dp-review-list') ||
                 document.querySelector('[data-hook=\"top-customer-reviews-widget\"]');
      if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
      else window.scrollBy(0, 6000);
    """)
    driver.sleep(2)
    for _ in range(6):
        driver.run_js("window.scrollBy(0, 1200)")
        driver.sleep(0.6)
    # 再回到评论区
    driver.run_js("""
      const el = document.querySelector('#reviewsMedley') || document.querySelector('[data-hook=\"top-customer-reviews-widget\"]');
      if (el) el.scrollIntoView({behavior: 'instant', block: 'start'});
    """)
    driver.sleep(3)
    html = driver.page_html
finally:
    driver.close()

soup = BeautifulSoup(html, "lxml")
print(f"bytes = {len(html)}")
print(f"title = {soup.title.text.strip()[:80]}\n")

# 评论
print("=" * 80)
print("【真实评论 from 详情页】")
print("=" * 80)
reviews = soup.select("[data-hook='review']")
for i, r in enumerate(reviews, 1):
    rating_node = r.select_one("i[data-hook='review-star-rating'] span") or r.select_one("i.a-icon-star span")
    rating = rating_node.get_text(strip=True) if rating_node else "?"
    title_node = r.select_one("a[data-hook='review-title']") or r.select_one("[data-hook='review-title']")
    title = title_node.get_text(" ", strip=True) if title_node else ""
    body_node = r.select_one("[data-hook='review-body']")
    body = body_node.get_text(" ", strip=True) if body_node else ""
    date_node = r.select_one("[data-hook='review-date']")
    date = date_node.get_text(strip=True) if date_node else ""
    print(f"\n#{i}  [{rating}]  {date}")
    print(f"  标题: {title[:80]}")
    print(f"  正文: {body[:200]}")

# AI summary
print("\n" + "=" * 80)
print("【AI 评论摘要】")
print("=" * 80)
for sel in ["#product-summary", "[data-hook='cr-summarization-attributes-list']",
            "[data-hook='cr-insights-widget']", "[data-hook*='insights']"]:
    el = soup.select_one(sel)
    if el:
        print(f"\n[{sel}]")
        print(el.get_text(" | ", strip=True)[:600])
