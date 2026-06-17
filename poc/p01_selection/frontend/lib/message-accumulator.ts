/**
 * 消息累积器（steering §1「订阅、累积、渲染」的累积环节 + §5 mid-stream 补全）。
 *
 * 把零散的 ai-sdk UIMessageChunk 累积成一条 assistant UIMessage（parts[]）。
 * 内置 mid-stream adapter 逻辑：中途接入时给残缺流补合成的 start / text-start /
 * tool-input-start，让累积不依赖订阅时机。
 */
import type { UIMessageChunk, UIMessage, UIMessagePart, ToolPart } from "./agent-types";
import { v4 as uuid } from "uuid";

export class MessageAccumulator {
  private message: UIMessage;
  private hasSeenStart = false;
  private knownTextIds = new Set<string>();
  private knownToolIds = new Set<string>();

  constructor(messageId?: string) {
    this.message = {
      id: messageId || uuid(),
      role: "assistant",
      parts: [],
      status: "streaming",
    };
  }

  getMessage(): UIMessage {
    // 返回深拷贝，避免 React 比较时引用不变
    return { ...this.message, parts: this.message.parts.map((p) => ({ ...p })) };
  }

  /** 喂一个 chunk，更新内部 message。返回是否有变化。 */
  feed(chunk: UIMessageChunk): boolean {
    // mid-stream 补全：第一个 chunk 不是 start，补一个
    if (!this.hasSeenStart) {
      this.hasSeenStart = true;
      if (chunk.type !== "start") {
        this.message.id = this.message.id || uuid();
      }
    }

    switch (chunk.type) {
      case "start":
        if (chunk.messageId) this.message.id = chunk.messageId;
        return true;

      case "start-step":
      case "finish-step":
        return false;

      case "text-start": {
        this.knownTextIds.add(chunk.id);
        this._ensureTextPart(chunk.id);
        return true;
      }
      case "text-delta": {
        if (!this.knownTextIds.has(chunk.id)) {
          this.knownTextIds.add(chunk.id);
          this._ensureTextPart(chunk.id);
        }
        const part = this._findPartById("text", chunk.id);
        if (part) {
          (part as any).text += chunk.delta;
          (part as any).state = "streaming";
        }
        return true;
      }
      case "text-end": {
        const part = this._findPartById("text", chunk.id);
        if (part) (part as any).state = "done";
        return true;
      }

      case "reasoning-start": {
        this._ensureReasoningPart(chunk.id);
        return true;
      }
      case "reasoning-delta": {
        const part = this._findPartById("reasoning", chunk.id);
        if (part) {
          (part as any).text += chunk.delta;
          (part as any).state = "streaming";
        } else {
          this._ensureReasoningPart(chunk.id);
          const p = this._findPartById("reasoning", chunk.id);
          if (p) (p as any).text += chunk.delta;
        }
        return true;
      }
      case "reasoning-end": {
        const part = this._findPartById("reasoning", chunk.id);
        if (part) (part as any).state = "done";
        return true;
      }

      case "tool-input-start": {
        this.knownToolIds.add(chunk.toolCallId);
        this._ensureToolPart(chunk.toolCallId, chunk.toolName);
        const p = this._findToolPart(chunk.toolCallId);
        if (p) p.state = "input-streaming";
        return true;
      }
      case "tool-input-available": {
        if (!this.knownToolIds.has(chunk.toolCallId)) {
          this.knownToolIds.add(chunk.toolCallId);
          this._ensureToolPart(chunk.toolCallId, chunk.toolName);
        }
        const p = this._findToolPart(chunk.toolCallId);
        if (p) {
          p.input = chunk.input;
          p.toolName = chunk.toolName || p.toolName;
          p.state = "input-available";
        }
        return true;
      }
      case "tool-output-available": {
        if (!this.knownToolIds.has(chunk.toolCallId)) {
          this.knownToolIds.add(chunk.toolCallId);
          this._ensureToolPart(chunk.toolCallId, "tool");
        }
        const p = this._findToolPart(chunk.toolCallId);
        if (p) {
          p.output = chunk.output;
          p.state = "output-available";
        }
        return true;
      }
      case "tool-output-error": {
        const p = this._findToolPart(chunk.toolCallId);
        if (p) {
          p.errorText = chunk.errorText;
          p.state = "output-error";
        }
        return true;
      }

      case "data-report-artifacts": {
        this.message.parts.push({ type: "data-report-artifacts", data: chunk.data });
        return true;
      }
      case "data-stage-status": {
        // 暂不单独渲染，忽略
        return false;
      }

      case "finish": {
        this.message.status = "sent";
        this.message.parts.forEach((p) => {
          if ("state" in p && (p as any).state === "streaming") (p as any).state = "done";
        });
        return true;
      }
      default:
        return false;
    }
  }

  // ── 内部 helpers ──
  private _ensureTextPart(id: string) {
    if (!this._findPartById("text", id)) {
      this.message.parts.push({ type: "text", text: "", state: "streaming", _id: id } as any);
    }
  }
  private _ensureReasoningPart(id: string) {
    if (!this._findPartById("reasoning", id)) {
      this.message.parts.push({ type: "reasoning", text: "", state: "streaming", _id: id } as any);
    }
  }
  private _ensureToolPart(toolCallId: string, toolName?: string) {
    if (!this._findToolPart(toolCallId)) {
      this.message.parts.push({
        type: `tool-${toolName || "tool"}`,
        toolCallId,
        toolName,
        state: "input-streaming",
      } as UIMessagePart);
    }
  }
  private _findPartById(type: string, id: string): UIMessagePart | undefined {
    return this.message.parts.find((p) => p.type === type && (p as any)._id === id);
  }
  private _findToolPart(toolCallId: string): ToolPart | undefined {
    return this.message.parts.find(
      (p) => p.type.startsWith("tool-") && (p as any).toolCallId === toolCallId
    ) as ToolPart | undefined;
  }
}
