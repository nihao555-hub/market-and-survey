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


# ─────────────────────── TikTok Shop（实时电商底盘）───────────────────────
def shop_search(keyword: str, region: str = "US", limit: int = 20) -> list[dict]:
    """实时搜 TikTok Shop 商品。返回归一化商品列表（价格/评分/评论数/销量/店铺/图/链接）。"""
    d = _get("/api/v1/tiktok/shop/web/fetch_search_products_list_v2",
             {"search_word": keyword, "region": region})
    node: Any = d
    for k in ("data", "data", "data"):
        node = node.get(k) if isinstance(node, dict) else None
    comp = (node or {}).get("component_data") if isinstance(node, dict) else None
    prods = (comp or {}).get("products") or []
    out: list[dict] = []
    for p in prods[:limit]:
        price = p.get("product_price_info") or {}
        rate = p.get("rate_info") or {}
        sold = p.get("sold_info") or {}
        seller = p.get("seller_info") or {}
        out.append({
            "product_id": p.get("product_id"),
            "title": (p.get("title") or "").strip(),
            "price": _num(price.get("sale_price_format") or price.get("sale_price_decimal")),
            "currency": price.get("currency_name") or "USD",
            "currency_symbol": price.get("currency_symbol") or "$",
            "rating": _num(rate.get("score")),
            "review_count": int(_num(rate.get("review_count")) or 0),
            "sold_count": sold.get("sold_count"),
            "shop_name": seller.get("shop_name"),
            "seller_id": seller.get("seller_id"),
            "image": _first_img(p.get("image")),
            "url": _product_url(p.get("seo_url"), p.get("product_id")),
        })
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


# 平台注册表：name → (中文标签, fetcher)
TREND_SOURCES: dict[str, tuple[str, Any]] = {
    "tiktok": ("TikTok 趋势搜索词", tiktok_trending_searchwords),
    "douyin": ("抖音热榜", douyin_hot_search),
    "weibo": ("微博热搜", weibo_hot_search),
    "xiaohongshu": ("小红书热词", xhs_trending),
}


def social_trends(platforms: Optional[list[str]] = None, limit: int = 20) -> dict[str, dict]:
    """聚合多平台实时社媒趋势。返回 {platform: {ok, label, items|error}}（逐平台容错）。"""
    platforms = platforms or list(TREND_SOURCES.keys())
    out: dict[str, dict] = {}
    for plat in platforms:
        meta = TREND_SOURCES.get(plat)
        if not meta:
            continue
        label, fn = meta
        try:
            items = fn(limit=limit)
            out[plat] = {"ok": True, "label": label, "items": items}
        except Exception as e:  # noqa: BLE001
            logger.warning(f"tikhub social_trends {plat} 失败: {e}")
            out[plat] = {"ok": False, "label": label, "error": str(e)[:200], "items": []}
    return out


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
