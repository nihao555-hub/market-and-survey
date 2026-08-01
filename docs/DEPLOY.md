# SelectPilot 后端部署指南（对接 Vercel 前端）

> 前端已部署在 Vercel；本文档部署 **后端**（FastAPI + 每日定时刷新 + 内嵌 Redis）。
> 部署后只需在 Vercel 项目设置 `NEXT_PUBLIC_BACKEND_BASE=https://<后端域名>` 并 Redeploy。

## 为什么之前「数据源没发挥作用、每天没有更新」

1. **后端没有长驻运行**：每日刷新是 APScheduler 进程内调度，后端不跑就没有任何更新；
   TikHub 等数据源也全部经由后端采集，后端缺席 = 数据源全部缺席。
2. **TikHub 解析层 bug**（已于 `optimize/20260801-tikhub-fix` 修复）：代码按三层 `data.data.data`
   解析，TikHub 当前版本实际为两层，商品/品类/热搜全部解析为空。修复后实测 13 类端点真实出数。
3. **环境变量未配**：`TIKHUB_API_KEY` 未配置时 TikHub 通道整体跳过；
   `OPEN_DATASET_ENABLED` 默认关闭，开源数据集底子不启用。

## 方案 A：Render（推荐， Blueprint 一键）

1. 仓库根已带 `render.yaml` + `Dockerfile`。
2. Render Dashboard → **New → Blueprint** → 选择本仓库（或本分支）→ Apply。
3. 构建完成后在 **Environment** 填入 4 个密钥（`render.yaml` 里 `sync:false` 的项）：

   | 变量 | 用途 | 必填 |
   |---|---|---|
   | `TIKHUB_API_KEY` | TikTok Shop 实时商品 / 社媒趋势 / 品类榜 | ✅ |
   | `DEEPSEEK_API_KEY` | LLM 调研 Agent | ✅ |
   | `SCRAPERAPI_KEY` | Google Trends 回退 / 被封电商平台 | 推荐 |
   | `BACKEND_API_KEYS` | API 调用凭据（逗号分隔，自定） | ✅ |

4. **务必选 Starter($7/月) 及以上**：免费实例 15 分钟无流量休眠，定时刷新会停摆。
5. 部署后验证：`curl https://<your-service>.onrender.com/healthz`
   应返回 `{"ok":true,"redis":true,...}`。

## 方案 B：Railway / Fly.io / 任意 Docker 平台

```bash
docker build -t selectpilot-backend .
docker run -p 8001:8001 \
  -e TIKHUB_API_KEY=... -e DEEPSEEK_API_KEY=... \
  -e SCRAPERAPI_KEY=... -e BACKEND_API_KEYS=... \
  selectpilot-backend
```

镜像默认 `EMBEDDED_REDIS=1`（容器内嵌 Redis，无需外部服务）、
`DAILY_REFRESH_ENABLED=1`、`OPEN_DATASET_ENABLED=1`。

## 定时更新机制（已内置，随后端启动）

| 任务 | 频率 | 内容 |
|---|---|---|
| 普通刷新 | 每 2 小时（`DAILY_REFRESH_INTERVAL_HOURS`） | 追踪词 Google Trends / Amazon 关键词 / TikTok Shop 商品 |
| 全量刷新 | 每天美国东部 0:00（UTC 5:00，`DAILY_FULL_REFRESH_HOUR_UTC`） | 含全部 220+ 子品类榜单 |
| 启动刷新 | 每次启动（`DAILY_REFRESH_ON_STARTUP=1`） | 精简词表快速上线底子数据 |

手动触发：`POST /admin/daily-refresh`（带 API Key）或 GraphQL `triggerDailyRefresh`。

## 对接 Vercel 前端

Vercel 项目 → Settings → Environment Variables：

```
NEXT_PUBLIC_BACKEND_BASE = https://<your-service>.onrender.com
```

保存后 **Redeploy**。前端所有 `/chat` `/events` `/graphql` 等请求会 rewrite 到后端。

## 部署后自检清单

1. `GET /healthz` → `ok:true, redis:true`
2. 启动日志出现 `刷新调度已启动：普通刷新 cron ... 全量刷新 ...`
3. 启动后几分钟内前端「数据看板」出现 TikTok Shop 品类榜 / 热销榜 / 社媒趋势
4. 次日确认快照时间戳每日递增（全量刷新生效）

## 数据持久化说明

默认 SQLite 落在容器内 `/app/poc/p01_selection/data/agent.sqlite`——**重新部署会丢失历史快照**。
需要保留历史：Render 挂 Disk（挂载路径设为该目录），或设 `DATABASE_URL` 指向外部 Postgres
（如 Supabase / Render PostgreSQL）。
