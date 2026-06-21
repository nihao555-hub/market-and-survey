"""
TikHub 实时社媒 + TikTok Shop 电商数据客户端。

为什么用它（对齐用户「要最新、实时性强、社媒趋势、可大规模、每天更新」）：
- **TikTok Shop**：实时商品搜索/详情/评论/分类（价格 / 评分 / 评论数 / 销量 / 店铺），
  是全球主流电商平台之一，数据每日更新——补上 2023 开源数据集「不是今日最新」的短板。
- **社媒趋势**：TikTok 每日热搜词、微博热搜、小红书热词、抖音热榜 ——
  选品 / 市场调研的实时风向标（今天大家在搜什么、什么在火）。
- 走官方化 REST API（合规、稳定、反爬轻），与亚马逊机房 IP 直连被 503/验证码完全不同。

反幻觉：任何端点失败 / 未配置 key 都如实返回 `{ok: False, status, error}`，**绝不编造**。

环境变量：
- TIKHUB_API_KEY（必填，开启 TikHub 通道）
- TIKHUB_BASE_URL（可选，默认 https://api.tikhub.io）
"""
from __future__ import annotations

import os
import time
import logging
from typing import Any, Optional

import requests

logger = logging.getLogger("tikhub")

BASE = (os.getenv("TIKHUB_BASE_URL") or "https://api.tikhub.io").rstrip("/")


def api_key() -> str:
    return (os.getenv("TIKHUB_API_KEY") or "").strip()


def is_configured() -> bool:
    """是否配置了 TikHub key（决定实时社媒 / TikTok Shop 通道是否可用）。"""
    return bool(api_key())


class TikHubError(RuntimeError):
    pass


