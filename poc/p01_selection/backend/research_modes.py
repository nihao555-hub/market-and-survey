"""
研究中心 5 个模式的「做精」配置（市场 / 趋势 / 竞品 / 受众 / 机会）。

为什么需要它：5 个侧边栏模式过去共用同一份 8 阶段选品 SYSTEM_TEMPLATE + 同一份写死的
part1/part2 报告 prompt，唯一区别只是 user_text 里一句开场+一句聚焦词——产出几乎一样。
本模块让每个模式拥有真正不同的三件套：
  1) system_addendum —— 追加到 SYSTEM_TEMPLATE 之后，重排「该模式优先调哪些工具、做哪些阶段、
     不做哪些阶段、最终交付什么」，把同一个 Agent 真正掰向不同方向。
  2) report_parts   —— 替换写死的 part1/part2，每个模式有自己的报告骨架（章节完全不同）。
  3) core_stages + nudge —— 让「别没做完就收尾」的阶段闸口与该模式实际该做的工作匹配。

零幻觉/只用真实数据/数据来源市场一致 等铁律仍由 SYSTEM_TEMPLATE + common_rules 全程约束，
本模块只改「侧重与交付物结构」，不放松任何真实性要求。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModeSpec:
    kind: str
    label: str
    system_addendum: str          # 追加到 SYSTEM_TEMPLATE 后的模式专属方法论
    core_stages: frozenset        # 阶段闸口：本模式至少要做过哪些 stage 才算到能写报告的程度
    min_core: int                 # 上述 core_stages 至少命中几个
    nudge: str                    # 想提前收尾时的「继续完成」催促语（按模式定制）
    report_parts: tuple           # 报告分段 prompt 模板（用 __SUMMARY__ / __RULES__ 占位）

    def build_report_prompts(self, summary_md: str, common_rules: str) -> list[str]:
        out: list[str] = []
        for tpl in self.report_parts:
            out.append(tpl.replace("__SUMMARY__", summary_md).replace("__RULES__", common_rules))
        return out


# ───────────────────────── 通用（默认）：完整 8 阶段选品报告 ─────────────────────────
# general 与 market 共用这套「全景」报告骨架（与历史行为一致，保证向后兼容/不回归）。
_GENERAL_PART1 = (
    "基于以上全部真实工具返回结果，输出选品决策报告【前半部分】（给商家看）。\n"
    "## 本次只写（不要写阶段5及以后）：\n"
    "1. 报告头部（标题+数据采集时间+市场/定位/预算）\n"
    "2. 执行汇总表：\n__SUMMARY__\n"
    "3. 阶段1 趋势洞察（季节性+关键词+BSR Top10真实月销）；有 Keepa/价格图嵌本章对应文字旁\n"
    "4. 阶段2 竞争格局（市场规模+价格带+CR4+评分门槛）；价格分布图嵌价格带旁\n"
    "5. 阶段3 痛点挖掘（频次统计 + <details>折叠真实评论原文，每痛点3-5条）\n"
    "6. 阶段4 候选品（5候选真实数据表）。**每个候选品正下方按序嵌它自己的图**（不要堆到末尾画廊）：\n"
    "   - 主图：用工具返回的 main_image.markdown_local（形如 `![](evidence/ASIN_main.jpg)`），没有 local 才退回 markdown_remote\n"
    "   - 详情页截图：用 detail_page.markdown（形如 `![](evidence/ASIN_dp.png)`）\n"
    "   - Keepa 历史图：用 get_keepa_charts_batch 返回的 markdown（形如 `![](keepa_charts/keepa_ASIN_US.png)`）\n"
    "   **务必原样粘贴工具返回的 markdown 字段，不要自己拼绝对路径或改写文件名**。每图配一句说明。\n"
    "每章顶部注明数据来源工具。结尾不要总结，后半部分会接着写。\n\n"
    "__RULES__"
)
_GENERAL_PART2 = (
    "接着上面的报告，继续输出【后半部分】（阶段5-8）。\n"
    "## 本次只写：\n"
    "1. 阶段5 利润可行性（14项成本 new_product+stable 双场景 + 盈亏点 + 蒙特卡洛亏率；"
    "采购成本用真实值，拿不到就整章'待用户提供1688链接'）\n"
    "2. 阶段6 供应链（MOQ阶梯价+比价+头程时间线，无真实数据则待用户提供）\n"
    "3. 阶段7 IP风险（deep_ip_risk_assessment真实结果；未跑写'待品牌名确认后执行'）\n"
    "4. 阶段8 决策表（候选品决策矩阵+主推建议+风险清单+90天行动计划）\n"
    "   **主推选择必须综合打分，不能只看单一指标**：按 ①真实月销/需求 ②竞争可进入性（避开大牌垄断/红海）"
    "③利润空间 ④IP风险 ⑤差异化机会 五维给每个候选品打分排序。\n"
    "   **必须显式说明为什么没选销量最高的那个**：若销量第一是 Amazon Basics / 平台自营 / 头部大牌等"
    "新卖家无法竞争的对象，明确写出'销量虽高但不可进入'的理由；主推应是『综合最优且新卖家可切入』的标的，"
    "而非单纯销量冠军。决策矩阵要让商家一眼看懂排序逻辑。\n"
    "5. 证据索引（只放 dp链接/BSR URL/1688链接 纯文字，禁止再嵌图做画廊，图都已在阶段1/3/4对应位置）+ 待用户提供清单（完整汇总）\n"
    "这是收尾部分，要完整写到阶段8决策表。\n\n"
    "__RULES__"
)

GENERAL = ModeSpec(
    kind="general",
    label="选品调研",
    system_addendum="",
    core_stages=frozenset({"stage1_trends", "stage2_competition", "stage3_pain_points", "stage4_candidates"}),
    min_core=3,
    nudge=(
        "⚠️ 核心阶段还没做完就想收尾（已登记阶段：{done}）。"
        "请**继续调用工具**完成：阶段1趋势+真实在售商品、阶段2竞争格局、"
        "阶段3评论痛点、阶段4候选品筛选。每完成一个阶段调 record_stage_status 登记。"
        "数据采集失败的市场如实标注失败即可，但不要跳过还能做的阶段直接写报告。"
    ),
    report_parts=(_GENERAL_PART1, _GENERAL_PART2),
)


# ───────────────────────── 市场调研：全景（沿用完整报告，侧重规模/竞争/利润）─────────────────────────
MARKET = ModeSpec(
    kind="market",
    label="市场调研",
    system_addendum=(
        "\n## 🎯 本次模式：市场调研（全景）——目标是把一个品类的「盘子有多大、增长怎样、"
        "竞争多激烈、还有多少利润空间」讲清楚。\n"
        "- 重心工具：estimate_market_size（TAM/SAM 真实测算）、get_trend + compare_seasonality（增长与季节性）、"
        "analyze_market_structure（CR4 集中度 / 价格带 / 评分门槛）、full_cost_breakdown + monte_carlo_stress_test（利润空间）。\n"
        "- 务必给出市场规模量级与增长判断（基于真实在售商品数/销量/趋势曲线），并显式标注估算口径与误差。\n"
        "- 这是 5 个模式里最完整的一档，按 8 阶段全流程推进，最终给出可落地的选品决策。\n"
    ),
    core_stages=GENERAL.core_stages,
    min_core=3,
    nudge=GENERAL.nudge,
    report_parts=(_GENERAL_PART1, _GENERAL_PART2),
)


# ───────────────────────── 趋势探索：上升关键词 + 热度曲线 + 拐点 ─────────────────────────
TREND = ModeSpec(
    kind="trend",
    label="趋势探索",
    system_addendum=(
        "\n## 🎯 本次模式：趋势探索 —— 目标是**发现正在上升的品类/关键词、判断热度拐点、捕捉早期机会**，"
        "**不是**做完整选品决策（不需要利润测算/IP/供应链/候选品五件套）。\n"
        "### 必须重度使用的工具（按序）：\n"
        "1. get_current_datetime —— 锚定时间语境（趋势必须有时间坐标）。\n"
        "2. get_trend（≥3 个关键词，传 geo=目标市场）—— Google Trends 12 月走势，算环比上升速度。\n"
        "3. compare_seasonality —— 5 年历史真实峰谷月，给季节性结论（禁止凭印象说 X 月旺季）。\n"
        "4. social_trends —— TikTok 趋势词 / 抖音热榜 等，看『今天大家在搜什么、什么在火』。\n"
        "5. tiktok_trending_hashtags（若可用）—— 话题 popularityCurve 时间序列 + 浏览量，判断声量拐点。\n"
        "6. tiktok_shop_search —— 把社媒热度落到『可购买商品』，验证趋势是否已转化为真实在售/销量。\n"
        "7. 关键词扩展：get_amazon_keyword_suggestions / get_keyword_metrics + validate_keywords，产出『相关上升词』。\n"
        "### 不做：阶段5利润 / 阶段6供应链 / 阶段7 IP / 阶段8候选品决策矩阵。\n"
        "### 交付：一份『趋势雷达』——哪些词在涨、涨多快、季节性、社媒声量与拐点、可购买性验证、早期机会清单。\n"
    ),
    core_stages=frozenset({"stage1_trends", "stage2_competition"}),
    min_core=1,
    nudge=(
        "⚠️ 趋势探索的核心信号还没拿够就想收尾（已登记：{done}）。"
        "请**继续调用工具**：get_trend(≥3词) 看 12 月走势与上升速度、compare_seasonality 看季节性、"
        "social_trends/tiktok_trending_hashtags 看社媒声量与拐点、tiktok_shop_search 验证可购买性。"
        "拿到这些再写趋势雷达，不要凭印象写趋势。"
    ),
    report_parts=(
        "基于以上全部真实工具返回结果，输出一份**趋势探索报告**（不是完整选品报告，不要写利润/IP/供应链/候选品决策矩阵）。\n"
        "## 报告结构：\n"
        "1. 报告头部（标题 + 数据采集时间 + 目标市场 + 关键词范围）。\n"
        "2. 数据来源汇总：\n__SUMMARY__\n"
        "3. **趋势总览**：当前处于上升/平台/下降期的一句话判断（基于真实曲线）。\n"
        "4. **上升关键词与热度曲线**：用 get_trend 的真实 12 月数据，给每个词的走势方向 + 近 3 月环比上升速度（表格）。\n"
        "5. **季节性**：compare_seasonality 的真实峰谷月（标注几年历史），给出『何时该提前备货』。\n"
        "6. **社媒声量与拐点**：social_trends / 话题 popularityCurve 里与本品类相关的词，"
        "标注浏览量/发布数与近 7 天曲线方向，判断是否临近声量拐点。\n"
        "7. **相关上升词扩展**：validate_keywords 验证过的长尾/关联词（搜得到真实商品的才列）。\n"
        "8. **可购买性验证**：tiktok_shop_search 看热度是否已转化为真实在售商品/销量（避免只热不卖的伪趋势）。\n"
        "9. **早期机会清单**：3-5 个『正在涨且已能买到』的方向，每条注明支撑它的真实数据点。\n"
        "每章顶部注明数据来源工具。趋势方向必须来自真实曲线，禁止编造涨跌幅。\n\n"
        "__RULES__",
    ),
)


# ───────────────────────── 竞品分析：Listing / 定价 / 评论 / 差异化 ─────────────────────────
COMPETITOR = ModeSpec(
    kind="competitor",
    label="竞品分析",
    system_addendum=(
        "\n## 🎯 本次模式：竞品分析 —— 目标是**拆解头部对手的 listing、定价、评论好评/差评，找出差异化切入点**，"
        "**不是**做完整选品决策（不需要 TAM/SAM 市场测算/IP/供应链）。\n"
        "### 必须重度使用的工具（按序）：\n"
        "1. tiktok_shop_search / discover_bsr_url + get_bestsellers_by_url（limit≥30，传 geo=目标市场）——锁定真实 Top 竞品。\n"
        "2. capture_evidence_batch —— 抓 Top 竞品主图/详情页，做 listing 对比（标题/卖点/主图）。\n"
        "3. get_reviews_batch（覆盖 Top 15-20 个竞品，样本≥80）+ extract_pain_points_precise —— 提炼好评亮点与差评痛点。\n"
        "4. tiktok_shop_reviews —— TikTok Shop 竞品的真实买家评论（region 与搜索一致）。\n"
        "5. analyze_market_structure —— 价格带分布 / CR4 / 评分门槛，定位对手的价格卡位。\n"
        "### 不做：阶段5利润测算细化 / 阶段6供应链 / 阶段7 IP。市场规模只做轻量背景，不展开 TAM/SAM。\n"
        "### 交付：竞品对比矩阵 + 定价策略 + 评论好差评洞察 + 明确的差异化切入点。\n"
    ),
    core_stages=frozenset({"stage2_competition", "stage3_pain_points"}),
    min_core=1,
    nudge=(
        "⚠️ 竞品分析的核心数据还没拿够就想收尾（已登记：{done}）。"
        "请**继续调用工具**：get_bestsellers_by_url/tiktok_shop_search 锁定 Top 竞品、"
        "capture_evidence_batch 抓 listing、get_reviews_batch + extract_pain_points_precise 提炼好评/差评。"
        "拿到对手真实 listing 与评论再写差异化结论。"
    ),
    report_parts=(
        "基于以上全部真实工具返回结果，输出一份**竞品分析报告**（不是完整选品报告，不要写利润测算/IP/供应链章节）。\n"
        "## 报告结构：\n"
        "1. 报告头部（标题 + 数据采集时间 + 目标市场 + 竞品范围）。\n"
        "2. 数据来源汇总：\n__SUMMARY__\n"
        "3. **竞品对比矩阵**（表格，Top 5-8 真实竞品）：品名/品牌、价格、评分、评论数、真实月销（或销量信号）、店铺、主卖点。\n"
        "   每个竞品下方按序嵌它的主图（用工具返回的 main_image.markdown_local，没有再退 markdown_remote）。\n"
        "4. **定价策略**：价格带分布 + CR4 集中度 + 促销/折扣手法（基于真实 marketing_labels / 折扣字段）。\n"
        "5. **Listing 拆解**：头部对手的标题结构、核心卖点词、主图风格的共性与差异。\n"
        "6. **评论洞察**：用 <details> 折叠真实评论原文——好评亮点（用户认可什么）+ 差评痛点（频次统计，每点 3-5 条原文）。\n"
        "7. **差异化切入点**：从差评痛点 + listing 同质化里，给出 3-5 个新卖家可切入的差异化方向，每条对应真实证据。\n"
        "每章顶部注明数据来源工具。禁止编造竞品名/价格/评分/月销。\n\n"
        "__RULES__",
    ),
)


# ───────────────────────── 受众洞察：人群 / 场景 / 动机 / 渠道 ─────────────────────────
AUDIENCE = ModeSpec(
    kind="audience",
    label="受众洞察",
    system_addendum=(
        "\n## 🎯 本次模式：受众洞察 —— 目标是**刻画目标人群画像、使用场景、购买动机与顾虑、触达渠道与内容偏好**，"
        "核心证据是『用户自己的声音』（评论 / Reddit / YouTube / 社媒），**不是**做完整选品决策。\n"
        "### 必须重度使用的工具（按序）：\n"
        "1. get_reviews_batch（覆盖 Top 15-20 商品，样本≥80）—— 从真实评论里看『谁在买、为什么买、用在什么场景』。\n"
        "2. reddit_search —— 真实用户讨论里的需求/吐槽/比较，验证动机与顾虑（需求验证层）。\n"
        "3. youtube_search —— 测评/开箱视频的标题与互动，看内容偏好与触达渠道（需求验证层）。\n"
        "4. social_trends —— 该人群当下在关注/搜索什么。\n"
        "5. tiktok_shop_search / get_bestsellers —— 仅用于确认人群真实在买的商品形态（轻量，不展开竞品矩阵）。\n"
        "### 不做：阶段5利润 / 阶段6供应链 / 阶段7 IP / 阶段4候选品决策矩阵。\n"
        "### 交付：人群画像 + 使用场景 + 购买动机与顾虑 + 触达渠道与内容偏好，每条都要挂真实用户原话作为证据。\n"
    ),
    core_stages=frozenset({"stage3_pain_points", "stage2_competition"}),
    min_core=1,
    nudge=(
        "⚠️ 受众洞察的『用户声音』还没拿够就想收尾（已登记：{done}）。"
        "请**继续调用工具**：get_reviews_batch 抓真实评论、reddit_search / youtube_search 做需求验证、"
        "social_trends 看人群当下关注。拿到真实用户原话再总结人群画像，禁止凭空臆测人群。"
    ),
    report_parts=(
        "基于以上全部真实工具返回结果，输出一份**受众洞察报告**（不是完整选品报告，不要写利润/IP/供应链/候选品决策矩阵）。\n"
        "## 报告结构：\n"
        "1. 报告头部（标题 + 数据采集时间 + 目标市场 + 人群/品类）。\n"
        "2. 数据来源汇总：\n__SUMMARY__\n"
        "3. **人群画像**：从真实评论/讨论推断的年龄段、地域、身份标签、价格敏感度（标注是推断还是直接证据）。\n"
        "4. **使用场景**：高频出现的真实使用场景（每个场景挂 1-2 条真实评论/讨论原文，<details> 折叠）。\n"
        "5. **购买动机与顾虑**：为什么买（动机）+ 犹豫/退货原因（顾虑），按真实提及频次排序，挂原话证据。\n"
        "6. **触达渠道与内容偏好**：从 Reddit 子版块 / YouTube 测评 / 社媒话题，看在哪触达、偏好什么内容形式。\n"
        "7. **给商家的沟通建议**：基于以上，主图/详情页/广告该强调哪些点、规避哪些顾虑（每条对应上面的真实证据）。\n"
        "每章顶部注明数据来源工具与来源市场。**人群结论必须来自真实用户声音**，禁止编造画像或原话。"
        "若 Reddit/YouTube 未取到数据，如实写『该来源未取到，结论仅基于评论』。\n\n"
        "__RULES__",
    ),
)


# ───────────────────────── 机会挖掘：缺口 / 差异化 / 蓝海红海 / 评分 ─────────────────────────
OPPORTUNITY = ModeSpec(
    kind="opportunity",
    label="机会挖掘",
    system_addendum=(
        "\n## 🎯 本次模式：机会挖掘 —— 目标是**从需求缺口 + 竞争强度 + 差异化空间里，找出可切入的产品机会并打分排序**。"
        "它是趋势+竞品+痛点的『交叉』，最终产出一张机会评分矩阵。\n"
        "### 必须重度使用的工具（按序）：\n"
        "1. get_trend + social_trends —— 需求是否在涨（机会的前提是有上升需求）。\n"
        "2. get_bestsellers_by_url / tiktok_shop_search + analyze_market_structure —— 竞争强度（CR4/价格带/大牌垄断度），判蓝海/红海。\n"
        "3. get_reviews_batch + extract_pain_points_precise —— 差评里『未被满足的需求缺口』（机会的核心来源）。\n"
        "4. reddit_search —— 真实用户『我希望有一个能…的产品』式诉求，补充缺口证据（需求验证层）。\n"
        "### 轻量做：利润只做毛估区间（可选 full_cost_breakdown），不展开 14 项；不做 IP/供应链细化。\n"
        "### 交付：需求缺口清单 + 差异化空间 + 蓝海/红海判定 + 进入壁垒与风险 + 机会评分矩阵（含优先级）。\n"
    ),
    core_stages=frozenset({"stage1_trends", "stage2_competition", "stage3_pain_points"}),
    min_core=2,
    nudge=(
        "⚠️ 机会挖掘的三类交叉信号（需求/竞争/缺口）还没凑齐就想收尾（已登记：{done}）。"
        "请**继续调用工具**：get_trend/social_trends 看需求是否在涨、analyze_market_structure 看竞争强度、"
        "get_reviews_batch + extract_pain_points_precise 挖差评里的需求缺口。三者齐了再做机会评分矩阵。"
    ),
    report_parts=(
        "基于以上全部真实工具返回结果，输出一份**机会挖掘报告**（不是完整选品报告，利润只做毛估区间，不写 IP/供应链细化）。\n"
        "## 报告结构：\n"
        "1. 报告头部（标题 + 数据采集时间 + 目标市场 + 品类）。\n"
        "2. 数据来源汇总：\n__SUMMARY__\n"
        "3. **需求缺口清单**：从差评痛点 + Reddit 诉求里提炼『未被满足的需求』，按真实提及频次排序，挂原话证据（<details> 折叠）。\n"
        "4. **差异化空间**：针对每个缺口，给出可改进的产品方向（功能/材质/规格/服务）。\n"
        "5. **竞争强度判定**：用 CR4 集中度 + 大牌垄断度 + 价格带拥挤度，明确判定蓝海 / 红海 / 细分蓝海。\n"
        "6. **进入壁垒与风险**：大牌垄断、价格战、技术/专利门槛、季节性风险（基于真实数据，拿不到就标注待确认）。\n"
        "7. **机会评分矩阵**（表格，3-5 个机会方向）：按 ①需求上升度 ②竞争可进入性 ③差异化空间 ④需求缺口强度 "
        "四维各 1-5 分打分并加权排序，给出优先级（高/中/低）与一句话推荐理由。\n"
        "8. **主推机会**：综合最优且新卖家可切入的 1-2 个方向，说明为什么不是单纯需求最大的那个。\n"
        "每章顶部注明数据来源工具。评分必须有真实数据支撑，禁止拍脑袋打分。\n\n"
        "__RULES__",
    ),
)


_REGISTRY = {m.kind: m for m in (GENERAL, MARKET, TREND, COMPETITOR, AUDIENCE, OPPORTUNITY)}


def get_mode_spec(kind: str | None) -> ModeSpec:
    """按 kind 返回模式配置；未知/空 → general（向后兼容）。"""
    return _REGISTRY.get((kind or "general"), GENERAL)
