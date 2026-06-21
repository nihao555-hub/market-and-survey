"""
GraphQL 层（对齐 frontend steering §1 + §2.2 + §2.3）。

- Query:  thread(id) / threads(tenantId)        历史任务 + 单会话状态
- Mutation: sendSelectionMessage / stopStream    发送 + 停止
- Subscription: onAgentChatEvent(threadId)        SSE 实时事件流（graphql-sse 协议）

event 字段是 JSON 标量（steering §2.2：不穷举 chunk 类型）。
订阅 resolver 内部用 UIChunkAdapter 把后端自定义 chunk 翻译成 ai-sdk UIMessageChunk，
catch-up + live 共用同一 adapter 实例保证顺序。
"""
from __future__ import annotations
import asyncio, json, uuid
import typing
import strawberry
from strawberry.scalars import JSON
import redis.asyncio as aioredis

from backend.events import (get_accumulated_chunks, request_cancel,
                              EVENT_CHANNEL, REDIS_URL)
from backend.storage import (get_or_create_thread, list_messages, set_active_stream,
                              SessionLocal, Thread, delete_thread)
from backend import storage as st
from backend.ui_chunks import UIChunkAdapter


# ─────────── 选品任务参数 → user_text 组装 ───────────
# 按调研类型给出不同的开场与分析框架，让 5 个功能页产出不同侧重。
_KIND_INTRO = {
    "market": "我想做{c}的市场调研",
    "trend": "我想做{c}的趋势探索",
    "competitor": "我想做{c}的竞品分析",
    "audience": "我想做{c}的受众洞察",
    "opportunity": "我想做{c}的机会挖掘",
    "general": "我想做{c}选品调研",
}
_KIND_FOCUS = {
    "market": "。请聚焦：市场规模(TAM/SAM)、增长趋势、需求强度、竞争格局与利润空间。",
    "trend": "。请聚焦：搜索热度与上升速度、季节性、相关上升词、平台话题声量与拐点判断。",
    "competitor": "。请聚焦：Top 竞品 listing 对比、价格带与卖点、评分与评论痛点、差异化切入点。",
    "audience": "。请聚焦：目标人群画像、使用场景与动机、购买决策因素、触达渠道与内容偏好。",
    "opportunity": "。请聚焦：未被满足的需求缺口、差异化机会、进入壁垒与风险、机会评分与优先级。",
    "general": "。请抓 BSR 子类目 Top + 多平台对比 + 真实评论痛点 + 利润测算。",
}


def _build_user_text(category: str, markets: list[str], positioning: str,
                     monthly_budget: str, exclude: str, kind: str = "general") -> str:
    intro = _KIND_INTRO.get(kind, _KIND_INTRO["general"]).format(c=category)
    parts = [intro]
    if markets:
        parts.append(f"，目标市场：{'/'.join(markets)}")
    if positioning:
        parts.append(f"，商家定位：{positioning}")
    if monthly_budget:
        parts.append(f"，月度预算：{monthly_budget}")
    if exclude:
        parts.append(f"，排除大牌：{exclude}")
    parts.append(_KIND_FOCUS.get(kind, _KIND_FOCUS["general"]))
    return "".join(parts)


# ─────────── GraphQL 类型 ───────────
@strawberry.type
class MessagePart:
    type: str
    json: JSON


@strawberry.type
class Message:
    id: str
    role: str
    parts: JSON
    created_at: typing.Optional[str]


@strawberry.type
class ThreadState:
    id: str
    title: str
    active_stream_id: typing.Optional[str]
    total_input_tokens: int
    total_output_tokens: int
    messages: typing.List[Message]


@strawberry.type
class ThreadSummary:
    id: str
    title: str
    updated_at: typing.Optional[str]
    active_stream_id: typing.Optional[str]
    is_favorite: bool = False
    kind: str = "general"


@strawberry.type
class DataSourceType:
    id: str
    name: str
    description: str
    kind: str
    frequency: str
    connected: bool
    builtin: bool


@strawberry.type
class MonitorType:
    id: str
    name: str
    description: str
    kind: str
    cadence: str
    enabled: bool


@strawberry.type
class DataSnapshotType:
    id: str
    term: str
    source: str
    geo: str
    tier: int
    status: str
    real_data: bool
    summary: str
    payload: JSON
    captured_at: typing.Optional[str]


