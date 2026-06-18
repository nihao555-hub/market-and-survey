"""
开源电商大数据底子：Amazon Reviews 2023（McAuley-Lab / UCSD，HuggingFace 公开）。

为什么用它（对齐用户「开源数据，量庞大、精准、反爬没那么严」）：
- ≈ 5.7 亿条真实评论 + 4800 万真实商品元数据（标题/价格/评分/评分数/品牌/类目/卖点）
- 公开数据集，HTTP 直接流式拉取，**零反爬、零封禁**，与亚马逊直连被 503/验证码完全不同
- 做选品/市场调研的「精准底盘」：真实价格带、评分分布、品牌格局、人气（rating_number）

实现：按需流式扫描某品类的 meta_*.jsonl（一行一个商品），在标题里匹配追踪词，
取人气最高的若干件。绝不编造——拿不到就返回空，由上层如实标注。

注意：该数据集是静态快照（覆盖至 2023），用作「底子/广度」；「今日最新」由实时层
（Amazon 自动补全等）另行补充。
"""
from __future__ import annotations

import json
import re
import time
from typing import Iterable, Optional

import requests
from loguru import logger

_HF_BASE = ("https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/"
            "resolve/main/raw/meta_categories/meta_{cat}.jsonl")

# 跨境选品常见的大类（按命中概率排序；每个词会在这些已扫描的品类里找匹配）
DEFAULT_CATEGORIES = [
    "Home_and_Kitchen",
    "Electronics",
    "Sports_and_Outdoors",
    "Tools_and_Home_Improvement",
    "Pet_Supplies",
    "Health_and_Household",
    "Beauty_and_Personal_Care",
    "Office_Products",
]

# 每个品类最多扫描多少行（控制时长；命中足够即提前停）
DEFAULT_MAX_LINES = 200_000
# 每个词保留多少件（按人气 rating_number 取 Top）
DEFAULT_PER_TERM = 15


