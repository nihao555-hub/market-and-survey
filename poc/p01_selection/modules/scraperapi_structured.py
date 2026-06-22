"""
ScraperAPI 结构化数据端点（Structured Data Endpoints）
=====================================================
直接返回 JSON，无需 HTML 解析。覆盖：
- Amazon Product / Search / Offers（全球 22 个 Amazon 站点）
- Walmart Product / Search / Category / Reviews
- eBay Product / Search
- Google Shopping（跨平台价格对比）

替代 RapidAPI Amazon，统一到一个 key 下。
"""
import os
import requests
from typing import Optional
from loguru import logger

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")
BASE = "https://api.scraperapi.com/structured"
TIMEOUT = 60

# Amazon TLD 映射：geo code → amazon tld
AMAZON_TLD_MAP = {
    "US": "com", "UK": "co.uk", "CA": "ca", "DE": "de", "ES": "es",
    "FR": "fr", "IT": "it", "JP": "co.jp", "IN": "in", "AU": "com.au",
    "BR": "com.br", "MX": "com.mx", "NL": "nl", "SE": "se", "PL": "pl",
    "AE": "ae", "SA": "sa", "SG": "com.sg", "TR": "com.tr", "IE": "ie",
    "ZA": "co.za", "CN": "cn",
}

# Walmart TLD 映射
WALMART_TLD_MAP = {"US": "com", "CA": "ca"}


def _key() -> str:
    return os.environ.get("SCRAPERAPI_KEY", "") or SCRAPERAPI_KEY


