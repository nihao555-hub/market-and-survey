"""
控制平面：FastAPI（对应 backend steering §1 + §8.7）
- POST /chat        接单 + 入队 + 立即返回 streamId
- POST /stop        发送 cancel 信号（pub/sub）
- GET  /events SSE  订阅事件流（threadId 过滤）
- GET  /catchup     重放历史 chunk
- GET  /thread/{id} 查会话状态
"""
from __future__ import annotations
import asyncio, json, uuid
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import redis.asyncio as aioredis

from backend.events import (publish, get_pub, get_accumulated_chunks, request_cancel,
                              EVENT_CHANNEL, REDIS_URL)
from backend.storage import (get_or_create_thread, list_messages, set_active_stream,
                              assert_thread_owner, SessionLocal, Thread)
from backend.stream_job import run_stream_job
from backend.selection_job import run_selection_job
from backend.auth import (require_tenant, require_tenant_query, get_metrics,
                          record_error, record_job_start)

app = FastAPI(title="选品 Agent — Backend Steering 对齐版")


@app.on_event("startup")
async def _clear_stale_streams():
    """启动清理遗留 active_stream（崩溃任务不显示为运行中）。"""
    try:
        from backend.storage import clear_all_active_streams
        clear_all_active_streams()
    except Exception:
        pass

# ─── CORS（前端 Next.js dev server 跨域）───
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── GraphQL 层（frontend steering：Query/Mutation/Subscription over graphql-sse）───
try:
    from strawberry.fastapi import GraphQLRouter
    from backend.graphql_api import schema as gql_schema
    graphql_app = GraphQLRouter(gql_schema, subscription_protocols=[
        "graphql-transport-ws",
    ])
    app.include_router(graphql_app, prefix="/graphql")
    # graphql-sse 的 POST/GET 由 GraphQLRouter 自动处理（strawberry 支持 SSE 订阅）
except Exception as _e:
    import logging
    logging.getLogger("uvicorn").warning(f"GraphQL 未挂载: {_e}")


# ─── 接单 + 入队（控制平面）───
class ChatBody(BaseModel):
    thread_id: str | None = None
    text: str
    model_choice: str = "flash"


@app.post("/chat")
async def chat(body: ChatBody, tenant_id: str = Depends(require_tenant)):
    thread_id = body.thread_id or str(uuid.uuid4())
    # 多租户隔离：复用已有 thread 时校验归属
    if not assert_thread_owner(thread_id, tenant_id):
        record_error()
        raise HTTPException(403, "thread belongs to another tenant")
    get_or_create_thread(thread_id, tenant_id=tenant_id)
    stream_id = str(uuid.uuid4())
    set_active_stream(thread_id, stream_id)

    # 后台执行（PoC 用 asyncio.create_task 模拟 worker 队列；
    # 生产换 dramatiq actor 异步触发即可）
    asyncio.create_task(run_stream_job(thread_id, stream_id, body.text, body.model_choice))

    return {"thread_id": thread_id, "stream_id": stream_id, "status": "queued"}


@app.post("/stop")
async def stop(body: dict, tenant_id: str = Depends(require_tenant)):
    thread_id = body.get("thread_id")
    if not thread_id:
        raise HTTPException(400, "thread_id required")
    if not assert_thread_owner(thread_id, tenant_id):
        record_error()
        raise HTTPException(403, "thread belongs to another tenant")
    await request_cancel(thread_id)
    return {"thread_id": thread_id, "cancelled": True}


# ─── 选品 Agent 专用路由（multi_region e2e 接入 backend）───
class SelectionBody(BaseModel):
    thread_id: str | None = None
    user_text: str  # "我想做 X 选品调研，目标 Y 市场..."
    model_choice: str = "flash"


@app.post("/selection/start")
async def selection_start(body: SelectionBody, tenant_id: str = Depends(require_tenant)):
    """
    启动一个完整的 8 阶段选品调研。
    任务通过 dramatiq 入队 Redis（持久化，服务重启不丢），由 worker 进程异步执行。
    
    返回 stream_id 后，客户端用 GET /events?thread_id=xxx 订阅 SSE 实时事件流。
    需鉴权：请求头 X-API-Key（dev 模式可省略，归到 dev_tenant）。
    """
    thread_id = body.thread_id or str(uuid.uuid4())
    # 多租户隔离：复用已有 thread 时校验归属
    if not assert_thread_owner(thread_id, tenant_id):
        record_error()
        raise HTTPException(403, "thread belongs to another tenant")
    get_or_create_thread(thread_id, tenant_id=tenant_id)
    stream_id = str(uuid.uuid4())
    set_active_stream(thread_id, stream_id)
    record_job_start()
    
    # 真任务队列：dramatiq 入队（Redis 持久化），worker 进程消费
    # 备选：如果 worker 没起，回退到 asyncio.create_task（仅 dev 用）
    try:
        from backend.queue import run_selection_actor
        run_selection_actor.send(thread_id, stream_id, body.user_text, body.model_choice)
        queued_via = "dramatiq"
    except Exception as e:
        # dev fallback
        asyncio.create_task(run_selection_job(
            thread_id, stream_id, body.user_text, body.model_choice
        ))
        queued_via = f"asyncio_fallback ({str(e)[:60]})"
    
    return {
        "thread_id": thread_id, "stream_id": stream_id, "status": "queued",
        "tenant_id": tenant_id,
        "queued_via": queued_via,
        "subscribe_url": f"/events?thread_id={thread_id}",
        "thread_state_url": f"/thread/{thread_id}",
    }


