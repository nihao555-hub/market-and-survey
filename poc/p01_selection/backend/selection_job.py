"""
选品任务后台执行 — backend 版本（对应 backend steering §2 + §8.8）

特性：
- 复用 multi_region_e2e 的 SYSTEM_TEMPLATE 和工具循环
- 全程 publish 真实工具调用 chunk（tool-input-start / tool-output）
- 监听 cancel
- 14 项成本 + 真实采购成本（1688 → Made-in-China 自动 fallback）
- onFinish 持久化 + 计费
- drain 后发 message-persisted
"""
from __future__ import annotations
import asyncio, json, re, time, uuid
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from modules.agent_tools import TOOLS_SCHEMA, TOOL_IMPL
from modules.browser_cleanup import start_watchdog, kill_orphan_browsers
from modules.llm import MODEL_FLASH, MODEL_PRO
from backend.events import publish, CANCEL_SUB, CANCEL_CHANNEL
from backend.storage import (add_message, set_active_stream, update_token_usage,
                              list_messages)

# 防僵尸进程：进程级看门狗（每 120s 清理 >240s 的孤儿爬虫浏览器，不误杀用户日常浏览器）
start_watchdog(interval_sec=120, max_age_sec=240)

# 模型名统一从 modules.llm 取（单一来源），避免与 llm.py / agent.py 漂移。

# 同步客户端（Agent 工具循环内部用，外层 await 走 to_thread）
# api_key 缺失时用占位符，保证 import 不报错（真正调用才会 401，提示更清晰）
_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY") or "MISSING_DEEPSEEK_API_KEY",
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
)

MAX_STEPS = 24


def _shrink_tool_output(result, max_list: int = 200, max_str: int = 100000):
    """把工具返回结果整理成适合前端结构化渲染的对象。
    默认上限放得很大（list 200 / 字符串 10 万字）——常规结果等于**不截断**，
    仅对异常超大列表保留一个安全阀，避免单条 SSE payload 撑爆。
    需要彻底不限时，调用方可传 max_list=None / max_str=None。
    """
    def _walk(v, depth=0):
        if depth > 8:
            return v if not isinstance(v, (list, dict)) else "…"
        if isinstance(v, str):
            if max_str is None or len(v) <= max_str:
                return v
            return v[:max_str] + "…"
        if isinstance(v, list):
            if max_list is None:
                return [_walk(x, depth + 1) for x in v]
            head = [_walk(x, depth + 1) for x in v[:max_list]]
            if len(v) > max_list:
                head.append(f"…(共 {len(v)} 项，已省略 {len(v) - max_list})")
            return head
        if isinstance(v, dict):
            return {k: _walk(val, depth + 1) for k, val in v.items()}
        return v
    try:
        return _walk(result)
    except Exception:
        return {"_repr": str(result)[:max_str or 5000]}


# 每个失败工具最多被反思引导重试的次数（穷尽手段后才允许标失败，不无限循环）
_MAX_REFLECT_RETRY = 3

# 收尾前最多催 agent「继续完成核心阶段」的次数（防"第一步没做完就生成报告"）
_MAX_NUDGE = 3
# 核心阶段（必须做过——completed/partial/failed 都算"尝试过"，not_run 才算没做）
_CORE_STAGES = {"stage1_trends", "stage2_competition", "stage3_pain_points", "stage4_candidates"}


def _stage_progress_ok(done_stages: set) -> bool:
    """核心阶段（1-4）是否至少做过 3 个。不足说明还没到能写报告的程度。"""
    return len(_CORE_STAGES & set(done_stages)) >= 3


