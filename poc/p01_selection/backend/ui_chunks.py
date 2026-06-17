"""
UIMessageChunk 适配层（对齐 frontend steering §2.1）。

后端 selection_job 产出的是自定义 chunk（step-start / tool-input-start / tool-output /
text-delta / final-report / report-artifacts / finish）。前端用 ai-sdk 的
readUIMessageStream 消费，要求 chunk 是 ai-sdk 标准 UIMessageChunk 格式。

本模块把自定义 chunk 翻译成 ai-sdk UIMessageChunk 子集，让前后端共用同一协议：
  start / start-step / finish-step / finish
  text-start / text-delta / text-end
  reasoning-start / reasoning-delta / reasoning-end
  tool-input-start / tool-input-available / tool-output-available / tool-output-error
  data-*（自定义数据片段，如报告产物）

用法：在 selection_job 里把要 publish 的 chunk 先过 adapter.feed(chunk)，
adapter 产出 0..N 个标准 chunk，逐个 publish。
"""
from __future__ import annotations
import uuid
from typing import Iterator


class UIChunkAdapter:
    """把一个 case/thread 的自定义 chunk 流翻译成 ai-sdk UIMessageChunk 流。

    维护内部状态：是否已发 start、当前 text part id、各 toolCallId 状态。
    """

    def __init__(self):
        self._started = False
        self._step_open = False
        self._text_id: str | None = None          # 当前 text part（流式文本）
        self._text_open = False
        self._known_tools: set[str] = set()        # 已 tool-input-start 的 toolCallId

    # ─── 内部小工具 ───
    def _ensure_start(self) -> Iterator[dict]:
        if not self._started:
            self._started = True
            yield {"type": "start", "messageId": str(uuid.uuid4())}
            yield {"type": "start-step"}
            self._step_open = True

    def _close_text(self) -> Iterator[dict]:
        if self._text_open and self._text_id:
            yield {"type": "text-end", "id": self._text_id}
            self._text_open = False
            self._text_id = None

    # ─── 主入口 ───
    def feed(self, chunk: dict) -> list[dict]:
        """喂一个自定义 chunk，返回 0..N 个 ai-sdk 标准 chunk。"""
        return list(self._feed(chunk))

    def _feed(self, chunk: dict) -> Iterator[dict]:
        ctype = chunk.get("type")

        # 工具循环每一步开始（仅作为分步标记，不直接映射）
        if ctype == "step-start":
            yield from self._ensure_start()
            return

        # 流式文本增量
        if ctype == "text-delta":
            yield from self._ensure_start()
            delta = chunk.get("delta", "")
            if not delta:
                return
            if not self._text_open:
                self._text_id = str(uuid.uuid4())
                self._text_open = True
                yield {"type": "text-start", "id": self._text_id}
            yield {"type": "text-delta", "id": self._text_id, "delta": delta}
            return

        # 工具开始调用（带参数）
        if ctype == "tool-input-start":
            yield from self._ensure_start()
            yield from self._close_text()
            tid = chunk.get("id") or str(uuid.uuid4())
            name = chunk.get("name", "tool")
            self._known_tools.add(tid)
            yield {"type": "tool-input-start", "toolCallId": tid, "toolName": name}
            if "args" in chunk and chunk["args"] is not None:
                yield {"type": "tool-input-available", "toolCallId": tid,
                       "toolName": name, "input": chunk["args"]}
            return

        # 工具返回结果
        if ctype == "tool-output":
            tid = chunk.get("id") or str(uuid.uuid4())
            name = chunk.get("name", "tool")
            if tid not in self._known_tools:
                # 没见过对应 start，补一个
                yield {"type": "tool-input-start", "toolCallId": tid, "toolName": name}
                self._known_tools.add(tid)
            # output 优先用结构化对象，回退到旧的 preview 字符串
            output = chunk.get("output")
            if output is None:
                output = chunk.get("preview")
            yield {"type": "tool-output-available", "toolCallId": tid, "output": output}
            return

        # 流式思考过程（reasoning-start/delta/end）直接透传给前端
        if ctype in ("reasoning-start", "reasoning-delta", "reasoning-end"):
            yield from self._ensure_start()
            if ctype == "reasoning-delta":
                yield {"type": "reasoning-delta", "id": chunk.get("id"), "delta": chunk.get("delta", "")}
            else:
                yield {"type": ctype, "id": chunk.get("id")}
            return

        # LLM 思考过程（一次性 reasoning 文本）→ 转成 reasoning-start/delta/end
        if ctype == "reasoning":
            yield from self._ensure_start()
            yield from self._close_text()
            rid = chunk.get("id") or str(uuid.uuid4())
            text = chunk.get("text", "")
            if text:
                yield {"type": "reasoning-start", "id": rid}
                yield {"type": "reasoning-delta", "id": rid, "delta": text}
                yield {"type": "reasoning-end", "id": rid}
            return

        # DSML 误输出检测（作为 reasoning 提示，可忽略）
        if ctype == "dsml-detected":
            return

        # 自我反思/修复提示（作为一个轻量 reasoning 片段透传，让前端显示"正在自我修复"）
        if ctype == "reflection":
            yield from self._ensure_start()
            yield from self._close_text()
            rid = str(uuid.uuid4())
            note = chunk.get("note", "检测到失败，正在换策略重试…")
            yield {"type": "reasoning-start", "id": rid}
            yield {"type": "reasoning-delta", "id": rid, "delta": f"🔧 自我修复：{note}"}
            yield {"type": "reasoning-end", "id": rid}
            return

        # 最终报告阶段开始（PRO 生成）—— 作为一段提示文本
        if ctype == "final-stage-starting":
            yield from self._ensure_start()
            yield from self._close_text()
            tid = str(uuid.uuid4())
            yield {"type": "tool-input-start", "toolCallId": tid, "toolName": "generate_report"}
            yield {"type": "tool-input-available", "toolCallId": tid,
                   "toolName": "generate_report", "input": {"model": chunk.get("model")}}
            self._known_tools.add(tid)
            self._report_tool_id = tid
            return

        # 最终报告预览
        if ctype == "final-report":
            tid = getattr(self, "_report_tool_id", None)
            if tid:
                yield {"type": "tool-output-available", "toolCallId": tid,
                       "output": {"preview": chunk.get("content", "")[:200]}}
            return

        # 报告产物（5 件套路径）—— 自定义 data part
        if ctype == "report-artifacts":
            yield from self._close_text()
            data = {k: v for k, v in chunk.items() if k != "type"}
            yield {"type": "data-report-artifacts", "data": data}
            return

        # 阶段状态汇总
        if ctype == "stage-status":
            yield {"type": "data-stage-status", "data": chunk.get("data")}
            return

        # 流结束
        if ctype == "finish":
            yield from self._close_text()
            if self._step_open:
                yield {"type": "finish-step"}
                self._step_open = False
            yield {"type": "finish"}
            return

        # 未知类型：忽略（不破坏流）
        return
