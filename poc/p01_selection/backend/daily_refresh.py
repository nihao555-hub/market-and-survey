"""
每日定时刷新（北京 0 点 = UTC 16:00）。

对一批追踪词跑**真实**数据采集并落库快照。分层（反幻觉：拿不到的如实标注，不编造）：
- Tier 1（免代理，当前可用）：Amazon 自动补全买家搜索词 / Google Trends 趋势 / 5 年季节性
- Tier 2（需美国代理 / 付费 API）：Amazon/Walmart 等商品级 BSR / 价格 / 评论。
  通过 US_PROXY 隧道或付费 API key 启用；通道不可用时本层如实标注 `unavailable`，
  不阻塞 Tier 1，也不编造任何商品数字。

调度入口：backend.app 在 startup 注册 APScheduler BackgroundScheduler，cron `0 16 * * *`(UTC)。
也可手动触发：POST /admin/daily-refresh，或 GraphQL mutation triggerDailyRefresh。
"""
from __future__ import annotations

import os
import re
import sys
import time
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 让 modules.* 可被导入（与 backend/app.py 一致：把 p01_selection 加进 sys.path）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from backend import storage as st

# 默认追踪词（跨境选品常见大批量品类；会与启用的监控规则、近期调研线程合并去重）。
# 这是「真实数据底子」的固定词表：每次刷新都覆盖全表，保证大批量底盘持续在线、
# 不会被下一次小批量刷新覆盖（前端只展示最近一个批次）。开源数据集底子已缓存复用，
# 故扩到几十个词也不会显著增加耗时；实时层（TikTok Shop）成本见 README/报告说明。
DEFAULT_SEED_TERMS = [
    # 厨房 / 家居
    "garlic press", "stainless steel water bottle", "silicone spatula", "kitchen scale",
    "vegetable chopper", "knife sharpener", "coffee grinder", "dish drying rack",
    "food storage containers",
    # 3C / 数码配件
    "wireless earbuds", "phone holder", "bluetooth speaker", "usb c charger",
    "laptop stand", "car phone mount", "led strip lights", "ring light",
    # 运动 / 户外
    "yoga mat", "resistance bands", "jump rope", "foam roller", "camping lantern",
    "hiking backpack",
    # 宠物
    "pet hair remover", "dog chew toy", "cat litter mat", "slow feeder bowl",
    # 美妆 / 个护
    "jade roller", "facial cleansing brush", "hair straightener brush", "makeup organizer",
    # 健康 / 家用
    "posture corrector", "massage gun", "humidifier", "air purifier",
    # 办公
    "desk organizer", "standing desk", "mechanical keyboard", "blue light glasses",
]

# 首次启动时只跑一小批核心词（加速数据上线），后续 schedule 跑完整词表。
STARTUP_SEED_TERMS = [
    "garlic press", "wireless earbuds", "yoga mat", "pet hair remover",
    "jade roller", "humidifier", "desk organizer", "led strip lights",
]

# 单次刷新最多处理多少个词（控制时长与限流风险）。默认足够容纳整张种子词表 +
# 若干监控规则/近期调研词；如需压实时层成本可用 DAILY_REFRESH_MAX_TERMS 调小。
MAX_TERMS = int(os.getenv("DAILY_REFRESH_MAX_TERMS", "50"))

# 开源数据集底子（Amazon Reviews 2023）配置
# 默认关闭以加速首次刷新（Render 免费实例下载 HuggingFace 大文件极慢）
OPEN_DATASET_ENABLED = os.getenv("OPEN_DATASET_ENABLED", "0") == "1"
OPEN_DATASET_TTL_DAYS = int(os.getenv("OPEN_DATASET_TTL_DAYS", "7"))
OPEN_DATASET_MAX_LINES = int(os.getenv("OPEN_DATASET_MAX_LINES", "150000"))
OPEN_DATASET_PER_TERM = int(os.getenv("OPEN_DATASET_PER_TERM", "30"))
_OPEN_CACHE_KEY = "open_dataset:cache:{tenant}"

_RUN_LOCK = threading.Lock()
_STATE_KEY = "daily_refresh:state:{tenant}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_key(tenant_id: str) -> str:
    return _STATE_KEY.format(tenant=tenant_id)


