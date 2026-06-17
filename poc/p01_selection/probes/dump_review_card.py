"""dump 一个 review 卡片的完整 HTML 看真实结构"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from botasaurus_driver import Driver
from bs4 import BeautifulSoup

PROXY = "http://127.0.0.1:10808"
ASIN = "B0DGHMNQ5Z"

driver = Driver(headless=True, block_images=True, proxy=PROXY)
try:
    driver.google_get(f"https://www.amazon.com/dp/{ASIN}", bypass_cloudflare=True)
    driver.sleep(4)
    driver.run_js("window.scrollTo(0, 8000)")
    driver.sleep(3)
    driver.run_js("window.scrollTo(0, 12000)")
    driver.sleep(3)
    html = driver.page_html
finally:
    driver.close()

Path("poc/01-选品/probes/captured/airpods4_dp.html").write_text(html, encoding="utf-8")
print(f"saved {len(html)} bytes")

soup = BeautifulSoup(html, "lxml")
cards = soup.select("[data-hook='review']")
print(f"reviews count: {len(cards)}")

if cards:
    print("\n=== 第一个 review 卡片完整 HTML（前 3000 字符） ===\n")
    print(str(cards[0])[:3000])
