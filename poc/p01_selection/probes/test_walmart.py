"""确认 botasaurus 是否真的拿到 Walmart 商品（提取标题+价格验证）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from botasaurus.browser import browser, Driver


@browser(headless=True, block_images=True)
def grab_walmart(driver: Driver, data):
    url = "https://www.walmart.com/search?q=wireless+earbuds"
    driver.google_get(url, bypass_cloudflare=True)
    driver.sleep(5)
    # 滚动加载
    for _ in range(3):
        driver.run_js("window.scrollBy(0, 2000)")
        driver.sleep(1)
    html = driver.page_html
    Path("poc/01-选品/probes/captured/walmart.html").write_text(html, encoding="utf-8")
    print(f"saved walmart.html: {len(html):,} bytes")

    # 用多种选择器试探真实商品卡
    for sel in ["div[data-item-id]", "div[data-testid='item-stack'] > div",
                "a[link-identifier]", "[data-testid='list-view'] > div"]:
        try:
            els = driver.select_all(sel, wait=3)
            print(f"  selector {sel!r}: {len(els) if els else 0} hits")
        except Exception as e:
            print(f"  selector {sel!r}: error {str(e)[:60]}")

    # 提取前 3 个商品标题
    try:
        titles = driver.run_js("""
            return Array.from(document.querySelectorAll('span[data-automation-id=\"product-title\"]'))
                        .slice(0,5).map(e => e.innerText);
        """)
        print("  titles:", titles)
    except Exception as e:
        print("  title extract error:", str(e)[:80])
    return {"bytes": len(html)}


if __name__ == "__main__":
    grab_walmart()
