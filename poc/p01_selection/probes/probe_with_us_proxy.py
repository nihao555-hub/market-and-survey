"""
带美国代理 + botasaurus，重测之前过不去的站点。
策略：浏览器只负责拉 HTML，离线用 bs4 分析多种选择器，避免 wait 阻塞。
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from botasaurus.browser import browser, Driver
from bs4 import BeautifulSoup

PROXY = "http://127.0.0.1:10808"
CAP = Path(__file__).resolve().parent / "captured"
CAP.mkdir(exist_ok=True)

TARGETS = [
    ("eBay",       "https://www.ebay.com/sch/i.html?_nkw=wireless+earbuds",
     ["li.s-item__pl-on-bp", "li.s-item", ".s-card"]),
    ("BestBuy",    "https://www.bestbuy.com/site/searchpage.jsp?st=wireless+earbuds",
     ["li.sku-item", "li.product-list-item"]),
    ("Etsy",       "https://www.etsy.com/search?q=wireless+earbuds",
     ["li[data-search-product-id]", "div.v2-listing-card", "[data-listing-id]"]),
    ("AliExpress", "https://www.aliexpress.com/w/wholesale-wireless-earbuds.html",
     ["a.search-card-item", "a[href*='/item/']"]),
]


@browser(headless=True, block_images=True, proxy=PROXY, reuse_driver=True,
         wait_for_complete_page_load=False)
def grab(driver: Driver, data):
    name, url = data["name"], data["url"]
    print(f"\n━━━ {name} ━━━ {url}", flush=True)
    try:
        driver.google_get(url, bypass_cloudflare=True)
        driver.sleep(4)
        driver.run_js("window.scrollBy(0, 2000)")
        driver.sleep(1)
        driver.run_js("window.scrollBy(0, 2000)")
        driver.sleep(1)
        html = driver.page_html
        (CAP / f"{name.lower()}_us.html").write_text(html or "", encoding="utf-8")
        print(f"  saved bytes={len(html or '')}", flush=True)
        return {"name": name, "html_len": len(html or "")}
    except Exception as e:
        print(f"  error: {str(e)[:200]}", flush=True)
        return {"name": name, "error": str(e)[:200]}


def analyze(name: str, sels: list[str]):
    p = CAP / f"{name.lower()}_us.html"
    if not p.exists():
        return {"site": name, "ok": False, "reason": "no html captured"}
    html = p.read_text(encoding="utf-8", errors="ignore")
    low = html[:8000].lower()
    blocked = ""
    if "captcha" in low and ("interception" in low or "punish" in low):
        blocked = "alibaba-nc"
    elif "datadome" in low or "geo.captcha-delivery" in low:
        blocked = "datadome"
    elif "/blocked" in low or "request unsuccessful" in low or "pardon our interruption" in low:
        blocked = "blocked-page"
    elif "robot check" in low:
        blocked = "amazon-robot"
    if len(html) < 3000:
        blocked = blocked or f"too-small({len(html)})"

    soup = BeautifulSoup(html, "lxml")
    title = soup.title.text.strip()[:80] if soup.title else "?"
    best_sel, best_n, sample = None, 0, ""
    for s in sels:
        try:
            cards = soup.select(s)
            if len(cards) > best_n:
                best_n = len(cards)
                best_sel = s
                if cards:
                    txt = cards[0].get_text(" ", strip=True)[:80]
                    sample = txt
        except Exception:
            pass
    return {"site": name, "title": title, "bytes": len(html),
            "blocked": blocked, "cards": best_n, "sel": best_sel, "sample": sample,
            "ok": best_n > 0 and not blocked}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    items = [{"name": n, "url": u, "sels": s} for n, u, s in TARGETS]
    # 如果 captured/ 已经有了，跳过重抓（避免每次都拉浏览器）
    has_all = all((CAP / f"{n.lower()}_us.html").exists() for n, _, _ in TARGETS)
    if not has_all:
        grab(items)
    print("\n" + "=" * 80)
    print("解析结果：")
    print("=" * 80)
    for n, u, s in TARGETS:
        r = analyze(n, s)
        mark = "[OK]" if r["ok"] else ("[BLK]" if r.get("blocked") else "[NF]")
        print(f"\n{mark} {r['site']:<11} title={r.get('title','')[:50]!r}")
        print(f"   bytes={r['bytes']}  blocked={r.get('blocked','no')}  "
              f"cards={r['cards']} sel={r.get('sel')}")
        if r.get("sample"):
            print(f"   sample: {r['sample']}")
