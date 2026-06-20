"""
端到端真实跑一次选品流程 v3
- 工具循环用 flash（编排 + 数据采集）
- 最终报告用 PRO + 8000 tokens（防 token 截断 → 完整 8 阶段报告）
- 强制每个阶段调 record_stage_status 登记状态
- 强制最终调 stage_status_summary 把执行汇总贴进报告
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
import time
from modules.agent_tools import TOOLS_SCHEMA, TOOL_IMPL
from modules.llm import get_client, MODEL_FLASH, MODEL_PRO

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
TRANSCRIPT_PATH = REPORTS_DIR / f"e2e_transcript_{TS}.md"
FINAL_PATH = REPORTS_DIR / f"e2e_final_{TS}.md"

transcript: list[str] = []


def t(line: str = ""):
    transcript.append(line)
    TRANSCRIPT_PATH.write_text("\n".join(transcript), encoding="utf-8")


SYSTEM = """你是资深跨境选品专家，严格按 procurement-research 8 阶段方法论。

## 数据真实性 — **零容忍**

**违反任何一条 = Agent 故障：**

1. **候选品 ASIN 必须从 ASIN 池选**
   - 提候选品前必须先 get_asin_pool() 看有什么真品
   - 必须 validate_candidate(asin) 校验通过
   - **禁止**虚构产品名/品牌名（如 "AuralPace"/"FitBuds Pro"）

2. **多平台 - 用户指定地区/国家时必须真抓所有相关平台**
   - 第一步必须 pick_platforms_for_market(markets=用户的市场) 推荐平台清单
   - 然后 search_multi_platform(platforms=清单, keyword) 真抓
   - 用户说 "美国 + 英国" → 至少抓 amazon + walmart + bestbuy + amazon_uk
   - **不允许只查一个平台就给结论**

3. **采购成本不能编**
   - 必须先 get_real_procurement_cost(中文关键词) 真抓 1688
   - 失败时 search_1688(具体型号) 反查
   - **如果都失败：不调用 full_cost_breakdown**！必须 record_stage_status('stage5_profit', 'skipped', reason='1688 获取失败', needs_user_action='请提供 1688 URL 或工厂报价') 显式登记

4. **评论分析不能编痛点**
   - 必须 get_reviews_batch + analyze_reviews 真跑
   - analyze_reviews 返回 error → 重试 1-2 次仍失败 → record_stage_status('stage3_pain_points', 'failed', ...)
   - **禁止凭印象写"耳罩脱皮""电池虚标"等行业通用痛点**

5. **每个数据点必须附 source_url**
   - 报告里每个数字后面引用工具返回的 url 字段
   - 不能引用就标 ⚠️ source_unknown

6. **月销量用区间**
   - 从 estimated_monthly_sales 字段取 low-high 区间
   - 不允许给单点数字

## 强制透明 — 每个阶段都要登记状态

**每完成一个阶段，必须立即调 record_stage_status 登记**：
- stage_id: stage1_trends / stage2_competition / stage3_pain_points / stage4_candidates / stage5_profit / stage6_supply / stage7_ip_risk / stage8_decision
- status: completed / partial / skipped / failed
- reason: 简要说明（partial/skipped/failed 必填）
- needs_user_action: 用户怎么帮忙补全
- artifacts: 产出物列表（如 ["BSR Top 30 获取", "71 条真评论", "3 张证据截图"]）

## 当前可调用的全球电商平台
共 29 个，按地区分组（US/UK/EU/JP/KR/SEA/LATAM/TR/Global/CN_B2B）。
verified（实测可抓 6 个）：amazon, walmart, bestbuy, shopee_sg, temu, aliexpress
其余 untested 23 个（已配 URL 选择器，跑过会返回真实数据或 error，不会编造）。

