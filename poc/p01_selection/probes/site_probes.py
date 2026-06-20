"""
真实主流跨境电商站点连通性 Probe（v2）
引擎：Scrapling(http) → curl_cffi → patchright(浏览器/反检测) → pydoll(浏览器/反检测)
打印中间流程：发请求 → 状态码 → 字节数 → 反爬识别 → 解析卡片数 → 示例
"""

from __future__ import annotations
import asyncio, sys, time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="DEBUG",
           format="<green>{time:HH:mm:ss}</green>|<level>{level:<7}</level>|<cyan>{extra[site]:<10}</cyan>|<yellow>{extra[engine]:<11}</yellow>| {message}")
logger = logger.bind(site="-", engine="-")


@dataclass
class ProbeResult:
    site: str
    url: str
    engine: str
    ok: bool = False
    status: int | None = None
    bytes_or_chars: int = 0
    elapsed_ms: int = 0
    blocked_reason: str = ""
    products_found: int = 0
    sample_title: str = ""


SITES = [
    {"name": "Amazon",
     "url": "https://www.amazon.com/s?k=wireless+earbuds&ref=nb_sb_noss",
     "card_selector": "div[data-component-type='s-search-result']",
     "title_selector": "h2 span"},
    {"name": "eBay",
     "url": "https://www.ebay.com/sch/i.html?_nkw=wireless+earbuds",
     "card_selector": "li.s-item",
     "title_selector": ".s-item__title"},
    {"name": "Walmart",
     "url": "https://www.walmart.com/search?q=wireless+earbuds",
     "card_selector": "div[data-item-id]",
     "title_selector": "span[data-automation-id='product-title']"},
    {"name": "AliExpress",
     "url": "https://www.aliexpress.com/w/wholesale-wireless-earbuds.html",
     "card_selector": "a.search-card-item, div[class*='SearchProductFeed'] a, a[href*='/item/']",
     "title_selector": "h3, [class*='title']"},
    {"name": "Etsy",
     "url": "https://www.etsy.com/search?q=wireless+earbuds",
     "card_selector": "li[data-search-product-id], div.v2-listing-card",
     "title_selector": "h3"},
    {"name": "Temu",
     "url": "https://www.temu.com/search_result.html?search_key=wireless+earbuds",
     "card_selector": "[class*='listItem-'], [class*='item-2khyy']",
     "title_selector": "h2, h3, [class*='title-'], img[alt]"},
    {"name": "Shopee",
     "url": "https://shopee.sg/search?keyword=wireless%20earbuds",
     "card_selector": "li.shopee-search-item-result__item, div[data-sqe='item']",
     "title_selector": "div[class*='title'], div._10Wbs-"},
    {"name": "BestBuy",
     "url": "https://www.bestbuy.com/site/searchpage.jsp?st=wireless+earbuds",
     "card_selector": "li.sku-item, div.sku-item",
     "title_selector": "h4.sku-title, .sku-title a"},
]


# ---------- 引擎 1：Scrapling 普通 HTTP ----------
def probe_scrapling(url: str, log) -> tuple[Optional[str], dict]:
    info = {"engine": "Scrapling"}
    log.debug(f"→ GET {url}")
    try:
        from scrapling.fetchers import Fetcher
        page = Fetcher.get(url, timeout=20)
        info["status"] = getattr(page, "status", None)
        body = page.body if hasattr(page, "body") else None
        info["bytes"] = len(body) if body else 0
        log.debug(f"← status={info['status']} bytes={info['bytes']}")
        return (body if info["status"] == 200 else None), info
    except Exception as e:
        log.debug(f"✗ {e}")
        info["error"] = str(e)[:200]
        return None, info


# ---------- 引擎 2：curl_cffi（TLS 指纹） ----------
def probe_curl_cffi(url: str, log) -> tuple[Optional[str], dict]:
    info = {"engine": "curl_cffi"}
    log.debug(f"→ GET {url} (impersonate=chrome120)")
    try:
        from curl_cffi import requests as cc
        r = cc.get(url, impersonate="chrome120", timeout=20,
                   headers={"Accept-Language": "en-US,en;q=0.9"})
        info["status"] = r.status_code
        info["bytes"] = len(r.text) if r.text else 0
        log.debug(f"← status={r.status_code} bytes={info['bytes']}")
        return (r.text if r.status_code == 200 else None), info
    except Exception as e:
        log.debug(f"✗ {e}")
        info["error"] = str(e)[:200]
        return None, info


# ---------- 引擎 3：patchright（Playwright 反检测补丁版） ----------
def probe_patchright(url: str, log) -> tuple[Optional[str], dict]:
    info = {"engine": "patchright"}
    log.debug(f"→ Browser GET {url} (patchright/stealth)")
    try:
        from patchright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 800},
                locale="en-US",
            )
            page = context.new_page()
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # 滚动促发懒加载（Temu/AliExpress 必需）
            for _ in range(4):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(700)
            page.wait_for_timeout(2000)
            html = page.content()
            status = resp.status if resp else None
            info["status"] = status
            info["bytes"] = len(html) if html else 0
            log.debug(f"← status={status} bytes={info['bytes']}")
            browser.close()
            return (html if html and status and status < 400 else None), info
    except Exception as e:
        log.debug(f"✗ {e}")
        info["error"] = str(e)[:200]
        return None, info


