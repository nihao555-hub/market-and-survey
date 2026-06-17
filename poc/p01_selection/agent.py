"""
选品 Agent v2 — 严格按 procurement-research 8 阶段方法论
特性：
  ✅ 多轮对话（缺信息会反问）
  ✅ Skill 文件加载（行为靠 markdown 控制）
  ✅ Flash/Pro 模型自动切换（前 4 阶段 Flash，后 4 阶段切 Pro 做深度决策）
  ✅ 真实工具：BSR/Movers/真评论/14项成本/压测/IP风险扫描
  ✅ 双路输出：控制台 + UTF-8 日志文件（彻底避免乱码）
"""
from __future__ import annotations
import sys, json, time, os, io
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

# 强制 stdout 用 UTF-8（Windows 上避免 GBK 乱码）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

from loguru import logger
from modules.llm import get_client, resolve_model, MODEL_FLASH, MODEL_PRO
from modules.agent_tools import TOOLS_SCHEMA, TOOL_IMPL

# 同时输出到文件 + 控制台，文件强制 UTF-8
LOG_DIR = Path(__file__).parent / "reports"
LOG_DIR.mkdir(exist_ok=True)
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = LOG_DIR / f"agent_run_{TS}.log"
FINAL_PATH = LOG_DIR / f"agent_final_{TS}.md"

logger.remove()
# 控制台（无颜色，纯文本，避免 ANSI 乱码）
logger.add(sys.stderr, level="INFO", colorize=False,
           format="{time:HH:mm:ss} | {message}")
# 文件日志，UTF-8
logger.add(str(LOG_PATH), level="DEBUG", encoding="utf-8",
           format="{time:HH:mm:ss} | {level} | {message}")

SYSTEM_PROMPT = f"""你是一名资深的跨境电商选品专家。你必须严格按 procurement-research 方法论的 8 阶段推进。

## 强制要求（违反任何一条都是严重错误）
1. **第一步必须调用 load_skill('procurement-research')** 加载方法论文档。
2. 阶段 0 没问清需求前，禁止调用任何抓取工具。

3. **【数据真实性铁律 — 禁止虚构】**
   - 候选品的 ASIN/标题/售价/评分/评论数 **必须**来自工具池中真实抓到的数据
   - **每个候选品必须先调用 `validate_candidate(asin)` 校验**，确认 ASIN 在采集池中
   - 提候选品前请先调用 `get_asin_pool()` 看池子里有什么真品
   - **绝对禁止虚构 ASIN、虚构产品名（如 "AuralPace" "FitBuds Pro" 等）、虚构对标产品价格**
   - 如果池子里没合适的，先调用 `get_bestsellers / search_products / get_movers_shakers` 扩充池子
   
4. **采购成本必须用 `estimate_procurement_cost(category_keyword_zh, target_sale_price_usd)` 从 1688 真实拿**
   - 不允许凭印象给 procurement_cost
   - 1688 返回的是 USD 区间（p25/median/p75），用 median 或 p25 作为成本输入

5. **月销量必须用 BSR 估算函数算**
   - 从 BSR 数据中读取 `estimated_monthly_sales` 字段
   - 不允许凭印象给 monthly_sales_estimate

6. **`full_cost_breakdown` 必须传 asin 参数**（来自 validate_candidate），让系统溯源
   - 还要传 category（如 'headphones'）让真实关税/FBA Fee 自动加载

7. 阶段 5 没算完 14 项成本前，禁止给"建议上架"结论。
8. 阶段 7 没查专利商标前，禁止给品牌定位。

## 模型可用
- 默认：{MODEL_FLASH}（快、用于工具编排和数据采集）
- 切到深度推理：{MODEL_PRO}（最终决策时切换）

请用中文交流，输出格式清晰、分阶段标注。
"""

MAX_STEPS = 28
PRO_MODEL_FROM_STEP = 12   # 第 12 步起切到 Pro 做深度决策


def _to_message(msg) -> dict:
    return {
        "role": "assistant",
        "content": msg.content,
        "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in (msg.tool_calls or [])
        ],
    }


# transcript 缓冲：所有 [Agent] 输出/工具调用/结果，最终写到独立 .md 文件
TRANSCRIPT: list[str] = []

def t(line: str = ""):
    """同时写入 transcript 和 stdout"""
    TRANSCRIPT.append(line)
    print(line, flush=True)


