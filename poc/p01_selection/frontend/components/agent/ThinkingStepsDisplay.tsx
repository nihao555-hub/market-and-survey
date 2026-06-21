"use client";
import React from "react";
import { ChevronDown, ChevronUp, Brain, Loader2 } from "lucide-react";
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

const zhThinkingMessage = (isStreaming: boolean, duration?: number) => {
  if (isStreaming || duration === 0) return <ShimmeringText>正在思考…</ShimmeringText>;
  if (duration === undefined) return <span>已完成思考</span>;
  return <span>已思考 {duration} 秒</span>;
};

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

  const autoExpanded = isThinking || !hasAssistantTextResponseStarted;
  const [manualOverride, setManualOverride] = React.useState<boolean | null>(null);
  const expanded = manualOverride ?? autoExpanded;

  const stepCount = parts.filter((p) => p.type.startsWith("tool-")).length;

  return (
    <Task
      open={expanded}
      onOpenChange={(o) => setManualOverride(o)}
      className="my-2 rounded-[4px] border border-[var(--gray-4)] bg-[var(--bg-transparent-lighter)] px-3 py-2"
    >
      <TaskTrigger title="">
        <div className="flex w-full cursor-pointer items-center gap-1 text-[16px] font-medium text-[var(--gray-9)] transition-colors hover:text-[var(--gray-12)]">
          {isThinking ? (
            <Loader2 className="h-4 w-4 animate-spin text-[var(--gray-9)]" />
          ) : (
            <Brain className="h-4 w-4 text-[var(--gray-9)]" />
          )}
          {isThinking ? (
            <ShimmeringText>正在分析…</ShimmeringText>
          ) : (
            <span>{stepCount > 0 ? `${stepCount} 个分析步骤` : "分析过程"}</span>
          )}
          {expanded ? (
            <ChevronUp className="ml-auto h-4 w-4 text-[var(--gray-9)]" />
          ) : (
            <ChevronDown className="ml-auto h-4 w-4 text-[var(--gray-9)]" />
          )}
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
                  className="text-[var(--gray-9)]"
                />
                <ReasoningContent className="!mt-2 rounded-[4px] border border-[var(--gray-4)] bg-[var(--bg-transparent-lighter)] p-3 text-[var(--gray-11)] text-[14px] leading-relaxed whitespace-pre-wrap">
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