# ─────────── Tier 2 通道可用性（决定是否真去爬电商商品级数据）───────────
def _proxy_alive(timeout: float = 6.0) -> bool:
    """快速健康检查 US_PROXY 是否真的在转发。默认指向本地 127.0.0.1:10808，
    没有起隧道时这里会很快失败 → Tier 2 标 unavailable（不浪费熔断重试时间）。"""
    proxy = (os.getenv("US_PROXY") or "").strip()
    if not proxy:
        return False
    try:
        import requests
        r = requests.get(
            "https://www.amazon.com/robots.txt",
            proxies={"http": proxy, "https": proxy},
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        return r.status_code < 500
    except Exception:
        return False


def _paid_api_available() -> bool:
    return any(os.getenv(k) for k in ("DATAFORSEO_LOGIN", "KEEPA_API_KEY", "RAPIDAPI_KEY"))


def _tikhub_ok() -> bool:
    try:
        from modules import tikhub
        return tikhub.is_configured()
    except Exception:
        return False


def tier2_channel_ok() -> bool:
    """电商商品级数据通道是否就绪。

    TikHub（实时 TikTok Shop 商品/评论）已就绪即视为可用；其次是美国代理 / 付费 API。
    """
    return _tikhub_ok() or _proxy_alive() or _paid_api_available()


# ─────────── 追踪词汇总 ───────────
def collect_terms(tenant_id: str = "dev_tenant", extra: Optional[list[str]] = None) -> list[str]:
    """汇总本次要刷新的追踪词：启用的监控规则 + 近期调研线程品类 + 默认种子词。

    电商搜索词以英文为主，故过滤掉不含 ASCII 字母的项（如中文监控名），避免拿去打 Amazon 拿空。
    """
    terms: list[str] = []
    try:
        for m in st.list_monitors(tenant_id):
            if getattr(m, "enabled", False) and m.name:
                terms.append(m.name)
    except Exception:
        pass
    try:
        for t in st.list_threads(tenant_id)[:20]:
            head = (t.title or "").split("·")[0].strip()
            if head:
                terms.append(head)
    except Exception:
        pass
    terms.extend(extra or [])
    terms.extend(DEFAULT_SEED_TERMS)

    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        t = (t or "").strip()
        key = t.lower()
        if not t or key in seen:
            continue
        # 电商搜索词须为干净英文：要有 ASCII 字母，且不含 CJK（避免「garlic press 压器」这类脏词打空）
        if not re.search(r"[a-zA-Z]", t):
            continue
        if re.search(r"[\u4e00-\u9fff]", t):
            continue
        seen.add(key)
        out.append(t)
    return out[:MAX_TERMS]


# ─────────── 单词采集 ───────────
def _collect_tier1(term: str, geo: str) -> list[dict]:
    """免代理可得的真实数据。返回若干 {source, tier, status, real_data, summary, payload}。"""
    out: list[dict] = []

    # 1) Amazon 自动补全（买家真实购物搜索词，按热度排序）
    try:
        from modules.amazon_keywords import get_amazon_keyword_suggestions
        r = get_amazon_keyword_suggestions(term, geo=geo, deep=False)
        if r.get("suggestions"):
            mods = ", ".join(m.get("word", "") for m in (r.get("top_modifiers") or [])[:6])
            out.append(dict(
                source="amazon_keywords", tier=1, status="ok",
                real_data=bool(r.get("_real_data")),
                summary=f"{r.get('suggestion_count', 0)} 个真实买家搜索词" + (f"；高频卖点词：{mods}" if mods else ""),
                payload=r,
            ))
        else:
            out.append(dict(source="amazon_keywords", tier=1, status="empty",
                            real_data=False, summary="未取到补全词", payload=r))
    except Exception as e:
        out.append(dict(source="amazon_keywords", tier=1, status="error",
                        real_data=False, summary=str(e)[:160], payload={"error": str(e)[:300]}))

    # 2) Google Trends 趋势方向
    try:
        from modules.agent_tools import tool_get_trend
        r = tool_get_trend(term, geo=geo)
        ok = (r.get("direction") is not None) and (r.get("trend") != "no data")
        out.append(dict(
            source="google_trends", tier=1, status="ok" if ok else "empty",
            real_data=ok,
            summary=(f"近端均热 {r.get('late_avg')} vs 前端 {r.get('early_avg')}，方向：{r.get('direction')}"
                     if ok else "无趋势数据"),
            payload=r,
        ))
    except Exception as e:
        out.append(dict(source="google_trends", tier=1, status="error",
                        real_data=False, summary=str(e)[:160], payload={"error": str(e)[:300]}))

    # 3) 季节性（5 年 Google Trends）
    try:
        from modules.agent_tools import tool_compare_seasonality
        r = tool_compare_seasonality(term, geo=geo)
        ok = "error" not in r
        out.append(dict(
            source="seasonality", tier=1, status="ok" if ok else "empty",
            real_data=ok,
            summary=(f"季节性强度 {r.get('seasonality_strength')}，峰月 {r.get('peak_month')} / 谷月 {r.get('valley_month')}"
                     if ok else str(r.get("error", "无数据"))),
            payload=r,
        ))
    except Exception as e:
        out.append(dict(source="seasonality", tier=1, status="error",
                        real_data=False, summary=str(e)[:160], payload={"error": str(e)[:300]}))

    return out


# ─────────── 开源数据集底子（零反爬，量大精准；静态快照做底盘）───────────
def open_dataset_products(tenant_id: str, terms: list[str]) -> dict[str, list[dict]]:
    """取追踪词的开源真实商品底子（Amazon Reviews 2023）。

    数据集是静态快照，故缓存在 GlobalConfig：仅当缓存过期（TTL）或出现新词时才重新流式拉取，
    每日刷新复用缓存，避免重复扫描。返回 {term: [product, ...]}。
    """
    if not OPEN_DATASET_ENABLED or not terms:
        return {t: [] for t in terms}
    key = _OPEN_CACHE_KEY.format(tenant=tenant_id)
    cache = st.get_config(key) or {}
    products: dict[str, list[dict]] = dict(cache.get("products") or {})
    ingested_at = cache.get("ingested_at")

    stale = True
    if ingested_at:
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(ingested_at)).total_seconds()
            stale = age > OPEN_DATASET_TTL_DAYS * 86400
        except Exception:
            stale = True
    missing = [t for t in terms if t not in products]
    to_ingest = terms if stale else missing

    if to_ingest:
        try:
            from modules.open_dataset import ingest_products
            logger.info(f"open_dataset 拉取底子 terms={to_ingest} (stale={stale})")
            fresh = ingest_products(to_ingest, max_lines=OPEN_DATASET_MAX_LINES,
                                    per_term=OPEN_DATASET_PER_TERM)
            products.update(fresh)
            st.set_config(key, {"ingested_at": _now_iso(), "products": products})
        except Exception as e:
            logger.warning(f"open_dataset 拉取失败: {e}")
    return {t: products.get(t, []) for t in terms}