@strawberry.type
class DailyRefreshStatus:
    status: str
    run_id: typing.Optional[str] = None
    trigger: typing.Optional[str] = None
    started_at: typing.Optional[str] = None
    finished_at: typing.Optional[str] = None
    elapsed_sec: typing.Optional[float] = None
    tier2_channel_ok: bool = False
    terms: typing.List[str] = strawberry.field(default_factory=list)
    counts: JSON = strawberry.field(default_factory=dict)


@strawberry.type
class ApiKeyType:
    id: str
    name: str
    prefix: str
    last4: str
    revoked: bool
    created_at: typing.Optional[str]
    last_used_at: typing.Optional[str]


@strawberry.type
class ApiKeyCreated:
    key: ApiKeyType
    token: str   # 明文，仅创建时返回一次


@strawberry.type
class SettingsType:
    display_name: str
    email: str
    plan: str
    default_model: str
    default_market: str
    default_positioning: str
    notify_email: bool
    notify_in_app: bool
    target_countries: typing.List[str] = strawberry.field(default_factory=lambda: ["US"])
    refresh_hour_utc: int = 16


def _thread_summary(t: Thread) -> ThreadSummary:
    return ThreadSummary(
        id=t.id, title=t.title or "未命名任务",
        updated_at=t.updated_at.isoformat() if t.updated_at else None,
        active_stream_id=t.active_stream_id,
        is_favorite=bool(t.is_favorite),
        kind=getattr(t, "kind", None) or "general",
    )


def _data_source_type(d: st.DataSource) -> DataSourceType:
    return DataSourceType(
        id=d.id, name=d.name, description=d.description or "", kind=d.kind,
        frequency=d.frequency, connected=bool(d.connected), builtin=bool(d.builtin),
    )


def _monitor_type(m: st.Monitor) -> MonitorType:
    return MonitorType(
        id=m.id, name=m.name, description=m.description or "", kind=m.kind,
        cadence=m.cadence, enabled=bool(m.enabled),
    )


def _snapshot_type(d: st.DataSnapshot) -> DataSnapshotType:
    return DataSnapshotType(
        id=d.id, term=d.term, source=d.source, geo=d.geo or "US",
        tier=d.tier or 1, status=d.status or "ok", real_data=bool(d.real_data),
        summary=d.summary or "", payload=d.payload or {},
        captured_at=d.captured_at.isoformat() if d.captured_at else None,
    )


def _refresh_status(d: dict) -> DailyRefreshStatus:
    return DailyRefreshStatus(
        status=d.get("status", "never_run"),
        run_id=d.get("run_id"),
        trigger=d.get("trigger"),
        started_at=d.get("started_at"),
        finished_at=d.get("finished_at"),
        elapsed_sec=d.get("elapsed_sec"),
        tier2_channel_ok=bool(d.get("tier2_channel_ok", False)),
        terms=list(d.get("terms") or []),
        counts=d.get("counts") or {},
    )


def _api_key_type(k: st.ApiKey) -> ApiKeyType:
    return ApiKeyType(
        id=k.id, name=k.name, prefix=k.prefix, last4=k.last4, revoked=bool(k.revoked),
        created_at=k.created_at.isoformat() if k.created_at else None,
        last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
    )


def _settings_type(d: dict) -> SettingsType:
    return SettingsType(
        display_name=d["displayName"], email=d["email"], plan=d["plan"],
        default_model=d["defaultModel"], default_market=d["defaultMarket"],
        default_positioning=d["defaultPositioning"],
        notify_email=bool(d["notifyEmail"]), notify_in_app=bool(d["notifyInApp"]),
        target_countries=list(d.get("targetCountries") or ["US"]),
        refresh_hour_utc=int(d.get("refreshHourUtc") or 16),
    )


@strawberry.type
class StartResult:
    thread_id: str
    stream_id: str
    status: str


@strawberry.type
class AgentEventPayload:
    thread_id: str
    event: JSON


