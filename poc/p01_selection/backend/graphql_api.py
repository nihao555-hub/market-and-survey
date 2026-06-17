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
from backend.ui_chunks import UIChunkAdapter


# ─────────── 选品任务参数 → user_text 组装 ───────────
def _build_user_text(category: str, markets: list[str], positioning: str,
                     monthly_budget: str, exclude: str) -> str:
    parts = [f"我想做{category}选品调研"]
    if markets:
        parts.append(f"，目标市场：{'/'.join(markets)}")
    if positioning:
        parts.append(f"，商家定位：{positioning}")
    if monthly_budget:
        parts.append(f"，月度预算：{monthly_budget}")
    if exclude:
        parts.append(f"，排除大牌：{exclude}")
    parts.append("。请抓 BSR 子类目 Top + 多平台对比 + 真实评论痛点 + 利润测算。")
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
        with SessionLocal() as s:
            rows = (s.query(Thread)
                    .filter(Thread.tenant_id == tenant_id)
                    .order_by(Thread.updated_at.desc()).all())
            return [ThreadSummary(
                id=t.id, title=t.title or "未命名任务",
                updated_at=t.updated_at.isoformat() if t.updated_at else None,
                active_stream_id=t.active_stream_id,
            ) for t in rows]

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
    ) -> StartResult:
        tid = thread_id or str(uuid.uuid4())
        get_or_create_thread(tid, title=title or f"{category} · {'/'.join(markets) or '全球'}")
        stream_id = str(uuid.uuid4())
        set_active_stream(tid, stream_id)

        user_text = _build_user_text(category, markets, positioning, monthly_budget, exclude)

        # 控制面/数据面分离（steering §2.1）：入队 dramatiq（Redis 持久化），
        # 由 worker 进程消费跑 LLM。worker 未启动时回退 asyncio（仅 dev）。
        import os as _os
        use_worker = _os.getenv("USE_DRAMATIQ_WORKER", "0") == "1"
        if use_worker:
            from backend.queue import run_selection_actor
            run_selection_actor.send(tid, stream_id, user_text, model_choice)
        else:
            from backend.selection_job import run_selection_job
            asyncio.create_task(run_selection_job(tid, stream_id, user_text, model_choice))

        return StartResult(thread_id=tid, stream_id=stream_id, status="queued")

    @strawberry.mutation
    async def stop_stream(self, thread_id: str) -> bool:
        await request_cancel(thread_id)
        return True

    @strawberry.mutation
    async def delete_thread(self, thread_id: str, tenant_id: str = "dev_tenant") -> bool:
        """删除会话及其消息。若该会话正在运行，先发取消信号再删。"""
        try:
            await request_cancel(thread_id)
        except Exception:
            pass
        return delete_thread(thread_id, tenant_id)


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