## 阶段流程（必走，不可跳）
- 阶段 1 趋势：get_trend + discover_bsr_url + get_bestsellers_by_url → record_stage_status('stage1_trends', ...)
- 阶段 2 竞争：search_multi_platform + analyze_market_structure → record_stage_status('stage2_competition', ...)
- 阶段 3 痛点：get_reviews_batch (5+ ASINs) + analyze_reviews → record_stage_status('stage3_pain_points', ...)
- 阶段 4 候选品：get_asin_pool + validate_candidate × N → record_stage_status('stage4_candidates', ...)
- 阶段 5 利润：get_real_procurement_cost / search_1688 → 成功就 full_cost_breakdown，失败就 skipped 并明示需要用户提供 → record_stage_status('stage5_profit', ...)
- 阶段 6 供应链：get_real_procurement_cost 拿到的供应商列表（如有）→ record_stage_status('stage6_supply', ...)
- 阶段 7 IP 风险：quick_ip_check → record_stage_status('stage7_ip_risk', ...)
- 阶段 8 决策：综合前面所有数据写决策建议 → record_stage_status('stage8_decision', ...)

## 收尾必做
完成所有阶段后，**必须** 调 stage_status_summary() 拿到执行汇总表。
然后停止工具调用，等待最终决策报告生成。

请用中文交流。
"""

USER = """我想做蓝牙耳机选品调研。

需求确认：
1. 目标市场：美国 + 加拿大 + 英国（多市场）
2. 目标平台：Amazon US（主），Walmart 和 BestBuy 作为对比，Amazon UK 看欧洲
3. 月度采购预算：$50,000，单 SKU MOQ 500-1000 接受
4. 物流：FBA
5. 商家定位：自有品牌中端精品（差异化）
6. 排除项：避开 Apple/Sony/Bose 大牌专利雷区

请严格按 8 阶段：
- 阶段 1 调真实 BSR + Trends
- 阶段 2 用 search_multi_platform 真抓多个平台
- 阶段 3 真评论 + analyze_reviews（如失败必须重试，不允许编痛点）
- 阶段 5 真采购成本（1688 失败时禁止凭空写数字，必须用 record_stage_status 登记 skipped）
- 阶段 7 IP 风险扫描
- 阶段 8 给候选品截图存证 + 综合决策

每个阶段完成后必须 record_stage_status 登记状态。
所有阶段跑完后必须 stage_status_summary 汇总。
不要在最后一步直接产出大段报告，让我用 PRO 模型在最后单独综合。

最大 24 步内完成。
"""


FINAL_INSTRUCTION = """所有数据已采集完毕（你已经看到完整 transcript）。

现在请你**综合所有真实工具调用的结果**，输出一份**完整的 8 阶段选品决策报告**：

# 选品决策报告 — 蓝牙耳机

## 执行汇总
（直接贴 stage_status_summary 工具返回的 markdown 表）

## 阶段 1 · 品类宏观
（Google Trends + BSR Top 表，每个数字带 url）

## 阶段 2 · 竞争格局
（价格带分布 + 评分门槛 + 品牌集中度 + 多平台覆盖矩阵）

## 阶段 3 · 痛点挖掘
（Top 5 真实痛点，每条带英文原话引用 + 频次 + 改进方案）

## 阶段 4 · 候选品画像卡
（每个候选品必须含：真实 ASIN + 真实标题 + 真实价格 + 真实评分 + 差异化点 + 蓝海评分）

## 阶段 5 · 利润测算
（如果有真采购成本就给 14 项拆解；如果没有就**明确标注 procurement_pending 并附用户应提供清单**，绝不能编数字）

## 阶段 6 · 供应链
（已拿到的供应商 / 待补全的清单）

## 阶段 7 · IP 风险扫描
（专利/商标检索结果）

## 阶段 8 · 选品决策
（推荐主推 + 备选 + 不推荐，每个都给真实 ASIN 对照 + 上架建议 + 定价区间）

## 证据清单
（所有截图路径 + BSR URL + 1688 URL，可点击验证）

## 待用户提供（如有）
（明确列出哪些信息需要用户补，补全后能继续走哪个阶段）

