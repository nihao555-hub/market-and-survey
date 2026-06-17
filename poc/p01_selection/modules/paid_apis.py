"""
付费 API 集成（均有免费额度）— 缺省 key 时自动降级到开源路径，不报错、不编造。

1. DataForSEO Keywords Data API
   - 真实 Google Ads 绝对搜索量（月搜索量、CPC、竞争度、12 月趋势）
   - 补『趋势洞察』最大短板（Google Trends 只有相对热度，这里给绝对值）
   - 注册送 ~$1 credit；search_volume 端点约 $0.05/任务（最多 1000 词/任务）

2. RapidAPI - Real-Time Amazon Data
   - 真实月销 / BSR / 评分 / 价格
   - 补『竞品分析』『利润测算』
   - 免费档 ~100-500 req/月

设计原则：
- key 缺省 → available()=False，调用方降级到现有开源工具（DDGS/scraper），绝不编造
- 每个返回都带 _source（API 名）+ 真实性标记，便于报告引用
"""
from __future__ import annotations
import os, base64, json, time
from pathlib import Path
from loguru import logger
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN", "").strip()
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD", "").strip()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_AMAZON_HOST = os.getenv("RAPIDAPI_AMAZON_HOST", "real-time-amazon-data.p.rapidapi.com").strip()


# ════════════════════════════════════════════════════════════════
# DataForSEO — 真实绝对搜索量
# ════════════════════════════════════════════════════════════════
def dataforseo_available() -> bool:
    return bool(DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD)


def _dataforseo_auth_header() -> dict:
    token = base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


# 地区名 → DataForSEO location_code（Google Ads 标准）
_LOCATION_CODES = {
    "US": 2840, "UK": 2826, "GB": 2826, "DE": 2276, "FR": 2250,
    "JP": 2392, "AU": 2036, "CA": 2124, "IN": 2356, "SG": 2702,
    "BR": 2076, "MX": 2484, "RU": 2643, "AE": 2784, "ES": 2724, "IT": 2380,
}
_LANG_CODES = {
    "US": "en", "UK": "en", "GB": "en", "DE": "de", "FR": "fr",
    "JP": "ja", "AU": "en", "CA": "en", "IN": "en", "SG": "en",
    "BR": "pt", "MX": "es", "RU": "ru", "AE": "ar", "ES": "es", "IT": "it",
}


def get_real_search_volume(keywords: list[str], geo: str = "US") -> dict:
    """
    真实 Google Ads 月搜索量（绝对值）+ CPC + 竞争度 + 12 月趋势。
    返回 available=False 时调用方应降级到 DDGS（相对值）。
    """
    if not dataforseo_available():
        return {"available": False, "reason": "no_dataforseo_key",
                "_hint": "在 .env 填 DATAFORSEO_LOGIN/PASSWORD 启用真实绝对搜索量"}
    if not keywords:
        return {"available": True, "results": [], "error": "no_keywords"}

    geo = geo.upper()
    loc = _LOCATION_CODES.get(geo, 2840)
    lang = _LANG_CODES.get(geo, "en")
    url = ("https://api.dataforseo.com/v3/keywords_data/google_ads/"
           "search_volume/live")
    payload = [{
        "keywords": keywords[:1000],
        "location_code": loc,
        "language_code": lang,
    }]
    try:
        resp = requests.post(url, headers=_dataforseo_auth_header(),
                             data=json.dumps(payload), timeout=40)
        if resp.status_code != 200:
            return {"available": True, "error": f"http_{resp.status_code}",
                    "detail": resp.text[:200]}
        data = resp.json()
        task = (data.get("tasks") or [{}])[0]
        if task.get("status_code") != 20000:
            return {"available": True, "error": "task_error",
                    "detail": task.get("status_message", "")[:200],
                    "_hint": "可能余额不足或 key 无效"}
        results = []
        for item in (task.get("result") or []):
            results.append({
                "keyword": item.get("keyword"),
                "search_volume": item.get("search_volume"),   # 真实月均搜索量（绝对值）
                "cpc": item.get("cpc"),
                "competition": item.get("competition"),
                "competition_index": item.get("competition_index"),
                "monthly_searches": item.get("monthly_searches", [])[:12],  # 近 12 月
            })
        # 按搜索量排序
        results.sort(key=lambda x: -(x.get("search_volume") or 0))
        return {
            "available": True, "geo": geo, "location_code": loc,
            "count": len(results), "results": results,
            "_source": "DataForSEO Google Ads Search Volume（真实绝对月搜索量）",
            "_real_data": True,
        }
    except Exception as e:
        return {"available": True, "error": str(e)[:200]}


# ════════════════════════════════════════════════════════════════
# RapidAPI - Real-Time Amazon Data — 真实月销/BSR/评分
# ════════════════════════════════════════════════════════════════
def rapidapi_amazon_available() -> bool:
    return bool(RAPIDAPI_KEY)


def _rapidapi_headers() -> dict:
    return {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_AMAZON_HOST}