def _dataset_row(term: str, products: list[dict]) -> dict:
    """把开源商品底子整理成一条快照行（tier1，零反爬，真实）。"""
    from modules.open_dataset import summarize, product_stats
    if products:
        return dict(
            source="dataset_products", tier=1, status="ok", real_data=True,
            summary=summarize(term, products),
            payload={"products": products, "stats": product_stats(products),
                     "dataset": "McAuley-Lab/Amazon-Reviews-2023"},
        )
    return dict(
        source="dataset_products", tier=1, status="empty", real_data=False,
        summary="开源数据集未匹配到该词的商品", payload={"products": []},
    )


def _collect_tikhub_products(term: str, geo: str) -> dict:
    """实时 TikTok Shop 商品（价格/评分/评论数/销量/店铺）。未配 key 时如实标 unavailable。"""
    if not _tikhub_ok():
        return dict(
            source="tiktok_shop", tier=2, status="unavailable", real_data=False,
            summary="TikTok Shop 实时通道未就绪（需 TIKHUB_API_KEY）；未编造，配置后自动补齐",
            payload={"reason": "no_tikhub_key"},
        )
    try:
        from modules import tikhub
        prods = tikhub.shop_search(term, region=geo, limit=30)
        if prods:
            return dict(
                source="tiktok_shop", tier=2, status="ok", real_data=True,
                summary=tikhub.shop_summary(term, prods),
                payload={"products": prods, "stats": tikhub.product_stats(prods),
                         "region": geo, "source_label": "TikTok Shop（实时）"},
            )
        return dict(source="tiktok_shop", tier=2, status="empty", real_data=False,
                    summary=f"TikTok Shop 未搜到「{term}」在售商品", payload={"region": geo})
    except Exception as e:
        return dict(source="tiktok_shop", tier=2, status="error", real_data=False,
                    summary=str(e)[:160], payload={"error": str(e)[:300]})