# ─────────── Query ───────────
@strawberry.type
class Query:
    @strawberry.field
    def threads(self, tenant_id: str = "dev_tenant") -> typing.List[ThreadSummary]:
        return [_thread_summary(t) for t in st.list_threads(tenant_id)]

    @strawberry.field
    def favorite_threads(self, tenant_id: str = "dev_tenant") -> typing.List[ThreadSummary]:
        return [_thread_summary(t) for t in st.list_threads(tenant_id, favorite=True)]

    @strawberry.field
    def threads_by_kind(self, kind: str, tenant_id: str = "dev_tenant") -> typing.List[ThreadSummary]:
        """按调研类型列出历史调研（供 5 个功能页各自展示本类型历史）。"""
        return [_thread_summary(t) for t in st.list_threads(tenant_id, kind=kind)]

    @strawberry.field
    def trashed_threads(self, tenant_id: str = "dev_tenant") -> typing.List[ThreadSummary]:
        return [_thread_summary(t) for t in st.list_threads(tenant_id, trashed=True)]

    @strawberry.field
    def data_sources(self, tenant_id: str = "dev_tenant") -> typing.List[DataSourceType]:
        return [_data_source_type(d) for d in st.list_data_sources(tenant_id)]

    @strawberry.field
    def monitors(self, tenant_id: str = "dev_tenant") -> typing.List[MonitorType]:
        return [_monitor_type(m) for m in st.list_monitors(tenant_id)]

    @strawberry.field
    def data_snapshots(
        self, tenant_id: str = "dev_tenant",
        term: typing.Optional[str] = None,
        source: typing.Optional[str] = None,
        limit: int = 200,
    ) -> typing.List[DataSnapshotType]:
        """最近一次每日刷新批次落库的真实数据快照（可按 term/source 过滤）。"""
        rows = st.list_latest_snapshots(tenant_id, term=term, source=source, limit=limit)
        return [_snapshot_type(d) for d in rows]

    @strawberry.field
    def all_snapshots(
        self, tenant_id: str = "dev_tenant",
        term: typing.Optional[str] = None,
        source: typing.Optional[str] = None,
        limit: int = 500,
    ) -> typing.List[DataSnapshotType]:
        """所有刷新批次的快照（跨 run_id），用于展示历史趋势。"""
        rows = st.list_all_snapshots(tenant_id, term=term, source=source, limit=limit)
        return [_snapshot_type(d) for d in rows]

    @strawberry.field
    def daily_refresh_status(self, tenant_id: str = "dev_tenant") -> DailyRefreshStatus:
        """最近一次每日刷新的状态摘要（时间/词表/各状态计数/Tier2 通道是否就绪）。"""
        from backend.daily_refresh import get_refresh_state
        return _refresh_status(get_refresh_state(tenant_id))

    @strawberry.field
    def api_keys(self, tenant_id: str = "dev_tenant") -> typing.List[ApiKeyType]:
        return [_api_key_type(k) for k in st.list_api_keys(tenant_id)]

    @strawberry.field
    def settings(self, tenant_id: str = "dev_tenant") -> SettingsType:
        return _settings_type(st.get_settings(tenant_id))

    @strawberry.field
    def thread(self, id: str) -> typing.Optional[ThreadState]:
        with SessionLocal() as s:
            t = s.get(Thread, id)
            if t is None:
                return None
            msgs = list_messages(id)
            return ThreadState(
                id=t.id, title=t.title or "",
                active_stream_id=t.active_stream_id,
                total_input_tokens=t.total_input_tokens or 0,
                total_output_tokens=t.total_output_tokens or 0,
                messages=[Message(
                    id=m.id, role=m.role, parts=m.parts,
                    created_at=m.created_at.isoformat() if m.created_at else None,
                ) for m in msgs],
            )


