"""
采集层：9 级降级冗余引擎链
按"成本/强度"排序，命中即止。所有引擎都参与，最大化鲁棒性。

L1  curl_cffi(TLS 指纹伪装)         最快无渲染
L2  Scrapling(自适应解析+stealth)    HTTP 层进阶
L3  patchright(Playwright 反检测)    SPA + 反检测中等强度
L4  pydoll(无 webdriver CDP)         反检测备用
L5  SeleniumBase(UC Mode)            综合反爬框架
L6  botasaurus(google_get + bypass)  反爬最强（攻 Walmart/AliExpress）
L7  camoufox(Firefox 反指纹)         浏览器内核级伪装（仅在已下载内核时启用）

代理：默认从 .env / 环境变量读 US_PROXY，否则用 127.0.0.1:10808（xray 启动后端口）
"""
from __future__ import annotations
import os
from typing import Optional, Callable
from loguru import logger

DEFAULT_PROXY = os.getenv("US_PROXY") or "http://127.0.0.1:10808"


# 反爬墙特征：拿到这些页面说明被反爬挡了，必须丢弃，不能假装成功
BLOCKED_SIGNS = [
    "press & hold", "robot or human", "px-captcha",
    "access denied", "verify you are human",
    "captcha interception", "请完成下方验证",
    "datadome", "are you a robot",
    "我们要确认您不是机器人",
    "bm-verify",  # Akamai bot manager
    "triggerinterstitialchallenge",  # Amazon Akamai 验证
    "/_sec/verify",  # Amazon 子链路验证
]


def is_blocked_page(html: str) -> tuple[bool, str]:
    """检测是否反爬页面。返回 (是否, 命中关键词)"""
    if not html or len(html) < 100:
        return False, ""
    lower = html[:8000].lower()
    for sign in BLOCKED_SIGNS:
        if sign in lower:
            return True, sign
    # Walmart 特征：HTML < 30KB 且 title 含 robot
    if len(html) < 30000 and "<title>robot" in lower:
        return True, "robot_title_short_html"
    # Amazon 特征：HTML < 5KB 且含 meta refresh（Akamai 跳转挑战）
    if len(html) < 5000 and "amazon" in lower and "meta http-equiv=\"refresh\"" in lower:
        return True, "amazon_short_html_refresh"
    return False, ""


class FetchFailed(Exception):
    pass