def _build_reflection(name: str, args: dict, result: dict, ledger: dict) -> str | None:
    """
    自我反思注入：检测工具返回的失败/低质量信号，生成一条"换一条不同的路再试"的硬提示。
    返回 None 表示本次成功、无需反思。

    核心理念（对齐用户要求）：
    - 重试 ≠ 按原路重做。每次必须换**不同的工具/策略**回退，由 agent 自己决定选哪条。
    - 追踪每个工具已经试过的参数（平台/关键词/提取方式），在提示里列出"已试过的路"，
      明确要求换一条**没试过的**路，并按递进顺序聚焦不同的回退手段。
    - 穷尽多条路仍失败，才允许诚实标注失败。
    """
    if not isinstance(result, dict):
        return None

    # 该工具是否失败 / 低质量
    failed = False
    reasons = []
    if result.get("error"):
        failed = True
        reasons.append(str(result.get("error"))[:120])
    if result.get("success") is False:
        failed = True
    if result.get("should_abort") or result.get("all_failed"):
        failed = True
        reasons.append("本批次全部失败")
    if name == "search_multi_platform":
        res = result.get("results", {}) or {}
        empties = [k for k, v in res.items()
                   if isinstance(v, dict) and v.get("count", 0) == 0 and not v.get("skipped_blocked")]
        if empties:
            failed = True
            reasons.append(f"空数据平台: {empties}")
    if name == "search_products" and result.get("count", 0) == 0 and not result.get("skipped_cooldown"):
        failed = True

    if not failed:
        return None

    # ── 台账：按"工具类别"聚合，记录已试过的关键词/平台/提取方式（不只是计数）──
    cat = _reflect_category(name)
    led = ledger.setdefault(cat, {"tries": 0, "keywords": [], "platforms": [],
                                   "tools_tried": [], "tactics_used": []})
    led["tries"] += 1
    tries = led["tries"]
    # 记录这次用过的关键词/平台/工具
    kw = args.get("keyword") or args.get("category") or args.get("category_keyword")
    if kw and kw not in led["keywords"]:
        led["keywords"].append(kw)
    for pk in ([args.get("platform")] if args.get("platform") else []) + (args.get("platforms") or []):
        if pk and pk not in led["platforms"]:
            led["platforms"].append(pk)
    if name not in led["tools_tried"]:
        led["tools_tried"].append(name)

    tried_summary = (
        f"已试过的关键词：{led['keywords'] or '无'}；"
        f"已试过的平台：{led['platforms'] or '无'}；"
        f"已试过的工具：{led['tools_tried']}"
    )

    if tries > _MAX_REFLECT_RETRY:
        return (
            f"⚠️ 自我修复检查：『{cat}』已换 {tries-1} 条不同的路重试仍失败"
            f"（{'; '.join(reasons)[:160]}）。{tried_summary}。"
            "现在判定为**真实失败**——请 record_stage_status 把该项标 failed/partial，"
            "并在报告里如实写'该数据采集失败/缺失'。**禁止用其它市场或编造数据顶替**。"
            "可以继续推进不依赖该数据的其它阶段。"
        )

    # ── 递进式换路：每次只聚焦一条【没试过的】不同回退路径 ──
    ladder = _RETRY_LADDER.get(cat, _RETRY_LADDER["_default"])
    # 选当前这一档（按 tries 递进），并附完整备选让 agent 自己挑
    focus = ladder[min(tries - 1, len(ladder) - 1)]
    alts = "\n".join(f"  - {s}" for i, s in enumerate(ladder) if i != min(tries - 1, len(ladder) - 1))

    return (
        f"🔧 自我修复（第 {tries} 次，上限 {_MAX_REFLECT_RETRY}）：『{name}』失败"
        f"（{'; '.join(reasons)[:160]}）。\n"
        f"**重试≠按原路重做**。{tried_summary}。\n"
        f"这次请换一条**还没试过的不同路**——优先尝试：\n  ▶ {focus}\n"
        f"其它可选回退（你自己判断哪条最可能成，但不要重复上面已试过的关键词/平台）：\n{alts}\n"
        "只有当你确实换过多条不同的路都拿不到，才允许标该项失败。"
    )


def _reflect_category(tool_name: str) -> str:
    """把工具名归到一个重试类别，让同类失败共享'已试过的路'台账。"""
    if tool_name in ("search_products", "search_multi_platform"):
        return "search"
    if tool_name in ("discover_bsr_url", "get_bestsellers", "get_bestsellers_by_url"):
        return "bsr"
    if tool_name in ("get_reviews_batch", "get_product_review_summary"):
        return "reviews"
    if tool_name in ("get_real_procurement_cost", "get_supplier_detail_price"):
        return "procurement"
    return "_default"


# 递进式回退阶梯：每个类别一组【按顺序逐级升级、彼此不同】的回退手段。
# agent 按 tries 递进聚焦其中一条，并可参考其余备选自行决定。
_RETRY_LADDER = {
    "search": [
        "换关键词：用当地语言/同义词/加去限定词/单复数变体，换一个没试过的词再 search_products",
        "换平台：换本市场另一个 verified 平台（看 pick_platforms_for_market 的 platform_keys），别再用刚失败那个",
        "换提取方式：对该平台 URL 调 extract_products_with_llm(url)（LLM 直接读渲染后文本，绕过 selector）",
        "换引擎深度：search_products 传 max_retries=4 让引擎链多轮换"
        "（curl→scrapling→crawl4ai→patchright→botasaurus→pydoll→seleniumbase→camoufox→FlareSolverr），"
        "内部还会自动接 LLM 文本兜底 + ScrapeGraphAI 图谱抽取",
    ],
    "bsr": [
        "确认 geo=目标市场；若 amazon_available=false，改用 search_multi_platform 获取本地平台（不要再试 BSR）",
        "换子类目关键词重试 discover_bsr_url",
        "直接 search_products(本市场平台, 关键词) 拿真实在售商品替代 BSR 榜",
    ],
    "reviews": [
        "换 ASIN 批次：选销量/评论数更高的另一批 ASIN 重试",
        "换获取强度：减小单批量或调并发，避免被限流",
        "换来源：非 Amazon 市场用 ASIN 获取不到评论时，如实标注'该市场评论未采集'，不要用别国评论顶替",
    ],
    "procurement": [
        "换关键词：用更准的中文品类词重试 1688",
        "换数据源：1688 失败自动 fallback Made-in-China；可改用 get_supplier_detail_price 获取详情页阶梯价",
        "标缺失：仍拿不到则 record_stage_status 标 stage5 待用户提供报价单",
    ],
    "_default": [
        "换参数/关键词，走一条没试过的路再试",
        "换一个能拿到同类数据的替代工具",
        "仍失败则如实标注该项数据缺失",
    ],
}


def _UNUSED_OLD_REFLECTION(name, args, result, ledger):
    """已废弃：旧的固定清单式反思，由上方递进式换路版替代。保留空壳避免外部误引用。"""
    return None


class _StreamMsg:
    """流式累积出的 message（鸭子类型兼容非流式的 choices[0].message）。"""
    def __init__(self):
        self.content = None
        self.tool_calls = []


class _StreamToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": arguments})()


