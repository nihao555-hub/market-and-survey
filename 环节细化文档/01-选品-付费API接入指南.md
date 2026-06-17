# 第①步选品 — 付费 API 接入指南（均有免费额度）

> 设计原则：**缺 key 自动降级到开源路径，不报错、不编造**。
> 配了 key → 真实绝对数据，客观评分提升；没配 → 仍能跑（DDGS 相对值 + scraper），只是精度低一档。

---

## 1. DataForSEO — 真实 Google Ads 绝对搜索量（补『趋势洞察』最大短板）

**解决什么**：Google Trends 只有 0-100 相对热度，没有"这个词每月多少人搜"。DataForSEO 给真实绝对月搜索量 + CPC + 竞争度 + 12 月走势。

### 注册步骤
1. 打开 https://dataforseo.com → Sign Up（注册送约 $1 credit 体验）
2. 登录后进 Dashboard → API Access / API Settings
3. 拿到 **API Login**（你的邮箱）和 **API Password**（系统生成的密码，**不是登录密码**）

### 配置（`.env`）
```
DATAFORSEO_LOGIN=你的邮箱
DATAFORSEO_PASSWORD=API密码（dashboard生成的那串）
```

### 成本
- `keywords_data/google_ads/search_volume/live` 约 **$0.05/任务**，一个任务最多 1000 个关键词
- $1 credit ≈ 20 次调用 ≈ 覆盖 20 个品类的关键词研究，体验足够

### 用到的工具
- `get_real_search_volume(keywords, geo)` — 直接拿绝对搜索量
- `get_keyword_metrics(seed)` — 自动检测，有 key 就给长尾词补真实搜索量并按量重排

---

## 2. RapidAPI - Real-Time Amazon Data（补『竞品分析』『利润测算』）

**解决什么**：真实月销（sales_volume）、真实 BSR、评分、评论数、价格。比 scraper 稳，比 BSR 经验公式准。

### 注册步骤
1. 打开 https://rapidapi.com → 注册（GitHub/Google 一键登录）
2. 搜索 **"Real-Time Amazon Data"**（作者 letscrape），进 API 页
3. 点 **Subscribe to Test** → 选 **Basic（免费档，约 100-500 请求/月）**
4. 在 API 页的 Endpoints 右侧 Code Snippets 里复制 **X-RapidAPI-Key**

### 配置（`.env`）
```
RAPIDAPI_KEY=你的key
RAPIDAPI_AMAZON_HOST=real-time-amazon-data.p.rapidapi.com
```

### 免费档省着用的策略
- 免费档请求有限 → 只对 **3-5 个候选品** 调 `get_amazon_product_details_api` 拿真实月销
- 不要对全部 BSR Top 200 调（会很快用完）；批量仍走 scraper，候选品才用 API 精校

### 用到的工具
- `get_amazon_product_details_api(asin, geo)` — 单品真实 BSR/月销/评分/卖家数/重量/上架日期/类目/星级分布
  - 实测返回示例（Amazon Basics 瑜伽垫）：BSR "#22 in Sports & Outdoors, #1 in Yoga Mats"、
    月销 "10K+ bought in past month"、★4.6(68575)、Amazon's Choice、4 个卖家、重量 2.2 lbs
- `search_products` — Amazon 系平台 scraper 失败时自动用 RapidAPI 兜底；
  成功但缺月销时自动用 RapidAPI 补 sales_volume
- **已实测可用**（key 已配置 + Basic 免费档已订阅，2026-06）

---

## 3. 验证配置成功

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe poc\p01_selection\modules\paid_apis.py
```
- 输出 `dataforseo.available=true / rapidapi_amazon.available=true` 即成功
- 配了 key 会顺带打印一次真实搜索量 + 真实搜索结果样例

或在 Agent 流程里阶段 0 调 `api_status()` 自检。

---

## 4. 对客观评分的预期提升

| 维度 | 当前 | 配 API 后 | 提升来源 |
|---|---|---|---|
| 趋势洞察 | 7.5 | **8.5+** | DataForSEO 真实绝对搜索量 |
| 竞品分析 | 8.5 | **9.0** | RapidAPI 真实月销/BSR |
| 利润测算 | 7.8 | **8.5** | 真实月销喂盈亏点，误差从±50%降到第一方数据 |

> 注意：采购成本（1688）仍是天花板——DataForSEO/RapidAPI 都不提供采购价，
> 那块仍靠 Made-in-China/DHgate 或用户提供报价。

---

## 4.5 Keepa 免费账号（登录态产品页数据，零成本）

**实测背景**：Keepa 产品页 `keepa.com/#!product/1-ASIN` 的数据走 Cloudflare Turnstile + WebSocket。
- 未登录：botasaurus 能过 Cloudflare，但只渲染空壳（实测 HTML 里 0 个价格）
- **登录后：价格统计表/BSR/评分/卖家数全部渲染进 DOM，可合规读取**

**这是用你自己的免费 Keepa 账号读取页面已渲染的数据，不破解、不逆向 API。**

### 注册步骤
1. https://keepa.com/#!registration 注册免费账号（邮箱 + 密码即可）
2. 填到 `.env`：
```
KEEPA_EMAIL=你的邮箱
KEEPA_PASSWORD=你的密码
```

### 用到的工具
- `get_keepa_product_data(asin, geo)` — 登录态抓 Buy Box/Amazon/New 当前价 + Sales Rank + 评分 + 评论数 + 卖家数（精确数字）
- 免费账号有频率限制 → 只对 3-5 个候选品调用
- 缺账号自动降级到 `get_keepa_price_history`（免费 PNG 曲线，无需登录）

### 三层 Keepa 数据策略（按精度递减，全部免费/自有账号）
1. `get_keepa_product_data` — 登录态精确数字（需免费账号）
2. `get_keepa_price_history` — 历史曲线 PNG（无需账号，图形式）
3. 都不行 → BSR 经验估算（标注 real_data=False）

---

## 5. 安全说明

- key 只写在 `.env`（已在 .gitignore），不要提交到仓库
- RapidAPI 免费档超额会返回 429，代码已优雅处理（降级到 scraper），不会产生意外扣费
- DataForSEO 是预付费 credit 制，余额用完返回 task_error，不会自动扣款
