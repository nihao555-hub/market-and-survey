/**
 * 前端 chunk 适配器：把后端 /events 的自定义 chunk 翻译成 ai-sdk 风格 UIMessageChunk。
 * （等价于后端 ui_chunks.py，但放前端，直接消费原生 SSE /events，不经 GraphQL 订阅。）
 */
import { v4 as uuid } from "uuid";
import type { UIMessageChunk } from "./agent-types";

export class ClientChunkAdapter {
  private started = false;
  private stepOpen = false;
  private textId: string | null = null;
  private textOpen = false;
  private knownTools = new Set<string>();
  private reportToolId: string | null = null;

  private ensureStart(out: UIMessageChunk[]) {
    if (!this.started) {
      this.started = true;
      out.push({ type: "start", messageId: uuid() });
      out.push({ type: "start-step" });
      this.stepOpen = true;
    }
  }
  private closeText(out: UIMessageChunk[]) {
    if (this.textOpen && this.textId) {
      out.push({ type: "text-end", id: this.textId });
      this.textOpen = false;
      this.textId = null;
    }
  }

  /** 喂一个后端自定义 chunk，返回 0..N 个标准 chunk */
  feed(chunk: any): UIMessageChunk[] {
    const out: UIMessageChunk[] = [];
    const t = chunk?.type;

    if (t === "step-start") {
      this.ensureStart(out);
      return out;
    }
    if (t === "text-delta") {
      this.ensureStart(out);
      const delta = chunk.delta || "";
      if (!delta) return out;
      if (!this.textOpen) {
        this.textId = uuid();
        this.textOpen = true;
        out.push({ type: "text-start", id: this.textId });
      }
      out.push({ type: "text-delta", id: this.textId!, delta });
      return out;
    }
    // 流式思考过程（reasoning-start/delta/end 直接透传，前端 ThinkingStepsDisplay 渲染）
    if (t === "reasoning-start") {
      this.ensureStart(out);
      out.push({ type: "reasoning-start", id: chunk.id } as any);
      return out;
    }
    if (t === "reasoning-delta") {
      out.push({ type: "reasoning-delta", id: chunk.id, delta: chunk.delta || "" } as any);
      return out;
    }
    if (t === "reasoning-end") {
      out.push({ type: "reasoning-end", id: chunk.id } as any);
      return out;
    }
    if (t === "tool-input-start") {
      this.ensureStart(out);
      this.closeText(out);
      const tid = chunk.id || uuid();
      const name = chunk.name || "tool";
      this.knownTools.add(tid);
      out.push({ type: "tool-input-start", toolCallId: tid, toolName: name });
      if (chunk.args != null) {
        out.push({ type: "tool-input-available", toolCallId: tid, toolName: name, input: chunk.args });
      }
      return out;
    }
    if (t === "tool-output") {
      const tid = chunk.id || uuid();
      const name = chunk.name || "tool";
      if (!this.knownTools.has(tid)) {
        out.push({ type: "tool-input-start", toolCallId: tid, toolName: name });
        this.knownTools.add(tid);
      }
      out.push({ type: "tool-output-available", toolCallId: tid, output: chunk.output ?? chunk.preview });
      return out;
    }
    if (t === "reasoning") {
      this.ensureStart(out);
      this.closeText(out);
      const rid = chunk.id || uuid();
      const text = chunk.text || "";
      if (text) {
        out.push({ type: "reasoning-start", id: rid } as any);
        out.push({ type: "reasoning-delta", id: rid, delta: text } as any);
        out.push({ type: "reasoning-end", id: rid } as any);
      }
      return out;
    }
    if (t === "dsml-detected") return out;
    if (t === "reflection") {
      this.ensureStart(out);
      this.closeText(out);
      const rid = uuid();
      const note = chunk.note || "检测到失败，正在换策略重试…";
      out.push({ type: "reasoning-start", id: rid } as any);
      out.push({ type: "reasoning-delta", id: rid, delta: `🔧 自我修复：${note}` } as any);
      out.push({ type: "reasoning-end", id: rid } as any);
      return out;
    }
    if (t === "final-stage-starting") {
      this.ensureStart(out);
      this.closeText(out);
      const tid = uuid();
      out.push({ type: "tool-input-start", toolCallId: tid, toolName: "generate_report" });
      out.push({ type: "tool-input-available", toolCallId: tid, toolName: "generate_report", input: { model: chunk.model } });
      this.knownTools.add(tid);
      this.reportToolId = tid;
      return out;
    }
    if (t === "final-report") {
      if (this.reportToolId) {
        out.push({ type: "tool-output-available", toolCallId: this.reportToolId, output: { preview: (chunk.content || "").slice(0, 200) } });
      }
      return out;
    }
    if (t === "report-artifacts") {
      this.closeText(out);
      const { type, ...data } = chunk;
      out.push({ type: "data-report-artifacts", data });
      return out;
    }
    if (t === "finish") {
      this.closeText(out);
      if (this.stepOpen) {
        out.push({ type: "finish-step" });
        this.stepOpen = false;
      }
      out.push({ type: "finish" });
      return out;
    }
    return out;
  }
}
