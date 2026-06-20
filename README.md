# market-and-survey · 跨境电商运营自动化

把跨境电商全流程拆成 10 个环节（① 市调/选品 → ② 供应链采购 → ③ Listing → ④ 本地化 → ⑤ 多平台铺货 → ⑥ 营销 → ⑦ 客服 → ⑧ 订单/物流/库存 → ⑨ 财务/合规 → ⑩ 数据复盘），逐环节用 AI Agent 自动化。总规划见 [`跨电完环清.md`](跨电完环清.md)，方法论/设计文档在 [`环细文/`](环细文/)。

> **当前进度**：仅实现第 ① 环节「市场调研 / 选品」的 PoC，位于 [`poc/p01_selection/`](poc/p01_selection/)。其余 9 个环节尚为文档规划。

## 选品 / 市场调研 Agent 是什么

一个对话式 AI 选品助手：卖家用自然语言描述需求（如「做蓝牙耳机选品，目标美国市场，预算 5 万/月」），Agent 按 8 阶段「procurement-research」方法论自动完成调研，产出选品决策报告。

- **大模型**：DeepSeek（`deepseek-v4-flash` 编排 / `deepseek-v4-pro` 决策），OpenAI 兼容 function-calling 智能体循环，约 56 个工具。
- **数据真实性铁律**：候选品 ASIN/价格/销量必须来自真实抓取池并经 `validate_candidate` 校验，成本从 1688 实时取，销量由 BSR 估算函数算 —— system prompt 明确禁止 LLM 编造。
- **采集层**：9 级降级引擎链（curl_cffi → Scrapling → patchright → botasaurus →（付费）住宅代理/打码），含反爬页特征检测与代理自检。
- **成本/风险建模**：14 项成本拆解利润测算 + 蒙特卡洛压力测试（亏损概率/VaR/CVaR）。
- **后端**：FastAPI 控制平面（`/chat`、`/selection/start`、SSE `/events`、GraphQL）+ Redis pub/sub + dramatiq 队列 + SQLite，X-API-Key 多租户。
- **前端**：Next.js 14 + React 18 + TypeScript + Tailwind 的聊天式 UI，通过原生 SSE 实时流式展示「思考 + 工具调用 + Markdown 报告」。

## 快速开始

### 1. 环境变量

```bash
cp .env.example .env
# 编辑 .env，至少填 DEEPSEEK_API_KEY（无 Key 也能 import / 跑单测，但 Agent 对话会 401）
```

各变量含义见 [`.env.example`](.env.example)。

### 2. Python 依赖（后端 + 核心）

需要 Python 3.12。依赖已按用途拆分到 [`requirements/`](requirements/)：

| 文件 | 内容 | 何时装 |
| --- | --- | --- |
| `requirements/core.txt` | LLM + 分析 + 报告导出 | 必装（被 backend 依赖） |
| `requirements/backend.txt` | FastAPI + 队列 + 存储（含 core） | 跑后端 |
| `requirements/scrapers.txt` | 9 级降级链爬虫引擎 | 仅真实抓取平台数据时 |

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt              # = backend.txt（含 core），新克隆即可起后端
pip install -r requirements/scrapers.txt     # 可选：真实抓取才需要
```

> 不装 `scrapers.txt` 时后端仍能启动、纯函数工具与单测照常跑；真正调用抓取类工具才会提示安装。

### 3. 启动后端

```bash
cd poc/p01_selection
# 可选：本机 Redis（启用队列/SSE 重放/cancel）。bin/ 内置 Windows 版 redis；
# 其他平台用系统 redis-server，或先不启（dev 模式下任务在进程内直接跑）。
uvicorn backend.app:app --reload --port 8001
```

### 4. 启动前端

```bash
cd poc/p01_selection/frontend
npm install
# 后端非默认地址时：echo "NEXT_PUBLIC_BACKEND_BASE=http://127.0.0.1:8001" > .env.local
npm run dev      # http://localhost:3000
```

## 测试

纯函数 / 一致性单测（无需 API Key、无需 Redis、无需爬虫依赖）：

```bash
cd poc/p01_selection
pip install -r ../../requirements/core.txt pytest
PYTHONPATH=. pytest -q
```

覆盖：14 项成本测算不变量、蒙特卡洛确定性与向量化等价性、BSR→月销映射、消息清洗（assistant↔tool 配对）、`TOOLS_SCHEMA`↔`TOOL_IMPL` 一致性。

## 目录结构

```
poc/p01_selection/
├── agent.py            # CLI 入口（单轮对话）
├── backend/            # FastAPI 控制平面（app/auth/events/storage/queue + selection/stream job）
├── modules/            # 工具实现：llm / agent_tools / scraper / parser / bestsellers /
│                       #   full_cost / ip_risk / report* / trends / extras …
├── skills/             # procurement-research 方法论 prompt
├── frontend/           # Next.js 聊天 UI
└── tests/              # pytest 单测
环细文/                  # 设计 / 方法论文档（高度缩写中文）
跨电完环清.md             # 10 环节总规划
requirements/           # 依赖（core / backend / scrapers）
```

## 注意

- 模型名（`deepseek-v4-flash` / `deepseek-v4-pro`）的唯一来源是 [`poc/p01_selection/modules/llm.py`](poc/p01_selection/modules/llm.py)，backend 与 CLI 都从这里 import，避免漂移。
- 生产部署务必设 `BACKEND_AUTH_REQUIRED=1` 并配置真实 `BACKEND_API_KEYS`，否则后端裸奔。
- `bin/` 内置的是 Windows 版 redis / xray 二进制；非 Windows 平台请用系统对应组件。
