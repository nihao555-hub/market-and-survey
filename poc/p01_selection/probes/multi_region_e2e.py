"""
5 地区 × 5 品类完整 e2e 批量测试 v2 — 并发 + 大样本量 + 透明化
- 5 个 case 并发跑（最多 3 个同时，避免代理瓶颈）
- 每个 case 抓 BSR 50+ 商品，评论 250+ 条
- 每个工具调用都附 _summary 字段让 LLM 真"看到"了什么
- 每阶段强制 record_stage_status，最后强制 traceability_check
"""
import sys, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports" / "multi_region"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TS = datetime.now().strftime("%Y%m%d_%H%M%S")

# 用线程锁保护打印（多 case 并发时）
_print_lock = threading.Lock()


def safe_print(msg: str):
    """子进程里 print 可能因 stdout 关闭失败，这里 try-except 保护"""
    try:
        print(msg, flush=True)
    except Exception:
        pass


def case_log(case_id: str, msg: str):
    """子进程专用：写到 case 自己的日志文件 + 尝试 print"""
    log_path = REPORTS_DIR / case_id / "live.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%H:%M:%S}] {msg}\n")
    safe_print(f"[{case_id}] {msg}")


# 5 地区 × 5 品类
TEST_CASES = [
    {
        "case_id": "T1_US_yoga",
        "markets": ["US"],
        "category": "瑜伽垫",
        "category_en": "yoga mat",
        "category_zh_1688": "瑜伽垫 健身",
        "user_input": ("我想做瑜伽垫选品调研，目标美国市场，FBA 自有品牌中端定位，"
                        "预算 5 万美元/月，避开大牌 Lululemon/Manduka。\n"
                        "请抓 BSR 子类目 Top 50 + 至少 200 条评论 + 多平台对比。"),
    },
    {
        "case_id": "T2_UK_kitchen",
        "markets": ["UK"],
        "category": "厨房收纳",
        "category_en": "kitchen storage organizer",
        "category_zh_1688": "厨房 收纳 不锈钢",
        "user_input": ("我想做厨房收纳产品选品调研，目标英国市场，Amazon UK FBA，"
                        "预算 3 万美元/月，差异化定位。\n"
                        "请抓 BSR 子类目 Top 50 + 至少 200 条评论。"),
    },
    {
        "case_id": "T3_DE_pet",
        "markets": ["DE"],
        "category": "宠物智能用品",
        "category_en": "smart pet feeder automatic",
        "category_zh_1688": "宠物 自动喂食 智能",
        "user_input": ("我想做宠物智能产品（自动喂食器）选品调研，目标德国市场，Amazon DE FBA，"
                        "预算 5 万美元/月。\n"
                        "请抓 BSR 子类目 Top 50 + 至少 200 条评论。"),
    },
    {
        "case_id": "T4_JP_beauty",
        "markets": ["JP"],
        "category": "美容工具",
        "category_en": "facial massager LED beauty",
        "category_zh_1688": "美容 LED 面部按摩",
        "user_input": ("我想做美容工具（LED 面部按摩仪）选品调研，目标日本市场，"
                        "Amazon JP + Rakuten 双平台，预算 4 万美元/月。\n"
                        "请抓 BSR Top 50 + 至少 200 条评论。"),
    },
    {
        "case_id": "T5_SEA_outdoor",
        "markets": ["SG"],
        "category": "户外露营",
        "category_en": "camping gear",
        "category_zh_1688": "户外 露营 便携",
        "user_input": ("我想做户外露营产品选品调研，目标新加坡市场，"
                        "Shopee SG 主战场 + Amazon US 对标，预算 2 万美元/月。\n"
                        "请抓 BSR 子类目 Top 50 + 至少 200 条评论。"),
    },
    {
        "case_id": "T6_RU_smarthome",
        "markets": ["RU"],
        "category": "智能家居小工具",
        "category_en": "smart home gadgets",
        "category_zh_1688": "智能家居 WIFI",
        "user_input": ("我想做智能家居小工具选品调研，目标俄罗斯市场，"
                        "主要平台 Ozon + Wildberries + Yandex Market，预算 3 万美元/月。\n"
                        "请抓 ≥ 25 件商品 + ≥ 100 条评论。"),
    },
    {
        "case_id": "T7_LATAM_pet",
        "markets": ["MX", "BR"],
        "category": "宠物用品",
        "category_en": "pet supplies",
        "category_zh_1688": "宠物用品 喂食器",
        "user_input": ("我想做宠物用品选品调研，目标墨西哥+巴西市场，"
                        "主要平台 MercadoLibre MX + MercadoLibre BR，预算 3 万美元/月。\n"
                        "请抓 ≥ 25 件商品 + ≥ 100 条评论。"),
    },
]