def _get(path: str, params: Optional[dict] = None, timeout: float = 30.0, retries: int = 1) -> dict:
    """调一个 TikHub GET 端点，返回解析后的 JSON。失败抛 TikHubError（调用方如实降级）。"""
    key = api_key()
    if not key:
        raise TikHubError("TIKHUB_API_KEY 未配置")
    url = f"{BASE}{path}"
    headers = {"Authorization": f"Bearer {key}", "User-Agent": "market-survey/1.0"}
    last: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params or {}, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last = TikHubError(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:  # noqa: BLE001 网络异常如实上抛
            last = e
        time.sleep(0.8 * (attempt + 1))
    raise last or TikHubError("unknown error")


def _num(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _first_img(img: Any) -> Optional[str]:
    if isinstance(img, dict):
        lst = img.get("url_list") or []
        return lst[0] if lst else None
    return None


def _product_url(seo_url: Any, product_id: Optional[str]) -> Optional[str]:
    if isinstance(seo_url, dict):  # 有时是 {url: ...} 结构
        seo_url = seo_url.get("url") or seo_url.get("seo_url")
    if isinstance(seo_url, str) and seo_url:
        if seo_url.startswith("http"):
            return seo_url
        if seo_url.startswith("/"):
            return f"https://www.tiktok.com{seo_url}"
    if product_id:
        return f"https://shop.tiktok.com/view/product/{product_id}"
    return None


def _marketing_labels(p: dict) -> list[str]:
    """从 product_marketing_info 抽取去重后的活动标签文案（Flash sale / Free shipping 等）。"""
    mi = p.get("product_marketing_info") or {}
    pl = mi.get("placement_labels") or {}
    out: list[str] = []
    if isinstance(pl, dict):
        for arr in pl.values():
            if isinstance(arr, list):
                for lbl in arr:
                    if isinstance(lbl, dict):
                        t = (lbl.get("text") or "").strip()
                        if t and t not in out:
                            out.append(t)
    return out


def _sku_price_info(p: dict) -> dict:
    """首个 SKU 的 PriceInfo（含 origin_price / discount_format / reduce_price，最可靠的折扣来源）。"""
    si = p.get("sku_info")
    if isinstance(si, list) and si and isinstance(si[0], dict):
        pi = si[0].get("PriceInfo")
        if isinstance(pi, dict):
            return pi
    return {}


# ─────────────────────── TikTok Shop（实时电商底盘）───────────────────────
def _normalize_product(p: dict) -> dict:
    """把一条 TikTok Shop 原始商品归一化（搜索/分类榜/热销榜共用同一字段 schema）。"""
    price = p.get("product_price_info") or {}
    rate = p.get("rate_info") or {}
    sold = p.get("sold_info") or {}
    seller = p.get("seller_info") or {}
    skup = _sku_price_info(p)
    sale = _num(price.get("sale_price_format") or price.get("sale_price_decimal"))
    # 原价 / 折扣：优先用 SKU PriceInfo 的 origin_price（最准），仅当 > 现价时才认定为有折扣
    origin = _num(skup.get("origin_price_format") or skup.get("origin_price_decimal"))
    discount_pct: Optional[int] = None
    if origin and sale and origin > sale:
        discount_pct = round((origin - sale) / origin * 100)
    else:
        origin = None  # 无真实折扣则不展示原价，避免误导
    return {
        "product_id": p.get("product_id"),
        "title": (p.get("title") or "").strip(),
        "price": sale,
        "original_price": origin,
        "discount_pct": discount_pct,
        "currency": price.get("currency_name") or "USD",
        "currency_symbol": price.get("currency_symbol") or "$",
        "rating": _num(rate.get("score")),
        "review_count": int(_num(rate.get("review_count")) or 0),
        "sold_count": sold.get("sold_count"),
        "sku_count": len(p.get("sku_info") or []) or None,
        "marketing_labels": _marketing_labels(p),
        "shop_name": seller.get("shop_name"),
        "seller_id": seller.get("seller_id"),
        "shop_logo": _first_img(seller.get("shop_logo")),
        "image": _first_img(p.get("image")),
        "url": _product_url(p.get("seo_url"), p.get("product_id")),
    }


def shop_search(keyword: str, region: str = "US", limit: int = 20) -> list[dict]:
    """实时搜 TikTok Shop 商品。返回归一化商品列表（价格/评分/评论数/销量/店铺/图/链接）。"""
    endpoints = [
        "/api/v1/tiktok_shop/web/fetch_search_products_list_v2",
        "/api/v1/tiktok/shop/web/fetch_search_products_list_v2",
    ]
    last_err: Exception | None = None
    for path in endpoints:
        try:
            d = _get(path, {"search_word": keyword, "region": region})
            node: Any = d
            for k in ("data", "data", "data"):
                node = node.get(k) if isinstance(node, dict) else None
            comp = (node or {}).get("component_data") if isinstance(node, dict) else None
            prods = (comp or {}).get("products") or []
            result = [_normalize_product(p) for p in prods[:limit]]
            if result:
                return result
        except Exception as e:  # noqa: BLE001
            last_err = e
    if last_err:
        raise last_err
    return []


def _product_list_node(d: Any) -> list:
    """分类榜 / 热销榜的商品列表都在 data.data.data.productList。"""
    node: Any = d
    for k in ("data", "data", "data"):
        node = node.get(k) if isinstance(node, dict) else None
    if isinstance(node, dict):
        return node.get("productList") or node.get("products") or []
    return []


def fetch_products_category_list(region: str = "US") -> list[dict]:
    """TikTok Shop 一级品类树（每个一级类带二级子类）。用于「按品类」选品的导航。"""
    d = _get("/api/v1/tiktok/shop/web/fetch_products_category_list", {"region": region})
    cats = ((d or {}).get("data") or {}).get("data") or []

    def _norm_cat(node: dict) -> dict:
        s = node.get("self") or {}
        children = node.get("children") or []
        return {
            "category_id": s.get("category_id"),
            "category_name": s.get("category_name"),
            "category_name_en": s.get("category_name_en"),
            "level": s.get("category_level"),
            "is_leaf": s.get("is_leaf"),
            "parent_category_id": s.get("parent_category_id"),
            "children": [
                {"category_id": (c.get("self") or {}).get("category_id"),
                 "category_name": (c.get("self") or {}).get("category_name"),
                 "is_leaf": (c.get("self") or {}).get("is_leaf")}
                for c in children if isinstance(c, dict)
            ],
        }

    return [_norm_cat(c) for c in cats if isinstance(c, dict)]


def fetch_products_by_category(category_id: str, region: str = "US",
                                limit: int = 20, offset: int = 0) -> list[dict]:
    """某品类下的实时在售商品（同 shop_search 的归一化 schema）。用于「按品类 Top5/榜单」。"""
    d = _get("/api/v1/tiktok/shop/web/fetch_products_by_category_id",
             {"category_id": str(category_id), "region": region, "offset": str(offset)})
    return [_normalize_product(p) for p in _product_list_node(d)[:limit]]


def fetch_hot_selling_products(region: str = "US", limit: int = 20) -> list[dict]:
    """TikTok Shop 实时热销榜（同 shop_search 的归一化 schema）。用于「实时爆品雷达」。

    按优先级尝试多个端点版本（API 版本迭代可能导致旧端点 404）。
    全部失败时回退到 shop_search 热度排序。
    """
    endpoints = [
        # v2 新端点
        ("/api/v1/tiktok_shop/web/fetch_hot_selling_products_list", {"region": region}),
        ("/api/v1/tiktok_shop/app/fetch_hot_selling_products_list",
         {"region": region, "count": str(limit)}),
        # v1 旧端点（可能已废弃但保留兼容）
        ("/api/v1/tiktok/shop/web/fetch_hot_selling_products_list", {"region": region}),
        ("/api/v1/tiktok/shop/app/fetch_hot_selling_products_list",
         {"region": region, "count": str(limit)}),
    ]
    last_err: Exception | None = None
    for path, params in endpoints:
        try:
            d = _get(path, params)
            prods = [_normalize_product(p) for p in _product_list_node(d)[:limit]]
            if prods:
                return prods
        except Exception as e:  # noqa: BLE001
            last_err = e
    # 全部端点失败时，回退到 shop_search（空词=热门）作为替代
    try:
        prods = shop_search("", region=region, limit=limit)
        if prods:
            return prods
    except Exception as e:  # noqa: BLE001
        last_err = last_err or e
    if last_err:
        raise last_err
    return []


# ─────────────────── 话题热度曲线（历史趋势的可用替代）+ 达人侦察 ───────────────────
def trending_hashtags(time_range: int = 7, country: str = "US", limit: int = 10) -> list[dict]:
    """TikTok Creative Center 热门话题榜。

    用于「趋势探索 / 机会挖掘」：返回每个话题的浏览量(vv)、发布数、排名、
    `popularity_curve`（time_range 天的时间序列，可看声量拐点）以及 `top_creators`
    （顺带做达人侦察——官方 search_creators 已废弃，用这个替代）。
    time_range 取值通常为 7 / 30 / 120 天。
    """
    d = _get("/api/v1/tiktok/ads/get_trends_hashtag_list",
             {"time_range": str(time_range), "country_code": country, "limit": str(limit)})
    items = ((d or {}).get("data") or {}).get("items") or []
    out: list[dict] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        curve = [{"t": pt.get("time") or pt.get("timestamp"), "v": _num(pt.get("value"))}
                 for pt in (it.get("popularityCurve") or it.get("popularity_curve") or [])
                 if isinstance(pt, dict)]
        creators = []
        for c in (it.get("topCreators") or it.get("top_creators") or [])[:5]:
            if isinstance(c, dict):
                creators.append({
                    "nickname": c.get("nickName") or c.get("nickname") or c.get("name"),
                    "avatar": c.get("avatarUrl") or c.get("avatar"),
                    "followers": c.get("followerCount") or c.get("follower_count"),
                })
        out.append({
            "hashtag": it.get("hashtagName") or it.get("hashtag_name"),
            "hashtag_id": it.get("hashtagID") or it.get("hashtag_id"),
            "views": it.get("vv"),
            "publish_count": it.get("publishCnt") or it.get("publish_cnt"),
            "rank": it.get("rankIndex") or it.get("rank_index"),
            "popularity_curve": curve,
            "top_creators": creators,
        })
    return out


# ─────────────────────── 需求验证层（Reddit / YouTube 口碑）───────────────────────
def reddit_search(query: str, time_range: str = "year", sort: str = "relevance",
                  limit: int = 10) -> list[dict]:
    """Reddit 帖子搜索（真实用户讨论 = 需求/吐槽/比较的一手声音）。

    用于「受众洞察 / 机会挖掘」的需求验证：返回标题、所在子版块、分数、评论数、
    发帖时间、正文摘要与链接。time_range: hour/day/week/month/year/all；sort: relevance/hot/top/new。
    """
    d = _get("/api/v1/reddit/app/fetch_dynamic_search",
             {"query": query, "search_type": "posts", "sort": sort, "time_range": time_range})
    posts: list[dict] = []

    def _walk(o: Any) -> None:
        if isinstance(o, dict):
            if o.get("__typename") == "SearchPost" and isinstance(o.get("post"), dict):
                posts.append(o["post"])
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)

    _walk((d or {}).get("data"))
    out: list[dict] = []
    for p in posts[:limit]:
        sub = p.get("subreddit") or {}
        content = p.get("content") or {}
        body = content.get("markdown") if isinstance(content, dict) else None
        out.append({
            "title": (p.get("postTitle") or "").strip(),
            "subreddit": sub.get("prefixedName") if isinstance(sub, dict) else None,
            "subreddit_subscribers": (sub.get("subscribersCount") if isinstance(sub, dict) else None),
            "score": p.get("score"),
            "comments": p.get("commentCount"),
            "created_at": p.get("createdAt"),
            "snippet": (body or "")[:500] or None,
            "url": p.get("url") or p.get("permalink"),
        })
    return [o for o in out if o["title"]]


def _yt_text(v: Any) -> Optional[str]:
    """YouTube innertube 文本字段：可能是 {simpleText} 或 {runs:[{text}]}。"""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        if v.get("simpleText"):
            return v["simpleText"]
        runs = v.get("runs")
        if isinstance(runs, list):
            return "".join(r.get("text", "") for r in runs if isinstance(r, dict)) or None
    return None


def youtube_search(query: str, country: str = "US", language: str = "en",
                   limit: int = 12) -> list[dict]:
    """YouTube 视频搜索（测评/开箱 = 内容偏好 + 触达渠道信号）。

    用于「受众洞察 / 竞品分析」：返回标题、频道、观看量、发布时间、时长、链接与描述摘要。
    """
    d = _get("/api/v1/youtube/web/get_general_search",
             {"search_query": query, "country_code": country, "language_code": language})
    vids: list[dict] = []

    def _walk(o: Any) -> None:
        if isinstance(o, dict):
            if o.get("videoId") and ("title" in o):
                vids.append(o)
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)

    _walk((d or {}).get("data"))
    out: list[dict] = []
    seen: set[str] = set()
    for v in vids:
        vid = v.get("videoId")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        snippets = v.get("detailedMetadataSnippets") or []
        snip = None
        if snippets and isinstance(snippets[0], dict):
            snip = _yt_text(snippets[0].get("snippetText"))
        out.append({
            "video_id": vid,
            "title": _yt_text(v.get("title")),
            "channel": _yt_text(v.get("ownerText") or v.get("longBylineText")),
            "views": _yt_text(v.get("viewCountText")),
            "published": _yt_text(v.get("publishedTimeText")),
            "length": _yt_text((v.get("lengthText") or {})),
            "snippet": (snip or "")[:300] or None,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
        if len(out) >= limit:
            break
    return out


def shop_reviews(product_id: str, region: str = "US", limit: int = 20) -> list[dict]:
    """实时抓 TikTok Shop 某商品的真实评论。区域不匹配 / 无评论时返回空列表（不编造）。"""
    d = _get("/api/v1/tiktok/shop/web/fetch_product_reviews_v2",
             {"product_id": product_id, "region": region})
    inner = ((d or {}).get("data") or {}).get("data") or {}
    if inner.get("error_code"):  # 如 region 不匹配
        return []
    reviews = inner.get("reviews") or inner.get("review_list") or inner.get("items") or []
    out: list[dict] = []
    for r in reviews[:limit]:
        if not isinstance(r, dict):
            continue
        out.append({
            "text": r.get("review_text") or r.get("content") or r.get("text") or "",
            "rating": _num(r.get("rating") or r.get("score") or r.get("star")),
            "author": (r.get("user") or {}).get("nickname") if isinstance(r.get("user"), dict) else r.get("author"),
            "ts": r.get("create_time") or r.get("review_time"),
        })
    return [r for r in out if r["text"]]


def product_stats(products: list[dict]) -> dict:
    """从商品列表算价格带 / 加权均分 / 店铺集中度（与 open_dataset.product_stats 对齐风格）。"""
    prices = sorted(p["price"] for p in products if isinstance(p.get("price"), (int, float)))
    rated = [(p["rating"], p["review_count"]) for p in products
             if isinstance(p.get("rating"), (int, float)) and (p.get("review_count") or 0) > 0]
    wsum = sum(rc for _, rc in rated)
    wavg = round(sum(rt * rc for rt, rc in rated) / wsum, 2) if wsum else None
    shops: dict[str, int] = {}
    for p in products:
        s = p.get("shop_name")
        if s:
            shops[s] = shops.get(s, 0) + 1
    top_shops = sorted(shops.items(), key=lambda kv: -kv[1])[:5]
    return {
        "count": len(products),
        "price_min": prices[0] if prices else None,
        "price_max": prices[-1] if prices else None,
        "price_median": prices[len(prices) // 2] if prices else None,
        "weighted_avg_rating": wavg,
        "total_reviews": int(wsum),
        "top_shops": [{"name": n, "count": c} for n, c in top_shops],
    }


def shop_summary(keyword: str, products: list[dict]) -> str:
    if not products:
        return f"TikTok Shop 未搜到「{keyword}」的在售商品"
    s = product_stats(products)
    sym = products[0].get("currency_symbol", "$")
    shops = "、".join(x["name"] for x in s["top_shops"][:3] if x.get("name"))
    parts = [f"TikTok Shop 实时 {s['count']} 件在售"]
    if s["price_min"] is not None:
        parts.append(f"价 {sym}{s['price_min']}–{sym}{s['price_max']}（中位 {sym}{s['price_median']}）")
    if s["weighted_avg_rating"] is not None:
        parts.append(f"加权均分 {s['weighted_avg_rating']}（{s['total_reviews']} 条评论）")
    if shops:
        parts.append(f"主要店铺：{shops}")
    return "；".join(parts)


# ─────────────────────── 社媒实时趋势（多平台热搜 / 热词）───────────────────────
def tiktok_trending_searchwords(limit: int = 30) -> list[dict]:
    """TikTok 每日趋势搜索词（今天 TikTok 用户在搜什么）。"""
    d = _get("/api/v1/tiktok/web/fetch_trending_searchwords")
    words = ((d or {}).get("data") or {}).get("trending_search_words") or []
    out = [{"keyword": w.get("trendingSearchWord"), "kind": w.get("trendingSearchWordType", "")}
           for w in words if w.get("trendingSearchWord")]
    return out[:limit]


def weibo_hot_search(limit: int = 30) -> list[dict]:
    """微博热搜榜。TikHub 偶发 400「please retry」，故按多端点回退。"""
    endpoints = [
        "/api/v1/weibo/web_v2/fetch_hot_search_summary",
        "/api/v1/weibo/web_v2/fetch_hot_search",
        "/api/v1/weibo/app/fetch_hot_search",
    ]
    last: Optional[Exception] = None
    for ep in endpoints:
        try:
            d = _get(ep)
        except Exception as e:  # noqa: BLE001
            last = e
            continue
        items = (d or {}).get("data") or []
        if isinstance(items, dict):
            items = items.get("data") or items.get("hot_search") or items.get("realtime") or []
        out = [{"keyword": it.get("keyword") or it.get("word") or it.get("note"),
                "rank": it.get("rank"), "heat": it.get("heat") or it.get("num"),
                "tag": it.get("tag")}
               for it in items if isinstance(it, dict) and (it.get("keyword") or it.get("word") or it.get("note"))]
        if out:
            return out[:limit]
    if last:
        raise last
    return []


def xhs_trending(limit: int = 30) -> list[dict]:
    """小红书热词 / 热搜。"""
    d = _get("/api/v1/xiaohongshu/web_v3/fetch_trending")
    queries = (((d or {}).get("data") or {}).get("data") or {}).get("queries") or []
    out = [{"keyword": q.get("searchWord") or q.get("title"), "desc": q.get("desc", "")}
           for q in queries if isinstance(q, dict) and (q.get("searchWord") or q.get("title"))]
    return out[:limit]


def douyin_hot_search(limit: int = 30) -> list[dict]:
    """抖音热榜（热搜词 + 热度值）。"""
    d = _get("/api/v1/douyin/app/v3/fetch_hot_search_list")
    words = (((d or {}).get("data") or {}).get("data") or {}).get("word_list") or []
    out = [{"keyword": w.get("word"), "heat": w.get("hot_value"),
            "views": w.get("view_count"), "label": w.get("label")}
           for w in words if isinstance(w, dict) and w.get("word")]
    return out[:limit]


def kuaishou_hot_list(limit: int = 30) -> list[dict]:
    """快手热榜（热词 + 热度 + 浏览量）。"""
    d = _get("/api/v1/kuaishou/web/fetch_kuaishou_hot_list_v2", params={"board_type": "1"})
    hots = ((d or {}).get("data") or {}).get("hots") or []
    out = [{"keyword": h.get("keyword"), "heat": h.get("hotValue"),
            "views": h.get("viewCount")}
           for h in hots if isinstance(h, dict) and h.get("keyword")]
    return out[:limit]


def bilibili_hot_search(limit: int = 30) -> list[dict]:
    """B 站热搜榜（热词 + 热度分）。"""
    d = _get("/api/v1/bilibili/web/fetch_hot_search", params={"limit": max(limit, 30)})
    lst = ((((d or {}).get("data") or {}).get("data") or {}).get("trending") or {}).get("list") or []
    out = [{"keyword": it.get("show_name") or it.get("keyword"), "heat": it.get("heat_score")}
           for it in lst if isinstance(it, dict) and (it.get("show_name") or it.get("keyword"))]
    return out[:limit]


def twitter_trending(limit: int = 30) -> list[dict]:
    """X / Twitter 全球趋势（默认美国）。"""
    d = _get("/api/v1/twitter/web/fetch_trending", params={"country": "UnitedStates"})
    trends = ((d or {}).get("data") or {}).get("trends") or []
    out = [{"keyword": t.get("name"), "tag": t.get("context")}
           for t in trends if isinstance(t, dict) and t.get("name")]
    return out[:limit]


def lemon8_hot_keywords(limit: int = 30) -> list[dict]:
    """Lemon8 热搜词（字节跳动海外种草社区）。"""
    d = _get("/api/v1/lemon8/app/fetch_hot_search_keywords")
    words = (((d or {}).get("data") or {}).get("data") or {}).get("hot_words") or []
    out = [{"keyword": w.get("query")} for w in words
           if isinstance(w, dict) and w.get("query")]
    return out[:limit]


# 平台注册表：name → (中文标签, fetcher)。逐个用便宜调用实测可用后才登记。
TREND_SOURCES: dict[str, tuple[str, Any]] = {
    "tiktok": ("TikTok 趋势搜索词", tiktok_trending_searchwords),
    "douyin": ("抖音热榜", douyin_hot_search),
    "weibo": ("微博热搜", weibo_hot_search),
    "xiaohongshu": ("小红书热词", xhs_trending),
    "kuaishou": ("快手热榜", kuaishou_hot_list),
    "bilibili": ("B站热搜", bilibili_hot_search),
    "twitter": ("X/Twitter 趋势", twitter_trending),
    "lemon8": ("Lemon8 热词", lemon8_hot_keywords),
}


def social_trends(platforms: Optional[list[str]] = None, limit: int = 20) -> dict[str, dict]:
    """聚合多平台实时社媒趋势。返回 {platform: {ok, label, items|error}}（逐平台容错）。"""
    platforms = platforms or list(TREND_SOURCES.keys())
    out: dict[str, dict] = {}
    for i, plat in enumerate(platforms):
        meta = TREND_SOURCES.get(plat)
        if not meta:
            continue
        label, fn = meta
        if i:
            time.sleep(0.4)  # 限流友好（微博等限 1 次/秒）
        try:
            items = fn(limit=limit)
            out[plat] = {"ok": True, "label": label, "items": items}
        except Exception as e:  # noqa: BLE001
            logger.warning(f"tikhub social_trends {plat} 失败: {e}")
            out[plat] = {"ok": False, "label": label, "error": str(e)[:200], "items": []}
    return out


# ─────────────────────── 新增 API：搜索联想 / 店铺商品 / 达人带货 ───────────────────────
def shop_search_suggestions(keyword: str, region: str = "US", limit: int = 10) -> list[dict]:
    """TikTok Shop 搜索联想词（买家输入时的热门补全建议）。用于关键词扩展和选品发散。"""
    d = _get("/api/v1/tiktok/shop/web/fetch_search_word_suggestion_v2",
             {"search_word": keyword, "region": region})
    inner = ((d or {}).get("data") or {}).get("data") or {}
    items = inner.get("data") if isinstance(inner.get("data"), list) else []
    out: list[dict] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        word = it.get("search_word") or it.get("word") or ""
        if word:
            out.append({"keyword": word.strip(), "raw": it})
    return out


def shop_seller_products(seller_id: str, region: str = "US", limit: int = 30) -> list[dict]:
    """获取某 TikTok Shop 店铺的所有在售商品。用于竞品店铺分析。"""
    d = _get("/api/v1/tiktok/shop/web/fetch_seller_products_list_v2",
             {"seller_id": seller_id, "region": region})
    node: Any = d
    for k in ("data", "data", "data"):
        node = node.get(k) if isinstance(node, dict) else None
    prods = (node or {}).get("products") or [] if isinstance(node, dict) else []
    return [_normalize_product(p) for p in prods[:limit]]


def shop_product_detail(product_id: str, region: str = "US") -> dict:
    """获取 TikTok Shop 单个商品的详细信息（含完整 SKU / 描述 / 图片列表）。"""
    d = _get("/api/v1/tiktok/shop/web/fetch_product_detail_v2",
             {"product_id": product_id, "region": region})
    node: Any = d
    for k in ("data", "data", "data"):
        node = node.get(k) if isinstance(node, dict) else None
    if isinstance(node, dict):
        return _normalize_product(node)
    return {}


def creator_showcase_products(unique_id: str, limit: int = 30) -> list[dict]:
    """获取 TikTok 达人展示橱窗中的带货商品列表。用于达人选品侦察。"""
    d = _get("/api/v1/tiktok/app/v3/fetch_creator_showcase_product_list",
             {"unique_id": unique_id, "count": str(limit)})
    node: Any = d
    for k in ("data", "data"):
        node = node.get(k) if isinstance(node, dict) else None
    prods = (node or {}).get("products") or [] if isinstance(node, dict) else []
    out: list[dict] = []
    for p in prods[:limit]:
        if not isinstance(p, dict):
            continue
        out.append({
            "product_id": p.get("product_id"),
            "title": (p.get("title") or "").strip(),
            "price": _num(p.get("price") or (p.get("price_info") or {}).get("sale_price")),
            "image": _first_img(p.get("image")),
            "url": _product_url(p.get("seo_url"), p.get("product_id")),
            "commission_rate": p.get("commission_rate"),
        })
    return out


def instagram_search_hashtags(query: str, limit: int = 10) -> list[dict]:
    """Instagram 话题搜索（跨平台验证趋势热度）。"""
    d = _get("/api/v1/instagram/v3/search_hashtags", {"query": query})
    items = ((d or {}).get("data") or {}).get("items") or []
    out: list[dict] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        hashtag = it.get("hashtag") or {}
        out.append({
            "name": hashtag.get("name") if isinstance(hashtag, dict) else it.get("name"),
            "media_count": hashtag.get("media_count") if isinstance(hashtag, dict) else it.get("media_count"),
            "search_subtitle": it.get("search_result_subtitle"),
        })
    return [h for h in out if h.get("name")]


def douyin_brand_hot_search(limit: int = 20) -> list[dict]:
    """抖音品牌热搜榜（品牌在抖音的热度排行，中国市场风向标）。"""
    d = _get("/api/v1/douyin/app/v3/fetch_brand_hot_search_list")
    items = (((d or {}).get("data") or {}).get("data") or {}).get("brand_list") or []
    out: list[dict] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        out.append({
            "brand_name": it.get("brand_name") or it.get("word"),
            "heat": it.get("hot_value"),
            "rank": it.get("position"),
        })
    return [b for b in out if b.get("brand_name")]


def kuaishou_shopping_top(limit: int = 20) -> list[dict]:
    """快手电商排行榜（带货商品热度排行）。"""
    d = _get("/api/v1/kuaishou/app/fetch_shopping_top_list")
    items = ((d or {}).get("data") or {}).get("items") or []
    out: list[dict] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        out.append({
            "title": it.get("title") or it.get("name"),
            "price": _num(it.get("price")),
            "sales": it.get("sales") or it.get("sold_count"),
            "rank": it.get("rank"),
        })
    return [p for p in out if p.get("title")]


if __name__ == "__main__":
    import json
    print("configured:", is_configured())
    if is_configured():
        prods = shop_search("garlic press", limit=5)
        print(shop_summary("garlic press", prods))
        print(json.dumps(prods[:2], ensure_ascii=False, indent=2))
        tr = social_trends(limit=8)
        for plat, r in tr.items():
            tag = "ok" if r["ok"] else "ERR"
            head = ", ".join(i.get("keyword", "") for i in r["items"][:6])
            print(f"[{tag}] {r['label']}: {head}")
