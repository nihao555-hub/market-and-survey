"use client";
import React from "react";
import { useAtomValue } from "jotai";
import {
  messagesAtomFamily,
  isStreamingAtomFamily,
  errorAtomFamily,
} from "@/lib/atoms";
import {
  groupContiguousThinkingStepParts,
  hasTextAfter,
} from "@/lib/thinking-steps";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message } from "@/components/ai-elements/message";
import { ThinkingStepsDisplay } from "./ThinkingStepsDisplay";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ReportArtifacts } from "./ReportArtifacts";
import { AlertTriangle, Compass, Loader2 } from "lucide-react";
import type { UIMessage, ReportArtifacts as ReportArtifactsData } from "@/lib/agent-types";
import { AgentChart, chartDataToOption, type ChartData } from "@/components/charts/AgentChart";

function MessageBubble({ message, isStreaming }: { message: UIMessage; isStreaming: boolean }) {
  const isUser = message.role === "user";
  if (isUser) {
    return (
      <Message from="user">
        {/* Twenty CRM: user messages right-aligned with bg-tertiary (#f1f1f1), rounded-sm (4px) */}
        <div className="max-w-[80%] whitespace-pre-wrap rounded-[4px] bg-[var(--gray-4)] px-4 py-2.5 text-[15px] leading-relaxed text-[var(--gray-11)]">
          {message.parts
            .filter((p) => p.type === "text")
            .map((p, i) => (
              <div key={i}>{(p as { text?: string }).text}</div>
            ))}
        </div>
      </Message>
    );
  }

  const renderItems = groupContiguousThinkingStepParts(message.parts);
  const isLastStreaming = isStreaming && message.status === "streaming";

  return (
    <Message from="assistant" className="max-w-full">
      {/* Twenty CRM: assistant avatar — minimal icon container */}
      <div className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)]">
        <Compass className="h-4 w-4 text-[var(--gray-11)]" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1 space-y-2">
        {renderItems.map((item, i) => {
          if (item.type === "thinking-steps") {
            return (
              <ThinkingStepsDisplay
                key={i}
                parts={item.parts}
                isLastMessageStreaming={isLastStreaming}
                hasAssistantTextResponseStarted={hasTextAfter(renderItems, i)}
              />
            );
          }
          const part = item.part;
          if (part.type === "text") {
            return <MarkdownRenderer key={i} text={(part as { text?: string }).text || ""} />;
          }
          if (part.type === "data-report-artifacts") {
            return (
              <ReportArtifacts
                key={i}
                artifacts={(part as unknown as { data: ReportArtifactsData }).data}
              />
            );
          }
          if (part.type === "data-chart") {
            const chartData = (part as unknown as { data: ChartData }).data;
            if (chartData && chartData.series) {
              return <AgentChart key={i} option={chartDataToOption(chartData)} />;
            }
          }
          return null;
        })}
      </div>
    </Message>
  );
}

/* ─── ThinkingIndicator: shown when streaming starts but no content yet ─── */
function ThinkingIndicator() {
  return (
    <Message from="assistant" className="max-w-full">
      <div className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)]">
        <Compass className="h-4 w-4 text-[var(--gray-11)]" strokeWidth={1.75} />
      </div>
      <div className="flex items-center gap-2 py-1">
        <Loader2 className="h-4 w-4 animate-spin text-[var(--gray-8)]" />
        <span className="text-[13px] text-[var(--gray-9)]">正在思考中…</span>
      </div>
    </Message>
  );
}

export function MessageList({ threadId }: { threadId: string }) {
  const messages = useAtomValue(messagesAtomFamily(threadId));
  const isStreaming = useAtomValue(isStreamingAtomFamily(threadId));
  const error = useAtomValue(errorAtomFamily(threadId));

  const hasContent = messages.some(
    (m) => m.role === "assistant" && m.parts.some((p) => p.type === "text" && (p as { text?: string }).text)
  );
  const showThinking = isStreaming && !hasContent;

  return (
    <Conversation className="h-full">
      {/* Twenty CRM: message list padding spacing[4]=16px, gap spacing[2]=8px */}
      <ConversationContent className="mx-auto w-full max-w-3xl gap-2 px-4 py-4">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} isStreaming={isStreaming} />
        ))}
        {showThinking && <ThinkingIndicator />}
        {error && (
          <div className="flex items-center gap-2 rounded-[4px] border border-red-200 bg-red-50 px-3 py-2 text-[14px] text-red-700">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}
