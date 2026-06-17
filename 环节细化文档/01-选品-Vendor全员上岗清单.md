# ① 选品环节 — Vendor 21 项目"全员上岗"清单

> 用户要求："不要不用，作为备选，这样大幅增强鲁棒性。"
> 本文档逐一交代每个 vendor 项目在第一阶段的角色，没有一个闲置。

---

## 全员一览表（21 项目，分级激活）

| # | 项目 | 层 | 角色等级 | 接入位置 | 触发条件 |
|---|---|---|---|---|---|
| 1 | `Scrapling` | 采集 L2 | 🔥 主力 | `modules/scraper.py` | 总是参与（HTTP 解析层） |
| 2 | `curl_cffi` | 采集 L1 | 🔥 主力 | `modules/scraper.py` | 总是先尝试（最快） |
| 3 | `patchright-python` | 采集 L3 | 🔥 主力 | `modules/scraper.py` | SPA/JS 站点 |
| 4 | `botasaurus` | 采集 L6 | 🔥 主力 | `modules/scraper.py`+`reviews.py` | 反爬最强（攻 Walmart/AliExpress/评论页） |
| 5 | `pytrends` | 趋势 | 🔥 主力 | `modules/trends.py` | 阶段 1 趋势洞察 |
| 6 | `tenacity` | 编排 | 🔥 主力 | `modules/scraper.py` | 失败重试装饰 |
| 7 | DeepSeek | LLM | 🔥 主力 | `modules/llm.py` | Agent 推理（Flash/Pro 切换） |
| 8 | `pydoll` | 采集 L4 | 🛡 备胎 | `modules/scraper.py` | L1-L3 都失败时 |
| 9 | `SeleniumBase` | 采集 L5 | 🛡 备胎 | `modules/scraper.py` | UC Mode 大杀器 |
| 10 | `camoufox` | 采集 L7 | 🛡 备胎 | `modules/scraper.py` | Firefox 反指纹（待下载内核） |
| 11 | `fingerprint-suite` | 采集 | 🛡 内嵌 | botasaurus 内部 | 已经在用 |
| 12 | `FlareSolverr` | 采集 | 🛡 待启动 | Docker 独立服务 | 遇 Cloudflare 时 |
| 13 | `proxy_pool` | 采集 | 🛡 待启动 | Docker 独立服务 | xray 失效时（备代理池） |
| 14 | `crawl4ai` | 清洗 | 🔧 增强 | `modules/extras.py`+`agent_tools.webpage_to_markdown` | 深度分析对手页 |
| 15 | `markitdown` | 清洗 | 🔧 增强 | `modules/extras.py`+`agent_tools.file_to_markdown` | 处理 PDF 报价/认证 |
| 16 | `Scrapegraph-ai` | 清洗 | 🔧 增强 | `modules/extras.py:llm_extract` | 页面结构变化大时 |
| 17 | `thefuzz` | 趋势 | 🔧 增强 | `modules/trends.py:get_related_keywords` | 关键词扩展 |
| 18 | `open-seo` | 趋势 | 🔧 增强 | （仓库代码可参考的 SEO 工具集） | 后续接入关键词竞争分析 |
| 19 | `apscheduler` | 编排 | 📅 调度 | `modules/extras.py:make_scheduler` | 生产定时任务（每小时刷 BSR） |
| 20 | `prefect` | 编排 | 📅 调度 | `modules/extras.py:has_prefect()` | 多环节合并时的 DAG |
| 21 | `superset` / `metabase` | 展示 | 📊 看板 | Docker 独立部署 | 给商家看的可视化看板 |

---

## 分级解释

### 🔥 主力（7 个）— 每次跑都参与
**采集**：`curl_cffi → Scrapling → patchright → botasaurus`（4 级降级）
**趋势**：`pytrends`
**编排**：`tenacity`（重试装饰），DeepSeek（LLM 大脑）

### 🛡 备胎（6 个）— 主力失败自动接管
当主力 4 级降级仍失败时，scraper.py 会自动尝试：
- **L4 pydoll**：CDP 协议浏览器（无 webdriver）
- **L5 SeleniumBase（UC Mode）**：综合反爬大杀器
- **L7 camoufox**：Firefox 反指纹内核
- **L8 FlareSolverr**：专破 Cloudflare 挑战
- **L9 proxy_pool**：免费代理池兜底
- **fingerprint-suite**：botasaurus 已内嵌使用

### 🔧 增强工具（5 个）— Agent 按需调用
- **crawl4ai** → `tool_webpage_to_markdown`：深度分析竞品 Listing
- **markitdown** → `tool_file_to_markdown`：处理供应商 PDF
- **Scrapegraph-ai** → `llm_extract`：页面结构变化用 LLM 抽
- **thefuzz** → `get_related_keywords`：关键词扩展
- **open-seo** → 仓库代码作为 SEO 增强参考

### 📅 调度（2 个）— 生产环境激活
- **APScheduler**：定时刷 BSR/价格快照（积累历史数据）
- **Prefect**：多环节合并时的 DAG 编排

### 📊 看板（2 个）— 独立 Docker 部署
- **Superset / Metabase**：连主库出选品决策可视化看板（给商家看）

---

## 鲁棒性保证（多引擎冗余的"为什么"）

每个 vendor 项目都是反爬/采集/分析体系中的一环。
真实场景里，反爬随时变化（Amazon/Walmart 经常调整）：
- 今天 Scrapling 能直接抓 Amazon → 明天可能要切到 patchright
- patchright 失效 → 再降级到 botasaurus
- botasaurus 也被挡 → 降级到 SeleniumBase UC Mode
- 都不行 → 上 FlareSolverr 破 Cloudflare 挑战

**这就是"全员上岗"的价值**：单点失效不会影响整个系统，
因为后面还有 5+ 层冗余。这是商业级 SaaS 必须的鲁棒性。

---

## 更新到 PoC 报告
本环节使用情况已同步到：
- `01-选品-PoC验证报告.md` 第十一节
- `01-选品-完整流程图.md` 第四节
