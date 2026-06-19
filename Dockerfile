# 选品/市场调研 后端镜像：FastAPI 控制面 + dramatiq worker + APScheduler 每日刷新。
# 一个容器同时跑 web 与 worker（见 poc/p01_selection/start.sh）。
# Redis / Postgres 走环境变量注入：REDIS_URL / DATABASE_URL。
# 构建上下文 = 仓库根目录。
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/poc/p01_selection

WORKDIR /app

# 自带 redis-server，使容器自包含（免费单容器平台无外部 Redis 时设 EMBEDDED_REDIS=1）。
RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server \
    && rm -rf /var/lib/apt/lists/*

# 依赖层（先拷 requirements 命中缓存）
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/backend.txt

# 应用代码
COPY poc/p01_selection/ poc/p01_selection/

WORKDIR /app/poc/p01_selection
RUN chmod +x start.sh

EXPOSE 8001
CMD ["bash", "start.sh"]