def run_agent(initial_query: str, *, auto_answer: dict | None = None):
    """
    initial_query: 商家的第一句话
    auto_answer: 用于自动化测试时，预填阶段 0 的澄清答复（dict）
                 实际生产为 None，由用户在多轮对话里逐步补全
    """
    client = get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": initial_query},
    ]

    t("=" * 75)
    t(f"🛒 商家：{initial_query}")
    t(f"📁 日志：{LOG_PATH.name}")
    t(f"📁 报告：{FINAL_PATH.name}")
    t("=" * 75)

    asked_clarify_once = False
    final_content = ""

    for step in range(1, MAX_STEPS + 1):
        # 模型自动切换：前期 flash 编排，后期 pro 决策
        model = MODEL_PRO if step >= PRO_MODEL_FROM_STEP else MODEL_FLASH
        logger.info(f"━━━━━ Step {step} / model={model} ━━━━━")
        t(f"\n━━━━━ Step {step} / model={model} ━━━━━")

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            max_tokens=2500,
        )
        msg = resp.choices[0].message

        if msg.content:
            t(f"\n💭 [Agent]\n{msg.content}\n")
            final_content = msg.content  # 持续记录最后一次模型输出（最终报告）

        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            if auto_answer and not asked_clarify_once and any(
                k in (msg.content or "") for k in ["确认", "请告诉我", "目标市场", "预算"]
            ):
                clarification = "\n".join(f"{i+1}. {v}" for i, v in enumerate(auto_answer.values()))
                t(f"\n📨 [自动答复-PoC]\n{clarification}\n")
                messages.append({"role": "user", "content": clarification})
                asked_clarify_once = True
                continue
            logger.info("✅ Agent 给出最终结论，流程结束")
            break

        messages.append(_to_message(msg))
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            preview = json.dumps(args, ensure_ascii=False)[:140]
            t(f"🔧 [{name}]({preview})")
            t0 = time.time()
            try:
                result = TOOL_IMPL[name](**args)
            except Exception as e:
                result = {"error": str(e)[:200]}
            ms = int((time.time() - t0) * 1000)
            preview_out = json.dumps(result, ensure_ascii=False)[:300]
            t(f"   ↳ {ms}ms {preview_out}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)[:8000],
            })
    else:
        logger.warning("⚠ 达到最大步数，强制总结")
        messages.append({"role": "user", "content":
            "请基于以上所有调研，按方法论第 8 阶段输出最终选品决策报告。"})
        final = client.chat.completions.create(
            model=MODEL_PRO, messages=messages, max_tokens=3000
        ).choices[0].message.content
        t(f"\n💭 [最终强制总结]\n{final}\n")
        final_content = final

    # 把最终决策报告独立保存为干净的 markdown
    # 如果 final_content 为空（如强制总结时模型没输出），用 transcript 兜底
    if not final_content or len(final_content.strip()) < 50:
        final_content = ("（最终模型未输出独立总结。完整决策内容见 transcript 文件。）\n\n"
                         "## 完整调研过程（节选 transcript）\n\n"
                         + "\n".join(TRANSCRIPT[-200:]))

    FINAL_PATH.write_text(
        f"# 选品 Agent — 最终决策报告\n\n"
        f"- 原始需求：{initial_query}\n"
        f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"- 完整运行日志：`{LOG_PATH.name}`\n\n"
        f"---\n\n{final_content}\n",
        encoding="utf-8"
    )
    # 完整 transcript 也存一份
    transcript_path = LOG_DIR / f"agent_transcript_{TS}.md"
    transcript_path.write_text("\n".join(TRANSCRIPT), encoding="utf-8")
    t("\n" + "=" * 75)
    t(f"✅ Agent 流程结束")
    t(f"📊 最终报告（中文清晰）：{FINAL_PATH}")
    t(f"📜 完整 transcript：{transcript_path}")
    t(f"📜 调试日志：{LOG_PATH}")
    return final_content


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else \
        "我想做蓝牙耳机这个品类，帮我做完整的选品调研。"
    # 自动答复（PoC 模式，省去人工答复，把 8 阶段全跑通）
    auto = {
        "市场": "美国市场",
        "平台": "Amazon FBA",
        "预算": "月度采购预算 5 万美元，单 SKU MOQ 500-1000 件接受",
        "物流": "FBA",
        "定位": "自有品牌 - 中端精品，做差异化",
        "排除": "避开苹果/索尼等大品牌专利雷区",
    }
    run_agent(query, auto_answer=auto)
    print("\n" + "=" * 75)
    print("✅ 选品 Agent 流程结束")
    print("=" * 75)