def _collect_tier2(term: str, geo: str, channel_ok: bool) -> list[dict]:
    """电商商品级数据。优先 TikTok Shop 实时；可选叠加 Amazon BSR（默认关，机房 IP 必封）。"""
    out: list[dict] = [_collect_tikhub_products(term, geo)]
    # Amazon BSR 获取较慢且机房 IP 基本必封，默认关闭；需要时 ENABLE_AMAZON_BSR=1 显式开启。
    if os.getenv("ENABLE_AMAZON_BSR") == "1" and (_proxy_alive() or _paid_api_available()):
        try:
            from modules.agent_tools import tool_get_bestsellers
            r = tool_get_bestsellers(category=term, limit=30, geo=geo)
            items = r.get("items") or []
            ok = bool(items)
            out.append(dict(
                source="bestsellers", tier=2, status="ok" if ok else "empty",
                real_data=ok,
                summary=(f"BSR Top {len(items)} 获取成功" if ok else "未获取到 BSR 榜单"),
                payload=r,
            ))
        except Exception as e:
            out.append(dict(source="bestsellers", tier=2, status="error",
                            real_data=False, summary=str(e)[:160], payload={"error": str(e)[:300]}))
    return out


# ─────────── 实时社媒趋势（每批一次，跨平台）───────────
SOCIAL_TREND_TERM = "🔥 实时社媒趋势"


def _collect_social_trends(limit: int = 20) -> list[dict]:
    """跨平台实时社媒热搜/热词（TikTok/X/Lemon8，面向海外）。每批采集一次。"""
    if not _tikhub_ok():
        return [dict(
            source="social_trends", tier=2, status="unavailable", real_data=False,
            summary="社媒趋势通道未就绪（需 TIKHUB_API_KEY）", payload={"reason": "no_tikhub_key"},
        )]
    from modules import tikhub
    trends = tikhub.social_trends(limit=limit)
    rows: list[dict] = []
    for plat, r in trends.items():
        src = f"trend_{plat}"
        if r.get("ok") and r.get("items"):
            kws = [i.get("keyword") for i in r["items"] if i.get("keyword")]
            rows.append(dict(
                source=src, tier=2, status="ok", real_data=True,
                summary=f"{r['label']}：{('、'.join(kws[:8]))}",
                payload={"platform": plat, "label": r["label"], "items": r["items"]},
            ))
        else:
            rows.append(dict(
                source=src, tier=2, status="error" if not r.get("ok") else "empty",
                real_data=False, summary=f"{r.get('label', plat)} 未取到：{r.get('error', '空')}"[:160],
                payload={"platform": plat, "error": r.get("error")},
            ))
    return rows


# ─────── 按品类榜单 / 实时热销榜 / 热门话题曲线（每批一次，与追踪词无关）───────
HOT_SELLING_TERM = "🛒 实时热销榜"
HASHTAG_TREND_TERM = "🏷️ 热门话题榜"

# 控制每批抓多少个一级品类、每类取多少商品（成本/时长可调）。
# 默认覆盖全部 28 个一级品类，每类 20 商品（单次接口调用即返回，零额外成本）。
# 想要更庞大的底盘时把 CATEGORY_PAGES 调大：每多一页 = 每类多一次接口调用、多约 20 商品。
# INCLUDE_SUBCATS=1 时也抓二级子品类（约 212 个），提供更精细的品类覆盖。
CATEGORY_MAX = int(os.getenv("DAILY_REFRESH_CATEGORIES", "28"))
CATEGORY_TOP_N = int(os.getenv("DAILY_REFRESH_CATEGORY_TOPN", "20"))
CATEGORY_PAGES = int(os.getenv("DAILY_REFRESH_CATEGORY_PAGES", "1"))
INCLUDE_SUBCATS = os.getenv("DAILY_REFRESH_INCLUDE_SUBCATS", "0") == "1"
SUBCAT_TOP_N = int(os.getenv("DAILY_REFRESH_SUBCAT_TOPN", "10"))
HASHTAG_TOP_N = int(os.getenv("DAILY_REFRESH_HASHTAGS", "20"))
# 热销榜单次接口约返回 95 条，默认全收（同一次调用，无额外成本）。
HOT_SELLING_TOP_N = int(os.getenv("DAILY_REFRESH_HOTSELLING", "100"))


