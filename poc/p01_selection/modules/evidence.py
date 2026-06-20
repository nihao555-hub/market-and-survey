"""
证据采集 — 给报告里每个数据点附 source URL + 真实截图 + 产品主图
所有截图存 reports/evidence/<thread>/<asin>_<type>.png
"""
from __future__ import annotations
import re, urllib.request
from pathlib import Path
from datetime import datetime
from loguru import logger

from modules.scraper import DEFAULT_PROXY, fetch


EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "reports" / "evidence"


def screenshot_url(url: str, save_name: str, use_proxy: bool = True) -> dict:
    """给指定 URL 截图，返回本地路径 + 实际 URL（用于报告引用）"""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE_DIR / f"{save_name}.png"
    try:
        from botasaurus_driver import Driver
        kw = {"headless": True, "block_images": False}  # 截图要图片
        if use_proxy:
            kw["proxy"] = DEFAULT_PROXY.replace("http://", "").replace("https://", "")
        driver = Driver(**kw)
        try:
            driver.google_get(url, bypass_cloudflare=True)
            driver.sleep(4)
            driver.run_js("window.scrollTo(0, 0)")
            driver.sleep(1)
            driver.save_screenshot(str(out_path))
            logger.info(f"📸 截图保存 {out_path}")
            return {"url": url, "screenshot_path": str(out_path),
                    "captured_at": datetime.utcnow().isoformat()}
        finally:
            try: driver.close()
            except Exception: pass
    except Exception as e:
        logger.warning(f"截图失败 {url}: {str(e)[:120]}")
        return {"url": url, "error": str(e)[:200]}


def fetch_amazon_main_image(asin: str, use_proxy: bool = True, geo: str = "US") -> dict:
    """抓 Amazon 商品详情页主图 URL（用于报告嵌入图片）。支持多站（US/UK/DE/FR/JP/IN/AU 等）。"""
    domain_map = {"US":"com","UK":"co.uk","GB":"co.uk","DE":"de","FR":"fr","JP":"co.jp",
                   "IN":"in","AU":"com.au","CA":"ca","IT":"it","ES":"es","MX":"com.mx",
                   "BR":"com.br","NL":"nl","SG":"sg","AE":"ae","SE":"se","PL":"pl","TR":"com.tr"}
    tld = domain_map.get(geo.upper(), "com")
    dp_url = f"https://www.amazon.{tld}/dp/{asin}"
    try:
        html = fetch(dp_url, use_proxy=use_proxy)
        m = re.search(r'data-old-hires="(https://[^"]+\.(jpg|png|webp))"', html)
        if not m:
            m = re.search(r'"hiRes":"(https://[^"]+\.(jpg|png|webp))"', html)
        if not m:
            m = re.search(r'"large":"(https://[^"]+\.(jpg|png|webp))"', html)
        img_url = m.group(1) if m else None
        tm = re.search(r'<span id="productTitle"[^>]*>([^<]+)</span>', html)
        title = (tm.group(1).strip() if tm else "")[:120]
        return {"asin": asin, "image_url": img_url, "alt": title, "dp_url": dp_url}
    except Exception as e:
        return {"asin": asin, "error": str(e)[:200], "dp_url": dp_url}


def fetch_generic_listing_image(url: str, use_proxy: bool = True) -> dict:
    """通用：从任意电商 listing 页抓主图（用于 Lazada/Yandex/MercadoLibre 等非 Amazon 平台）。"""
    try:
        html = fetch(url, use_proxy=use_proxy)
        # 多种主图特征：og:image / 大图 / lazyload data-src
        patterns = [
            r'<meta[^>]+property="og:image"[^>]+content="(https://[^"]+\.(jpg|png|webp|jpeg))"',
            r'<meta[^>]+name="twitter:image"[^>]+content="(https://[^"]+\.(jpg|png|webp|jpeg))"',
            r'"(?:largeUrl|main_image|image_url|imageUrl|hiResUrl)"\s*:\s*"(https://[^"]+\.(jpg|png|webp|jpeg))"',
        ]
        img_url = None
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                img_url = m.group(1)
                break
        # 标题
        title = ""
        tm = re.search(r'<title[^>]*>([^<]{5,200})</title>', html)
        if tm:
            title = tm.group(1).strip()[:120]
        return {"url": url, "image_url": img_url, "alt": title}
    except Exception as e:
        return {"url": url, "error": str(e)[:200]}


