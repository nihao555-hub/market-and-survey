/**
 * 思考步骤分组（steering §3.2）：把相邻的 reasoning/tool part 攒成一组，
 * 普通 text part 出现就 flush 当前组。
 */
import type { UIMessagePart } from "./agent-types";

export type RenderItem =
  | { type: "thinking-steps"; parts: UIMessagePart[] }
  | { type: "part"; part: UIMessagePart };

function isThinkingStepPart(part: UIMessagePart): boolean {
  return part.type === "reasoning" || part.type.startsWith("tool-");
}

export function groupContiguousThinkingStepParts(parts: UIMessagePart[]): RenderItem[] {
  const items: RenderItem[] = [];
  let buffer: UIMessagePart[] = [];

  const flush = () => {
    if (buffer.length) {
      items.push({ type: "thinking-steps", parts: buffer });
      buffer = [];
    }
  };

  for (const part of parts) {
    if (isThinkingStepPart(part)) {
      buffer.push(part);
    } else {
      flush();
      items.push({ type: "part", part });
    }
  }
  flush();
  return items;
}

/** 后续 renderItems 是否已有非空文本（决定思考区是否折叠，steering §3.4） */
export function hasTextAfter(items: RenderItem[], index: number): boolean {
  for (let i = index + 1; i < items.length; i++) {
    const it = items[i];
    if (it.type === "part" && it.part.type === "text") {
      const t = (it.part as any).text;
      if (t && t.trim()) return true;
    }
  }
  return false;
}

export function isThinkingStepActive(
  part: UIMessagePart,
  isLastMessageStreaming: boolean
): boolean {
  if (part.type === "reasoning") return (part as any).state === "streaming";
  // tool：整体仍流式 + 尚无 output 也无 errorText
  const p = part as any;
  return isLastMessageStreaming && !p.output && !p.errorText;
}