# ─────────── Mutation ───────────
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def send_selection_message(
        self,
        category: str,
        markets: typing.List[str],
        positioning: str = "",
        monthly_budget: str = "",
        exclude: str = "",
        model_choice: str = "flash",
        thread_id: typing.Optional[str] = None,
        title: typing.Optional[str] = None,
        kind: str = "general",
    ) -> StartResult:
        tid = thread_id or str(uuid.uuid4())
        get_or_create_thread(tid, title=title or f"{category} · {'/'.join(markets) or '全球'}", kind=kind)
        stream_id = str(uuid.uuid4())
        set_active_stream(tid, stream_id)

        user_text = _build_user_text(category, markets, positioning, monthly_budget, exclude, kind)

        # 控制面/数据面分离（steering §2.1）：入队 dramatiq（Redis 持久化），
        # 由 worker 进程消费跑 LLM。worker 未启动时回退 asyncio（仅 dev）。
        import os as _os
        use_worker = _os.getenv("USE_DRAMATIQ_WORKER", "0") == "1"
        if use_worker:
            from backend.queue import run_selection_actor
            run_selection_actor.send(tid, stream_id, user_text, model_choice, kind)
        else:
            from backend.selection_job import run_selection_job
            asyncio.create_task(run_selection_job(tid, stream_id, user_text, model_choice, kind))

        return StartResult(thread_id=tid, stream_id=stream_id, status="queued")

    @strawberry.mutation
    async def stop_stream(self, thread_id: str) -> bool:
        await request_cancel(thread_id)
        return True

    @strawberry.mutation
    async def delete_thread(self, thread_id: str, tenant_id: str = "dev_tenant") -> bool:
        """软删除：移入回收站（可恢复）。若正在运行，先发取消信号。"""
        try:
            await request_cancel(thread_id)
        except Exception:
            pass
        return st.soft_delete_thread(thread_id, tenant_id)

    @strawberry.mutation
    def restore_thread(self, thread_id: str, tenant_id: str = "dev_tenant") -> bool:
        """从回收站恢复会话。"""
        return st.restore_thread(thread_id, tenant_id)

    @strawberry.mutation
    async def purge_thread(self, thread_id: str, tenant_id: str = "dev_tenant") -> bool:
        """彻底删除会话及其消息（不可恢复）。"""
        try:
            await request_cancel(thread_id)
        except Exception:
            pass
        return delete_thread(thread_id, tenant_id)

    @strawberry.mutation
    def toggle_favorite(self, thread_id: str, tenant_id: str = "dev_tenant") -> bool:
        """切换收藏态，返回新状态。"""
        result = st.toggle_favorite(thread_id, tenant_id)
        return bool(result)

    # ── 数据源 ──
    @strawberry.mutation
    def create_data_source(
        self, name: str, description: str = "", kind: str = "trends",
        frequency: str = "每日", tenant_id: str = "dev_tenant",
    ) -> DataSourceType:
        return _data_source_type(
            st.create_data_source(tenant_id, name, description, kind, frequency))

    @strawberry.mutation
    def set_data_source_connected(
        self, source_id: str, connected: bool, tenant_id: str = "dev_tenant",
    ) -> bool:
        result = st.set_data_source_connected(source_id, connected, tenant_id)
        return bool(result)

    # ── 监控规则 ──
    @strawberry.mutation
    def create_monitor(
        self, name: str, description: str = "", kind: str = "trend",
        cadence: str = "每日", tenant_id: str = "dev_tenant",
    ) -> MonitorType:
        return _monitor_type(st.create_monitor(tenant_id, name, description, kind, cadence))

    @strawberry.mutation
    def set_monitor_enabled(
        self, monitor_id: str, enabled: bool, tenant_id: str = "dev_tenant",
    ) -> bool:
        result = st.set_monitor_enabled(monitor_id, enabled, tenant_id)
        return bool(result)

    @strawberry.mutation
    def delete_monitor(self, monitor_id: str, tenant_id: str = "dev_tenant") -> bool:
        return st.delete_monitor(monitor_id, tenant_id)

    # ── 每日数据刷新 ──
    @strawberry.mutation
    def trigger_daily_refresh(self, tenant_id: str = "dev_tenant") -> bool:
        """手动触发一次每日刷新（后台线程跑，立即返回是否已启动）。按用户设置的目标国家逐个刷新。"""
        from backend.daily_refresh import run_in_background
        settings = st.get_settings(tenant_id)
        geos = settings.get("targetCountries") or ["US"]
        return run_in_background(tenant_id=tenant_id, geos=geos, trigger="manual")

    @strawberry.mutation
    def backfill_google_trends(self, tenant_id: str = "dev_tenant") -> bool:
        """回填 Google Trends 过去一个月的时间序列数据。后台线程运行，立即返回。"""
        import threading

        def _do_backfill():
            import sys, uuid
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from modules.trends import get_keyword_trend
            from backend.daily_refresh import DEFAULT_SEED_TERMS
            from datetime import datetime, timezone, timedelta
            from loguru import logger

            run_id = f"gt_backfill_{uuid.uuid4().hex[:8]}"
            keywords = DEFAULT_SEED_TERMS[:20]
            logger.info(f"Google Trends 回填开始: {len(keywords)} 个关键词, run_id={run_id}")
            for kw in keywords:
                try:
                    df = get_keyword_trend([kw], timeframe="today 1-m", geo="US")
                    if df.empty:
                        continue
                    col = kw if kw in df.columns else df.columns[0]
                    for ts, val in zip(df.index, df[col]):
                        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                        st.save_snapshot(
                            tenant_id=tenant_id, run_id=run_id, term=kw,
                            source="google_trends", geo="US", tier=1,
                            status="ok", real_data=True,
                            summary=f"Google Trends 回填: {kw} @ {ts_str}",
                            payload={
                                "keyword": kw, "geo": "US",
                                "late_avg": float(val), "early_avg": float(val),
                                "direction": "回填", "max": float(val), "min": float(val),
                                "recent_3m_avg": None,
                                "backfill": True, "backfill_ts": ts_str,
                            },
                        )
                    logger.info(f"回填完成: {kw} ({len(df)} 个数据点)")
                except Exception as e:
                    logger.warning(f"回填失败: {kw}: {e}")
            logger.info(f"Google Trends 回填全部完成: run_id={run_id}")

        threading.Thread(target=_do_backfill, daemon=True).start()
        return True

    # ── API Key ──
    @strawberry.mutation
    def create_api_key(self, name: str = "默认 Key", tenant_id: str = "dev_tenant") -> ApiKeyCreated:
        rec, token = st.create_api_key(tenant_id, name)
        return ApiKeyCreated(key=_api_key_type(rec), token=token)

    @strawberry.mutation
    def revoke_api_key(self, key_id: str, tenant_id: str = "dev_tenant") -> bool:
        return st.revoke_api_key(key_id, tenant_id)

    # ── 设置 ──
    @strawberry.mutation
    def update_settings(
        self,
        tenant_id: str = "dev_tenant",
        display_name: typing.Optional[str] = None,
        email: typing.Optional[str] = None,
        default_model: typing.Optional[str] = None,
        default_market: typing.Optional[str] = None,
        default_positioning: typing.Optional[str] = None,
        notify_email: typing.Optional[bool] = None,
        notify_in_app: typing.Optional[bool] = None,
        target_countries: typing.Optional[typing.List[str]] = None,
        refresh_hour_utc: typing.Optional[int] = None,
    ) -> SettingsType:
        patch = {
            "displayName": display_name,
            "email": email,
            "defaultModel": default_model,
            "defaultMarket": default_market,
            "defaultPositioning": default_positioning,
            "notifyEmail": notify_email,
            "notifyInApp": notify_in_app,
            "targetCountries": target_countries,
            "refreshHourUtc": refresh_hour_utc,
        }
        return _settings_type(st.update_settings(tenant_id, patch))