def _stream_llm_step(thread_id: str, model: str, messages: list, loop):
    """
    流式调用一步 LLM：实时把 reasoning（思考过程）和 text（正文）增量推给前端，
    同时累积 tool_calls。返回 (msg_like, reasoning_text)。

    解决两个问题：
    1. 「提交后无反应几秒」——思考期间 reasoning delta 立刻流出，用户看得到 agent 在想什么。
    2. 思考过程可见——reasoning-delta chunk 进前端 ThinkingStepsDisplay 思考区。
    """
    import asyncio as _aio

    def _pub(event: dict):
        """把发布调度回主事件循环（本函数在 to_thread 里跑）。"""
        try:
            fut = _aio.run_coroutine_threadsafe(publish(thread_id, event), loop)
            fut.result(timeout=5)
        except Exception:
            pass

    reasoning_id = str(uuid.uuid4())
    text_id = str(uuid.uuid4())
    reasoning_parts: list[str] = []
    content_parts: list[str] = []
    reasoning_started = False
    text_started = False
    # toolcall 累积：index -> {id,name,args}
    tc_acc: dict[int, dict] = {}

    stream = _client.chat.completions.create(
        model=model, messages=messages,
        tools=TOOLS_SCHEMA, tool_choice="auto",
        max_tokens=2500, stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        # 1) 思考过程增量
        rc = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
        if rc:
            if not reasoning_started:
                reasoning_started = True
                _pub({"type": "stream-chunk", "chunk": {"type": "reasoning-start", "id": reasoning_id}})
            reasoning_parts.append(rc)
            _pub({"type": "stream-chunk",
                  "chunk": {"type": "reasoning-delta", "id": reasoning_id, "delta": rc}})
        # 2) 正文增量
        if getattr(delta, "content", None):
            if reasoning_started and not text_started:
                _pub({"type": "stream-chunk", "chunk": {"type": "reasoning-end", "id": reasoning_id}})
            if not text_started:
                text_started = True
            content_parts.append(delta.content)
            _pub({"type": "stream-chunk",
                  "chunk": {"type": "text-delta", "id": text_id, "delta": delta.content}})
        # 3) 工具调用增量累积
        for tcd in (getattr(delta, "tool_calls", None) or []):
            idx = tcd.index or 0
            slot = tc_acc.setdefault(idx, {"id": None, "name": "", "args": ""})
            if tcd.id:
                slot["id"] = tcd.id
            if tcd.function:
                if tcd.function.name:
                    slot["name"] = tcd.function.name
                if tcd.function.arguments:
                    slot["args"] += tcd.function.arguments

    if reasoning_started and not text_started:
        _pub({"type": "stream-chunk", "chunk": {"type": "reasoning-end", "id": reasoning_id}})

    msg = _StreamMsg()
    msg.content = "".join(content_parts) or None
    msg.tool_calls = [
        _StreamToolCall(s["id"] or str(uuid.uuid4()), s["name"], s["args"] or "{}")
        for _, s in sorted(tc_acc.items()) if s["name"]
    ]
    return msg, "".join(reasoning_parts)


def _sanitize_messages_for_completion(messages: list) -> list:
    """
    清洗对话历史，保证可安全用于 chat.completions（无 tools 的纯文本补全）。

    修复 400「An assistant message with 'tool_calls' must be followed by tool messages」：
    - 每个带 tool_calls 的 assistant 消息，其后必须紧跟与每个 tool_call_id 配对的 tool 消息；
      缺失的（被 abort 中断 / MAX_STEPS 用尽 / 流式累积异常）补一条占位 tool 响应。
    - 末尾若仍有未配对的 tool_calls，直接降级为普通 assistant 文本，避免 API 拒绝。
    """
    out: list = []
    i = 0
    n = len(messages)
    while i < n:
        m = messages[i]
        if m.get("role") == "assistant" and m.get("tool_calls"):
            call_ids = [tc["id"] for tc in m["tool_calls"] if tc.get("id")]
            # 收集紧随其后的 tool 响应
            responded: set = set()
            j = i + 1
            while j < n and messages[j].get("role") == "tool":
                responded.add(messages[j].get("tool_call_id"))
                j += 1
            missing = [cid for cid in call_ids if cid not in responded]
            if missing and j >= n:
                # 末尾孤儿：整条降级为普通文本，丢弃 tool_calls
                txt = m.get("content") or "[已发起工具调用]"
                out.append({"role": "assistant", "content": txt})
                i += 1
                continue
            # 保留 assistant + 已有 tool 响应，并为缺失的补占位
            out.append(m)
            for k in range(i + 1, j):
                out.append(messages[k])
            for cid in missing:
                out.append({"role": "tool", "tool_call_id": cid,
                            "content": '{"error":"tool response missing (interrupted)"}'})
            i = j
            continue
        # 孤儿 tool 消息（前面不是 assistant.tool_calls）→ 丢弃，避免 400
        if m.get("role") == "tool":
            i += 1
            continue
        out.append(m)
        i += 1
    return out


# 模型偶尔会把工具调用以 DSML / DeepSeek 控制标记直接写进正文（尤其在生成最终报告
# 这种「无工具」补全里），这些控制标记不是给用户看的，渲染出来就是一段乱码尾巴。
# 这里把首个控制标记及其后的全部残留剔除，并去掉紧贴其前的「我先补跑工具…」过渡孤句。
_CTRL_TAG_RE = re.compile(r"<[^>\n]{0,40}(?:DSML|tool[\u2581_\s]?calls)[^>]*>", re.IGNORECASE)
_TRAILING_INTENT_RE = re.compile(
    r"(?:\n\s*)+[^\n]*?(?:补跑|继续(?:输出|调用)|调用(?:以下)?工具|工具调用|我(?:先|现在)[^\n]*工具)[^\n]*$"
)


def _strip_control_markup(text: str) -> str:
    """剔除正文里误混入的工具调用控制标记（DSML / DeepSeek tool-calls）及其尾随残留。"""
    if not text:
        return text
    m = _CTRL_TAG_RE.search(text)
    if not m:
        return text
    head = text[: m.start()].rstrip()
    head = _TRAILING_INTENT_RE.sub("", head).rstrip()
    return head


SYSTEM_TEMPLATE = """你是资深跨境选品专家。严格按 procurement-research 8 阶段方法论。

## 🚨 第一优先级：客观性与零幻觉铁律（违反即报告作废）
这套规则适用于**任何品类、任何市场**，不是只针对某几个例子。

1. **只陈述工具真实返回的数据**。报告里每个数字/结论都必须能追溯到某次工具调用的真实返回。
   绝不允许凭记忆、凭常识、凭"行业经验"编造任何 ASIN/价格/评分/月销/品牌/销量。
2. **失败就是失败，绝不粉饰**。工具返回 `success=false` / `error` / `count=0` / `should_abort=true` /
   `blocked` / 403 / timeout 时，这就是**失败**。禁止把失败说成"成功""数据已获取""市场清晰"。
   失败要在报告里如实写"该项数据采集失败/缺失"，缺失 > 编造。
3. **零主观评估**。不要为了"把任务做完""让报告好看"而把不确定说成确定、把估算说成真实。
   不确定时显式标注"待确认/数据不足/估算值±X%"，宁可结论保守，不可虚假自信。
4. **发现自己错了要立刻自我纠正**。如果后续工具返回与你之前的判断矛盾（例如之前说"市场数据已就绪"
   但其实只拿到 0 件），必须当场承认前面判断有误并修正，不要将错就错往下写。
5. **数据来源市场必须一致**。目标市场是 A 国，就只能用 A 国平台的数据。**严禁**用别国（尤其 Amazon US）
   的数据冒充目标市场。不同国家的品牌/价格/型号/消费习惯完全不同，张冠李戴会让整份报告失真。
6. **失败时先自我修复，穷尽手段后才认输**。工具返回失败/空数据时，**不要立刻停、也不要用别国数据顶替**。
   你有多层成熟工具可回退（curl→scrapling→patchright→botasaurus→camoufox→FlareSolverr 引擎链、
   extract_products_with_llm、webpage_to_markdown、换关键词、换本市场其它 verified 平台、调高 max_retries）。
   系统会在工具失败后给你一条「自我修复」提示，按它换策略真的再试 1-2 次。
   **只有当这些手段都试过仍拿不到**，才 record_stage_status 标 failed/partial 并如实写"该市场数据采集失败"，
   然后继续推进不依赖该数据的其它阶段。绝不回退去获取不相关市场（如目标是俄/巴却去获取 Amazon US）凑数。

## 数据真实性 — 零容忍

1. **第一步必调 get_current_datetime() 拿真实日期**（写到报告"数据采集时间"）
2. **候选品 ASIN 必须从 ASIN 池选** + validate_candidate 校验
3. **多平台真实获取** — 用户指定地区 → pick_platforms_for_market(only_verified=false) → search_multi_platform
   - 当前 verified 平台（18 个）：amazon, amazon_uk, amazon_de, amazon_fr, amazon_jp,
     amazon_au, amazon_in, bestbuy, newegg, target, mercadolibre_mx/br, otto, rakuten,
     yandex_market, lazada_sg, flipkart, aliexpress
   - **地理受限站已用多国出口代理突破**（amazon_uk→英国节点 / de→德国 / fr→德国邻近 / in→印度，
     由 multi_country 自动路由，无需额外配置）
   - partial（间歇）: shopee_sg, cdiscount, **wildberries**（并发场景下 100% 失败）
   - blocked（需付费代理/打码）: walmart, ebay, etsy, wayfair, amazon_ae,
     shopee_my, tokopedia, 1688, tiktok_shop, coupang, trendyol, ozon, noon,
     temu/shein/alibaba（数据藏嵌入式 JSON 或 NC 验证码）
   - **🚀 search_multi_platform 自动跳过 blocked 平台**（不再耗 60s/个超时），
     skipped_blocked 字段照实写到报告
   - **🛡️ 熔断机制**：单平台连续失败 ≥ 2 次后本 case 内自动 cooldown_skipped，
     看到该字段或 cooldown_warning 立即换平台，不要再试同一个
   - **俄罗斯特别提示**：只用 yandex_market（verified 稳定），wildberries 已降级 partial
4. **采购成本** — get_real_procurement_cost 现在自动 1688→Made-in-China fallback
   仍失败 → record_stage_status('stage5_profit', 'skipped')
   - **绝对禁止**'行业毛利率参考 / 假设采购成本 / 经验估算'等虚构数字
5. **样本量**：商品 ≥ 25 件 / 评论 ≥ 80 条
   - **真实月销优先**：商品含 `bought_past_month` 字段时（Amazon『X+ bought in past month』第一方数据），
     报告必须用真实值，不要用 BSR 经验估算；无该字段才退回估算并标注"误差±50%"
6. **每个阶段完成后立即 record_stage_status 登记**
7. **最终报告前必调**：stage_status_summary + traceability_check
8. **报告中必须包含真实产品图片**（capture_evidence.main_image.markdown_remote 或 ASIN 池 image_url）
9. **痛点章节用 `<details>` 包裹完整真实评论原文**

## 阶段流程
- 阶段 0: get_current_datetime + load_skill + pick_platforms_for_market
- 阶段 1: get_trend(≥3 关键词) + discover_bsr_url + get_bestsellers_by_url(limit=50)
  - **⚠️ BSR 必须按目标市场获取**：discover_bsr_url / get_bestsellers 必须传 geo=用户指定市场（如 SG/UK/DE），
    工具会自动用对应 Amazon 站点（amazon.sg / .co.uk / .de）。**禁止默认 amazon.com 美国站**——
    那是另一个市场的数据，对用户的目标市场无意义。
  - **该市场无 Amazon 业务时**（返回 amazon_available=false，如 RU/印尼/泰国/马来等）：
    不要硬获取 Amazon，直接用 search_multi_platform 获取本地平台（lazada_sg/ozon/mercadolibre 等）的畅销品。
  - **必须覆盖真正最畅销的商品**：limit≥50，按真实月销（bought_past_month）或评论数降序，
    确保拿到该品类该市场销量 Top 的真实商品，而不是随机几个。样本要能代表整个品类的主流盘子。
  - **季节性必用 compare_seasonality**（拿 5 年历史真实算峰谷月，禁止 LLM 凭空说"X月旺季"）
  - **关键词必须高质量（决定整份报告质量）**，按这个顺序做：
    1) **首选 get_amazon_keyword_suggestions**（Amazon 买家真实购物搜索词，带购买意图、按热度排序、附 top_modifiers 卖点词）——
       电商选品最准的词就是买家在购物框真实输入的词。英语市场(US/UK/DE/FR/JP/CA/IN/AU)优先用它。
    2) 补充 get_keyword_metrics（DDGS 长尾）；非英语市场(RU/BR/MX/CN)先把品类词翻成当地语言再扩展。
    3) **扩展出候选词后，正式获取前必须调 validate_keywords 做验证闭环**：
       它用"真实能搜到几件对口商品 + 语义相关度"给每个词打分，淘汰搜不到/跑偏的词
       （能杜绝"防盗门→门锁配件""geladeira em ingles=查资料词"这类错位）。
       **只用 validate_keywords 返回的 recommended_keywords 去正式 search_multi_platform**，不要用没验证过的词硬获取。
    4) 若 recommended_keywords 为空（候选词全验证失败）→ 换种子词/换本地语言词重新扩展，而不是硬获取。
- 阶段 2: search_multi_platform + analyze_market_structure
  - **⚠️ 市场一致性铁律**：搜索的平台必须属于目标市场。目标是俄罗斯/巴西，就只用 yandex_market /
    mercadolibre_br 等**当地平台**。**绝对禁止为了凑数据去获取 Amazon US**——美国的迷你冰箱
    不能代表巴西/俄罗斯的家用大冰箱市场，价格/型号/品牌完全不同，会让整份报告失真。
    当地平台获取失败时，宁可标 partial / 数据不足，也不要用美国数据顶替。
  - **平台名要用注册表 key**：mercadolibre_br（不是 mercadolivre_br）、yandex_market、amazon 等；
    工具已内置常见拼写别名自动纠正，但仍应尽量用标准 key。
- 阶段 3: get_reviews_batch(15-20 ASIN, max_total=260)
  - **评论普遍性铁律**：评论必须覆盖该品类该市场**销量/评论数 Top 15-20 个商品**（横向覆盖主流盘子），
    而不是只看 1-2 个单品。单品评论只代表那一个 listing，不能代表整个品类用户诉求。
    优先选 bought_past_month 或 review_count 最高的那批 ASIN 获取评论，样本≥80 条，这样痛点才有普遍代表性。
  - **用真实加权的诉求云，不要用简单计数**：get_reviews_batch 返回的 `demand_cloud` 已按
    Amazon 官方真实提及次数(或销量/评论体量)加权排序——这才代表"多少人真的在乎这个点"。
    报告的痛点/需求排序**以 demand_cloud 的 weighted_mentions 为准**，不要用出现商品数这种弱信号。
  - **先看代表性自检再下结论**：get_reviews_batch 返回的 `representativeness` 给出覆盖商品数、
    背后真实评论体量。若 verdict 是"代表性偏弱"（覆盖<10个商品 或 评论体量<1000），
    **必须先扩样本**（加更多 Top 商品）再总结诉求；扩不上去就在报告里如实标注"样本代表性有限"。
  - **⚠️ 评论市场一致性铁律（最重要）**：评论来源市场必须与目标市场一致。
    `get_reviews_batch` 当前只支持 **Amazon 系**（用 ASIN）。
    · 目标是美国/英国/德国/日本等 Amazon 市场 → 正常用。
    · 目标是**俄罗斯/巴西/东南亚等非 Amazon 主战场** → **绝对禁止**用 Amazon US 评论冒充当地诉求！
      那是另一个国家消费者的声音，会严重误导。此时应：① 用 MercadoLibre/Yandex 商品页的评分与
      标题信息做有限推断；② 在报告里**明确写"该市场评论数据未采集，痛点分析待补"**，
      不要编、不要拿美国数据顶替。诚实缺失 > 虚假普遍性。
  - **评论来源说明**：Amazon 评论取自各商品详情页公开的 8 条 top reviews + Amazon AI『Customers say』
    方面摘要（含每个方面真实提及次数与情感）。报告里要标注样本来源、覆盖商品数/评论数、以及来源市场。
  - **痛点频次必用 extract_pain_points_precise**（LLM 出词 + Python 精确匹配，0 误差；禁止 analyze_reviews 估算"出现 N 次"）
  - **评论时间分布用 analyze_review_temporal**（看产品质量是否在下降）
- 阶段 4: get_asin_pool + validate_candidate × 3-5
  - **候选品真实数据用 get_amazon_product_details_api**（RapidAPI 已可用）：真实 BSR/月销/卖家数/重量
  - **演进分析用 get_wayback_snapshots / analyze_listing_evolution**（archive.org 免费）：first_seen 上架时间、标题改动次数、历史价格
- 阶段 5: get_real_procurement_cost → 成功就 full_cost_breakdown(asin, category, stage='new_product' 和 'stable' 各跑一次)
  - **采购价精准化用 get_supplier_detail_price**（获取详情页 MOQ 阶梯价，按下单量取精准单价）
  - **风险必用 monte_carlo_stress_test**（5000 次模拟，给亏损概率分布；ACOS/退货率因卖家而异，禁止当单点真值写）
- 阶段 7: quick_ip_check → **候选品深查用 deep_ip_risk_assessment**（PatentsView 官方 API + 引用链）
- 阶段 8: capture_evidence_batch（**🚀 并发获取 3-5 候选品**，替代多次 capture_evidence；3x 提速）
- 收尾: stage_status_summary + traceability_check

## ⚠️ 工具调用格式铁律
必须用标准 function_calling 调工具。**禁止**在 content 里写 DSML 标签。

## 🚫 不准反问用户 — 直接获取数据
- ❌ 不准在 Step 1 反问"物流/定位/子类目"等问题
- ❌ 不准等"用户回复后再开始获取"
- ✅ 用户输入的目标市场+品类+预算足够开始，直接调 get_current_datetime + pick_platforms_for_market
- ✅ 子品类不确定就并发获取多个候选词的 BSR
- "待用户提供清单"放在阶段 5/7，不要 Step 1 就停下

## ⚠️ 成本数据诚实铁律
- A 类（佣金/FBA/关税/汇率/头程）从真实数据源取，已由 full_cost_breakdown 自动覆盖
- C 类（ACOS/退货率）**无公开真实数据源、因卖家而异** → 报告里必须配合 monte_carlo_stress_test 的概率分布呈现，绝不写成"真实值"
- 没拿到真实采购成本时，绝对禁止写"行业毛利率参考/假设采购成本/经验估算"等虚构数字，直接 record_stage_status('stage5_profit','skipped')

请用中文交流。
"""


async def run_selection_job(thread_id: str, stream_id: str, user_text: str,
                             model_choice: str = "flash", kind: str = "general"):
    """
    选品 Agent 后台执行。
    - thread_id: 会话 id（持久化用）
    - stream_id: 本次执行 id
    - user_text: 用户输入（"我想做 X 选品调研..."）
    - model_choice: 'flash' 或 'pro'（决定工具循环模型；最终报告固定用 PRO）
    - kind: 研究模式（market/trend/competitor/audience/opportunity/general）——
      决定系统方法论侧重、阶段闸口与最终报告骨架（5 个模式做精）。
    """
    from backend.research_modes import get_mode_spec
    mode = get_mode_spec(kind)
    aborted = {"flag": False}

    def _on_cancel():
        aborted["flag"] = True
        logger.warning(f"[cancel] selection job for {thread_id}")

    cancel_ch = CANCEL_CHANNEL.format(thread_id=thread_id)
    await CANCEL_SUB.subscribe(cancel_ch, _on_cancel)

    user_msg_id = str(uuid.uuid4())
    add_message(thread_id, user_msg_id, "user", [{"type": "text", "text": user_text}])
    set_active_stream(thread_id, stream_id)

    await publish(thread_id, {"type": "start", "messageId": user_msg_id})

    dataset_first = (
        "\n## 📦 开局先用零成本大盘（省 TikHub 额度）：\n"
        "正式调用任何付费实时工具前，**先调一次 browse_daily_dataset(query=本次品类/关键词)**，"
        "用每日刷新已落库的真实快照（28 品类商品榜 + 热销榜 + 8 平台社媒热词 + 话题声量曲线）快速定位方向。"
        "若它返回该方向已有数据，就以此为底子，只在需要更新/更细颗粒时再去调实时付费工具补齐；"
        "若返回为空（还没刷新过），再正常走实时工具。这样既不浪费已花钱攒下的大盘，也减少重复调用。\n"
    )
    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE + mode.system_addendum + dataset_first},
        {"role": "user", "content": user_text},
    ]
    asst_parts = []
    asst_msg_id = str(uuid.uuid4())
    final_content = ""
    # 自我修复重试台账：记录每个 (工具,关键参数) 已被反思引导重试多少次，避免无限循环
    _retry_ledger: dict = {}
    # 防"核心阶段没做完就收尾"的催促计数
    _premature_nudge: dict = {"n": 0}

    base_model = MODEL_PRO if model_choice == "pro" else MODEL_FLASH

    try:
        # 工具循环
        for step in range(1, MAX_STEPS + 1):
            if aborted["flag"]:
                await publish(thread_id, {"type": "stream-error",
                                            "chunk": {"reason": "user-cancelled"}})
                break
            
            await publish(thread_id, {"type": "stream-chunk",
                                        "chunk": {"type": "step-start",
                                                  "step": step, "max_steps": MAX_STEPS,
                                                  "model": base_model}})

            # ── 流式调用：实时把思考过程(reasoning)和正文(text)推给前端 ──
            # 解决"提交后无反应几秒"——思考期间 reasoning delta 就开始流出。
            try:
                _loop = asyncio.get_running_loop()
                msg, reasoning_text = await asyncio.to_thread(
                    _stream_llm_step, thread_id, base_model, messages, _loop
                )
            except Exception as e:
                await publish(thread_id, {"type": "stream-error",
                                            "chunk": {"reason": f"llm_error: {str(e)[:150]}"}})
                break

            # 注：reasoning 和 text 已在 _stream_llm_step 内实时流出，这里不重复发。

            # DSML 检测
            if msg.content and "DSML" in (msg.content or ""):
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "dsml-detected",
                                                      "step": step}})
                messages.append({"role": "assistant", "content": "[DSML 误输出已删除]"})
                messages.append({
                    "role": "user",
                    "content": "❌ 你刚才把工具调用写在了 content 里（DSML 标签格式）。"
                                "请使用标准的 function calling 格式调用工具。",
                })
                continue

            if msg.content:
                final_content = msg.content
                asst_parts.append({"type": "text", "text": msg.content})

            if not msg.tool_calls:
                # agent 不再调工具 = 想收尾。但要防"阶段没做完就生成报告"。
                # 检查核心阶段完成度，不足则注入"继续完成"提示，最多催 _MAX_NUDGE 次。
                try:
                    _summary = TOOL_IMPL["stage_status_summary"]()
                    _rows = _summary.get("rows", [])
                    _done_stages = {r.get("stage_id") for r in _rows
                                    if r.get("status") not in (None, "not_run")}
                except Exception:
                    _done_stages = set()
                _core_ok = len(mode.core_stages & set(_done_stages)) >= mode.min_core
                if (not _core_ok) and _premature_nudge["n"] < _MAX_NUDGE:
                    _premature_nudge["n"] += 1
                    messages.append({"role": "assistant", "content": msg.content or ""})
                    messages.append({"role": "user", "content":
                        mode.nudge.format(done=sorted(_done_stages) or "几乎没有")
                    })
                    await publish(thread_id, {"type": "stream-chunk",
                                                "chunk": {"type": "reflection",
                                                          "tool": "stage_gate",
                                                          "note": "核心阶段未完成，要求 agent 继续"}})
                    continue
                # 阶段够了 或 已催足次数 → 收尾
                messages.append({"role": "assistant", "content": msg.content or ""})
                break

            # 加 assistant tool_calls 到历史
            messages.append({
                "role": "assistant", "content": msg.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })
            asst_parts.append({
                "type": "step-tool-calls", "step": step,
                "calls": [{"id": tc.id, "name": tc.function.name,
                            "args": tc.function.arguments[:300]} for tc in msg.tool_calls],
            })

            # 执行工具（顺序，但 search_multi_platform 内部并发）
            _pending_reflections: list[tuple[str, str]] = []  # (tool_name, reflection_text)
            for tc in msg.tool_calls:
                if aborted["flag"]: break
                name = tc.function.name
                try: args = json.loads(tc.function.arguments or "{}")
                except Exception: args = {}
                
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "tool-input-start",
                                                      "id": tc.id, "name": name,
                                                      "args": args}})
                t0 = time.time()
                try:
                    fn = TOOL_IMPL.get(name)
                    result = await asyncio.to_thread(
                        lambda: fn(**args) if fn else {"error": f"unknown tool {name}"}
                    )
                except Exception as e:
                    result = {"error": str(e)[:300]}
                ms = int((time.time() - t0) * 1000)
                # 给前端发结构化对象（用于美化渲染），而非截断的 JSON 字符串。
                # 大体积字段（products/items/reviews 列表）裁剪，避免 SSE payload 过大。
                output_obj = _shrink_tool_output(result)
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "tool-output",
                                                      "id": tc.id, "name": name,
                                                      "elapsed_ms": ms,
                                                      "output": output_obj}})
                messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)[:30000],
                })

                # ── 自我反思：先收集，等本批 tool 响应全部 append 完再统一注入 ──
                # （绝不能在 tool 序列中间插 system/user 消息，否则破坏
                #   assistant(tool_calls) → tool → tool 的紧邻配对，触发 400）
                reflection = _build_reflection(name, args, result, _retry_ledger)
                if reflection:
                    _pending_reflections.append((name, reflection))

            # 本批工具全部执行完毕后，再统一把反思以 user 消息注入（位置安全）
            for r_name, r_text in _pending_reflections:
                messages.append({"role": "user", "content": r_text})
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "reflection",
                                                      "tool": r_name, "note": r_text[:200]}})

        # 收尾 — PRO 综合报告
        if not aborted["flag"]:
            await publish(thread_id, {"type": "stream-chunk",
                                        "chunk": {"type": "final-stage-starting",
                                                  "model": MODEL_PRO}})
            try:
                summary = TOOL_IMPL["stage_status_summary"]()
                common_rules = (
                    "## 严格禁令：\n"
                    "- ❌ 禁止'行业毛利率参考/假设采购成本/经验估算'等虚构数字\n"
                    "- ❌ 阶段5 失败时整章只写'待用户提供'，不给任何利润数字\n"
                    "- ❌ 禁止虚构 ASIN/品牌/价格/评分；禁止 DSML 标签\n"
                    "- ✅ 数据缺失明确写'待用户提供 XXX'\n"
                )
                # 分段生成（按模式定制报告骨架），避免单次 8000 token 截断
                report_prompts = mode.build_report_prompts(summary["markdown"], common_rules)

                def _gen_part(prompt: str) -> str:
                    # 清洗历史，避免末尾未配对的 tool_calls 触发 400
                    safe_msgs = _sanitize_messages_for_completion(messages)
                    msgs = safe_msgs + [{"role": "user", "content": prompt}]
                    for _ in range(2):
                        r = _client.chat.completions.create(
                            model=MODEL_PRO, messages=msgs,
                            max_tokens=8000, temperature=0.3,
                        )
                        ft = r.choices[0].message.content or ""
                        if "DSML" in ft or len(ft) < 800:
                            msgs = msgs + [
                                {"role": "assistant", "content": ft[:300]},
                                {"role": "user", "content": "❌ 输出有问题（DSML/太短），用纯 markdown 重写本部分。"},
                            ]
                            continue
                        return _strip_control_markup(ft)
                    return _strip_control_markup(ft)

                parts: list[str] = []
                for _p in report_prompts:
                    parts.append(await asyncio.to_thread(_gen_part, _p))
                final_content = "\n\n".join(p.strip() for p in parts if p and p.strip())
                final_content = _strip_control_markup(final_content)
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "final-report",
                                                      "content": final_content[:200] + "..."}})
                asst_parts.append({"type": "text", "text": final_content})
            except Exception as e:
                logger.exception("PRO final fail")
                await publish(thread_id, {"type": "stream-error",
                                            "chunk": {"reason": f"pro_final: {str(e)[:120]}"}})

        # 持久化
        add_message(thread_id, asst_msg_id, "assistant",
                     asst_parts or [{"type": "text", "text": final_content or "(empty)"}])
        
        # 自动产出三件套：完整报告 / 1 页摘要 / PDF
        if final_content and len(final_content) > 1500:
            try:
                from pathlib import Path as _P
                reports_dir = _P(__file__).resolve().parent.parent / "reports" / "backend"
                reports_dir.mkdir(parents=True, exist_ok=True)
                base_name = f"report_{thread_id[:8]}"

                # 把报告内图片（evidence/keepa_charts 相对 reports 根 + 远程图）
                # 落地到 reports/backend/assets/ 并改写为 assets/xxx.jpg 相对路径，
                # 让下载的 md / PDF 自包含、可离线渲染（PDF 的 CWD 即 reports/backend）。
                from modules.report_export import (one_pager, detail_5pages, export_pdf,
                                                    build_merchant_report, localize_report_images)
                try:
                    localized_content = localize_report_images(final_content, reports_dir)
                except Exception as _le:
                    logger.warning(f"localize images fail: {_le}")
                    localized_content = final_content

                full_md_path = reports_dir / f"{base_name}_full.md"
                full_md_path.write_text(localized_content, encoding="utf-8")

                # 1 页摘要
                one_pager_md = one_pager(localized_content)
                onepager_path = reports_dir / f"{base_name}_1page.md"
                onepager_path.write_text(one_pager_md, encoding="utf-8")

                # 商家版（默认主产出：1页核心 + 中价值折叠 + 去水分）
                merchant_md = build_merchant_report(localized_content)
                merchant_path = reports_dir / f"{base_name}_merchant.md"
                merchant_path.write_text(merchant_md, encoding="utf-8")

                # 5 页详情
                detail_md = detail_5pages(localized_content)
                detail_path = reports_dir / f"{base_name}_detail.md"
                detail_path.write_text(detail_md, encoding="utf-8")

                # PDF（完整版，图片已 localize 到 assets/）
                pdf_path = reports_dir / f"{base_name}.pdf"
                pdf_result = export_pdf(localized_content, str(pdf_path), title="选品决策报告")
                
                await publish(thread_id, {"type": "stream-chunk", "chunk": {
                    "type": "report-artifacts",
                    "merchant_md": str(merchant_path),
                    "full_md": str(full_md_path),
                    "one_pager_md": str(onepager_path),
                    "detail_md": str(detail_path),
                    "pdf": str(pdf_path) if pdf_result.get("ok") else None,
                    "pdf_error": pdf_result.get("error") if not pdf_result.get("ok") else None,
                    "_primary": "merchant_md",
                }})
            except Exception as e:
                logger.warning(f"report artifacts gen fail: {e}")
        
        await publish(thread_id, {"type": "stream-chunk", "chunk": {"type": "finish"}})
        await publish(thread_id, {"type": "message-persisted",
                                    "messageId": asst_msg_id,
                                    "report_chars": len(final_content)})

    except Exception as e:
        logger.exception("selection job error")
        await publish(thread_id, {"type": "stream-error", "chunk": {"reason": str(e)[:200]}})
    finally:
        await CANCEL_SUB.unsubscribe(cancel_ch)
        set_active_stream(thread_id, None)
        # 任务结束清理本次产生的孤儿爬虫浏览器（max_age=0 立即清，防累计）
        try:
            await asyncio.to_thread(kill_orphan_browsers, 0)
        except Exception:
            pass

    return {"thread_id": thread_id, "stream_id": stream_id,
             "assistant_message_id": asst_msg_id,
             "final_chars": len(final_content)}
