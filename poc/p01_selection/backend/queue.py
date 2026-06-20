"""
真正的任务队列（dramatiq + Redis broker）— 替换 asyncio.create_task
- 多 worker 进程
- Redis 持久化任务（重启不丢）
- 自动重试 / 限速 / 超时
- 支持 fanout（多 case 并发跑）
"""
from __future__ import annotations
import os, json, asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, TimeLimit, ShutdownNotifications, Callbacks, Pipelines, Retries

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

# 创建 broker（生产可换 RabbitMQ）
redis_broker = RedisBroker(url=REDIS_URL)
redis_broker.add_middleware(AgeLimit(max_age=3600 * 1000))      # 任务最多存活 1 小时
redis_broker.add_middleware(TimeLimit(time_limit=1800 * 1000))  # 单任务最多 30 分钟
redis_broker.add_middleware(ShutdownNotifications())
redis_broker.add_middleware(Callbacks())
redis_broker.add_middleware(Pipelines())
redis_broker.add_middleware(Retries(max_retries=2, min_backoff=10000))

dramatiq.set_broker(redis_broker)


@dramatiq.actor(max_retries=2, time_limit=1800 * 1000, queue_name="selection")
def run_selection_actor(thread_id: str, stream_id: str, user_text: str,
                        model_choice: str = "flash", kind: str = "general"):
    """
    选品 Agent 后台 actor —— 在 worker 进程跑（控制面/数据面分离，steering §2.1 / §8.8）。
    调用 run_selection_job（异步，会 publish 到 Redis pub/sub），SSE /events 端点消费事件流。
    """
    import asyncio
    from backend.selection_job import run_selection_job
    try:
        asyncio.run(run_selection_job(thread_id, stream_id, user_text, model_choice, kind))
        return {"thread_id": thread_id, "stream_id": stream_id, "ok": True}
    except Exception as e:
        return {"thread_id": thread_id, "stream_id": stream_id, "fatal_error": str(e)[:300]}


# 启动 worker：dramatiq backend.queue
