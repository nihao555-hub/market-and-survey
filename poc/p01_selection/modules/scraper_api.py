"""
ScraperAPI 集成 — 全球电商平台爬取的第三方 API 代理层。

解决的问题：
- 住宅代理太贵，尤其是东南亚/中东/俄罗斯/拉美等地区
- 很多平台有商业反爬（Walmart/eBay/Etsy/Coupang/Ozon 等）
- ScraperAPI 自带 IP 轮换 + 反爬绕过 + 全球地理定位

免费额度：
- ScraperAPI: 1000 credits/月（注册即得），Amazon 5 credits/req
- 启用 render=true（JS 渲染）+10 credits/req
- 启用 country_code（地理定位）不额外收费
- 启用 premium=true（高级代理池）+10 credits/req

使用策略：
- 仅对 status=blocked 且有 ScraperAPI 支持的平台启用
- verified 平台继续走原有 xray 代理（更快、不消耗额度）
- 优先用 autoparse=true（结构化 JSON）省去 selector 解析
"""
from __future__ import annotations
import os, json, time
from typing import Optional
from urllib.parse import quote_plus
from loguru import logger
import requests

SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY", "").strip()

# ScraperAPI 支持 autoparse 的电商站点（自动返回结构化 JSON）
AUTOPARSE_DOMAINS = {
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.co.jp",
    "amazon.in", "amazon.com.au", "amazon.ae", "amazon.ca",
    "walmart.com", "ebay.com", "etsy.com",
}

