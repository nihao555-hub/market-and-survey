"""
数据平面：StreamChatJob（对应 backend steering §2 + §8.8）
- 在后台 worker 跑 LLM 工具循环
- 监听 cancel pub/sub
- 流式 publish chunk + onFinish persist + drain 后发 message-persisted
- 逐 step 扣 token（计费）
"""
from __future__ import annotations
import asyncio, json, time, uuid
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from modules.agent_tools import TOOLS_SCHEMA, TOOL_IMPL
from modules.llm import MODEL_FLASH, MODEL_PRO
from backend.events import publish, CANCEL_SUB, CANCEL_CHANNEL
from backend.storage import (add_message, set_active_stream, update_token_usage,
                              list_messages)

# 模型名统一从 modules.llm 取（单一来源）。

_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY") or "MISSING_DEEPSEEK_API_KEY",
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
)

MAX_STEPS = 28
PRO_FROM_STEP = 12
SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "skills" / "procurement-research.md"


def load_system_prompt() -> str:
    skill = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else ""
    return f"""你是资深跨境选品专家，严格按 procurement-research 8 阶段方法论。

数据真实性铁律：
- 候选品 ASIN 必须先 get_asin_pool() 看池子 + validate_candidate(asin) 校验
- procurement_cost 必须 estimate_procurement_cost(中文关键词)
- monthly_sales_estimate 必须从 BSR 抓的 estimated_monthly_sales 字段取
- full_cost_breakdown 必须传 asin + category（'headphones' 等）

禁止凭空虚构产品、品牌、价格、销量。

模型可用：{MODEL_FLASH}（编排）/ {MODEL_PRO}（决策）。

【方法论文档】：
{skill[:3000]}
"""


async def run_stream_job(thread_id: str, stream_id: str, user_text: str,
                          model_choice: str = "flash"):
    """
    入参：thread_id（会话）+ stream_id（本次执行 id）+ user_text（用户消息）
    职责：跑 Agent 工具循环，全程 publish chunk，onFinish persist + 计费 + drain 后发 persisted。
    """
    aborted = {"flag": False}

    def _on_cancel():
        aborted["flag"] = True
        logger.warning(f"[cancel] received for {thread_id}")

    cancel_ch = CANCEL_CHANNEL.format(thread_id=thread_id)
    await CANCEL_SUB.subscribe(cancel_ch, _on_cancel)

    # 持久化 user message
    user_msg_id = str(uuid.uuid4())
    add_message(thread_id, user_msg_id, "user", [{"type": "text", "text": user_text}])
    set_active_stream(thread_id, stream_id)

    await publish(thread_id, {"type": "start", "messageId": user_msg_id})
    await publish(thread_id, {"type": "start-step"})

    messages = [{"role": "system", "content": load_system_prompt()}]
    # 加载历史
    for m in list_messages(thread_id, status="sent"):
        if m.role in ("user", "assistant"):
            content = ""
            for p in (m.parts or []):
                if isinstance(p, dict) and p.get("type") == "text":
                    content += p.get("text", "")
            if content:
                messages.append({"role": m.role, "content": content})

    final_content = ""
    asst_msg_id = str(uuid.uuid4())
    asst_parts = []  # UIMessagePart[]

    try:
        for step in range(1, MAX_STEPS + 1):
            if aborted["flag"]:
                await publish(thread_id, {"type": "stream-error",
                                            "chunk": {"reason": "user-cancelled"}})
                break

            model = MODEL_PRO if step >= PRO_FROM_STEP else MODEL_FLASH
            await publish(thread_id, {"type": "stream-chunk",
                                        "chunk": {"type": "step-start",
                                                  "step": step, "model": model}})

            # 真正用流式
            stream = await _client.chat.completions.create(
                model=model, messages=messages, tools=TOOLS_SCHEMA,
                tool_choice="auto", max_tokens=2500, stream=True,
            )
            text_buf = ""
            tool_calls_buf: dict[int, dict] = {}
            usage = None
            async for ev in stream:
                if aborted["flag"]:
                    break
                delta = ev.choices[0].delta if ev.choices else None
                if not delta:
                    continue
                if delta.content:
                    text_buf += delta.content
                    await publish(thread_id, {"type": "stream-chunk",
                                                "chunk": {"type": "text-delta",
                                                          "delta": delta.content}})
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        slot = tool_calls_buf.setdefault(idx, {"id": "", "name": "", "args": ""})
                        if tc.id: slot["id"] = tc.id
                        if tc.function:
                            if tc.function.name: slot["name"] += tc.function.name
                            if tc.function.arguments: slot["args"] += tc.function.arguments
                if getattr(ev, "usage", None):
                    usage = ev.usage

            if text_buf:
                asst_parts.append({"type": "text", "text": text_buf})
                final_content = text_buf
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "text-end"}})

            # 累计 token（逐 step 扣费）
            if usage:
                update_token_usage(thread_id,
                    input_delta=usage.prompt_tokens or 0,
                    output_delta=usage.completion_tokens or 0,
                    input_credits=(usage.prompt_tokens or 0) * 0.0001,    # 简易费率
                    output_credits=(usage.completion_tokens or 0) * 0.0004,
                )

            if not tool_calls_buf:
                # 模型没调工具 → 终态
                break

            # 把 assistant tool_calls 加入历史
            assistant_msg = {"role": "assistant", "content": text_buf,
                              "tool_calls": [
                                  {"id": v["id"], "type": "function",
                                   "function": {"name": v["name"], "arguments": v["args"]}}
                                  for v in tool_calls_buf.values()
                              ]}
            messages.append(assistant_msg)
            asst_parts.append({"type": "step-tool-calls",
                                "calls": list(tool_calls_buf.values())})

            # 执行工具
            for tc in tool_calls_buf.values():
                if aborted["flag"]:
                    break
                name, raw_args = tc["name"], tc["args"]
                try: args = json.loads(raw_args or "{}")
                except Exception: args = {}
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "tool-input-start",
                                                      "id": tc["id"], "name": name,
                                                      "args": args}})
                t0 = time.time()
                try:
                    fn = TOOL_IMPL.get(name)
                    result = fn(**args) if fn else {"error": f"unknown tool {name}"}
                except Exception as e:
                    result = {"error": str(e)[:200]}
                ms = int((time.time() - t0) * 1000)
                preview = json.dumps(result, ensure_ascii=False)[:300]
                await publish(thread_id, {"type": "stream-chunk",
                                            "chunk": {"type": "tool-output", "id": tc["id"],
                                                      "name": name, "elapsed_ms": ms,
                                                      "preview": preview}})
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                  "content": json.dumps(result, ensure_ascii=False)[:8000]})

        # 持久化 assistant 最终消息
        add_message(thread_id, asst_msg_id, "assistant",
                     asst_parts or [{"type": "text", "text": final_content or ""}])
        # drain 完才发 persisted（steering §2.5）
        await publish(thread_id, {"type": "stream-chunk", "chunk": {"type": "finish"}})
        await publish(thread_id, {"type": "message-persisted", "messageId": asst_msg_id})

    except Exception as e:
        logger.exception("stream job error")
        await publish(thread_id, {"type": "stream-error", "chunk": {"reason": str(e)[:200]}})
    finally:
        await CANCEL_SUB.unsubscribe(cancel_ch)
        set_active_stream(thread_id, None)

    return {"thread_id": thread_id, "stream_id": stream_id,
            "assistant_message_id": asst_msg_id, "final": final_content}