def _fetch_category_products_paged(tikhub, category_id: str, geo: str,
                                   per_page: int, pages: int) -> list[dict]:
    """按 offset 翻页累计某品类的在售商品并按 product_id 去重。

    per_page 为单页条数（接口单次约返回 ≤20），pages 为翻页次数（=接口调用次数）。
    某页返回数 < per_page 视为到底，提前结束以省调用。
    """
    seen: set = set()
    out: list[dict] = []
    for i in range(max(1, pages)):
        batch = tikhub.fetch_products_by_category(
            category_id, region=geo, limit=per_page, offset=i * per_page)
        new = [p for p in batch if p.get("product_id") and p["product_id"] not in seen]
        for p in new:
            seen.add(p["product_id"])
        out.extend(new)
        if len(batch) < per_page:
            break
    return out


def _collect_category_rankings(geo: str = "US", include_subcats: Optional[bool] = None) -> list[dict]:
    """按 TikTok Shop 一级品类（+可选二级子品类）抓实时商品榜。
    
    一级品类 28 个是 TikTok Shop 的全部顶级分类；二级子品类约 212 个。
    include_subcats=True 时抓取全部子品类（约 220+ 个），用于定时全量刷新。
    """
    _include_subcats = include_subcats if include_subcats is not None else INCLUDE_SUBCATS
    if not _tikhub_ok():
        return [dict(source="category_rank", tier=2, status="unavailable", real_data=False,
                     summary="按品类榜单通道未就绪（需 TIKHUB_API_KEY）", payload={"reason": "no_tikhub_key"})]
    from modules import tikhub
    try:
        cats = tikhub.fetch_products_category_list(region=geo)
    except Exception as e:  # noqa: BLE001
        return [dict(source="category_rank", tier=2, status="error", real_data=False,
                     summary=f"品类列表获取失败：{str(e)[:140]}", payload={"error": str(e)[:300]})]
    
    # Build flat list: top-level + optional sub-categories
    # 定时全量刷新时不限制顶级品类数量，覆盖全部
    cat_limit = len(cats) if _include_subcats else CATEGORY_MAX
    flat: list[dict] = []
    for cat in cats[:cat_limit]:
        cid = cat.get("category_id")
        cname = cat.get("category_name") or cid
        if not cid:
            continue
        flat.append({"id": cid, "name": cname, "name_en": cat.get("category_name_en"),
                     "parent": None, "top_n": CATEGORY_TOP_N})
        if _include_subcats:
            for sub in (cat.get("children") or []):
                sid = sub.get("category_id")
                sname = sub.get("category_name") or sid
                if sid:
                    flat.append({"id": sid, "name": sname, "name_en": sub.get("category_name_en"),
                                 "parent": cname, "top_n": SUBCAT_TOP_N})
    
    rows: list[dict] = []
    t_start = time.time()
    # 定时全量刷新（含子品类）允许更长超时（30 分钟），startup 保持 5 分钟
    default_timeout = "1800" if _include_subcats else "300"
    CATEGORY_TIMEOUT = int(os.getenv("DAILY_REFRESH_CATEGORY_TIMEOUT", default_timeout))
    for entry in flat:
        # 超时保护：品类收集不超过 5 分钟
        if time.time() - t_start > CATEGORY_TIMEOUT:
            logger.warning(f"category_rankings timeout after {CATEGORY_TIMEOUT}s, collected {len(rows)} categories")
            break
        cid, cname = entry["id"], entry["name"]
        top_n = entry["top_n"]
        try:
            prods = _fetch_category_products_paged(tikhub, cid, geo, top_n, CATEGORY_PAGES)
            if prods:
                payload = {"category_id": cid, "category_name": cname,
                           "category_name_en": entry.get("name_en"),
                           "products": prods, "stats": tikhub.product_stats(prods),
                           "source_label": "TikTok Shop（按品类·实时）"}
                if entry.get("parent"):
                    payload["parent_category"] = entry["parent"]
                rows.append(dict(
                    source="category_rank", tier=2, status="ok", real_data=True,
                    summary=f"{cname}：实时 Top {len(prods)} · {tikhub.shop_summary(cname, prods)}",
                    payload=payload,
                ))
            else:
                rows.append(dict(source="category_rank", tier=2, status="empty", real_data=False,
                                 summary=f"{cname}：未取到在售商品",
                                 payload={"category_id": cid, "category_name": cname, "products": []}))
        except Exception as e:  # noqa: BLE001
            rows.append(dict(source="category_rank", tier=2, status="error", real_data=False,
                             summary=f"{cname}：{str(e)[:120]}",
                             payload={"category_id": cid, "category_name": cname, "error": str(e)[:300]}))
    return rows