# 平台 → ScraperAPI 最佳参数配置（80+ 平台全球覆盖）
PLATFORM_SCRAPERAPI_CONFIG = {
    # ═══ 北美 ═══
    "amazon": {"country_code": "us", "render": False},
    "amazon_ca": {"country_code": "ca", "render": False},
    "walmart": {"country_code": "us", "render": True, "premium": True},
    "walmart_ca": {"country_code": "ca", "render": True, "premium": True},
    "ebay": {"country_code": "us", "render": False, "premium": True},
    "etsy": {"country_code": "us", "render": True, "premium": True},
    "target": {"country_code": "us", "render": True},
    "bestbuy": {"country_code": "us", "render": True},
    "newegg": {"country_code": "us", "render": True},
    "wayfair": {"country_code": "us", "render": True, "premium": True},
    "costco": {"country_code": "us", "render": True, "premium": True},
    "homedepot": {"country_code": "us", "render": True, "premium": True},
    # ═══ 拉丁美洲 ═══
    "mercadolibre_mx": {"country_code": "mx", "render": False},
    "mercadolibre_br": {"country_code": "br", "render": False},
    "mercadolibre_ar": {"country_code": "ar", "render": False},
    "mercadolibre_co": {"country_code": "co", "render": False},
    "mercadolibre_cl": {"country_code": "cl", "render": False},
    "amazon_br": {"country_code": "br", "render": False},
    "amazon_mx": {"country_code": "mx", "render": False},
    "falabella": {"country_code": "cl", "render": True},
    # ═══ 欧洲 ═══
    "amazon_uk": {"country_code": "uk", "render": False},
    "amazon_de": {"country_code": "de", "render": False},
    "amazon_fr": {"country_code": "fr", "render": False},
    "amazon_it": {"country_code": "it", "render": False},
    "amazon_es": {"country_code": "es", "render": False},
    "amazon_nl": {"country_code": "nl", "render": False},
    "amazon_pl": {"country_code": "pl", "render": False},
    "amazon_se": {"country_code": "se", "render": False},
    "otto": {"country_code": "de", "render": True},
    "zalando": {"country_code": "de", "render": True, "premium": True},
    "cdiscount": {"country_code": "fr", "render": True},
    "bol_com": {"country_code": "nl", "render": True},
    "allegro": {"country_code": "pl", "render": True, "premium": True},
    "emag": {"country_code": "ro", "render": True},
    "ebay_uk": {"country_code": "uk", "render": False, "premium": True},
    "ebay_de": {"country_code": "de", "render": False, "premium": True},
    # ═══ 东南亚 ═══
    "shopee_sg": {"country_code": "sg", "render": True, "premium": True},
    "shopee_my": {"country_code": "my", "render": True, "premium": True},
    "shopee_th": {"country_code": "th", "render": True, "premium": True},
    "shopee_vn": {"country_code": "vn", "render": True, "premium": True},
    "shopee_ph": {"country_code": "ph", "render": True, "premium": True},
    "shopee_id": {"country_code": "id", "render": True, "premium": True},
    "lazada_sg": {"country_code": "sg", "render": True},
    "lazada_my": {"country_code": "my", "render": True},
    "lazada_th": {"country_code": "th", "render": True},
    "lazada_vn": {"country_code": "vn", "render": True},
    "lazada_ph": {"country_code": "ph", "render": True},
    "lazada_id": {"country_code": "id", "render": True},
    "tokopedia": {"country_code": "id", "render": True, "premium": True},
    "tiki_vn": {"country_code": "vn", "render": True},
    # ═══ 日韩 ═══
    "amazon_jp": {"country_code": "jp", "render": False},
    "rakuten": {"country_code": "jp", "render": True},
    "yahoo_shopping_jp": {"country_code": "jp", "render": True},
    "coupang": {"country_code": "kr", "render": True, "premium": True},
    "gmarket_kr": {"country_code": "kr", "render": True},
    # ═══ 俄罗斯 + 独联体 ═══
    "ozon": {"country_code": "ru", "render": True, "premium": True},
    "wildberries": {"country_code": "ru", "render": True, "premium": True},
    "yandex_market": {"country_code": "ru", "render": True},
    "kaspi_kz": {"country_code": "kz", "render": True},
    # ═══ 南亚 ═══
    "amazon_in": {"country_code": "in", "render": False},
    "flipkart": {"country_code": "in", "render": True},
    "myntra": {"country_code": "in", "render": True, "premium": True},
    "daraz_pk": {"country_code": "pk", "render": True},
    "daraz_bd": {"country_code": "bd", "render": True},
    # ═══ 中东 ═══
    "amazon_ae": {"country_code": "ae", "render": False},
    "amazon_sa": {"country_code": "sa", "render": False},
    "noon": {"country_code": "ae", "render": True, "premium": True},
    "noon_sa": {"country_code": "sa", "render": True, "premium": True},
    "trendyol": {"country_code": "tr", "render": True, "premium": True},
    "hepsiburada": {"country_code": "tr", "render": True, "premium": True},
    # ═══ 大洋洲 ═══
    "amazon_au": {"country_code": "au", "render": False},
    "catch_au": {"country_code": "au", "render": True},
    "trademe_nz": {"country_code": "nz", "render": True},
    # ═══ 非洲 ═══
    "jumia_ng": {"country_code": "ng", "render": False},
    "jumia_ke": {"country_code": "ke", "render": False},
    "jumia_eg": {"country_code": "eg", "render": False},
    "jumia_gh": {"country_code": "gh", "render": False},
    "takealot": {"country_code": "za", "render": True},
    # ═══ 全球 ═══
    "aliexpress": {"country_code": "us", "render": True},
    "temu": {"country_code": "us", "render": True, "premium": True},
    "shein": {"country_code": "us", "render": True, "premium": True},
    "alibaba": {"country_code": "us", "render": True, "premium": True},
    # ═══ 中国 ═══
    "jd": {"country_code": "cn", "render": True},
    "taobao": {"country_code": "cn", "render": True, "premium": True},
    "tmall": {"country_code": "cn", "render": True, "premium": True},
    "pinduoduo": {"country_code": "cn", "render": True, "premium": True},
    "1688": {"country_code": "cn", "render": True, "premium": True},
}


def scraperapi_available() -> bool:
    return bool(SCRAPERAPI_KEY)