SYSTEM_TEMPLATE = """你是资深跨境选品专家。严格按 procurement-research 8 阶段方法论。

## 数据真实性 — 零容忍

1. **第一步必调 get_current_datetime() 拿真实日期**（写到报告"数据采集时间"）
2. **候选品 ASIN 必须从 ASIN 池选** + validate_candidate 校验
3. **多平台真抓** — 用户指定地区 → pick_platforms_for_market → search_multi_platform
   - **当前 verified 平台（18 个）**: amazon, amazon_uk, amazon_de, amazon_fr, amazon_jp,
     amazon_au, amazon_in, bestbuy, newegg, target, mercadolibre_mx/br, otto,
     rakuten, yandex_market, lazada_sg, flipkart, aliexpress
   - **地理受限站已用多国出口代理突破**（uk→英国节点/de→德国/fr→德国邻近/in→印度，自动路由）
   - **partial（不稳定，可试但结果可能空）**: shopee_sg, cdiscount, **wildberries**（并发场景下 100% 失败，单跑偶尔成功）
   - **blocked**（商业反爬/嵌入式JSON）: walmart, ebay, etsy, wayfair, amazon_ae,
     shopee_my, tokopedia, 1688, tiktok_shop, coupang, trendyol, ozon, noon,
     temu, shein, alibaba
   - **🚀 优化（2026-06）**：search_multi_platform 默认自动跳过 blocked 平台（节省 60s/个超时），
     skipped_blocked 列表照实写到报告，不需要你手动过滤
   - **🛡️ 熔断机制**：单平台连续失败 ≥ 2 次后，本 case 内自动 cooldown_skipped，
     看到 `skipped_cooldown=true` 或 `cooldown_warning` 字段时**立即换平台**，不要再试同一个
   - 用户的目标地区如果只有 untested 平台，必须真试一次 + record_stage_status 登记结果
   - **俄罗斯特别提示**：只用 yandex_market（verified 稳定），wildberries 已降级 partial 并发不稳定，ozon blocked
4. **采购成本不能编** — get_real_procurement_cost / search_1688 失败 → record_stage_status('stage5_profit', 'skipped', needs_user_action='提供 1688 商品 URL 或工厂报价')
   - **绝对禁止在报告里出现"行业毛利率参考 / 假设采购成本 / 经验估算 25-35%"等任何虚构数字**
   - 阶段 5 失败时，整章只能写"待用户提供"，不能给毛利率/利润测算/盈亏点的任何数字
   - 这是给商家看的报告，假数据会导致破产风险

## 样本量要求 — 避免偶然性

5. **BSR 抓 ≥ 100 件**（用 get_bestsellers_by_url(limit=200, paginate=True) 翻页拿 200 条）
6. **评论 ≥ 350 条**（用 get_reviews_batch 传 25-30 个 ASIN, max_total=500）
   - 必须含 Top 10（爆款）+ 中部 10（中位价）+ 长尾 5-10（低评分商品）
   - 避免 survivorship bias，别只看爆款
7. **多平台覆盖 ≥ 2 个 verified 平台**

## 真实月销 — 优先用第一方数据

- **优先级 1**：若 api_status 显示 rapidapi_amazon 可用 → get_amazon_product_details_api 拿真实 BSR/月销/评分
- **优先级 2**：search_products / get_bestsellers_by_url 返回的 `bought_past_month` 字段
  （Amazon 官方『X+ bought in past month』真实月销，第一方数据）
- **优先级 3**：都没有 → BSR 经验区间，明确标注"估算值，误差±50%"
- 盈亏点 monthly_sales_estimate 参数优先填真实 bought_past_month 值

## 真实绝对搜索量 — 趋势洞察优先用

- 阶段 0 先调 api_status 看 dataforseo 是否可用
- 可用 → get_real_search_volume 拿真实 Google Ads 月搜索量（绝对值），写报告时用绝对值
- 不可用 → get_keyword_metrics（DDGS 相对值）+ get_trend（Google Trends 相对热度）

## 必用的精确工具（替代旧的估算工具）

8. **痛点统计**：用 **extract_pain_points_precise**（Python 精确匹配，0 误差），不用 analyze_reviews
9. **季节性判断**：用 **compare_seasonality**（5 年历史数据），不要 LLM 自己推断
10. **长尾词扩展**：用 **get_keyword_metrics**（DDGS 真实搜索数据），不要 LLM 自己想
11. **压力测试**：用 **monte_carlo_stress_test**（5000 次 6 变量模拟），不用 stress_test
12. **IP 风险**：用 **deep_ip_risk_assessment**（PatentsView 官方 API + 引用链），不用 quick_ip_check
13. **评论质量趋势**：用 **analyze_review_temporal** 看产品质量是否在下降
14. **利润测算**：用 full_cost_breakdown(stage='new_product') 和 stage='stable' **两个都跑**，让商家看到双场景差异

## 透明化 — 不能黑盒

15. 每次工具返回都会有 `_summary` 字段，**必须把里面的关键发现写到本步思考中**：
   - 例：「BSR Top 1: Amazon Basics Yoga Mat $13.99，前 10 个商品标题包含 ...」
   - 例：「评论 256 条已抓，前 5 条原文：...」
   - **目标：让用户看到"Agent 真的读了"，而不是黑盒**

## 强制透明：每个阶段完成后必须立即 record_stage_status

stage_id 用：stage1_trends / stage2_competition / stage3_pain_points / 
            stage4_candidates / stage5_profit / stage6_supply / 
            stage7_ip_risk / stage8_decision

填 reason + needs_user_action（partial/skipped/failed 必填）+ artifacts（产出物清单）

## 收尾必做

完成全部阶段后，按顺序调用：
1. stage_status_summary() — 拿执行汇总
2. traceability_check(claims=[每个候选品的 {asin, claim_price, claim_rating, claim_title_contains}]) — 校验报告里每个 ASIN 声明真实

## ⚠️ 工具调用格式铁律

**必须用标准 function_calling 调工具，禁止在 content 里写 `<｜｜DSML｜｜tool_calls>` 标签**。
DSML 输出会被检测到并强制重试。每次工具调用必须通过 `tool_calls` 字段，不要把"我现在调用 xxx"写成文本。

## 🚫 不准反问用户 — 直接抓数据

**严格禁令**：
- ❌ 不准在 Step 1 反问用户"物流方式怎么走/商家定位选哪种/关键词细分到哪个子类目"等问题
- ❌ 不准等"用户回复后再开抓"，用户输入已经包含目标市场+品类+预算，足够开始
- ✅ 第一步直接调 get_current_datetime + load_skill + pick_platforms_for_market，立刻进阶段 0
- ✅ 子品类不确定时，并发抓 3-4 个相关词的 BSR/搜索结果，从结果倒推哪个最热
- 报告里需要"用户提供"的部分（如 1688 链接、品牌名、目标售价）放在阶段 5/7 的"待用户提供清单"里写明，**不要在 Step 1 就停下问**

## 阶段流程（升级版 — 用更精确的工具）
- 阶段 0: get_current_datetime + load_skill + pick_platforms_for_market
- 阶段 1: 
  • get_trend × 3 关键词 + **compare_seasonality**（5 年历史季节性）+ **get_keyword_metrics**（DDGS 真长尾词）
  • discover_bsr_url + get_bestsellers_by_url(limit=200, paginate=True)
- 阶段 2: search_multi_platform（≥3 平台并发）+ analyze_market_structure（含 sponsored_ratio）
  • **市场规模用 estimate_market_size**（聚合 Top N 真实月销+评论+价格，比搜索量更接近真实需求）
  • **候选品价格/BSR 历史用 get_keepa_charts_batch** 拿 PNG 曲线图
    ✅ 现在每张图自带 trend_text（像素分析还原的趋势：涨跌+波动），**你可以读 trend_text 做分析**
    PNG 本身嵌报告给商家看；趋势结论用 trend_text；绝对当前数字用 get_amazon_product_details_api
- 阶段 3: 
  • get_reviews_batch(25-30 ASIN, max_total=500)  ← 关键：≥30 个 ASIN，含 Top 10 + 中部 10 + 长尾 5-10
  • **extract_pain_points_precise**（替代 analyze_reviews，Python 精确统计 0 误差）
  • **analyze_review_temporal**（评论时间分布看产品质量是否在下降）
- 阶段 4: get_asin_pool + validate_candidate × 5
  • **候选品真实数据用 get_amazon_product_details_api**（RapidAPI 已可用）：拿真实 BSR/月销/评分/卖家数/重量
  • **候选品演进用 get_wayback_snapshots / analyze_listing_evolution**（archive.org 免费）：
    看 first_seen 上架时间、标题改过几次、历史价格区间。判断老品 vs 新品、识别试错方向。建议只对 1-2 核心竞品调 analyze_listing_evolution（较慢）
- 阶段 5: 
  • get_real_procurement_cost（自动 1688→Made-in-China→DHgate→GlobalSources 四级 fallback）
  • **采购价精准化用 get_supplier_detail_price**（对 get_real_procurement_cost 返回的 items[].source_url 抓详情页 MOQ 阶梯价，按下单量取精准单价，比区间准）
  • 真实数据 → full_cost_breakdown(stage='new_product') + full_cost_breakdown(stage='stable')
  • **monte_carlo_stress_test(n=5000, is_new_product=True)** ← 替代 stress_test，6 变量 5000 模拟
- 阶段 7: **deep_ip_risk_assessment**（PatentsView API + 引用链）替代 quick_ip_check
- 阶段 8: capture_evidence_batch（**🚀 一次并发抓 3-5 候选品**，替代多次 capture_evidence；3x 提速）+ **generate_price_chart** 真图表
- 收尾: stage_status_summary + traceability_check
  → backend 自动产出三件套：1 页摘要 + 5 页详情 + 完整 PDF

请用中文交流，每一步都简短说明你看到了什么数据。
"""