def _collect_hot_selling(geo: str = "US", limit: int = HOT_SELLING_TOP_N) -> dict:
    """TikTok Shop 实时热销榜（爆品雷达，每批一条快照）。"""
    if not _tikhub_ok():
        return dict(source="hot_selling", tier=2, status="unavailable", real_data=False,
                    summary="热销榜通道未就绪（需 TIKHUB_API_KEY）", payload={"reason": "no_tikhub_key"})
    from modules import tikhub
    try:
        prods = tikhub.fetch_hot_selling_products(region=geo, limit=limit)
        if prods:
            return dict(source="hot_selling", tier=2, status="ok", real_data=True,
                        summary=f"实时热销 Top {len(prods)} · {tikhub.shop_summary('热销', prods)}",
                        payload={"products": prods, "stats": tikhub.product_stats(prods),
                                 "region": geo, "source_label": "TikTok Shop（热销·实时）"})
        return dict(source="hot_selling", tier=2, status="empty", real_data=False,
                    summary="未取到热销榜商品", payload={"region": geo, "products": []})
    except Exception as e:  # noqa: BLE001
        return dict(source="hot_selling", tier=2, status="error", real_data=False,
                    summary=str(e)[:160], payload={"error": str(e)[:300]})


def _collect_hashtag_trends(country: str = "US", time_range: int = 7, limit: int = HASHTAG_TOP_N) -> dict:
    """TikTok 热门话题榜（声量曲线 + 达人侦察，每批一条快照）。"""
    if not _tikhub_ok():
        return dict(source="hashtag_trends", tier=2, status="unavailable", real_data=False,
                    summary="话题榜通道未就绪（需 TIKHUB_API_KEY）", payload={"reason": "no_tikhub_key"})
    from modules import tikhub
    try:
        tags = tikhub.trending_hashtags(time_range=time_range, country=country, limit=limit)
        if tags:
            head = "、".join(f"#{t['hashtag']}" for t in tags[:6] if t.get("hashtag"))
            return dict(source="hashtag_trends", tier=2, status="ok", real_data=True,
                        summary=f"近 {time_range} 天 Top {len(tags)} 话题：{head}",
                        payload={"hashtags": tags, "country": country, "time_range": time_range,
                                 "source_label": "TikTok 热门话题（实时）"})
        return dict(source="hashtag_trends", tier=2, status="empty", real_data=False,
                    summary="未取到热门话题", payload={"country": country, "hashtags": []})
    except Exception as e:  # noqa: BLE001
        return dict(source="hashtag_trends", tier=2, status="error", real_data=False,
                    summary=str(e)[:160], payload={"error": str(e)[:300]})