def estimate_credit_cost(platform: str) -> int:
    """估算单次请求的 credit 消耗"""
    cfg = PLATFORM_SCRAPERAPI_CONFIG.get(platform, {})
    cost = 1  # base
    # Amazon 等电商域名基础消耗 5
    if "amazon" in platform:
        cost = 5
    if cfg.get("render"):
        cost += 10
    if cfg.get("premium"):
        cost += 10
    return cost


def get_credit_balance() -> dict:
    """查询当前 ScraperAPI 账户余额"""
    if not scraperapi_available():
        return {"available": False, "reason": "no_scraperapi_key"}
    try:
        resp = requests.get(
            "https://api.scraperapi.com/account",
            params={"api_key": SCRAPERAPI_KEY},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "available": True,
                "credits_remaining": data.get("requestCount", 0),
                "credits_limit": data.get("requestLimit", 0),
                "concurrent_limit": data.get("concurrencyLimit", 0),
            }
        return {"available": True, "error": f"http_{resp.status_code}"}
    except Exception as e:
        return {"available": True, "error": str(e)[:200]}


def fetch_via_scraperapi(url: str, platform: str = None,
                         country_code: str = None,
                         render: bool = None,
                         premium: bool = None,
                         autoparse: bool = None,
                         timeout: int = 60) -> dict:
    """
    通过 ScraperAPI 抓取页面。
    
    返回:
      {"html": "...", "status_code": 200, "credits_used": N}
      或 {"error": "...", "status_code": 4xx/5xx}
    """
    if not scraperapi_available():
        return {"error": "no_scraperapi_key", "html": None}
    
    # 从平台配置获取默认参数
    cfg = PLATFORM_SCRAPERAPI_CONFIG.get(platform, {}) if platform else {}
    
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": url,
    }
    
    # 应用配置（显式传入优先于平台默认）
    cc = country_code or cfg.get("country_code")
    if cc:
        params["country_code"] = cc
    
    use_render = render if render is not None else cfg.get("render", False)
    if use_render:
        params["render"] = "true"
    
    use_premium = premium if premium is not None else cfg.get("premium", False)
    if use_premium:
        params["premium"] = "true"
    
    # autoparse 对支持的域名自动返回结构化 JSON
    if autoparse is None:
        # 检查 URL 是否属于支持 autoparse 的域名
        for domain in AUTOPARSE_DOMAINS:
            if domain in url:
                autoparse = True
                break
    if autoparse:
        params["autoparse"] = "true"
    
    logger.info(f"[ScraperAPI] 请求: platform={platform}, country={cc}, "
                f"render={use_render}, premium={use_premium}, autoparse={autoparse}")
    
    try:
        resp = requests.get(
            "https://api.scraperapi.com",
            params=params,
            timeout=timeout
        )
        
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type or autoparse:
                # autoparse 返回 JSON
                try:
                    data = resp.json()
                    return {
                        "json": data,
                        "html": None,
                        "status_code": 200,
                        "autoparse": True,
                    }
                except:
                    pass
            return {
                "html": resp.text,
                "status_code": 200,
                "content_length": len(resp.text),
            }
        elif resp.status_code == 403:
            return {"error": "blocked_by_target", "status_code": 403,
                    "detail": "ScraperAPI could not bypass anti-bot protection"}
        elif resp.status_code == 429:
            return {"error": "rate_limited", "status_code": 429,
                    "detail": "ScraperAPI credit limit reached"}
        else:
            return {"error": f"http_{resp.status_code}", "status_code": resp.status_code,
                    "detail": resp.text[:300]}
    except requests.Timeout:
        return {"error": "timeout", "detail": f"Request timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)[:200]}


def search_products_via_scraperapi(platform: str, keyword: str, limit: int = 20) -> dict:
    """
    通过 ScraperAPI 搜索电商平台商品。
    对支持 autoparse 的平台直接返回结构化数据，否则返回 HTML 待解析。
    """
    from modules.platforms import PLATFORMS
    
    if not scraperapi_available():
        return {"available": False, "platform": platform, 
                "error": "SCRAPERAPI_KEY 未配置，请设置环境变量",
                "products": []}
    
    p = PLATFORMS.get(platform)
    if not p:
        return {"available": True, "platform": platform,
                "error": f"unknown platform: {platform}", "products": []}
    
    url_template = p.get("search_url")
    if not url_template:
        return {"available": True, "platform": platform,
                "error": "no search_url for platform", "products": []}
    
    url = url_template.format(kw=keyword.replace(" ", "+"))
    
    result = fetch_via_scraperapi(url, platform=platform)
    
    if result.get("error"):
        return {
            "available": True, "platform": platform, "platform_name": p.get("name"),
            "keyword": keyword, "url": url,
            "error": result["error"], "detail": result.get("detail"),
            "products": [],
            "credit_cost": estimate_credit_cost(platform),
        }
    
    # autoparse 返回的结构化数据
    if result.get("autoparse") and result.get("json"):
        data = result["json"]
        products = []
        # Amazon autoparse 格式
        search_results = data.get("results") or data.get("search_results") or []
        for item in search_results[:limit]:
            products.append({
                "title": item.get("name") or item.get("title"),
                "price": item.get("price_string") or item.get("price"),
                "rating": item.get("stars") or item.get("rating"),
                "reviews": item.get("total_reviews") or item.get("reviews_count"),
                "url": item.get("url") or item.get("link"),
                "image": item.get("image") or item.get("thumbnail"),
                "asin": item.get("asin"),
            })
        return {
            "available": True, "platform": platform, "platform_name": p.get("name"),
            "keyword": keyword, "url": url,
            "count": len(products), "products": products,
            "method": "scraperapi_autoparse",
            "credit_cost": estimate_credit_cost(platform),
            "_source": f"ScraperAPI autoparse ({platform})",
        }
    
    # 非 autoparse：返回 HTML，需要用 selector 解析
    html = result.get("html", "")
    if not html or len(html) < 500:
        return {
            "available": True, "platform": platform, "platform_name": p.get("name"),
            "keyword": keyword, "url": url,
            "error": "empty_response", "products": [],
            "html_length": len(html) if html else 0,
            "credit_cost": estimate_credit_cost(platform),
        }
    
    # 用平台的 CSS selector 解析
    products = _parse_html_products(html, p, limit)
    
    return {
        "available": True, "platform": platform, "platform_name": p.get("name"),
        "keyword": keyword, "url": url,
        "count": len(products), "products": products,
        "method": "scraperapi_html_parse",
        "html_length": len(html),
        "credit_cost": estimate_credit_cost(platform),
        "_source": f"ScraperAPI + CSS parse ({platform})",
    }


def _parse_html_products(html: str, platform_cfg: dict, limit: int = 20) -> list[dict]:
    """用 BeautifulSoup 和平台 selector 解析商品列表"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    card_sel = platform_cfg.get("card_sel", "")
    title_sel = platform_cfg.get("title_sel", "")
    price_sel = platform_cfg.get("price_sel", "")
    
    if not card_sel:
        return []
    
    cards = soup.select(card_sel)[:limit]
    products = []
    
    for card in cards:
        title = ""
        price = ""
        
        if title_sel:
            for sel in title_sel.split(","):
                el = card.select_one(sel.strip())
                if el:
                    title = el.get_text(strip=True)
                    break
        
        if price_sel:
            for sel in price_sel.split(","):
                el = card.select_one(sel.strip())
                if el:
                    price = el.get_text(strip=True)
                    break
        
        if title:
            products.append({
                "title": title[:200],
                "price": price or "N/A",
            })
    
    return products


def scraperapi_status() -> dict:
    """返回 ScraperAPI 集成状态摘要"""
    available = scraperapi_available()
    supported_platforms = list(PLATFORM_SCRAPERAPI_CONFIG.keys())
    
    result = {
        "available": available,
        "supported_platforms": len(supported_platforms),
        "platforms": supported_platforms,
        "free_credits_per_month": 1000,
        "note": "ScraperAPI 免费 1000 credits/月，支持全球地理定位 + JS 渲染 + 反爬绕过",
    }
    
    if available:
        balance = get_credit_balance()
        result["balance"] = balance
    
    return result
