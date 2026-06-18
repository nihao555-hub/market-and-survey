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

# 默认追踪词（跨境选品常见品类；会与启用的监控规则、近期调研线程合并去重）
DEFAULT_SEED_TERMS = [
    "garlic press",
    "stainless steel water bottle",
    "yoga mat",
    "wireless earbuds",
    "pet hair remover",
    "led strip lights",
]

# 单次刷新最多处理多少个词（控制时长与限流风险）
MAX_TERMS = int(os.getenv("DAILY_REFRESH_MAX_TERMS", "8"))

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


def tier2_channel_ok() -> bool:
    """电商商品级数据通道是否就绪（真实代理在转发，或配了付费 API）。"""
    return _proxy_alive() or _paid_api_available()


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


def _collect_tier2(term: str, geo: str, channel_ok: bool) -> list[dict]:
    """电商商品级数据（需代理/付费 API）。通道未就绪时如实标 unavailable，不编造。"""
    if not channel_ok:
        return [dict(
            source="bestsellers", tier=2, status="unavailable", real_data=False,
            summary="电商商品级数据通道未就绪（需美国代理或付费 API）；未编造，通道接入后自动补齐",
            payload={"reason": "no_proxy_or_paid_api", "us_proxy_host": "127.0.0.1:10808"},
        )]
    out: list[dict] = []
    try:
        from modules.agent_tools import tool_get_bestsellers
        r = tool_get_bestsellers(category=term, limit=30, geo=geo)
        items = r.get("items") or []
        ok = bool(items)
        out.append(dict(
            source="bestsellers", tier=2, status="ok" if ok else "empty",
            real_data=ok,
            summary=(f"BSR Top {len(items)} 抓取成功" if ok else "未抓到 BSR 榜单"),
            payload=r,
        ))
    except Exception as e:
        out.append(dict(source="bestsellers", tier=2, status="error",
                        real_data=False, summary=str(e)[:160], payload={"error": str(e)[:300]}))
    return out


# ─────────── 批次刷新 ───────────
def run_daily_refresh(tenant_id: str = "dev_tenant", terms: Optional[list[str]] = None,
                      geo: str = "US", trigger: str = "schedule") -> dict:
    """跑一次刷新：遍历追踪词 → 采集 → 落库快照 → 写状态摘要。返回摘要 dict。

    用非阻塞锁保证同一时刻只跑一个批次（定时与手动触发不会并发踩踏）。
    """
    if not _RUN_LOCK.acquire(blocking=False):
        logger.warning("daily_refresh 已在运行，跳过本次触发")
        return {"skipped": True, "reason": "already_running"}

    run_id = str(uuid.uuid4())
    started = _now_iso()
    t0 = time.time()
    try:
        terms = terms or collect_terms(tenant_id)
        channel_ok = tier2_channel_ok()
        st.set_config(_state_key(tenant_id), {
            "run_id": run_id, "status": "running", "trigger": trigger,
            "started_at": started, "finished_at": None, "geo": geo,
            "terms": terms, "tier2_channel_ok": channel_ok, "counts": {},
        })
        logger.info(f"daily_refresh start run={run_id} terms={terms} tier2_ok={channel_ok}")

        counts = {"total": 0, "ok": 0, "empty": 0, "error": 0, "unavailable": 0,
                  "real": 0, "terms": len(terms)}
        for term in terms:
            rows = _collect_tier1(term, geo) + _collect_tier2(term, geo, channel_ok)
            for row in rows:
                st.save_snapshot(tenant_id=tenant_id, run_id=run_id, term=term, geo=geo, **row)
                counts["total"] += 1
                counts[row["status"]] = counts.get(row["status"], 0) + 1
                if row["real_data"]:
                    counts["real"] += 1

        summary = {
            "run_id": run_id, "status": "done", "trigger": trigger,
            "started_at": started, "finished_at": _now_iso(),
            "elapsed_sec": round(time.time() - t0, 1), "geo": geo,
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


def run_in_background(tenant_id: str = "dev_tenant", terms: Optional[list[str]] = None,
                      geo: str = "US", trigger: str = "manual") -> bool:
    """后台线程跑一次刷新（手动触发用，立即返回）。已在跑则返回 False。"""
    if _RUN_LOCK.locked():
        return False
    threading.Thread(
        target=run_daily_refresh,
        kwargs=dict(tenant_id=tenant_id, terms=terms, geo=geo, trigger=trigger),
        daemon=True,
    ).start()
    return True


def get_refresh_state(tenant_id: str = "dev_tenant") -> dict:
    return st.get_config(_state_key(tenant_id)) or {"status": "never_run"}


if __name__ == "__main__":
    import json
    out = run_daily_refresh(terms=["garlic press", "yoga mat"], trigger="cli")
    print(json.dumps(out, ensure_ascii=False, indent=2))