def _request(endpoint: str, params: dict, timeout: int = TIMEOUT) -> dict:
    """统一请求封装，返回 JSON 或 error dict"""
    key = _key()
    if not key:
        return {"error": "SCRAPERAPI_KEY 未配置", "available": False}
    params["api_key"] = key
    url = f"{BASE}/{endpoint}"
    try:
        safe_params = {k: v for k, v in params.items() if k != "api_key"}
        logger.info(f"[ScraperAPI SDE] {endpoint} params={safe_params}")
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return {"error": "product_not_found", "status_code": 404}
        elif resp.status_code == 429:
            return {"error": "rate_limited", "status_code": 429}
        else:
            return {"error": f"http_{resp.status_code}", "detail": resp.text[:300]}
    except requests.Timeout:
        return {"error": "timeout", "detail": f"Request timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)[:200]}


# ═══════════════════════════════════════════════════════════════════════════════
# Amazon Product API — 替代 RapidAPI，含 BSR/月销/评论/品牌/重量/变体
# ═══════════════════════════════════════════════════════════════════════════════

def amazon_product(asin: str, geo: str = "US") -> dict:
    """
    获取 Amazon 商品完整详情（BSR/月销/评分分布/品牌/重量/尺寸/上架日期/评论）。
    替代 RapidAPI Real-Time Amazon Data。
    
    返回字段：name, price, rating, total_ratings, bsr, sales_volume,
              product_information, reviews, variants, brand, ...
    """
    tld = AMAZON_TLD_MAP.get(geo.upper(), "com")
    params = {"asin": asin, "tld": tld, "country_code": geo.lower()}
    raw = _request("amazon/product", params)
    if raw.get("error"):
        return {"available": False, **raw}
    
    # 标准化输出格式（兼容原 RapidAPI 格式让 Agent 无感切换）
    pinfo = raw.get("product_information", {}) or {}
    bsr_raw = raw.get("best_sellers_rank") or pinfo.get("Best Sellers Rank") or pinfo.get("best_sellers_rank")
    
    # 提取评论
    reviews_raw = raw.get("reviews", []) or []
    reviews = []
    for r in reviews_raw:
        if isinstance(r, dict):
            reviews.append({
                "title": r.get("title"),
                "text": r.get("text") or r.get("review"),
                "rating": r.get("stars") or r.get("rating"),
                "date": r.get("date"),
                "author": r.get("author"),
                "verified": r.get("verified_purchase", False),
            })
    
    # 评分分布（ScraperAPI 格式：5_star_percentage, 4_star_percentage ...）
    rating_dist = raw.get("rating_distribution")
    if not rating_dist:
        rating_dist = {}
        for star in [5, 4, 3, 2, 1]:
            pct = raw.get(f"{star}_star_percentage")
            if pct is not None:
                rating_dist[f"{star}_star"] = f"{pct}%"
    
    return {
        "available": True,
        "asin": asin,
        "geo": geo,
        "title": raw.get("name") or raw.get("title"),
        "price": raw.get("pricing") or raw.get("price") or raw.get("list_price"),
        "original_price": raw.get("list_price") or raw.get("original_price"),
        "shipping_price": raw.get("shipping_price"),
        "currency": raw.get("currency"),
        "rating": raw.get("average_rating") or raw.get("rating") or raw.get("stars"),
        "total_ratings": raw.get("total_ratings") or raw.get("ratings_total"),
        "total_reviews": raw.get("total_reviews"),
        "rating_distribution": rating_dist,
        "bsr": bsr_raw,
        "sales_volume": raw.get("sales_volume") or raw.get("bought_past_month"),
        "brand": pinfo.get("brand_name") or raw.get("brand") or pinfo.get("manufacturer"),
        "manufacturer": pinfo.get("manufacturer"),
        "weight": pinfo.get("item_weight") or pinfo.get("Item Weight"),
        "dimensions": pinfo.get("item_dimensions_d_x_w_x_h") or pinfo.get("Product Dimensions"),
        "date_first_available": pinfo.get("date_first_available") or pinfo.get("Date First Available"),
        "category": raw.get("product_category") or raw.get("category"),
        "is_best_seller": raw.get("is_best_seller"),
        "is_amazon_choice": raw.get("is_amazon_choice"),
        "is_coupon_exists": raw.get("is_coupon_exists"),
        "availability": raw.get("availability_status") or raw.get("availability"),
        "sold_by": raw.get("sold_by"),
        "num_sellers": raw.get("sellers_count") or raw.get("num_offers"),
        "image_url": (raw.get("images") or [None])[0] if raw.get("images") else raw.get("image"),
        "url": raw.get("url") or raw.get("product_url"),
        "feature_bullets": raw.get("feature_bullets", []),
        "variants": raw.get("customization_options") or raw.get("variants", []),
        "reviews": reviews[:20],
        "reviews_count_fetched": len(reviews),
        "product_information": pinfo,
        "_source": f"ScraperAPI Structured Amazon Product (tld={tld})",
        "_real_data": True,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Amazon Search API — 结构化搜索结果
# ═══════════════════════════════════════════════════════════════════════════════

def amazon_search(query: str, geo: str = "US", page: int = 1) -> dict:
    """Amazon 结构化搜索，直接返回 JSON 产品列表"""
    tld = AMAZON_TLD_MAP.get(geo.upper(), "com")
    params = {"query": query, "tld": tld, "country_code": geo.lower(), "page": str(page)}
    raw = _request("amazon/search", params)
    if raw.get("error"):
        return {"available": False, **raw}
    
    results = raw.get("results") or raw.get("organic_results") or []
    products = []
    for item in results:
        if not isinstance(item, dict):
            continue
        products.append({
            "title": item.get("name") or item.get("title"),
            "asin": item.get("asin"),
            "price": item.get("price_string") or item.get("price"),
            "rating": item.get("stars") or item.get("rating"),
            "reviews": item.get("total_reviews") or item.get("ratings_total"),
            "sales_volume": item.get("sales_volume") or item.get("bought_past_month"),
            "url": item.get("url") or item.get("link"),
            "image": item.get("image") or item.get("thumbnail"),
            "is_prime": item.get("is_prime"),
            "is_best_seller": item.get("is_best_seller"),
            "is_amazon_choice": item.get("is_amazon_choice"),
            "sponsored": item.get("sponsored", False),
        })
    
    return {
        "available": True,
        "query": query, "geo": geo, "page": page, "tld": tld,
        "count": len(products),
        "products": products,
        "total_results": raw.get("total_results"),
        "_source": f"ScraperAPI Structured Amazon Search (tld={tld})",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Amazon Offers API — 竞争卖家分析
# ═══════════════════════════════════════════════════════════════════════════════

def amazon_offers(asin: str, geo: str = "US") -> dict:
    """获取某 ASIN 的所有卖家报价（价格/运费/卖家名/评分）"""
    tld = AMAZON_TLD_MAP.get(geo.upper(), "com")
    params = {"asin": asin, "tld": tld, "country_code": geo.lower()}
    raw = _request("amazon/offers", params)
    if isinstance(raw, dict) and raw.get("error"):
        return {"available": False, **raw}
    
    # ScraperAPI 格式：{item: {...}, listings: [...]}
    item_info = raw.get("item", {}) if isinstance(raw, dict) else {}
    listings = raw.get("listings") or raw.get("offers") or raw.get("results") or []
    sellers = []
    for o in listings:
        if not isinstance(o, dict):
            continue
        sellers.append({
            "seller": o.get("seller_name") or o.get("seller") or o.get("sold_by"),
            "price": o.get("price") or o.get("price_string"),
            "shipping": o.get("shipping_price") or o.get("shipping") or o.get("delivery"),
            "condition": o.get("condition"),
            "rating": o.get("seller_rating") or o.get("rating"),
            "ratings_count": o.get("seller_ratings_count"),
            "is_fba": o.get("fullfilled_by_amazon") or o.get("is_fba") or o.get("fulfilled_by_amazon"),
            "is_prime": o.get("is_prime"),
            "delivery_date": o.get("delivery_earliest_date"),
        })
    
    return {
        "available": True,
        "asin": asin, "geo": geo,
        "product_name": item_info.get("name") or raw.get("product_name"),
        "product_rating": item_info.get("average_rating"),
        "product_reviews": item_info.get("total_reviews"),
        "buy_box_price": sellers[0]["price"] if sellers else None,
        "total_offers": len(sellers),
        "offers": sellers,
        "_source": f"ScraperAPI Structured Amazon Offers (tld={tld})",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Walmart Product API
# ═══════════════════════════════════════════════════════════════════════════════

def walmart_product(product_id: str, geo: str = "US") -> dict:
    """Walmart 商品详情（价格/评分/评论数/卖家/品牌/规格）"""
    tld = WALMART_TLD_MAP.get(geo.upper(), "com")
    params = {"product_id": product_id, "tld": tld, "country_code": geo.lower()}
    raw = _request("walmart/product", params)
    if raw.get("error"):
        return {"available": False, **raw}
    
    return {
        "available": True,
        "product_id": product_id, "geo": geo,
        "title": raw.get("name") or raw.get("product_name"),
        "price": raw.get("price") or raw.get("current_price"),
        "original_price": raw.get("original_price") or raw.get("was_price"),
        "rating": raw.get("rating") or raw.get("average_rating"),
        "review_count": raw.get("review_count") or raw.get("reviews_count"),
        "brand": raw.get("brand"),
        "seller": raw.get("seller") or raw.get("sold_by"),
        "availability": raw.get("availability") or raw.get("in_stock"),
        "category": raw.get("category") or raw.get("breadcrumb"),
        "specifications": raw.get("specifications") or raw.get("product_details"),
        "images": raw.get("images", []),
        "url": raw.get("url") or raw.get("product_url"),
        "_source": "ScraperAPI Structured Walmart Product",
        "_raw": raw,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Walmart Search API
# ═══════════════════════════════════════════════════════════════════════════════

def walmart_search(query: str, geo: str = "US", page: int = 1) -> dict:
    """Walmart 结构化搜索"""
    tld = WALMART_TLD_MAP.get(geo.upper(), "com")
    params = {"query": query, "tld": tld, "country_code": geo.lower(), "page": str(page)}
    raw = _request("walmart/search", params)
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and raw.get("error"):
        return {"available": False, **raw}
    elif isinstance(raw, dict):
        items = raw.get("items") or raw.get("results") or raw.get("organic_results") or []
    else:
        items = []
    
    products = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # rating 可能是嵌套 dict: {average_rating: 4.3, number_of_reviews: 889}
        rating_data = item.get("rating")
        if isinstance(rating_data, dict):
            avg_rating = rating_data.get("average_rating")
            review_count = rating_data.get("number_of_reviews")
        else:
            avg_rating = rating_data or item.get("average_rating")
            review_count = item.get("number_of_reviews") or item.get("review_count")
        products.append({
            "title": item.get("name") or item.get("title") or item.get("product_name"),
            "product_id": item.get("id") or item.get("product_id") or item.get("us_item_id"),
            "price": item.get("price") or (item.get("price_info", {}) or {}).get("current_price"),
            "brand": item.get("brand"),
            "rating": avg_rating,
            "reviews": review_count,
            "seller": item.get("seller") or item.get("sold_by"),
            "url": item.get("url") or item.get("product_url"),
            "image": item.get("image") or item.get("thumbnail"),
            "badges": item.get("badges", []),
            "sponsored": item.get("sponsored", False),
        })
    
    return {
        "available": True,
        "query": query, "geo": geo, "page": page,
        "count": len(products),
        "products": products,
        "_source": "ScraperAPI Structured Walmart Search",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Walmart Reviews API
# ═══════════════════════════════════════════════════════════════════════════════

def walmart_reviews(product_id: str, geo: str = "US", page: int = 1,
                    sort: str = "relevancy", ratings: str = None) -> dict:
    """
    Walmart 商品评论（支持分页/排序/评分筛选）。
    sort: relevancy / helpful / submission-desc / submission-asc / rating-desc / rating-asc
    ratings: "1,2,3" 逗号分隔筛选指定星级
    """
    tld = WALMART_TLD_MAP.get(geo.upper(), "com")
    params = {"product_id": product_id, "tld": tld, "country_code": geo.lower(),
              "sort": sort, "page": str(page)}
    if ratings:
        params["ratings"] = ratings
    raw = _request("walmart/review", params)
    if raw.get("error"):
        return {"available": False, **raw}
    
    reviews_raw = raw.get("reviews", []) or []
    reviews = []
    for r in reviews_raw:
        if not isinstance(r, dict):
            continue
        reviews.append({
            "title": r.get("title"),
            "text": r.get("text") or r.get("review_text"),
            "rating": r.get("rating"),
            "date": r.get("date_published") or r.get("date"),
            "author": r.get("author") or r.get("reviewer"),
            "verified": "Verified Purchase" in (r.get("badges", []) or []),
            "positive_feedback": r.get("positive_feedback", 0),
            "negative_feedback": r.get("negative_feedback", 0),
        })
    
    return {
        "available": True,
        "product_id": product_id, "geo": geo,
        "product_name": raw.get("product_name"),
        "overall_rating": raw.get("rating") or raw.get("overall_rating"),
        "total_reviews": raw.get("review_count") or raw.get("total_reviews"),
        "reviews": reviews,
        "page": page,
        "_source": "ScraperAPI Structured Walmart Reviews",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Walmart Category API
# ═══════════════════════════════════════════════════════════════════════════════

def walmart_category(category_id: str, geo: str = "US", page: int = 1) -> dict:
    """Walmart 品类浏览（按类目获取商品列表）"""
    tld = WALMART_TLD_MAP.get(geo.upper(), "com")
    params = {"category_id": category_id, "tld": tld, "country_code": geo.lower(),
              "page": str(page)}
    raw = _request("walmart/category", params)
    if raw.get("error"):
        return {"available": False, **raw}
    
    items = raw.get("results") or raw.get("items") or []
    products = []
    for item in items:
        if not isinstance(item, dict):
            continue
        products.append({
            "title": item.get("name") or item.get("title"),
            "product_id": item.get("id") or item.get("product_id"),
            "price": item.get("price"),
            "rating": item.get("average_rating") or item.get("rating"),
            "reviews": item.get("number_of_reviews"),
            "url": item.get("url"),
            "image": item.get("image"),
        })
    
    return {
        "available": True,
        "category_id": category_id, "geo": geo, "page": page,
        "count": len(products),
        "products": products,
        "_source": "ScraperAPI Structured Walmart Category",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# eBay Product API
# ═══════════════════════════════════════════════════════════════════════════════

def ebay_product(product_id: str, geo: str = "US") -> dict:
    """eBay 商品详情"""
    params = {"product_id": product_id, "country_code": geo.lower()}
    raw = _request("ebay/product", params)
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if isinstance(raw, dict) and raw.get("error"):
        return {"available": False, **raw}
    
    return {
        "available": True,
        "product_id": product_id, "geo": geo,
        "title": raw.get("title") or raw.get("name"),
        "price": raw.get("price") or raw.get("current_price"),
        "condition": raw.get("condition"),
        "seller": raw.get("seller") or raw.get("seller_name"),
        "seller_rating": raw.get("seller_rating") or raw.get("seller_feedback_score"),
        "bids": raw.get("bids") or raw.get("bid_count"),
        "watchers": raw.get("watchers") or raw.get("watching_count"),
        "sold_count": raw.get("sold") or raw.get("quantity_sold"),
        "available_count": raw.get("available") or raw.get("quantity_available"),
        "shipping": raw.get("shipping") or raw.get("shipping_cost"),
        "location": raw.get("item_location") or raw.get("location"),
        "category": raw.get("category") or raw.get("breadcrumb"),
        "specifications": raw.get("item_specifics") or raw.get("specifications"),
        "images": raw.get("images", []),
        "url": raw.get("url") or raw.get("item_url"),
        "_source": "ScraperAPI Structured eBay Product",
        "_raw": raw,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# eBay Search API
# ═══════════════════════════════════════════════════════════════════════════════

def ebay_search(query: str, geo: str = "US", page: int = 1) -> dict:
    """eBay 结构化搜索"""
    params = {"query": query, "country_code": geo.lower(), "page": str(page)}
    raw = _request("ebay/search", params)
    
    # eBay 可能直接返回 list
    if isinstance(raw, list):
        results = raw
    elif isinstance(raw, dict) and raw.get("error"):
        return {"available": False, **raw}
    elif isinstance(raw, dict):
        results = raw.get("results") or raw.get("organic_results") or []
    else:
        results = []
    products = []
    for item in results:
        if not isinstance(item, dict):
            continue
        price = item.get("price") or item.get("item_price")
        if isinstance(price, dict):
            price = price.get("value") or price.get("raw")
        products.append({
            "title": item.get("title") or item.get("product_title") or item.get("name"),
            "product_id": item.get("id") or item.get("item_id"),
            "price": price,
            "condition": item.get("condition"),
            "seller": item.get("seller_name") or item.get("seller"),
            "sold_count": item.get("items_sold") or item.get("sold"),
            "url": item.get("url") or item.get("product_url") or item.get("link"),
            "image": item.get("image") or item.get("thumbnail"),
            "shipping": item.get("shipping") or item.get("shipping_cost"),
            "location": item.get("shipping_location") or item.get("location"),
        })
    
    return {
        "available": True,
        "query": query, "geo": geo, "page": page,
        "count": len(products),
        "products": products,
        "_source": "ScraperAPI Structured eBay Search",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Google Shopping API — 跨平台价格对比
# ═══════════════════════════════════════════════════════════════════════════════

def google_shopping(query: str, geo: str = "US", page: int = 1) -> dict:
    """
    Google Shopping 搜索 — 跨平台价格对比利器。
    返回多个平台的商品（Amazon/Walmart/Target/BestBuy/eBay 等）。
    """
    params = {"query": query, "country_code": geo.lower(), "page": str(page)}
    raw = _request("google/shopping", params)
    if raw.get("error"):
        return {"available": False, **raw}
    
    results = raw.get("shopping_results") or raw.get("results") or raw.get("organic_results") or []
    products = []
    for item in results:
        if not isinstance(item, dict):
            continue
        products.append({
            "title": item.get("title") or item.get("name"),
            "price": item.get("price") or item.get("extracted_price"),
            "source": item.get("source") or item.get("merchant"),
            "url": item.get("link") or item.get("url"),
            "image": item.get("thumbnail") or item.get("image"),
            "rating": item.get("rating"),
            "reviews": item.get("reviews") or item.get("reviews_count"),
            "delivery": item.get("delivery_options") or item.get("delivery"),
            "position": item.get("position"),
        })
    
    # 广告结果
    ads = raw.get("ads", []) or []
    ad_products = []
    for item in ads:
        if not isinstance(item, dict):
            continue
        ad_products.append({
            "title": item.get("title"),
            "price": item.get("price") or item.get("extracted_price"),
            "source": item.get("source") or item.get("merchant"),
            "url": item.get("link"),
        })
    
    return {
        "available": True,
        "query": query, "geo": geo, "page": page,
        "count": len(products),
        "products": products,
        "ads_count": len(ad_products),
        "ads": ad_products[:5],
        "_source": "ScraperAPI Structured Google Shopping",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 便捷方法：批量获取多个 ASIN 详情
# ═══════════════════════════════════════════════════════════════════════════════

def amazon_products_batch(asins: list, geo: str = "US") -> dict:
    """批量获取多个 ASIN 的商品详情（串行请求，适合 <10 个 ASIN）"""
    results = {}
    errors = []
    for asin in asins[:20]:  # 最多 20 个防止过度消耗
        detail = amazon_product(asin, geo=geo)
        if detail.get("available"):
            results[asin] = detail
        else:
            errors.append({"asin": asin, "error": detail.get("error")})
    return {
        "count": len(results),
        "errors": errors,
        "products": results,
        "geo": geo,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 便捷方法：跨平台价格对比
# ═══════════════════════════════════════════════════════════════════════════════

def cross_platform_price_compare(keyword: str, geo: str = "US") -> dict:
    """
    用 Google Shopping + Amazon Search + Walmart Search 做跨平台价格对比。
    返回各平台的价格区间和中位价。
    """
    import statistics
    
    results = {}
    
    # Google Shopping（聚合多平台）
    gs = google_shopping(keyword, geo=geo)
    if gs.get("available"):
        results["google_shopping"] = {
            "count": gs["count"],
            "products": gs["products"][:10],
            "sources": list(set(p.get("source", "") for p in gs["products"] if p.get("source"))),
        }
    
    # Amazon
    az = amazon_search(keyword, geo=geo)
    if az.get("available"):
        prices = [p.get("price") for p in az["products"] if p.get("price")]
        float_prices = []
        for p in prices:
            try:
                fp = float(str(p).replace("$", "").replace(",", "").strip())
                float_prices.append(fp)
            except (ValueError, TypeError):
                pass
        results["amazon"] = {
            "count": az["count"],
            "price_range": [min(float_prices), max(float_prices)] if float_prices else None,
            "price_median": statistics.median(float_prices) if float_prices else None,
            "products": az["products"][:5],
        }
    
    # Walmart
    if geo.upper() in WALMART_TLD_MAP:
        wm = walmart_search(keyword, geo=geo)
        if wm.get("available"):
            prices = [p.get("price") for p in wm["products"] if p.get("price")]
            float_prices = []
            for p in prices:
                try:
                    fp = float(str(p).replace("$", "").replace(",", "").strip())
                    float_prices.append(fp)
                except (ValueError, TypeError):
                    pass
            results["walmart"] = {
                "count": wm["count"],
                "price_range": [min(float_prices), max(float_prices)] if float_prices else None,
                "price_median": statistics.median(float_prices) if float_prices else None,
                "products": wm["products"][:5],
            }
    
    return {
        "available": True,
        "keyword": keyword, "geo": geo,
        "platforms_compared": list(results.keys()),
        "results": results,
        "_source": "ScraperAPI Cross-Platform Price Comparison",
    }