_COUNTRY_MAP = {"US": "US", "UK": "GB", "GB": "GB", "DE": "DE", "FR": "FR",
                "JP": "JP", "AU": "AU", "CA": "CA", "IN": "IN", "ES": "ES", "IT": "IT"}


def get_amazon_product_details(asin: str, geo: str = "US") -> dict:
    """
    真实商品详情：BSR / 月销（sales_volume）/ 评分 / 评论数 / 价格。
    返回 available=False 时调用方降级到 scraper 抓取。
    """
    if not rapidapi_amazon_available():
        return {"available": False, "reason": "no_rapidapi_key"}
    country = _COUNTRY_MAP.get(geo.upper(), "US")
    url = f"https://{RAPIDAPI_AMAZON_HOST}/product-details"
    try:
        resp = requests.get(url, headers=_rapidapi_headers(),
                            params={"asin": asin, "country": country}, timeout=30)
        if resp.status_code != 200:
            return {"available": True, "error": f"http_{resp.status_code}",
                    "detail": resp.text[:200]}
        data = resp.json().get("data", {}) or {}
        # BSR 在 product_information["Best Sellers Rank"] 里（非顶层字段）
        pinfo = data.get("product_information", {}) or {}
        bsr_raw = pinfo.get("Best Sellers Rank") or data.get("sales_rank") or data.get("best_seller_rank")
        # 重量/尺寸（喂头程成本计算）
        weight = pinfo.get("Item Weight")
        dims = pinfo.get("Product Dimensions")
        return {
            "available": True, "asin": asin, "country": country,
            "title": data.get("product_title"),
            "price": data.get("product_price"),
            "original_price": data.get("product_original_price"),
            "currency": data.get("currency"),
            "rating": data.get("product_star_rating"),
            "review_count": data.get("product_num_ratings"),
            "rating_distribution": data.get("rating_distribution"),  # 1-5星分布
            "bsr": bsr_raw,
            "sales_volume": data.get("sales_volume"),  # "2K+ bought in past month"
            "num_offers": data.get("product_num_offers"),  # 卖家数
            "is_best_seller": data.get("is_best_seller"),
            "is_amazon_choice": data.get("is_amazon_choice"),
            "is_prime": data.get("is_prime"),
            "availability": data.get("product_availability"),
            "category": data.get("category"),
            "weight": weight, "dimensions": dims,
            "brand": pinfo.get("Manufacturer") or (data.get("product_details") or {}).get("Brand"),
            "date_first_available": pinfo.get("Date First Available"),  # 上架时间（判断新老品）
            "image_url": data.get("product_photo"),
            "url": data.get("product_url"),
            "_source": "RapidAPI Real-Time Amazon Data（真实第一方数据）",
            "_real_data": True,
        }
    except Exception as e:
        return {"available": True, "error": str(e)[:200]}


def search_amazon_products(keyword: str, geo: str = "US", page: int = 1) -> dict:
    """
    真实搜索结果（含每个商品的 sales_volume 月销标签 + BSR + 评分）。
    """
    if not rapidapi_amazon_available():
        return {"available": False, "reason": "no_rapidapi_key"}
    country = _COUNTRY_MAP.get(geo.upper(), "US")
    url = f"https://{RAPIDAPI_AMAZON_HOST}/search"
    try:
        resp = requests.get(url, headers=_rapidapi_headers(),
                            params={"query": keyword, "country": country,
                                    "page": page, "sort_by": "RELEVANCE"}, timeout=30)
        if resp.status_code != 200:
            return {"available": True, "error": f"http_{resp.status_code}",
                    "detail": resp.text[:200]}
        data = resp.json().get("data", {}) or {}
        products = []
        for p in (data.get("products") or []):
            products.append({
                "asin": p.get("asin"),
                "title": p.get("product_title"),
                "price": p.get("product_price"),
                "rating": p.get("product_star_rating"),
                "review_count": p.get("product_num_ratings"),
                "sales_volume": p.get("sales_volume"),  # 真实月销标签
                "image_url": p.get("product_photo"),
                "url": p.get("product_url"),
                "is_sponsored": p.get("is_sponsored", False),
            })
        return {
            "available": True, "keyword": keyword, "country": country,
            "count": len(products), "products": products,
            "_source": "RapidAPI Real-Time Amazon Data 搜索（真实第一方）",
            "_real_data": True,
        }
    except Exception as e:
        return {"available": True, "error": str(e)[:200]}


def api_status() -> dict:
    """汇报哪些付费 API 已配置可用。"""
    return {
        "dataforseo": {"available": dataforseo_available(),
                       "use": "真实绝对搜索量（趋势洞察）"},
        "rapidapi_amazon": {"available": rapidapi_amazon_available(),
                            "use": "真实月销/BSR/评分（竞品+利润）"},
    }


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    print(json.dumps(api_status(), ensure_ascii=False, indent=2))
    if dataforseo_available():
        print(json.dumps(get_real_search_volume(["yoga mat", "exercise mat"], "US"),
                         ensure_ascii=False, indent=2))
    if rapidapi_amazon_available():
        print(json.dumps(search_amazon_products("yoga mat", "US"), ensure_ascii=False, indent=2)[:1500])
