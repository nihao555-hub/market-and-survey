"use client";
import React from "react";
import { ChevronDown, ChevronUp, Brain, Loader2, Cpu, Clock, Wrench } from "lucide-react";
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

  const toolParts = parts.filter((p) => p.type.startsWith("tool-"));
  const stepCount = toolParts.length;
  const completedCount = toolParts.filter((p) => {
    const tp = p as ToolPart;
    return tp.output !== undefined || !!tp.errorText;
  }).length;
  const errorCount = toolParts.filter((p) => !!(p as ToolPart).errorText).length;

  return (
    <Task
      open={expanded}
      onOpenChange={(o) => setManualOverride(o)}
      className="my-2 overflow-hidden rounded-lg border border-[var(--gray-5)] bg-[var(--gray-1)]"
    >
      {/* Twenty CRM Summary Card header */}
      <TaskTrigger title="">
        <div className="flex w-full cursor-pointer items-center gap-3 p-3 transition-colors hover:bg-[var(--gray-3)]/50">
          <div className="flex items-center gap-2 text-sm font-medium text-[var(--gray-12)]">
            {isThinking ? (
              <Loader2 className="h-4 w-4 animate-spin text-[var(--gray-9)]" />
            ) : (
              <Brain className="h-4 w-4 text-[var(--gray-9)]" />
            )}
            {isThinking ? (
              <ShimmeringText>AI 调研进行中</ShimmeringText>
            ) : (
              <span>AI 调研运行</span>
            )}
          </div>

          {/* Twenty CRM metrics row */}
          <div className="ml-auto flex items-center gap-3">
            <div className="flex items-center gap-1 text-[11px] uppercase tracking-wider text-[var(--gray-8)]">
              <Wrench className="h-3 w-3" />
              <span>工具调用</span>
              <span className="ml-0.5 font-semibold text-[var(--gray-12)]">{stepCount}</span>
            </div>
            {stepCount > 0 && (
              <div className="flex items-center gap-1 text-[11px] text-[var(--gray-8)]">
                <Cpu className="h-3 w-3" />
                <span>{completedCount}/{stepCount}</span>
              </div>
            )}
            {errorCount > 0 && (
              <span className="rounded-[3px] bg-red-100 px-1.5 py-0.5 text-[10px] font-semibold text-red-600">
                {errorCount} 错误
              </span>
            )}
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-[var(--gray-8)]" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[var(--gray-8)]" />
            )}
          </div>
        </div>
      </TaskTrigger>
      <TaskContent>
        <div className="border-t border-[var(--gray-4)] px-3 py-2 space-y-1">
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
                  <ReasoningContent className="!mt-1 rounded-md border border-[var(--gray-4)] bg-[var(--gray-2)] p-3 text-[13px] leading-relaxed text-[var(--gray-11)] whitespace-pre-wrap">
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
        </div>
      </TaskContent>
    </Task>
  );
}