# ─── SSE 订阅事件流 ───
@app.get("/events")
async def events(thread_id: str, last_seq: int = 0,
                 tenant_id: str = Depends(require_tenant_query)):
    """
    SSE 端点。客户端可传 last_seq 做 catch-up 衔接。
    鉴权：EventSource 无法设请求头，故用 `?api_key=`（dev 模式可省略）。
    多租户隔离：只能订阅本租户的 thread。
    """
    if not assert_thread_owner(thread_id, tenant_id):
        record_error()
        raise HTTPException(403, "thread belongs to another tenant")

    async def event_gen():
        # 1. 先重放未消费的 chunk
        chunks = await get_accumulated_chunks(thread_id)
        for i, c in enumerate(chunks, 1):
            if i > last_seq:
                yield {"event": "stream-chunk",
                       "data": json.dumps({"chunk": c, "seq": i}, ensure_ascii=False)}
        # 2. 订阅实时
        sub_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        ps = sub_client.pubsub()
        await ps.subscribe(EVENT_CHANNEL.format(thread_id=thread_id))
        try:
            while True:
                msg = await ps.get_message(ignore_subscribe_messages=True, timeout=30)
                if msg and msg.get("type") == "message":
                    yield {"event": "agent-event", "data": msg["data"]}
                else:
                    # heartbeat
                    yield {"event": "ping", "data": "1"}
        finally:
            await ps.unsubscribe()
            await sub_client.aclose()

    return EventSourceResponse(event_gen())


@app.get("/catchup")
async def catchup(thread_id: str, tenant_id: str = Depends(require_tenant_query)):
    if not assert_thread_owner(thread_id, tenant_id):
        record_error()
        raise HTTPException(403, "thread belongs to another tenant")
    chunks = await get_accumulated_chunks(thread_id)
    return {"thread_id": thread_id, "chunks": chunks}


@app.get("/thread/{thread_id}")
async def thread_state(thread_id: str, tenant_id: str = Depends(require_tenant)):
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None:
            raise HTTPException(404, "thread not found")
        # 多租户隔离：非归属租户禁止读取
        owner = getattr(t, "tenant_id", None) or "dev_tenant"
        if owner != tenant_id and tenant_id != "dev_tenant":
            record_error()
            raise HTTPException(403, "thread belongs to another tenant")
        msgs = list_messages(thread_id)
        return {
            "id": t.id, "title": t.title, "tenant_id": owner,
            "active_stream_id": t.active_stream_id,
            "tokens": {"in": t.total_input_tokens, "out": t.total_output_tokens,
                        "in_credits": t.total_input_credits,
                        "out_credits": t.total_output_credits},
            "messages": [
                {"id": m.id, "role": m.role, "parts": m.parts,
                 "created_at": m.created_at.isoformat() if m.created_at else None}
                for m in msgs
            ],
        }


@app.get("/metrics")
async def metrics():
    """监控端点：请求数/各租户用量/错误数/运行时长（供 Prometheus/健康检查抓取）。"""
    return get_metrics()


@app.get("/healthz")
async def healthz():
    """健康检查：确认进程存活 + Redis 可达。"""
    redis_ok = False
    try:
        c = aioredis.from_url(REDIS_URL, decode_responses=True)
        await c.ping()
        await c.aclose()
        redis_ok = True
    except Exception:
        pass
    return {"ok": True, "redis": redis_ok}


@app.get("/")
async def root():
    return {"ok": True, "endpoints": ["/chat", "/stop", "/selection/start",
                                        "/events", "/catchup", "/thread/{id}",
                                        "/metrics", "/healthz", "/graphql",
                                        "/report-file", "/report-asset"]}


# ─── 报告文件 / 资源服务（前端下载 5 件套 + 嵌图） ───
from fastapi.responses import FileResponse
import os as _os

_REPORTS_ROOT = Path(__file__).resolve().parent.parent / "reports"


def _safe_report_path(path: str) -> Path:
    """把前端传来的路径解析为 reports/ 下的安全绝对路径（防目录穿越）。"""
    p = Path(path)
    if not p.is_absolute():
        p = (_REPORTS_ROOT / path).resolve()
    else:
        p = p.resolve()
    # 必须在 reports/ 目录下
    if _REPORTS_ROOT.resolve() not in p.parents and p != _REPORTS_ROOT.resolve():
        raise HTTPException(403, "path outside reports dir")
    if not p.exists():
        raise HTTPException(404, "file not found")
    return p


@app.get("/report-file")
async def report_file(path: str):
    """下载报告文件（merchant.md / report.pdf 等）。"""
    p = _safe_report_path(path)
    media = "application/pdf" if p.suffix == ".pdf" else "text/markdown; charset=utf-8"
    return FileResponse(str(p), media_type=media, filename=p.name)


@app.get("/report-asset")
async def report_asset(path: str):
    """提供报告里引用的图片（assets/xxx.jpg 等），相对路径基于报告目录解析。"""
    p = _safe_report_path(path)
    return FileResponse(str(p))


# 启动方式：uvicorn poc.p01_selection.backend.app:app --reload --port 8001
