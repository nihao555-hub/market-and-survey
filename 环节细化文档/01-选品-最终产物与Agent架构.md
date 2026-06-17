# ① 市场调研/选品 — 最终产物 & Agent 架构

> 回答两个问题：1) 这一环节最终交付什么（商家输入什么→输出什么）；2) 为什么要做成 Agent，怎么做。
> LLM：DeepSeek，用户可选 V4 Flash(deepseek-chat) / Pro(deepseek-reasoner)。
> Agent 架构参考 `.kiro/steering/agent-backend-patterns.md` + `agent-frontend-patterns.md`。

---

## 一、最终产物：一个「选品决策 Agent」

不是一个静态报表工具，而是一个**对话式选品助手**。商家像跟一个资深选品专员对话一样使用它。

### 商家输入（任选其一，自然语言）
- "帮我看看无线耳机这个品类在美国市场值不值得做"
- "我想做厨房小工具，预算采购价 5 美元以内，找几个有机会的"
- "分析一下这个竞品 [URL]，我能不能做一个更好的"
- 或结构化输入：品类 + 目标站点(Amazon/Walmart/Temu...) + 目标市场 + 采购成本区间

### Agent 输出（选品决策报告）
一份结构化报告 + 对话解释，包含 5 个子任务的完整结论：

| 子任务 | 报告中的具体产物 |
|---|---|
| 趋势洞察 | 品类 Google Trends 热度曲线、季节性、上升/下降判断 |
| 竞品分析 | Top 竞品表（价格/评分/评论数/BSR估算销量）+ 评论痛点 TOP5 + 卖点提炼 |
| 利润测算 | 每个候选品的成本拆解 + 净利 + 毛利率（采购+头程+佣金+FBA+广告+退货+税） |
| 蓝海/红海 | 竞争度评分 + 市场集中度 + 差异化机会点（基于评论痛点） |
| 选品决策 | 每个候选品："上架/观察/放弃" + 建议定价区间 + 理由 |

交付形态：
- **对话流**：Agent 边调研边把"思考步骤+工具调用"实时流式展示（参考前端 steering 的思考步骤可视化）
- **结构化报告**：HTML/在线看板（Superset 嵌入）+ 可导出 JSON/Excel
- **可追问**：商家可继续问"为什么放弃 B"、"如果定价降到 X 呢"，Agent 基于已采集数据再分析

---

## 二、为什么做成 Agent（而不是固定流水线）

| 固定流水线 | 选品 Agent |
|---|---|
| 商家必须按表单填死参数 | 自然语言提需求，门槛低 |
| 输出固定模板 | 按商家关注点动态组织分析 |
| 不能追问 | 可多轮对话深挖 |
| 加新平台/新分析要改代码 | 加一个工具/技能包即可 |
| 商家看不懂"为什么" | 思考过程透明，给理由 |

选品的本质是**多步推理 + 动态调度数据源**，这正是 Agent 的主场：模型自己决定"先查趋势→发现上升→再抓竞品→看到差评多→提示差异化机会→算利润→给结论"。

---

## 三、Agent 架构（落地到我们的技术栈）

参考 steering 的"控制平面/数据平面分离 + 元工具 + 技能包"，但 MVP 先做精简版（不必一上来全套）。

```
商家自然语言
   │
   ▼
[选品 Agent  (DeepSeek + 工具循环)]
   │  system prompt：你是跨境选品专家，按需调用工具，最终给选品决策
   │  模型可选：deepseek-chat(V4 Flash, 快) / deepseek-reasoner(Pro, 深度推理)
   │
   ├─ tool: search_products(平台, 关键词)      → 采集层(Scrapling/botasaurus/patchright 多引擎冗余)
   ├─ tool: get_product_reviews(商品)          → 采集评论
   ├─ tool: get_trend(关键词, 地区)            → pytrends
   ├─ tool: calc_profit(售价,成本,...)         → 利润公式
   ├─ tool: analyze_reviews(评论[])            → LLM 提炼痛点/卖点（可递归用 LLM）
   ├─ tool: score_market(竞品[])               → 蓝海/红海评分
   └─ tool: save_report(...)                   → 出报告/入库
   │
   ▼
流式返回：思考步骤 + 工具调用过程 + 最终决策报告
```

### 工具数量判断
本环节工具约 7~8 个 → **直接平铺 ToolSet 即可**，不需要 steering 里的"元工具(learn_tools/execute_tool)"。元工具是几百个工具时才需要。后续多环节合并（选品+Listing+客服…几十个工具）时再上元工具收敛。

### 模型接入（按 steering §3.2 万金油方案）
DeepSeek 是 OpenAI 兼容协议，直接用 openai SDK + baseUrl 即可：
```
baseUrl: https://api.deepseek.com/v1
models:
  - deepseek-chat     (V4 Flash, 快/便宜, 默认 DEFAULT_FAST)
  - deepseek-reasoner (Pro, 深度推理, DEFAULT_SMART)
```
用户在前端下拉切换。Flash 用于快速调研/抓取调度，Pro 用于最终的蓝海判断和决策（需要深度推理）。

---

## 四、采集层最终方案（实测后定稿）

经 8 站实测，多引擎按"成本/强度"分级，Agent 的 search_products 工具内部自动降级：

```
L1 curl_cffi(TLS)         → 最快，无反爬站
L2 Scrapling              → 自适应解析，Amazon 直通
L3 patchright(浏览器)      → SPA 渲染，Shopee/Temu 直通
L4 botasaurus(google_get + bypass_cloudflare)  → 反爬攻坚，攻破 Walmart
L5 + 住宅代理(美国IP)      → 解 eBay/BestBuy 地理封锁  [需付费]
L6 + 打码服务(CapSolver)   → 解 Etsy DataDome / AliExpress 阿里NC  [需付费]
```

实测覆盖（开源免费部分）：**Amazon / Shopee / Temu / Walmart = 4/8 直通**。
其余 4 站是地理封锁 + 商业反爬，需付费代理/打码（行业通用，非技术问题）。

---

## 五、最终产物的"数据沉淀"价值
每次 Agent 跑选品，都把抓到的 BSR/价格快照入历史库。跑得越多，**自有的"价格/BSR 历史曲线"越厚**，逐步替代 Keepa，形成数据护城河。

---

## 六、MVP 落地顺序（基于已跑通的 PoC）
1. [x] 采集层多引擎跑通（4 站直通已验证）
2. [x] DeepSeek 双模型连通已验证
3. [ ] 把 modules/* 的函数包装成 Agent 的 tools（function calling）
4. [ ] 写选品 Agent 的 system prompt + 工具循环（DeepSeek function calling）
5. [ ] 评论采集 + analyze_reviews(LLM 痛点提炼)
6. [ ] 接前端对话流（参考 frontend steering：思考步骤可视化）
7. [ ] save_report 出 HTML/看板
8. [ ] 后续：付费代理/打码接入，覆盖剩余 4 站

---

## 七、与 steering 的对齐情况
- ✅ 多模型接入（DeepSeek 走 openai-compatible 万金油）
- ✅ 工具循环（function calling + step 上限）
- 🟡 控制平面/数据平面分离（队列+pubsub）→ MVP 可先同步，规模化再上
- 🟡 元工具 → 本环节工具少，暂不需要，多环节合并后再上
- ✅ 技能包思路 → 每个环节(选品/Listing/客服)做成一个 skill 包
- ✅ 前端思考步骤流式可视化 → 直接照 frontend steering 实现