def _parse_price(raw) -> Optional[float]:
    """数据集 price 可能是 None / "24.95" / "$24.95" / "from 19.99"，安全解析为 float。"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if raw > 0 else None
    m = re.search(r"\d+(?:\.\d+)?", str(raw).replace(",", ""))
    if not m:
        return None
    try:
        v = float(m.group(0))
        return v if v > 0 else None
    except ValueError:
        return None


def _first_image(images) -> str:
    """images 是 [{thumb, large, hi_res, variant}, ...]，取一张高清图 URL。"""
    if isinstance(images, list):
        for im in images:
            if isinstance(im, dict):
                for k in ("hi_res", "large", "thumb"):
                    if im.get(k):
                        return im[k]
    return ""


def _normalize(o: dict, term: str) -> dict:
    asin = o.get("parent_asin") or ""
    feats = o.get("features") or []
    if not isinstance(feats, list):
        feats = []
    cats = o.get("categories") or []
    if not isinstance(cats, list):
        cats = []
    return {
        "term": term,
        "asin": asin,
        "title": (o.get("title") or "").strip(),
        "price": _parse_price(o.get("price")),
        "avg_rating": o.get("average_rating"),
        "rating_number": int(o.get("rating_number") or 0),
        "store": (o.get("store") or "").strip(),
        "main_category": o.get("main_category") or "",
        "categories": cats[:6],
        "features": [str(f)[:160] for f in feats[:5]],
        "image": _first_image(o.get("images")),
        "url": f"https://www.amazon.com/dp/{asin}" if asin else "",
        "source": "amazon_reviews_2023",
    }


def _iter_jsonl(url: str, max_lines: int, timeout: int = 90) -> Iterable[dict]:
    """流式逐行读取一个远端 jsonl（不落盘整文件），最多 max_lines 行。"""
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    try:
        n = 0
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            n += 1
            if n > max_lines:
                break
            try:
                yield json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
    finally:
        r.close()


def search_category(category: str, terms: list[str], *,
                    max_lines: int = DEFAULT_MAX_LINES,
                    per_term: int = DEFAULT_PER_TERM,
                    min_rating_number: int = 1) -> dict[str, list[dict]]:
    """扫描一个品类的商品元数据，给每个词匹配标题命中的真实商品。

    返回 {term: [product, ...]}（仅含本品类命中的；上层负责跨品类合并 + 排序裁剪）。
    """
    terms_lc = [(t, t.lower()) for t in terms]
    found: dict[str, list[dict]] = {t: [] for t in terms}
    url = _HF_BASE.format(cat=category)
    t0 = time.time()
    scanned = 0
    try:
        for o in _iter_jsonl(url, max_lines):
            scanned += 1
            title = (o.get("title") or "").lower()
            if not title:
                continue
            if int(o.get("rating_number") or 0) < min_rating_number:
                continue
            for orig, lc in terms_lc:
                if lc in title:
                    found[orig].append(_normalize(o, orig))
    except Exception as e:
        logger.warning(f"open_dataset 扫描 {category} 失败: {e}")
    logger.info(f"open_dataset {category}: 扫描 {scanned} 行 / {round(time.time()-t0,1)}s，"
                f"命中 {sum(len(v) for v in found.values())} 件")
    return found


def ingest_products(terms: list[str], *,
                    categories: Optional[list[str]] = None,
                    max_lines: int = DEFAULT_MAX_LINES,
                    per_term: int = DEFAULT_PER_TERM) -> dict[str, list[dict]]:
    """对一批词从开源数据集取真实商品底子。按人气（rating_number）取每词 Top N。

    返回 {term: [product, ...]}（已按人气降序裁剪到 per_term）。
    """
    categories = categories or DEFAULT_CATEGORIES
    terms = [t for t in (terms or []) if t and re.search(r"[a-zA-Z]", t)]
    if not terms:
        return {}

    # 扫描所有候选品类（每个品类只扫一次、同时匹配全部词），跨品类合并后按人气全局排序。
    # 不做「命中即停」——否则一个词可能停在弱相关品类（如「yoga mat」停在家居挂毯），
    # 错过更相关品类里评分数更高的真品。
    acc: dict[str, list[dict]] = {t: [] for t in terms}
    for cat in categories:
        part = search_category(cat, terms, max_lines=max_lines, per_term=per_term)
        for t, items in part.items():
            acc[t].extend(items)

    out: dict[str, list[dict]] = {}
    for t, items in acc.items():
        # 去重（同 asin）+ 按人气降序 + 裁剪
        seen: set[str] = set()
        uniq: list[dict] = []
        for p in sorted(items, key=lambda x: x.get("rating_number") or 0, reverse=True):
            a = p.get("asin")
            if a and a in seen:
                continue
            if a:
                seen.add(a)
            uniq.append(p)
        out[t] = uniq[:per_term]
    return out


def product_stats(products: list[dict]) -> dict:
    """从一组真实商品算选品概览：价格带（min/中位/max）、加权均分、品牌集中度。"""
    prices = sorted(p["price"] for p in products if p.get("price"))
    ratings = [(p.get("avg_rating"), p.get("rating_number") or 0)
               for p in products if p.get("avg_rating")]
    brands: dict[str, int] = {}
    total_reviews = 0
    for p in products:
        if p.get("store"):
            brands[p["store"]] = brands.get(p["store"], 0) + 1
        total_reviews += p.get("rating_number") or 0

    def _median(xs):
        if not xs:
            return None
        n = len(xs)
        return xs[n // 2] if n % 2 else round((xs[n // 2 - 1] + xs[n // 2]) / 2, 2)

    wsum = sum(r * c for r, c in ratings)
    wcnt = sum(c for _, c in ratings)
    weighted_avg = round(wsum / wcnt, 2) if wcnt else None
    top_brands = sorted(brands.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {
        "count": len(products),
        "price_min": prices[0] if prices else None,
        "price_median": _median(prices),
        "price_max": prices[-1] if prices else None,
        "priced_count": len(prices),
        "weighted_avg_rating": weighted_avg,
        "total_reviews": total_reviews,
        "brand_count": len(brands),
        "top_brands": [{"name": n, "products": c} for n, c in top_brands],
    }


def summarize(term: str, products: list[dict]) -> str:
    """人类可读摘要（落库 summary 字段用）。"""
    if not products:
        return "开源数据集未匹配到该词的商品"
    s = product_stats(products)
    parts = [f"开源数据集 {s['count']} 件真实商品"]
    if s["price_min"] is not None:
        parts.append(f"价格 ${s['price_min']}–${s['price_max']}（中位 ${s['price_median']}）")
    if s["weighted_avg_rating"] is not None:
        parts.append(f"加权均分 {s['weighted_avg_rating']}（{s['total_reviews']} 条评分）")
    if s["top_brands"]:
        parts.append("主要品牌：" + "、".join(b["name"] for b in s["top_brands"][:3]))
    return "；".join(parts)


if __name__ == "__main__":
    res = ingest_products(["garlic press", "yoga mat"], max_lines=120_000, per_term=8)
    for term, items in res.items():
        print(f"\n=== {term} ({len(items)}) ===")
        print(summarize(term, items))
        for p in items[:3]:
            print(f"  - {p['title'][:60]} | ${p['price']} | {p['avg_rating']}({p['rating_number']}) | {p['store']}")