# ─────────────────────────── L1: curl_cffi ───────────────────────────
def fetch_with_curl_cffi(url: str, proxy: Optional[str] = None) -> Optional[str]:
    try:
        from curl_cffi import requests as cc
        kw = {"impersonate": "chrome120", "timeout": 20,
              "headers": {"Accept-Language": "en-US,en;q=0.9"}}
        if proxy:
            kw["proxies"] = {"http": proxy, "https": proxy}
        r = cc.get(url, **kw)
        if r.status_code == 200 and r.text and len(r.text) > 1000:
            blocked, sign = is_blocked_page(r.text)
            if blocked:
                logger.warning(f"[L1 curl_cffi] 拿到 {len(r.text)} chars 但是 blocked ({sign})，丢弃")
                return None
            logger.info(f"[L1 curl_cffi] OK {len(r.text)} chars")
            return r.text
    except Exception as e:
        logger.debug(f"[L1 curl_cffi] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L2: Scrapling ───────────────────────────
def fetch_with_scrapling(url: str, proxy: Optional[str] = None) -> Optional[str]:
    try:
        from scrapling.fetchers import Fetcher
        kw = {"timeout": 20}
        if proxy:
            kw["proxy"] = proxy
        page = Fetcher.get(url, **kw)
        if page and page.status == 200 and page.body and len(page.body) > 1000:
            logger.info(f"[L2 Scrapling] OK {len(page.body)} bytes")
            return page.body
    except Exception as e:
        logger.debug(f"[L2 Scrapling] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L2.5: crawl4ai（Scrapling 的回退，AI 友好渲染获取）───────────────────────────
def fetch_with_crawl4ai(url: str, proxy: Optional[str] = None) -> Optional[str]:
    """
    用 crawl4ai 渲染获取（内置 Playwright + 反检测 + 自动等待）。
    作为 Scrapling(L2) 之后、重浏览器引擎(L3+)之前的一层回退。
    返回渲染后的完整 HTML（crawl4ai 的 result.html），失败返回 None。
    """
    try:
        import asyncio
        from crawl4ai import AsyncWebCrawler

        async def _run():
            kw = {"verbose": False, "headless": True}
            if proxy:
                kw["proxy"] = proxy
            async with AsyncWebCrawler(**kw) as crawler:
                # 等页面网络空闲 + 给 SPA 留渲染时间
                result = await crawler.arun(
                    url=url,
                    page_timeout=45000,
                    wait_until="networkidle",
                    delay_before_return_html=3.0,
                    scan_full_page=True,
                )
                # 优先要原始渲染 HTML（含商品卡），markdown 作兜底
                return getattr(result, "html", None) or getattr(result, "cleaned_html", None) or ""

        html = asyncio.run(_run())
        if html and len(html) > 3000:
            blocked, sign = is_blocked_page(html)
            if blocked:
                logger.warning(f"[L2.5 crawl4ai] 拿到 {len(html)} chars 但是 blocked ({sign})，丢弃")
                return None
            logger.info(f"[L2.5 crawl4ai] OK {len(html)} chars (render)")
            return html
    except Exception as e:
        logger.debug(f"[L2.5 crawl4ai] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L3: patchright ───────────────────────────
def fetch_with_patchright(url: str, proxy: Optional[str] = None,
                          wait_ms: int = 6000,
                          wait_for_selector: Optional[str] = None) -> Optional[str]:
    """
    完整渲染获取：① domcontentloaded → ② 等 networkidle → ③ 多次滚动触发懒加载 →
    ④ 可选等待关键 selector → ⑤ 等额外 wait_ms → ⑥ 抓完整 HTML（不截断）

    僵尸进程防护：browser 用 try/finally 强制 close，异常也不残留 chrome。
    SPA 站点（Yandex/MercadoLibre/Shopee）默认等 6s + 滚动，给足渲染时间。
    """
    try:
        from patchright.sync_api import sync_playwright
        with sync_playwright() as p:
            launch_kw = {"headless": True}
            if proxy:
                launch_kw["proxy"] = {"server": proxy}
            browser = p.chromium.launch(**launch_kw)
            html = None
            status = None
            try:
                ctx = browser.new_context(
                    user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = ctx.new_page()
                resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)

                # ① 等 networkidle（最多 8 秒，SPA 数据请求较慢）
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass

                # ② 多次滚动到底（触发懒加载）
                try:
                    last_h = 0
                    for _ in range(10):
                        new_h = page.evaluate("document.body.scrollHeight")
                        if new_h == last_h:
                            break
                        last_h = new_h
                        page.mouse.wheel(0, 1800)
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # ③ 滚回顶部
                try:
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(500)
                except Exception:
                    pass

                # ④ 可选等关键 selector（等到商品卡真正出现，最多 12s）
                if wait_for_selector:
                    try:
                        page.wait_for_selector(wait_for_selector, timeout=12000)
                    except Exception:
                        pass

                # ⑤ 最后等额外 wait_ms
                page.wait_for_timeout(wait_ms)

                html = page.content()
                status = resp.status if resp else None
            finally:
                # 强制关闭，异常也执行（防僵尸进程）
                try:
                    browser.close()
                except Exception:
                    pass

            if html and status and status < 400 and len(html) > 3000:
                blocked, sign = is_blocked_page(html)
                if blocked:
                    logger.warning(f"[L3 patchright] 拿到 {len(html)} chars 但是 blocked 页面 ({sign})，丢弃")
                    return None
                logger.info(f"[L3 patchright] OK {len(html)} chars status={status} (full render)")
                return html
            elif status and status >= 400:
                logger.warning(f"[L3 patchright] HTTP {status}（视为失败，继续降级）")
    except Exception as e:
        logger.debug(f"[L3 patchright] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L4: pydoll ───────────────────────────
def fetch_with_pydoll(url: str, proxy: Optional[str] = None) -> Optional[str]:
    try:
        import asyncio
        from pydoll.browser.chromium import Chrome
        from pydoll.browser.options import ChromiumOptions

        async def _run():
            opts = ChromiumOptions()
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            if proxy:
                opts.add_argument(f"--proxy-server={proxy}")
            async with Chrome(options=opts) as browser:
                tab = await browser.start()
                await tab.go_to(url)
                await asyncio.sleep(4)
                return await tab.page_source

        html = asyncio.run(_run())
        if html and len(html) > 3000:
            blocked, sign = is_blocked_page(html)
            if blocked:
                logger.warning(f"[L4 pydoll] 拿到 {len(html)} chars 但是 blocked ({sign})，丢弃")
                return None
            logger.info(f"[L4 pydoll] OK {len(html)} chars")
            return html
    except Exception as e:
        logger.debug(f"[L4 pydoll] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L5: SeleniumBase（UC Mode） ───────────────────────────
def fetch_with_seleniumbase(url: str, proxy: Optional[str] = None) -> Optional[str]:
    try:
        from seleniumbase import SB
        sb_kw = {"uc": True, "headless": True, "block_images": True}
        if proxy:
            # SeleniumBase 接受 host:port 或 user:pass@host:port 形式（去 http://）
            sb_kw["proxy"] = proxy.replace("http://", "").replace("https://", "")
        with SB(**sb_kw) as sb:
            sb.uc_open_with_reconnect(url, 4)
            sb.sleep(3)
            sb.execute_script("window.scrollBy(0, 3000)")
            sb.sleep(1)
            html = sb.get_page_source()
            if html and len(html) > 3000:
                blocked, sign = is_blocked_page(html)
                if blocked:
                    logger.warning(f"[L5 SeleniumBase] 拿到 {len(html)} chars 但是 blocked ({sign})，丢弃")
                    return None
                logger.info(f"[L5 SeleniumBase] OK {len(html)} chars")
                return html
    except Exception as e:
        logger.debug(f"[L5 SeleniumBase] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L6: botasaurus ───────────────────────────
def fetch_with_botasaurus(url: str, proxy: Optional[str] = None) -> Optional[str]:
    try:
        from botasaurus_driver import Driver
        kw = {"headless": True, "block_images": True}
        if proxy:
            # botasaurus 需要不带协议前缀的 ip:port 格式
            clean = proxy.replace("http://", "").replace("https://", "")
            kw["proxy"] = clean
        driver = Driver(**kw)
        try:
            driver.google_get(url, bypass_cloudflare=True)
            # 等更久让 SPA 完整渲染
            driver.sleep(5)
            # 多次滚动直到底部不再变长
            try:
                last_h = 0
                for _ in range(6):
                    new_h = driver.run_js("return document.body.scrollHeight")
                    if new_h == last_h:
                        break
                    last_h = new_h
                    driver.run_js("window.scrollTo(0, document.body.scrollHeight)")
                    driver.sleep(1.2)
                # 滚回顶部
                driver.run_js("window.scrollTo(0, 0)")
                driver.sleep(1)
            except Exception:
                pass
            html = driver.page_html
            if html and len(html) > 3000:
                blocked, sign = is_blocked_page(html)
                if blocked:
                    logger.warning(f"[L6 botasaurus] 拿到 {len(html)} chars 但是 blocked 页面 ({sign})，丢弃")
                    return None
                logger.info(f"[L6 botasaurus] OK {len(html)} chars (full render)")
                return html
        finally:
            try: driver.close()
            except Exception: pass
    except Exception as e:
        logger.debug(f"[L6 botasaurus] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L7: camoufox（仅当浏览器内核已下载） ───────────────────────────
def fetch_with_camoufox(url: str, proxy: Optional[str] = None) -> Optional[str]:
    try:
        from camoufox.sync_api import Camoufox
        kw = {"headless": True}
        if proxy:
            kw["proxy"] = {"server": proxy}
        with Camoufox(**kw) as browser:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            html = page.content()
            if html and len(html) > 3000:
                blocked, sign = is_blocked_page(html)
                if blocked:
                    logger.warning(f"[L7 camoufox] 拿到 {len(html)} chars 但是 blocked ({sign})，丢弃")
                    return None
                logger.info(f"[L7 camoufox] OK {len(html)} chars")
                return html
    except Exception as e:
        logger.debug(f"[L7 camoufox] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── L8: FlareSolverr (Cloudflare 绕过) ───────────────────────────
def fetch_with_flaresolverr(url: str, proxy: Optional[str] = None) -> Optional[str]:
    """
    用 FlareSolverr 绕 Cloudflare（需 docker 启动 FlareSolverr 服务）。
    docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
    """
    try:
        import requests
        # 检查 FlareSolverr 是否在跑（10 秒超时）
        try:
            r = requests.get("http://localhost:8191/health", timeout=2)
            if r.status_code != 200:
                return None
        except Exception:
            return None  # 没启动就跳过
        
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
        }
        if proxy:
            payload["proxy"] = {"url": proxy}
        
        resp = requests.post("http://localhost:8191/v1", json=payload, timeout=70)
        if resp.status_code != 200:
            logger.debug(f"[L8 FlareSolverr] http {resp.status_code}")
            return None
        data = resp.json()
        if data.get("status") != "ok":
            logger.debug(f"[L8 FlareSolverr] status={data.get('status')}: {data.get('message')}")
            return None
        html = data.get("solution", {}).get("response", "")
        if html and len(html) > 3000:
            blocked, sign = is_blocked_page(html)
            if blocked:
                logger.warning(f"[L8 FlareSolverr] 拿到 {len(html)} chars 但是 blocked ({sign})，丢弃")
                return None
            logger.info(f"[L8 FlareSolverr] OK {len(html)} chars (Cloudflare 绕过)")
            return html
    except Exception as e:
        logger.debug(f"[L8 FlareSolverr] fail: {str(e)[:120]}")
    return None


# ─────────────── L0 级：API 代理服务（云 IP 被封时的首选通道） ───────────────

SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY", "")
SCRAPEOPS_KEY = os.getenv("SCRAPEOPS_KEY", "")


def fetch_with_scraperapi(url: str, proxy: Optional[str] = None) -> Optional[str]:
    """ScraperAPI — 付费代理 API（免费额度 1000 次/月）。设置 SCRAPERAPI_KEY 启用。"""
    if not SCRAPERAPI_KEY:
        return None
    try:
        import requests as _req
        api_url = "https://api.scraperapi.com"
        params = {"api_key": SCRAPERAPI_KEY, "url": url, "render": "false"}
        r = _req.get(api_url, params=params, timeout=30)
        if r.status_code == 200 and r.text and len(r.text) > 1000:
            blocked, sign = is_blocked_page(r.text)
            if blocked:
                logger.warning(f"[L0 ScraperAPI] blocked ({sign})，丢弃")
                return None
            logger.info(f"[L0 ScraperAPI] OK {len(r.text)} chars")
            return r.text
        logger.debug(f"[L0 ScraperAPI] status={r.status_code}, len={len(r.text)}")
    except Exception as e:
        logger.debug(f"[L0 ScraperAPI] fail: {str(e)[:120]}")
    return None


def fetch_with_scrapeops(url: str, proxy: Optional[str] = None) -> Optional[str]:
    """ScrapeOps — 付费代理 API（免费额度 1000 次/月）。设置 SCRAPEOPS_KEY 启用。"""
    if not SCRAPEOPS_KEY:
        return None
    try:
        import requests as _req
        api_url = "https://proxy.scrapeops.io/v1/"
        params = {"api_key": SCRAPEOPS_KEY, "url": url}
        r = _req.get(api_url, params=params, timeout=30)
        if r.status_code == 200 and r.text and len(r.text) > 1000:
            blocked, sign = is_blocked_page(r.text)
            if blocked:
                logger.warning(f"[L0 ScrapeOps] blocked ({sign})，丢弃")
                return None
            logger.info(f"[L0 ScrapeOps] OK {len(r.text)} chars")
            return r.text
        logger.debug(f"[L0 ScrapeOps] status={r.status_code}, len={len(r.text)}")
    except Exception as e:
        logger.debug(f"[L0 ScrapeOps] fail: {str(e)[:120]}")
    return None


def fetch_with_free_proxy(url: str, proxy: Optional[str] = None) -> Optional[str]:
    """ProxyScrape 免费代理池 — 无需 API Key，轮换公共代理 IP。"""
    try:
        import requests as _req
        # 获取一个免费 HTTP 代理
        pool_url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=us&ssl=yes&anonymity=elite&simplified=true"
        pool_resp = _req.get(pool_url, timeout=5)
        proxies_list = [p.strip() for p in pool_resp.text.strip().split("\n") if p.strip()]
        if not proxies_list:
            logger.debug("[L0.8 FreeProxy] 代理池为空")
            return None
        # 尝试前 3 个代理
        for px in proxies_list[:3]:
            px_url = f"http://{px}"
            try:
                r = _req.get(url, proxies={"http": px_url, "https": px_url},
                             timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
                if r.status_code == 200 and r.text and len(r.text) > 1000:
                    blocked, sign = is_blocked_page(r.text)
                    if blocked:
                        continue
                    logger.info(f"[L0.8 FreeProxy] OK {len(r.text)} chars via {px}")
                    return r.text
            except Exception:
                continue
        logger.debug("[L0.8 FreeProxy] 所有免费代理均失败")
    except Exception as e:
        logger.debug(f"[L0.8 FreeProxy] fail: {str(e)[:120]}")
    return None


# ─────────────────────────── 主降级链 ───────────────────────────

# API 代理引擎（优先级最高：云 IP 常被电商平台封禁，API 代理绕过）
ENGINES_API: list[tuple[str, Callable]] = [
    ("L0 ScraperAPI", fetch_with_scraperapi),
    ("L0 ScrapeOps", fetch_with_scrapeops),
    ("L0.8 FreeProxy", fetch_with_free_proxy),
]

ENGINES_FAST: list[tuple[str, Callable]] = [
    ("L1 curl_cffi", fetch_with_curl_cffi),
    ("L2 Scrapling", fetch_with_scrapling),
]
ENGINES_BROWSER: list[tuple[str, Callable]] = [
    ("L2.5 crawl4ai", fetch_with_crawl4ai),  # Scrapling 的回退（AI 友好渲染）
    ("L3 patchright", fetch_with_patchright),
    ("L6 botasaurus", fetch_with_botasaurus),
    ("L4 pydoll", fetch_with_pydoll),
    ("L5 SeleniumBase", fetch_with_seleniumbase),
    ("L7 camoufox", fetch_with_camoufox),
    ("L8 FlareSolverr", fetch_with_flaresolverr),  # 终极 Cloudflare 绕过
]


def fetch(url: str, proxy: Optional[str] = None,
          force_browser: bool = False, use_proxy: bool = False,
          wait_for_selector: Optional[str] = None) -> str:
    """
    9 级降级获取（命中即止）。
    - proxy: 显式代理；不给且 use_proxy=True 用 DEFAULT_PROXY
    - force_browser: 强制走浏览器引擎（适合 SPA/重 JS 站）
    - use_proxy: 简化开关
    - wait_for_selector: SPA 站点传入商品卡 selector，浏览器引擎会等它真正渲染出来
      （解决"等待太短拿到空壳"的问题）

    代理不可用时自动降级到直连（curl_cffi TLS 指纹伪装足以通过大多数反爬）。
    """
    eff = proxy if proxy else (DEFAULT_PROXY if use_proxy else None)
    
    # 代理自检：可用则走代理，不可用则降级直连（不再强制失败）
    if eff:
        import socket, re as _re
        _m = _re.search(r":(\d+)", eff)
        _port = int(_m.group(1)) if _m else 10808
        s = socket.socket(); s.settimeout(2)
        try:
            s.connect(("127.0.0.1", _port)); s.close()
        except Exception:
            # 代理不可用 → 降级直连（curl_cffi TLS 指纹伪装足以通过 Amazon 等反爬）
            # 云部署环境（Render 等）无 xray 代理，直接降级不浪费 30s 重启超时
            if _port == 10808:
                # 仅在有 xray 二进制时尝试重启（避免云环境白等 30 秒）
                xray_bin = os.path.join(os.path.dirname(__file__), "..", "proxy", "xray")
                if os.path.isfile(xray_bin):
                    logger.warning("[fetch] 代理端口 10808 未监听，尝试重启...")
                    restarted = False
                    try:
                        from proxy.ensure_proxy import ensure_proxy_alive
                        restarted = ensure_proxy_alive(verbose=False)
                    except ImportError:
                        pass
                    if not restarted:
                        logger.warning(f"[fetch] 代理重启失败，降级直连: {url}")
                        eff = None
                else:
                    logger.info(f"[fetch] 无代理环境（云部署），直连获取: {url}")
                    eff = None
            else:
                logger.warning(f"[fetch] 国家代理端口 {_port} 不可用，降级直连: {url}")
                eff = None
    
    chain = []
    # API 代理优先（云 IP 被电商封禁时直接绕过，无需本地浏览器）
    chain.extend(ENGINES_API)
    # 即使 force_browser=True 也先试 HTTP 引擎（curl_cffi TLS 指纹已够强，
    # 很多 SPA 站其实只是服务端渲染+JSON 嵌入，HTTP 层能直接拿到完整 HTML）。
    # 只有 HTTP 引擎全部失败才回退到浏览器引擎。
    chain.extend(ENGINES_FAST)
    chain.extend(ENGINES_BROWSER)

    for name, fn in chain:
        try:
            # 浏览器引擎支持 wait_for_selector（等 SPA 渲染）；HTTP 引擎不支持，忽略该参数
            if wait_for_selector and "patchright" in name:
                html = fn(url, proxy=eff, wait_for_selector=wait_for_selector)
            else:
                html = fn(url, proxy=eff)
        except TypeError:
            # 引擎签名不接受 wait_for_selector，降级普通调用
            html = fn(url, proxy=eff)
        except Exception as e:
            logger.warning(f"[{name}] crashed: {str(e)[:120]}")
            continue
        if html:
            return html
    raise FetchFailed(f"All {len(chain)} engines failed for {url}")


if __name__ == "__main__":
    print(fetch("https://example.com")[:200])