# ─────────── 批次刷新 ───────────
def run_daily_refresh(tenant_id: str = "dev_tenant", terms: Optional[list[str]] = None,
                      geo: str = "US", geos: Optional[list[str]] = None,
                      trigger: str = "schedule") -> dict:
    """跑一次刷新：遍历追踪词 → 采集 → 落库快照 → 写状态摘要。返回摘要 dict。

    用非阻塞锁保证同一时刻只跑一个批次（定时与手动触发不会并发踩踏）。
    """
    # 支持多国家刷新：如果传入 geos 列表，对每个国家分别跑一次采集
    geo_list = geos or [geo]

    if not _RUN_LOCK.acquire(blocking=False):
        logger.warning("daily_refresh 已在运行，跳过本次触发")
        return {"skipped": True, "reason": "already_running"}

    run_id = str(uuid.uuid4())
    started = _now_iso()
    t0 = time.time()
    try:
        # startup 触发用精简词表加速首次数据上线
        if terms is None:
            if trigger == "startup":
                terms = STARTUP_SEED_TERMS[:]
            else:
                terms = collect_terms(tenant_id)
        channel_ok = tier2_channel_ok()
        ds_products = open_dataset_products(tenant_id, terms)
        st.set_config(_state_key(tenant_id), {
            "run_id": run_id, "status": "running", "trigger": trigger,
            "started_at": started, "finished_at": None, "geo": ",".join(geo_list),
            "terms": terms, "tier2_channel_ok": channel_ok, "counts": {},
        })
        logger.info(f"daily_refresh start run={run_id} geos={geo_list} terms={terms} tier2_ok={channel_ok}")

        counts = {"total": 0, "ok": 0, "empty": 0, "error": 0, "unavailable": 0,
                  "real": 0, "terms": len(terms)}

        def _persist(term_label: str, rows: list[dict], g: str = "US") -> None:
            for row in rows:
                st.save_snapshot(tenant_id=tenant_id, run_id=run_id, term=term_label, geo=g, **row)
                counts["total"] += 1
                counts[row["status"]] = counts.get(row["status"], 0) + 1
                if row["real_data"]:
                    counts["real"] += 1

        # 跨平台实时社媒趋势：每批采集一次（与具体追踪词无关）
        _persist(SOCIAL_TREND_TERM, _collect_social_trends())

        for current_geo in geo_list:
            logger.info(f"daily_refresh geo={current_geo} collecting...")
            # 按品类榜单 / 实时热销榜 / 热门话题曲线
            # daily_full（美国 EST 0:00）时抓全部 220+ 子品类；startup/schedule 只抓 28 个顶级品类
            _include_all_subcats = trigger == "daily_full"
            _persist("📦 品类榜单", _collect_category_rankings(current_geo, include_subcats=_include_all_subcats), current_geo)
            _persist(HOT_SELLING_TERM, [_collect_hot_selling(current_geo)], current_geo)
            _persist(HASHTAG_TREND_TERM, [_collect_hashtag_trends(current_geo)], current_geo)

            for term in terms:
                rows = (_collect_tier1(term, current_geo)
                        + [_dataset_row(term, ds_products.get(term, []))]
                        + _collect_tier2(term, current_geo, channel_ok))
                _persist(term, rows, current_geo)

        summary = {
            "run_id": run_id, "status": "done", "trigger": trigger,
            "started_at": started, "finished_at": _now_iso(),
            "elapsed_sec": round(time.time() - t0, 1), "geo": ",".join(geo_list),
            "terms": terms, "tier2_channel_ok": channel_ok, "counts": counts,
        }
        st.set_config(_state_key(tenant_id), summary)
        logger.info(f"daily_refresh done run={run_id} counts={counts}")
        return summary
    except Exception as e:
        logger.exception("daily_refresh failed")
        fail = {"run_id": run_id, "status": "failed", "trigger": trigger,
                "started_at": started, "finished_at": _now_iso(), "error": str(e)[:300]}
        try:
            st.set_config(_state_key(tenant_id), fail)
        except Exception:
            pass
        return fail
    finally:
        _RUN_LOCK.release()


def has_fresh_data(tenant_id: str = "dev_tenant", max_age_hours: int = 24) -> bool:
    """检查数据库中是否有新鲜的品类数据（< max_age_hours 小时内）。
    用于启动时决定是否需要重新从 TikHub 获取数据。有新鲜数据就跳过，节省 API 成本。"""
    from datetime import timedelta
    try:
        from backend.storage import SessionLocal, DataSnapshot
        with SessionLocal() as s:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            count = (s.query(DataSnapshot)
                     .filter(DataSnapshot.tenant_id == tenant_id,
                             DataSnapshot.source == "category_rank",
                             DataSnapshot.real_data == True,
                             DataSnapshot.captured_at >= cutoff)
                     .count())
            if count > 0:
                logger.info(f"数据库中有 {count} 条新鲜品类数据（{max_age_hours}h 内），跳过 TikHub 重复抓取")
                return True
            return False
    except Exception as e:
        logger.warning(f"检查新鲜数据出错: {e}")
        return False


def run_in_background(tenant_id: str = "dev_tenant", terms: Optional[list[str]] = None,
                      geo: str = "US", geos: Optional[list[str]] = None,
                      trigger: str = "manual") -> bool:
    """后台线程跑一次刷新（手动触发用，立即返回）。已在跑则返回 False。"""
    if _RUN_LOCK.locked():
        return False
    threading.Thread(
        target=run_daily_refresh,
        kwargs=dict(tenant_id=tenant_id, terms=terms, geo=geo, geos=geos, trigger=trigger),
        daemon=True,
    ).start()
    return True


def get_refresh_state(tenant_id: str = "dev_tenant") -> dict:
    return st.get_config(_state_key(tenant_id)) or {"status": "never_run"}


if __name__ == "__main__":
    import json
    out = run_daily_refresh(terms=["garlic press", "yoga mat"], trigger="cli")
    print(json.dumps(out, ensure_ascii=False, indent=2))
