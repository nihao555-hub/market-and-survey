"use client";
import React from "react";
import { ChevronDown, Brain, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ShimmeringText } from "./ShimmeringText";
import { ToolStepRenderer } from "./ToolStepRenderer";
import { isThinkingStepActive } from "@/lib/thinking-steps";
import type { UIMessagePart, ToolPart } from "@/lib/agent-types";

/**
 * 思考步骤聚合区（steering §3）：可折叠，流结束 + 答案已开始 → 自动折叠为"X steps"。
 */
export function ThinkingStepsDisplay({
  parts,
  isLastMessageStreaming,
  hasAssistantTextResponseStarted,
}: {
  parts: UIMessagePart[];
  isLastMessageStreaming: boolean;
  hasAssistantTextResponseStarted: boolean;
}) {
  const isThinking = parts.some((p) => isThinkingStepActive(p, isLastMessageStreaming));

  // 自动展开/折叠规则（steering §3.4）
  const autoExpanded = isThinking || !hasAssistantTextResponseStarted;
  const [manualOverride, setManualOverride] = React.useState<boolean | null>(null);
  const expanded = manualOverride ?? autoExpanded;

  const stepCount = parts.filter((p) => p.type.startsWith("tool-")).length;

  return (
    <div className="my-2 overflow-hidden rounded-lg border border-hairline bg-surface-1">
      <button
        onClick={() => setManualOverride(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-sm text-ink-muted transition-colors hover:bg-surface-2"
      >
        {isThinking ? (
          <Loader2 className="h-4 w-4 animate-spin text-accent" />
        ) : (
          <Brain className="h-4 w-4 text-ink-subtle" />
        )}
        {isThinking ? (
          <ShimmeringText>正在分析…</ShimmeringText>
        ) : (
          <span>{stepCount > 0 ? `${stepCount} 个分析步骤` : "分析过程"}</span>
        )}
        <ChevronDown
          className={cn("ml-auto h-4 w-4 text-ink-subtle transition-transform", expanded && "rotate-180")}
        />
      </button>
      {expanded && (
        <div className="space-y-0.5 border-t border-hairline px-3 py-2">
          {parts.map((part, i) => {
            if (part.type === "reasoning") {
              return (
                <div key={i} className="py-1 text-sm italic text-ink-subtle">
                  {(part as any).text}
                </div>
              );
            }
            if (part.type.startsWith("tool-")) {
              return (
                <ToolStepRenderer
                  key={i}
                  part={part as ToolPart}
                  isStreaming={isLastMessageStreaming}
                />
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}
