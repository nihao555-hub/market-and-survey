"use client";
import React from "react";
import { ChevronDown, Brain, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Task, TaskContent, TaskTrigger } from "@/components/ai-elements/task";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import { ShimmeringText } from "./ShimmeringText";
import { ToolStepRenderer } from "./ToolStepRenderer";
import { isThinkingStepActive } from "@/lib/thinking-steps";
import type { UIMessagePart, ToolPart } from "@/lib/agent-types";

/** reasoning 折叠的中文文案 */
const zhThinkingMessage = (isStreaming: boolean, duration?: number) => {
  if (isStreaming || duration === 0) return <ShimmeringText>正在思考…</ShimmeringText>;
  if (duration === undefined) return <span>已完成思考</span>;
  return <span>已思考 {duration} 秒</span>;
};

/**
 * 思考步骤聚合区（steering §3）：用 ai-elements 的 Task 作为「任务树」外壳，
 * 内部 reasoning 用标准 Reasoning 折叠、工具用 ToolStepRenderer 折叠卡片。
 * 流结束 + 答案已开始 → 自动折叠为「X 个分析步骤」。
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
    <Task
      open={expanded}
      onOpenChange={(o) => setManualOverride(o)}
      className="my-2 rounded-lg border border-hairline bg-surface-1 px-3 py-2"
    >
      <TaskTrigger title="">
        <div className="flex w-full cursor-pointer items-center gap-2 text-sm text-ink-muted transition-colors hover:text-ink">
          {isThinking ? (
            <Loader2 className="h-4 w-4 text-brand animate-spin" />
          ) : (
            <Brain className="h-4 w-4 text-ink-subtle" />
          )}
          {isThinking ? (
            <ShimmeringText>正在分析…</ShimmeringText>
          ) : (
            <span>{stepCount > 0 ? `${stepCount} 个分析步骤` : "分析过程"}</span>
          )}
          <ChevronDown
            className={cn(
              "ml-auto h-4 w-4 text-ink-subtle transition-transform",
              expanded && "rotate-180"
            )}
          />
        </div>
      </TaskTrigger>
      <TaskContent>
        {parts.map((part, i) => {
          if (part.type === "reasoning") {
            const text = (part as { text?: string }).text || "";
            const streaming = (part as { state?: string }).state === "streaming";
            if (!text) return null;
            return (
              <Reasoning
                key={i}
                className="mb-0"
                isStreaming={streaming}
                defaultOpen={streaming}
              >
                <ReasoningTrigger
                  getThinkingMessage={zhThinkingMessage}
                  className="text-ink-subtle"
                />
                <ReasoningContent className="!mt-2 text-ink-subtle">
                  {text}
                </ReasoningContent>
              </Reasoning>
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
      </TaskContent>
    </Task>
  );
}
