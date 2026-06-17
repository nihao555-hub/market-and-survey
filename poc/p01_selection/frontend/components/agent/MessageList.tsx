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
import { AlertTriangle, Compass } from "lucide-react";
import type { UIMessage, ReportArtifacts as ReportArtifactsData } from "@/lib/agent-types";

/** 单条消息渲染（steering §9.5 主消息渲染入口） */
function MessageBubble({ message, isStreaming }: { message: UIMessage; isStreaming: boolean }) {
  const isUser = message.role === "user";
  if (isUser) {
    return (
      <Message from="user">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-[15px] leading-relaxed text-white">
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
      <div className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg border border-hairline bg-white">
        <Compass className="h-4 w-4 text-brand" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
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
          return null;
        })}
      </div>
    </Message>
  );
}

export function MessageList({ threadId }: { threadId: string }) {
  const messages = useAtomValue(messagesAtomFamily(threadId));
  const isStreaming = useAtomValue(isStreamingAtomFamily(threadId));
  const error = useAtomValue(errorAtomFamily(threadId));

  return (
    <Conversation className="h-full">
      <ConversationContent className="mx-auto w-full max-w-3xl gap-6 px-4 py-8">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} isStreaming={isStreaming} />
        ))}
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}
