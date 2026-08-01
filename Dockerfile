# SelectPilot 后端一体化镜像（FastAPI + APScheduler 每日刷新 + 内嵌 Redis）
# 适用于 Render / Railway / Fly.io / 任意支持 Docker 的长驻进程平台。
#
# 构建：docker build -t selectpilot-backend .
# 运行：docker run -p 8001:8001 --env-file .env selectpilot-backend
#
# 平台注入的环境变量：
#   PORT                 平台分配端口（Render/Railway 自动注入；默认 8001）
#   EMBEDDED_REDIS=1     单容器内嵌 Redis（免费层无外部 Redis 时设 1，推荐）
#   REDIS_URL            有外部 Redis（Render Key Value / Upstash）时改用它
#   TIKHUB_API_KEY       TikHub 实时数据（TikTok Shop / 社媒趋势）必填
#   DEEPSEEK_API_KEY     LLM 必填
#   SCRAPERAPI_KEY       Google Trends / 被封平台回退（推荐）
#   DATABASE_URL         可选；不设则用容器内 SQLite（/app/data/agent.sqlite，
#                        建议挂持久卷，否则重部署后历史快照丢失）
#   OPEN_DATASET_ENABLED=1  启用开源数据集底子（Amazon Reviews 2023）
#   BACKEND_API_KEYS     API 访问密钥（逗号分隔），前端/管理端调用凭据
FROM python:3.12-slim

# 内嵌 Redis（EMBEDDED_REDIS=1 时由 start.sh 拉起）+ 基础工具
RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依赖分层缓存：先拷 requirements 再拷代码
COPY requirements/ ./requirements/
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements/backend.txt

# 产品代码（poc/p01_selection 为后端工作目录，start.sh 在其中）
COPY poc/ ./poc/

WORKDIR /app/poc/p01_selection
RUN chmod +x start.sh

ENV PORT=8001 \
    EMBEDDED_REDIS=1 \
    DAILY_REFRESH_ENABLED=1 \
    DAILY_REFRESH_ON_STARTUP=1 \
    OPEN_DATASET_ENABLED=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

CMD ["./start.sh"]