# ─────────── Subscription ───────────
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def on_agent_chat_event(
        self, thread_id: str, last_seq: int = 0
    ) -> typing.AsyncGenerator[AgentEventPayload, None]:
        """实时事件流。catch-up + live 共用一个 adapter 实例（顺序保证）。

        把后端自定义 chunk 翻译成 ai-sdk UIMessageChunk 后下发。
        非 stream-chunk 的事件（start/stream-error/message-persisted）原样透传。
        """
        adapter = UIChunkAdapter()
        seq = 0

        def wrap_chunks(std_chunks: list[dict]):
            nonlocal seq
            out = []
            for c in std_chunks:
                seq += 1
                out.append({"type": "stream-chunk", "chunk": c, "seq": seq})
            return out

        # 1) catch-up：重放历史自定义 chunk（过 adapter）
        try:
            history = await get_accumulated_chunks(thread_id)
        except Exception:
            history = []
        for raw in history:
            for ev in wrap_chunks(adapter.feed(raw)):
                if ev["seq"] > last_seq:
                    yield AgentEventPayload(thread_id=thread_id, event=ev)

        # 2) live：订阅 Redis pub/sub
        client = aioredis.from_url(REDIS_URL, decode_responses=True)
        ps = client.pubsub()
        await ps.subscribe(EVENT_CHANNEL.format(thread_id=thread_id))
        try:
            while True:
                msg = await ps.get_message(ignore_subscribe_messages=True, timeout=30)
                if not msg or msg.get("type") != "message":
                    continue
                try:
                    evt = json.loads(msg["data"])
                except Exception:
                    continue

                etype = evt.get("type")
                if etype == "stream-chunk":
                    raw_chunk = evt.get("chunk", {})
                    for ev in wrap_chunks(adapter.feed(raw_chunk)):
                        yield AgentEventPayload(thread_id=thread_id, event=ev)
                elif etype in ("message-persisted", "stream-error", "start"):
                    # 顶层事件原样透传（前端 hook 直接识别）
                    yield AgentEventPayload(thread_id=thread_id, event=evt)
                    if etype == "message-persisted":
                        break  # 流结束
        finally:
            await ps.unsubscribe()
            await client.aclose()


schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