def download_image(url: str, save_name: str) -> str | None:
    """下载图片到本地（用于离线 markdown）"""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE_DIR / f"{save_name}.jpg"
    try:
        # 走代理下
        proxy = DEFAULT_PROXY
        proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [("User-Agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(url, str(out_path))
        return str(out_path)
    except Exception as e:
        logger.warning(f"下载图片失败 {url}: {e}")
        return None


def capture_evidence_for_asin(asin: str, use_proxy: bool = True, geo: str = "US") -> dict:
    """对一个候选 Amazon ASIN 抓三类证据：① 详情页截图 ② 搜索页截图 ③ 主图 URL（嵌报告用）。
    支持多站（US/UK/DE/FR/JP/IN/MX/BR 等），按 geo 选 amazon 域名。
    
    **C 优化（2026-06）**：dp 截图 / search 截图 / 主图获取三路并发（独立 driver/HTTP 连接），
    单 ASIN 从 ~90s 降到 ~40s。
    """
    from concurrent.futures import ThreadPoolExecutor
    domain_map = {"US":"com","UK":"co.uk","GB":"co.uk","DE":"de","FR":"fr","JP":"co.jp",
                   "IN":"in","AU":"com.au","CA":"ca","IT":"it","ES":"es","MX":"com.mx",
                   "BR":"com.br","NL":"nl","SG":"sg","AE":"ae","SE":"se","PL":"pl","TR":"com.tr"}
    tld = domain_map.get(geo.upper(), "com")
    dp_url = f"https://www.amazon.{tld}/dp/{asin}"
    sr_url = f"https://www.amazon.{tld}/s?k={asin}"
    
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_dp = ex.submit(screenshot_url, dp_url, f"{asin}_dp", use_proxy)
        f_sr = ex.submit(screenshot_url, sr_url, f"{asin}_search", use_proxy)
        f_img = ex.submit(fetch_amazon_main_image, asin, use_proxy, geo)
        dp_res = f_dp.result()
        sr_res = f_sr.result()
        img = f_img.result()
    
    img_local = None
    if img.get("image_url"):
        img_local = download_image(img["image_url"], f"{asin}_main")
    
    # 给截图加现成的 markdown（相对 reports/ 的路径，PDF 和网页都能渲染）
    def _shot_md(res, label):
        sp = res.get("screenshot_path")
        if not sp:
            return None
        fname = Path(sp).name
        return f"![{label}](evidence/{fname})"
    
    return {
        "asin": asin, "geo": geo,
        "detail_page": {**dp_res, "markdown": _shot_md(dp_res, f"{asin} 详情页截图")},
        "search_result": {**sr_res, "markdown": _shot_md(sr_res, f"{asin} 搜索页截图")},
        "main_image": {
            "remote_url": img.get("image_url"),
            "local_path": img_local,
            "alt": img.get("alt", ""),
            "dp_url": dp_url,
            "markdown_remote": (f"![{img.get('alt','')}]({img['image_url']})"
                                  if img.get("image_url") else None),
            "markdown_local": (f"![{img.get('alt','')}](evidence/{asin}_main.jpg)"
                                if img_local else None),
        },
    }


def capture_evidence_for_url(listing_url: str, save_name: str = None,
                              use_proxy: bool = True) -> dict:
    """通用：对任意非 Amazon 平台 listing URL 抓证据
    （Lazada SG / Yandex Market / MercadoLibre MX/BR 等）。
    返回 listing 截图 + 主图 URL（如能抓到）。
    
    **C 优化（2026-06）**：截图 + 主图获取并发。
    """
    from concurrent.futures import ThreadPoolExecutor
    if not save_name:
        save_name = re.sub(r'\W+', '_', listing_url.split("//", 1)[-1])[:60]
    
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_shot = ex.submit(screenshot_url, listing_url, f"{save_name}_page", use_proxy)
        f_img = ex.submit(fetch_generic_listing_image, listing_url, use_proxy)
        shot_res = f_shot.result()
        img = f_img.result()
    
    img_local = None
    if img.get("image_url"):
        img_local = download_image(img["image_url"], f"{save_name}_main")
    
    shot_md = None
    if shot_res.get("screenshot_path"):
        shot_md = f"![{save_name} 页面截图](evidence/{Path(shot_res['screenshot_path']).name})"
    
    return {
        "url": listing_url, "save_name": save_name,
        "page_screenshot": {**shot_res, "markdown": shot_md},
        "main_image": {
            "remote_url": img.get("image_url"),
            "local_path": img_local,
            "alt": img.get("alt", ""),
            "markdown_remote": (f"![{img.get('alt','')}]({img['image_url']})"
                                  if img.get("image_url") else None),
            "markdown_local": (f"![{img.get('alt','')}](evidence/{save_name}_main.jpg)"
                                if img_local else None),
        },
    }


def capture_evidence_batch(asins: list[str], geo: str = "US",
                            use_proxy: bool = True, concurrency: int = 3) -> dict:
    """**C 优化批量并发**：N 个候选 ASIN 并发截图（每个 ASIN 内部已并发 3 路）。
    3 个 ASIN 串行 ~270s → 并发 ~90s。
    
    建议 concurrency=3：单浏览器实例约 200-300 MB 内存，3 实例稳定，超过有 OOM 风险。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    logger.info(f"📸 batch capture {len(asins)} ASINs (geo={geo}, concurrency={concurrency})")
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(capture_evidence_for_asin, a, use_proxy, geo): a for a in asins}
        for fut in as_completed(futures):
            asin = futures[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"asin": asin, "error": str(e)[:200]})
    return {
        "asins_count": len(asins),
        "captured": len([r for r in results if not r.get("error")]),
        "evidence": results,
    }