# ---------- 引擎 4：pydoll（无 webdriver, 反检测 CDP） ----------
async def _pydoll_async(url: str, log) -> tuple[Optional[str], dict]:
    info = {"engine": "pydoll"}
    log.debug(f"→ CDP Browser GET {url} (pydoll)")
    try:
        from pydoll.browser.chromium import Chrome
        from pydoll.browser.options import ChromiumOptions
        opts = ChromiumOptions()
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        async with Chrome(options=opts) as browser:
            tab = await browser.start()
            await tab.go_to(url)
            await asyncio.sleep(3)
            html = await tab.page_source
            info["status"] = 200 if html else None
            info["bytes"] = len(html) if html else 0
            log.debug(f"← bytes={info['bytes']}")
            return html, info
    except Exception as e:
        log.debug(f"✗ {e}")
        info["error"] = str(e)[:200]
        return None, info


def probe_pydoll(url: str, log):
    return asyncio.run(_pydoll_async(url, log))


# ---------- 反爬识别 ----------
def detect_block(html: str) -> str:
    if not html:
        return "empty response"
    h = html[:8000].lower()
    flags = {
        "cloudflare": ["cf-chl-", "challenge-platform", "cloudflare ray id"],
        "amazon-robot-check": ["robot check", "/errors/validatecaptcha"],
        "perimeterx": ["px-captcha", "_pxhd"],
        "datadome": ["datadome", "geo.captcha-delivery.com"],
        "captcha-cn": ["请输入验证码"],
        "alibaba-nc-captcha": ["captcha interception", "nc-container", "nc_iconfont"],
        "walmart-blocked": ["/blocked", "request unsuccessful"],
        "access-denied": ["access denied", "request blocked"],
    }
    for name, keys in flags.items():
        if any(k in h for k in keys):
            return name
    if len(html) < 2000:
        return f"too-small({len(html)})"
    return ""


# ---------- 选择器解析 ----------
def try_parse(html: str, card_sel: str, title_sel: str) -> tuple[int, str]:
    try:
        from scrapling.parser import Adaptor
        adp = Adaptor(html, url="https://x", auto_match=False)
        cards = adp.css(card_sel)
        n = len(cards)
        sample = ""
        if n:
            _r = cards[0].css(title_sel)
            t = _r[0] if _r else None
            if t is not None:
                sample = (t.text or t.attrib.get("title", "") or "")[:80].strip()
        return n, sample
    except Exception as e:
        return 0, ""


# ---------- 主流程 ----------
def run():
    results: list[ProbeResult] = []
    overall = logger.bind(site="*", engine="*")
    overall.info(f"Probe {len(SITES)} 个主流电商站")
    print("=" * 95)

    for s in SITES:
        slog = logger.bind(site=s["name"], engine="-")
        slog.info(f"━━ {s['url']}")

        engines = [
            ("Scrapling",  probe_scrapling),
            ("curl_cffi",  probe_curl_cffi),
            ("patchright", probe_patchright),
            ("pydoll",     probe_pydoll),
        ]
        succeeded = False
        for ename, fn in engines:
            elog = logger.bind(site=s["name"], engine=ename)
            t0 = time.time()
            html, info = fn(s["url"], elog)
            elapsed = int((time.time() - t0) * 1000)

            res = ProbeResult(site=s["name"], url=s["url"], engine=ename,
                              status=info.get("status"),
                              bytes_or_chars=info.get("bytes", 0),
                              elapsed_ms=elapsed)

            if html:
                blk = detect_block(html)
                if blk:
                    res.blocked_reason = blk
                    elog.warning(f"⚠ 被反爬：{blk}")
                else:
                    n, sample = try_parse(html, s["card_selector"], s["title_selector"])
                    res.products_found, res.sample_title = n, sample
                    if n > 0:
                        res.ok = True
                        elog.success(f"✓ 解析 {n} 卡，示例：{sample!r}")
                        succeeded = True
                    else:
                        elog.warning(f"⚠ 200 但选择器没匹配（结构变了/SPA 未渲染）")
            else:
                elog.warning(f"✗ 拉取失败 status={res.status} {info.get('error','')}")
            results.append(res)
            if succeeded:
                break
            time.sleep(1)

        slog.info("─" * 60)

    # 汇总
    print("\n" + "=" * 95)
    print(f"{'站点':<10} {'引擎':<11} {'状态':<6} {'字节':>9} {'耗时':>8} {'卡片':>5}  反爬/备注")
    print("-" * 95)
    by_site: dict[str, list[ProbeResult]] = {}
    for r in results:
        by_site.setdefault(r.site, []).append(r)
    success_sites = []
    for sname, rs in by_site.items():
        if any(r.ok for r in rs):
            success_sites.append(sname)
        for r in rs:
            mark = "✅" if r.ok else ("⚠️ " if r.blocked_reason else "❌")
            print(f"{r.site:<10} {r.engine:<11} {str(r.status or '-'):<6} "
                  f"{r.bytes_or_chars:>9} {r.elapsed_ms:>6}ms {r.products_found:>5}  "
                  f"{mark} {r.blocked_reason}")
    print("=" * 95)
    print(f"\n🎯 可直接获取的站：{', '.join(success_sites) or '（全失败，需配代理/FlareSolverr）'}")
    print(f"📌 不通过的站：{', '.join([n for n in (s['name'] for s in SITES) if n not in success_sites])}")
    return results, success_sites


if __name__ == "__main__":
    run()
