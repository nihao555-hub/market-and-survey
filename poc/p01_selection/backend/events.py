"""
事件层（对应 backend steering §2.3 + §2.4）：
- Redis pub/sub 跨进程广播
- chunk seq + catch-up list（带 TTL）
- cancel channel 单订阅连接 + 内部 Map 路由
"""
from __future__ import annotations
import json, uuid, asyncio
from typing import Optional, Callable
import redis.asyncio as aioredis

REDIS_URL = "redis://127.0.0.1:6379/0"
CHUNK_TTL = 3600
CHUNKS_KEY = "agent-chat-stream-chunks:{thread_id}"
EVENT_CHANNEL = "agent-chat-events:{thread_id}"
CANCEL_CHANNEL = "agent-chat-cancel:{thread_id}"


_pub_client: aioredis.Redis | None = None
_sub_client: aioredis.Redis | None = None


def get_pub() -> aioredis.Redis:
    global _pub_client
    if _pub_client is None:
        _pub_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _pub_client


async def publish(thread_id: str, event: dict) -> dict:
    """发布事件。stream-chunk 自带 seq + 写 catch-up list；message-persisted 清 list"""
    pub = get_pub()
    published = dict(event)
    if event.get("type") == "stream-chunk":
        chunks_key = CHUNKS_KEY.format(thread_id=thread_id)
        seq = await pub.rpush(chunks_key, json.dumps(event.get("chunk", {}), ensure_ascii=False))
        await pub.expire(chunks_key, CHUNK_TTL)
        published["seq"] = seq
    elif event.get("type") == "message-persisted":
        await pub.delete(CHUNKS_KEY.format(thread_id=thread_id))

    channel = EVENT_CHANNEL.format(thread_id=thread_id)
    await pub.publish(channel, json.dumps(published, ensure_ascii=False))
    return published


async def get_accumulated_chunks(thread_id: str) -> list[dict]:
    """catch-up：取已发布的 chunk 重放"""
    pub = get_pub()
    raw = await pub.lrange(CHUNKS_KEY.format(thread_id=thread_id), 0, -1)
    return [json.loads(x) for x in raw]


# ─── 取消订阅服务（steering §2.4）───
class CancelSubscriber:
    """单 Redis 订阅连接 + 内部 Map 路由 cancel 信号"""
    def __init__(self):
        self._client: aioredis.Redis | None = None
        self._pubsub = None
        self._callbacks: dict[str, Callable] = {}
        self._listener_task = None

    async def _ensure(self):
        if self._client is None:
            self._client = aioredis.from_url(REDIS_URL, decode_responses=True)
            self._pubsub = self._client.pubsub()
            self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self):
        while True:
            try:
                msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    ch = msg["channel"]
                    cb = self._callbacks.pop(ch, None)
                    if cb:
                        try: cb()
                        except Exception: pass
                        await self._pubsub.unsubscribe(ch)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.5)

    async def subscribe(self, channel: str, on_cancel: Callable):
        await self._ensure()
        self._callbacks[channel] = on_cancel
        await self._pubsub.subscribe(channel)

    async def unsubscribe(self, channel: str):
        self._callbacks.pop(channel, None)
        if self._pubsub:
            try: await self._pubsub.unsubscribe(channel)
            except Exception: pass


CANCEL_SUB = CancelSubscriber()


async def request_cancel(thread_id: str):
    pub = get_pub()
    await pub.publish(CANCEL_CHANNEL.format(thread_id=thread_id), "1")
