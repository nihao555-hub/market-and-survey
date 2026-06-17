"""
用 botasaurus（最强开源反检测框架之一）实测能否过之前失败的站点。
botasaurus 自带：真实指纹、绕过 Cloudflare、google-referer 等高级反检测。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from botasaurus.browser import browser, Driver

TARGETS = [
    ("eBay", "https://www.ebay.com/sch/i.html?_nkw=wireless+earbuds", "li.s-item, .s-card"),
    ("Walmart", "https://www.walmart.com/search?q=wireless+earbuds", "div[data-item-id]"),
    ("BestBuy", "https://www.bestbuy.com/site/searchpage.jsp?st=wireless+earbuds", "li.sku-item"),
]


@browser(
    headless=True,
    block_images=True,
    reuse_driver=True,
)
def probe(driver: Driver, data):
    name, url, sel = data["name"], data["url"], data["sel"]
    result = {"site": name, "ok": False, "info": ""}
    try:
        driver.google_get(url, bypass_cloudflare=True)  # 关键：以 google 为 referer + 过 CF
        driver.sleep(4)
        html = driver.page_html
        size = len(html) if html else 0
        # 检测验证码/拦截
        low = (html[:8000] or "").lower()
        blocked = any(k in low for k in ["captcha", "robot check", "access denied", "/blocked", "datadome", "pardon our interruption"])
        # 数选择器命中数
        try:
            els = driver.select_all(sel, wait=5)
            n = len(els) if els else 0
        except Exception:
            n = 0
        result["info"] = f"bytes={size} blocked={blocked} cards={n}"
        result["ok"] = (n > 0 and not blocked)
        print(f"[{name}] {result['info']}  => {'OK' if result['ok'] else 'FAIL'}")
    except Exception as e:
        result["info"] = f"error: {str(e)[:150]}"
        print(f"[{name}] {result['info']}")
    return result


if __name__ == "__main__":
    items = [{"name": n, "url": u, "sel": s} for n, u, s in TARGETS]
    probe(items)
