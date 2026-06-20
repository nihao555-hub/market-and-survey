#!/usr/bin/env bash
# 单容器拉起：可选自带 Redis -> dramatiq worker（后台）-> uvicorn web（前台）。
# APScheduler 每日刷新在 web 进程内启动（见 backend/app.py）。
# 平台注入：PORT / DATABASE_URL / TIKHUB_API_KEY / DEEPSEEK_API_KEY / BACKEND_API_KEYS。
# 免费单容器平台（无外部 Redis）：设 EMBEDDED_REDIS=1，本脚本会在容器内起一个 Redis。
# 横向扩容时多余副本设 DAILY_REFRESH_ENABLED=0，避免重复刷新浪费 TikHub 额度。
set -uo pipefail

PORT="${PORT:-8001}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
WORKER_PID=""

# 事件/流式层（SSE chunk catch-up + pub/sub，见 backend/events.py）始终需要 Redis。
# 免费单容器（无外部 Redis）：设 EMBEDDED_REDIS=1，本脚本在容器内起一个轻量 Redis
#   （空载 ~5MB，512MB 实例绰绰有余），单进程内既当流式总线又做 catch-up。
if [ "${EMBEDDED_REDIS:-0}" = "1" ]; then
  echo "[start] launching embedded redis-server on 127.0.0.1:6379"
  redis-server --daemonize yes --save "" --appendonly no \
    --dir /tmp --bind 127.0.0.1 --port 6379 --loglevel warning
  for _ in $(seq 1 20); do
    redis-cli ping >/dev/null 2>&1 && break
    sleep 0.3
  done
fi

# USE_DRAMATIQ_WORKER=1 -> 控制面/数据面分离：独立 worker 消费 Redis 队列（多实例/高并发）。
# USE_DRAMATIQ_WORKER=0（默认）-> 单进程，调研任务在 web 进程内 asyncio 跑（见 graphql_api.py）。
if [ "${USE_DRAMATIQ_WORKER:-0}" = "1" ]; then
  echo "[start] launching dramatiq worker"
  python -m dramatiq backend.queue \
    --processes "${DRAMATIQ_PROCESSES:-1}" \
    --threads "${DRAMATIQ_THREADS:-2}" &
  WORKER_PID=$!
fi

term() { [ -n "$WORKER_PID" ] && kill -TERM "$WORKER_PID" 2>/dev/null || true; }
trap term TERM INT

echo "[start] uvicorn on 0.0.0.0:${PORT} (worker=${USE_DRAMATIQ_WORKER:-0})"
exec python -m uvicorn backend.app:app --host 0.0.0.0 --port "${PORT}"
