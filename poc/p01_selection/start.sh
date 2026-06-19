#!/usr/bin/env bash
# 单容器同时拉起 dramatiq worker（后台）+ uvicorn web（前台）。
# APScheduler 每日刷新在 web 进程内启动（见 backend/app.py）。
# 平台注入：PORT / REDIS_URL / DATABASE_URL / TIKHUB_API_KEY / DEEPSEEK_API_KEY / BACKEND_API_KEYS。
# 横向扩容时，多余副本设 DAILY_REFRESH_ENABLED=0，避免重复刷新浪费 TikHub 额度。
set -uo pipefail

PORT="${PORT:-8001}"

python -m dramatiq backend.queue \
  --processes "${DRAMATIQ_PROCESSES:-1}" \
  --threads "${DRAMATIQ_THREADS:-2}" &
WORKER_PID=$!

term() { kill -TERM "$WORKER_PID" 2>/dev/null || true; }
trap term TERM INT

exec python -m uvicorn backend.app:app --host 0.0.0.0 --port "${PORT}"