def run_one_case(tc: dict) -> dict:
    """跑一个测试用例（在子进程中独立运行）"""
    # 子进程内独立 import + 独立 POOL
    # 注意：multiprocessing 子进程的 stdout 已经是 utf-8（用 spawn），不要重新包装
    import sys, json, time
    
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    
    # 启动浏览器看门狗（防僵尸进程拖垮机器）
    from modules.browser_cleanup import start_watchdog, kill_orphan_browsers
    start_watchdog(interval_sec=120, max_age_sec=240)
    
    # 自检代理（每个 case 开始前确认）
    from proxy.ensure_proxy import ensure_proxy_alive
    ensure_proxy_alive(verbose=False)
    
    from modules.agent_tools import TOOLS_SCHEMA, TOOL_IMPL
    from modules.llm import get_client, MODEL_FLASH, MODEL_PRO
    from modules.asin_pool import POOL
    
    # 子进程的 POOL 是独立的（多进程隔离）
    if hasattr(POOL, "_items"):
        POOL._items.clear()
    
    case_dir = REPORTS_DIR / tc["case_id"]
    case_dir.mkdir(exist_ok=True)
    transcript_path = case_dir / "transcript.md"
    final_path = case_dir / "final.md"
    metrics_path = case_dir / "metrics.json"
    
    transcript: list[str] = []
    metrics = {
        "case_id": tc["case_id"], "started_at": datetime.now().isoformat(),
        "markets": tc["markets"], "category": tc["category"],
        "tool_calls": [], "errors": [],
        "asin_pool_size": [], "stage_records": [],
    }
    
    def t(line: str = ""):
        transcript.append(line)
        transcript_path.write_text("\n".join(transcript), encoding="utf-8")
    
    client = get_client()
    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE},
        {"role": "user", "content": tc["user_input"]},
    ]
    
    t(f"# {tc['case_id']} — {tc['category']} ({','.join(tc['markets'])})")
    t(f"\n时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    t(f"用户输入：\n```\n{tc['user_input']}\n```\n")
    
    MAX_STEPS = 24
    for step in range(1, MAX_STEPS + 1):
        t(f"\n## ━━━━━ Step {step} ━━━━━")
        safe_print(f"[{tc['case_id']}/Step {step}/{MAX_STEPS}]")
        
        try:
            resp = client.chat.completions.create(
                model=MODEL_FLASH, messages=messages,
                tools=TOOLS_SCHEMA, tool_choice="auto", max_tokens=2500,
            )
        except Exception as e:
            err = f"LLM error: {e}"
            t(f"\n❌ {err}")
            metrics["errors"].append({"step": step, "error": str(e)[:200]})
            break
        
        msg = resp.choices[0].message
        # 检测 DSML 模式（LLM 错误地把工具调用写到 content 里而不是 tool_calls）
        # 出现这种情况时，必须告诉 LLM 用正确的 function_calling 格式
        content_has_dsml = msg.content and "DSML" in (msg.content or "")
        
        if msg.content:
            t(f"\n💭 [Agent]\n\n{msg.content}\n")
            safe_print(f"  [{tc['case_id']}] 💭 {msg.content[:140]}")
        
        # DSML 误输出修复：如果 LLM 把工具调用写到 content 里，强制让它重新用 function_calling
        if content_has_dsml and not msg.tool_calls:
            t(f"\n⚠️ DSML 误输出检测：LLM 把工具调用写到 content 里。强制重新尝试。\n")
            messages.append({
                "role": "assistant", "content": "[DSML 误输出已删除]",
            })
            messages.append({
                "role": "user",
                "content": "❌ 你刚才把工具调用写在了 content 里（DSML 标签格式）。"
                            "**请使用标准的 function calling 格式调用工具，不要在文本里写 DSML 标签**。"
                            "请重新执行你想做的工具调用。",
            })
            metrics["errors"].append({"step": step, "error": "DSML output detected, retried"})
            continue
        
        if not msg.tool_calls:
            # 防御：早期步骤（< 3）就停止 → 多半是 Agent 跑去反问用户了，强制重试
            if step <= 2:
                t(f"\n⚠️ Step {step} 没有 tool_calls，疑似 Agent 反问用户。强制要求开抓。\n")
                metrics["errors"].append({"step": step, "error": "early_stop_no_tools_retry"})
                messages.append({"role": "assistant", "content": msg.content or "[skipped]"})
                messages.append({
                    "role": "user",
                    "content": "❌ 不要在 Step 1-2 反问用户。立即调用 get_current_datetime + "
                                "load_skill + pick_platforms_for_market 开始抓数据。"
                                "用户输入已经足够开始（含市场/品类/预算）。"
                                "需要用户补充的部分留到阶段 5/7 的'待用户提供清单'里写。",
                })
                continue
            t("\n✅ 工具循环结束")
            messages.append({"role": "assistant", "content": msg.content})
            break
        
        messages.append({
            "role": "assistant", "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        
        for tcal in msg.tool_calls:
            name = tcal.function.name
            try:
                args = json.loads(tcal.function.arguments or "{}")
            except Exception:
                args = {}
            preview_args = json.dumps(args, ensure_ascii=False)[:300]
            t(f"\n🔧 **{name}**\n```json\n{preview_args}\n```")
            t0 = time.time()
            try:
                fn = TOOL_IMPL.get(name)
                result = fn(**args) if fn else {"error": f"unknown tool {name}"}
            except Exception as e:
                result = {"error": str(e)[:300]}
                metrics["errors"].append({"step": step, "tool": name, "error": str(e)[:200]})
            ms = int((time.time() - t0) * 1000)
            preview_out = json.dumps(result, ensure_ascii=False)[:1200]
            t(f"\n↳ {ms}ms\n```json\n{preview_out}\n```")
            safe_print(f"  [{tc['case_id']}/{name}] {ms}ms")
            
            metrics["tool_calls"].append({
                "step": step, "tool": name, "ms": ms,
                "has_error": isinstance(result, dict) and "error" in result,
            })
            if isinstance(result, dict) and "pool_size_after" in result:
                metrics["asin_pool_size"].append({"step": step, "size": result["pool_size_after"]})
            if name == "record_stage_status" and isinstance(result, dict):
                metrics["stage_records"].append(result.get("recorded", {}))
            
            messages.append({
                "role": "tool", "tool_call_id": tcal.id,
                "content": json.dumps(result, ensure_ascii=False)[:10000],
            })
    
    # 强制收尾
    summary = TOOL_IMPL["stage_status_summary"]()
    t(f"\n📊 阶段执行汇总：\n{summary['markdown']}\n")
    metrics["final_stage_summary"] = summary
    
    # PRO 综合报告 — 分两段生成（避免单次 8000 token 截断阶段 7/8）
    t(f"\n## ━━━━━ FINAL / model={MODEL_PRO}（分段生成）━━━━━")
    
    common_rules = (
        f"## 严格禁令（违反 = 报告废稿）：\n"
        f"- ❌ 禁止出现'行业毛利率参考 / 假设采购成本 / 经验估算 25-35%'等任何虚构数字\n"
        f"- ❌ 阶段 5 失败时整章只能写'待用户提供'，不能给毛利率/利润测算/盈亏点的任何数字\n"
        f"- ❌ 禁止虚构 ASIN/品牌名/价格/评分 — 全部必须来自真实工具返回\n"
        f"- ❌ 禁止用'根据行业经验''通常情况下''参考值'等模糊表述包装假数字\n"
        f"- ❌ 禁止写 DSML 标签，所有工具调用已完成，现在只组织真实数据成报告\n"
        f"- ✅ 数据缺失时必须明确写'待用户提供 XXX'，并列出用户应提供的具体清单\n"
    )
    
    # ── 第 1 段：阶段 1-4（趋势/竞争/痛点/候选品）──
    part1_prompt = (
        f"基于以上全部真实工具返回结果，输出 {tc['category']}选品决策报告的【前半部分】（给电商商家看）。\n\n"
        f"## 本次只写这些章节（不要写阶段5及以后）：\n"
        f"1. **报告头部**：标题 + 数据采集时间（get_current_datetime 真实日期）+ 目标市场/定位/预算\n"
        f"2. **执行汇总表**（8 阶段状态总览，贴到头部）：\n{summary['markdown']}\n"
        f"3. **阶段 1 · 趋势洞察**：季节性峰谷月 + 关键词热度 + 长尾词 + BSR Top10 真实月销表。\n"
        f"   若有 generate_price_chart / Keepa 趋势图，**把图嵌在本章对应文字旁**（不要堆到末尾）。\n"
        f"4. **阶段 2 · 竞争格局**：市场规模(真实月销聚合) + 价格带分布 + CR4 集中度 + 评分门槛。\n"
        f"   若有价格分布柱状图，嵌在价格带分析旁。\n"
        f"5. **阶段 3 · 痛点挖掘**：痛点频次统计 + **<details> 折叠真实评论原文**（每痛点 3-5 条）\n"
        f"6. **阶段 4 · 候选品筛选**：5 候选品真实数据表（BSR/月销/评分/重量）。\n"
        f"   **每个候选品正下方按顺序嵌入它自己的图**（不要堆到报告末尾做画廊）：\n"
        f"   - 产品主图：直接用 capture_evidence 返回的 `main_image.markdown_remote` 字段（现成 markdown）\n"
        f"   - 详情页截图：直接用 capture_evidence 返回的 `detail_page.markdown` 字段（现成 markdown）\n"
        f"   - Keepa 价格历史图（若有）：用 get_keepa_charts_batch 返回的本地 png 路径\n"
        f"   这些字段已经是 `![...](...)` 现成格式，直接粘贴即可，不要自己改路径。"
        f"   图必须紧跟在对应候选品下方，每张配一句说明。\n"
        f"每章顶部注明数据来源工具。\n"
        f"**结尾不要写总结，因为后半部分（阶段5-8）会接着写。**\n\n"
        f"{common_rules}"
    )
    
    def _gen_part(prompt: str, label: str) -> str:
        msgs = messages + [{"role": "user", "content": prompt}]
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=MODEL_PRO, messages=msgs, max_tokens=8000, temperature=0.3,
                )
                ft = resp.choices[0].message.content or ""
                if "DSML" in ft or len(ft) < 800:
                    t(f"\n⚠️ {label} 输出异常（DSML/过短），重试 {attempt+1}/3\n")
                    msgs = msgs + [
                        {"role": "assistant", "content": ft[:300]},
                        {"role": "user", "content": "❌ 输出有问题（DSML/太短）。请直接用纯 markdown 重写本部分。"},
                    ]
                    continue
                return ft
            except Exception as e:
                t(f"\n❌ {label} 失败: {e}")
                metrics["errors"].append({"step": f"final_{label}", "error": str(e)[:200]})
                break
        return ""
    
    part1 = _gen_part(part1_prompt, "part1_阶段1-4")
    t(f"\n💭 [PRO 前半部分 阶段1-4]\n\n{part1}\n")
    
    # ── 第 2 段：阶段 5-8（利润/供应链/IP/决策）──
    part2_prompt = (
        f"接着上面的报告，继续输出 {tc['category']}选品决策报告的【后半部分】（阶段 5-8）。\n\n"
        f"## 本次只写这些章节：\n"
        f"1. **阶段 5 · 利润可行性**：14 项成本拆解（new_product + stable 双场景）+ 盈亏点 + 蒙特卡洛亏损概率。"
        f"   采购成本来自 get_real_procurement_cost / get_supplier_detail_price 真实值；"
        f"   拿不到就整章写'待用户提供 1688 链接'，不能编数字。\n"
        f"2. **阶段 6 · 供应链方案**：MOQ 阶梯价 + 供应商比价 + 头程时间线（有真实数据才写，否则待用户提供）\n"
        f"3. **阶段 7 · IP 风险**：deep_ip_risk_assessment 真实结果（专利/商标）；未跑则写'待品牌名确认后执行'\n"
        f"4. **阶段 8 · 决策表**：候选品决策矩阵（售价/净利/毛利率/盈亏点/蒙特卡洛亏率/决策）+ 主推建议 + 风险清单 + 90天行动计划\n"
        f"5. **证据索引**（只放链接，不要再嵌图！所有截图已嵌在阶段1/3/4 对应位置）：\n"
        f"   纯文字列出 dp 链接 / BSR URL / 1688 链接，方便核查。**禁止在这里用 `![]()` 嵌图做画廊。**\n"
        f"6. **待用户提供清单**（完整汇总）\n"
        f"每章顶部注明数据来源工具。**这是报告的收尾部分，要完整写到阶段 8 决策表。**\n\n"
        f"{common_rules}"
    )
    part2 = _gen_part(part2_prompt, "part2_阶段5-8")
    t(f"\n💭 [PRO 后半部分 阶段5-8]\n\n{part2}\n")
    
    # 拼接两段
    final_text = ""
    if part1:
        final_text = part1.rstrip()
    if part2:
        final_text = (final_text + "\n\n" + part2.lstrip()) if final_text else part2
    
    if not final_text:
        t(f"\n❌ 两段都生成失败，报告为空")
    
    # 图片处理：① 删 PRO 可能自加的图廊章节 ② 本地图自包含到 case/assets/
    if final_text:
        try:
            from modules.report_export import strip_gallery_section, localize_report_images
            final_text = strip_gallery_section(final_text)
            final_text = localize_report_images(final_text, case_dir)
            t(f"\n🖼️ 图片已自包含到 {case_dir}/assets/，并清理冗余图廊章节")
        except Exception as e:
            t(f"\n⚠️ 图片自包含处理失败: {str(e)[:120]}")
    
    final_path.write_text(
        f"# {tc['case_id']} — {tc['category']} 选品决策报告\n\n"
        f"- 市场：{','.join(tc['markets'])}\n"
        f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
        f"---\n\n{final_text}\n",
        encoding="utf-8"
    )
    
    # 5 件套产物（对齐 backend/selection_job.py，让 e2e 也产商家版/1页/5页/PDF）
    artifacts = {}
    if final_text and len(final_text) > 1500:
        try:
            from modules.report_export import (build_merchant_report, one_pager,
                                                detail_5pages, export_pdf)
            base = case_dir / tc["case_id"]
            
            # 商家版（_primary，推荐展示）
            merchant_md = build_merchant_report(final_text)
            merchant_path = case_dir / "merchant.md"
            merchant_path.write_text(merchant_md, encoding="utf-8")
            artifacts["merchant_md"] = str(merchant_path)
            
            # 1 页摘要
            onepager_md = one_pager(final_text)
            onepager_path = case_dir / "1page.md"
            onepager_path.write_text(onepager_md, encoding="utf-8")
            artifacts["one_pager_md"] = str(onepager_path)
            
            # 5 页详情
            detail_md = detail_5pages(final_text)
            detail_path = case_dir / "5page.md"
            detail_path.write_text(detail_md, encoding="utf-8")
            artifacts["detail_md"] = str(detail_path)
            
            # PDF（完整版）
            pdf_path = case_dir / "report.pdf"
            pdf_result = export_pdf(final_text, str(pdf_path),
                                       title=f"{tc['category']} 选品决策报告")
            if pdf_result.get("ok"):
                artifacts["pdf"] = str(pdf_path)
            else:
                artifacts["pdf_error"] = pdf_result.get("error", "")[:120]
            
            artifacts["full_md"] = str(final_path)
            artifacts["_primary"] = "merchant_md"
            safe_print(f"  📦 [{tc['case_id']}] 5 件套产出：商家版/1页/5页/完整版/PDF")
        except Exception as e:
            import traceback
            artifacts["build_error"] = str(e)[:200]
            safe_print(f"  ⚠️ [{tc['case_id']}] 5 件套生成失败: {str(e)[:120]}")
    
    metrics["artifacts"] = artifacts
    
    metrics["final_report_chars"] = len(final_text)
    metrics["pool_final_size"] = (metrics["asin_pool_size"][-1]["size"]
                                    if metrics["asin_pool_size"] else 0)
    metrics["total_tool_calls"] = len(metrics["tool_calls"])
    metrics["error_count"] = len(metrics["errors"])
    metrics["finished_at"] = datetime.now().isoformat()
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    
    # 任务结束 — 清理本 case 残留的爬虫浏览器（防僵尸累计）
    try:
        from modules.browser_cleanup import kill_orphan_browsers
        kill_orphan_browsers(max_age_sec=0)  # case 结束，本进程所有爬虫 chrome 都该清
    except Exception:
        pass
    
    safe_print(f"\n✅ {tc['case_id']} 完成：报告 {len(final_text)}字 / "
                f"ASIN池 {metrics['pool_final_size']} / "
                f"调用 {metrics['total_tool_calls']} / 错 {metrics['error_count']}")
    return metrics


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=2,
                         help="并发度（每个子进程独占浏览器/代理一个会话）。"
                              "**硬上限 2**：实测 4 路并发时代理 sub-port 被打挂（WinError 10061）+ "
                              "30+ 浏览器实例 OOM 风险。需要更多并发请分批跑。")
    parser.add_argument("--cases", type=str, default="",
                         help="只跑特定 case，逗号分隔，如 T1_US_yoga,T3_DE_pet")
    args = parser.parse_args()
    
    # 强制并发上限
    MAX_SAFE_CONCURRENCY = 2
    if args.concurrency > MAX_SAFE_CONCURRENCY:
        safe_print(f"\n⚠️ 并发度 {args.concurrency} 超过安全上限 {MAX_SAFE_CONCURRENCY}，"
                    f"自动降到 {MAX_SAFE_CONCURRENCY}")
        safe_print(f"   理由：实测 4 路并发触发代理 sub-port 拒连（WinError 10061），"
                    f"且单 case 内部已 reviews_batch 并发 8 + capture_evidence 并发 3。")
        safe_print(f"   要跑更多 case 请分批：先跑 2 个，等结束再跑下一批。\n")
        args.concurrency = MAX_SAFE_CONCURRENCY
    
    cases = TEST_CASES
    if args.cases:
        ids = [s.strip() for s in args.cases.split(",")]
        cases = [c for c in TEST_CASES if c["case_id"] in ids]
    
    safe_print(f"\n{'='*60}")
    safe_print(f"批测开始：{len(cases)} 个 case，并发度 {args.concurrency}")
    safe_print(f"{'='*60}\n")
    
    all_metrics = []
    
    if args.concurrency <= 1:
        # 串行
        for tc in cases:
            safe_print(f"\n{'─'*60}")
            safe_print(f"开始 {tc['case_id']}: {tc['category']} @ {','.join(tc['markets'])}")
            safe_print(f"{'─'*60}")
            try:
                m = run_one_case(tc)
                all_metrics.append(m)
            except Exception as e:
                import traceback
                safe_print(f"\n❌ {tc['case_id']} 崩溃: {e}\n{traceback.format_exc()[:800]}")
                all_metrics.append({"case_id": tc["case_id"], "fatal_error": str(e)})
    else:
        # 多进程并发（独立 ASIN 池）
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=args.concurrency) as ex:
            futures = {ex.submit(run_one_case, tc): tc for tc in cases}
            for fut in as_completed(futures):
                tc = futures[fut]
                try:
                    m = fut.result()
                    all_metrics.append(m)
                    safe_print(f"\n✅ {tc['case_id']} 完成")
                except Exception as e:
                    import traceback
                    safe_print(f"\n❌ {tc['case_id']} 崩溃: {e}\n{traceback.format_exc()[:800]}")
                    all_metrics.append({"case_id": tc["case_id"], "fatal_error": str(e)})
    
    # 总报告
    summary_path = REPORTS_DIR / f"summary_{TS}.md"
    lines = [f"# 批测总览（{len(cases)} 个 case，并发 {args.concurrency}）\n",
             f"测试时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n"]
    lines.append("\n| 用例 | 品类 | 地区 | ASIN池 | 工具调用 | 报告字数 | 错误 |")
    lines.append("|---|---|---|---|---|---|---|")
    for m in all_metrics:
        if "fatal_error" in m:
            lines.append(f"| {m['case_id']} | — | — | — | — | — | ❌ {m['fatal_error'][:60]} |")
        else:
            lines.append(f"| {m['case_id']} | {m.get('category', '')} | "
                          f"{','.join(m.get('markets', []))} | {m.get('pool_final_size', 0)} | "
                          f"{m.get('total_tool_calls', 0)} | {m.get('final_report_chars', 0)} | "
                          f"{m.get('error_count', 0)} |")
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    safe_print(f"\n📊 总报告: {summary_path}")


if __name__ == "__main__":
    main()