要求：
- 每个数字必须能从 transcript 中找到对应的工具返回值
- 禁止虚构任何 ASIN/品牌名/采购成本
- 报告要完整，不要中途截断
"""


def main():
    client = get_client()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}]

    t(f"# E2E 完整流程测试 v3 — 蓝牙耳机选品")
    t(f"\n时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    t(f"用户输入：\n```\n{USER}\n```\n")

    MAX_STEPS = 24

    # ════ 阶段 A：工具循环（flash 全程编排）════
    for step in range(1, MAX_STEPS + 1):
        t(f"\n## ━━━━━ Step {step} / model={MODEL_FLASH} (工具循环) ━━━━━")
        print(f"\n[{step}/工具] {MODEL_FLASH}", flush=True)

        try:
            resp = client.chat.completions.create(
                model=MODEL_FLASH, messages=messages,
                tools=TOOLS_SCHEMA, tool_choice="auto", max_tokens=2000,
            )
        except Exception as e:
            t(f"\n❌ LLM 调用失败：{e}")
            break

        msg = resp.choices[0].message

        if msg.content:
            t(f"\n💭 [Agent]\n\n{msg.content}\n")
            print(msg.content[:200], flush=True)

        if not msg.tool_calls:
            t("\n✅ Agent 工具循环结束，准备进入最终报告生成")
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

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            preview = json.dumps(args, ensure_ascii=False)[:200]
            t(f"\n🔧 **{name}**\n```json\n{preview}\n```")
            t0 = time.time()
            try:
                fn = TOOL_IMPL.get(name)
                result = fn(**args) if fn else {"error": f"unknown tool {name}"}
            except Exception as e:
                result = {"error": str(e)[:300]}
            ms = int((time.time() - t0) * 1000)
            preview_out = json.dumps(result, ensure_ascii=False)[:600]
            t(f"\n↳ {ms}ms\n```json\n{preview_out}\n```")
            print(f"  [{name}] {ms}ms", flush=True)
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)[:8000],
            })

    # ════ 阶段 B：最终综合（PRO 模型 + 8000 tokens，防截断）════
    t(f"\n\n## ━━━━━ FINAL STAGE / model={MODEL_PRO} (综合决策报告) ━━━━━\n")
    print(f"\n[FINAL] {MODEL_PRO} 综合决策报告生成中...", flush=True)

    # 先强制调 stage_status_summary（如果 Agent 漏调了，这里兜底）
    summary = TOOL_IMPL["stage_status_summary"]()
    t(f"\n📊 阶段执行汇总（自动兜底）:\n```\n{summary['markdown']}\n```\n")

    messages.append({
        "role": "user",
        "content": FINAL_INSTRUCTION + "\n\n阶段执行汇总（必须贴到报告顶部）：\n" + summary["markdown"],
    })

    final_text = ""
    try:
        resp = client.chat.completions.create(
            model=MODEL_PRO, messages=messages,
            max_tokens=8000,   # 关键：防 token 截断
            temperature=0.3,
        )
        final_text = resp.choices[0].message.content or ""
        t(f"\n💭 [PRO 综合报告]\n\n{final_text}\n")
        print(final_text[:500], flush=True)
    except Exception as e:
        t(f"\n❌ PRO 综合报告失败: {e}")

    # 写最终报告
    FINAL_PATH.write_text(
        f"# 选品决策报告\n\n"
        f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"- 完整 transcript：[`{TRANSCRIPT_PATH.name}`]({TRANSCRIPT_PATH.name})\n"
        f"- 工具循环模型：{MODEL_FLASH}\n"
        f"- 综合决策模型：{MODEL_PRO}\n\n---\n\n"
        f"{final_text or '（PRO 模型未输出，请查看 transcript）'}\n",
        encoding="utf-8"
    )
    print(f"\n\n✅ 完成")
    print(f"📜 transcript: {TRANSCRIPT_PATH}")
    print(f"📊 final: {FINAL_PATH}")


if __name__ == "__main__":
    main()
