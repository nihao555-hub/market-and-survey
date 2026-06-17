"use client";
import React from "react";
import { useAtomValue, useSetAtom, useStore, useAtom } from "jotai";
import { ArrowLeft } from "lucide-react";
import {
  activeThreadIdAtom,
  draftCategoryAtom,
  isStreamingAtomFamily,
  messagesAtomFamily,
} from "@/lib/atoms";
import { useAgentChatSubscription } from "@/hooks/useAgentChatSubscription";
import { dispatchBrowserEvent, AGENT_SEND_EVENT, AGENT_STOP_EVENT } from "@/lib/browser-events";
import { gqlRequest } from "@/lib/graphql-client";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { ClarifyForm } from "@/components/agent/ClarifyForm";
import { MessageList } from "@/components/agent/MessageList";
import type { SelectionParams, UIMessage } from "@/lib/agent-types";

const THREAD_QUERY = /* GraphQL */ `
  query Thread($id: String!) {
    thread(id: $id) {
      id title activeStreamId
      messages { id role parts createdAt }
    }
  }
`;

/** 澄清态：用户已输入品类，显示 A2UI 表单等待补充参数 */
function ClarifyState({
  category,
  onSubmit,
  onReset,
}: {
  category: string;
  onSubmit: (p: SelectionParams) => void;
  onReset: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="scroll-area flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl space-y-4 px-4 py-6">
          <button
            onClick={onReset}
            className="inline-flex items-center gap-1.5 text-xs text-ink-subtle transition-colors hover:text-ink"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            返回工作台
          </button>
          {/* 用户消息气泡 */}
          <div className="flex justify-end">
            <div className="rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-[15px] text-white">
              {category}
            </div>
          </div>
          {/* A2UI 表单 */}
          <div className="flex justify-start">
            <div className="w-full max-w-xl">
              <ClarifyForm category={category} onSubmit={onSubmit} />
            </div>
          </div>
        </div>
      </div>
      <div className="border-t border-hairline bg-white px-4 py-3">
        <div className="mx-auto w-full max-w-3xl">
          <PromptInputBox
            onSend={() => onReset()}
            showParams
            placeholder="想换个品类？在上方表单填完即可开始，或重新输入…"
          />
        </div>
      </div>
    </div>
  );
}

/** 会话态：消息流 + 底部输入框 */
function ActiveThread({ threadId }: { threadId: string }) {
  useAgentChatSubscription(threadId);
  const isStreaming = useAtomValue(isStreamingAtomFamily(threadId));
  const store = useStore();
  const setMessages = useSetAtom(messagesAtomFamily(threadId));

  React.useEffect(() => {
    const cur = store.get(messagesAtomFamily(threadId));
    if (cur.length > 0) return;
    (async () => {
      try {
        const data = await gqlRequest<{ thread: { messages: Array<{ id: string; role: string; parts: unknown }> } | null }>(
          THREAD_QUERY,
          { id: threadId }
        );
        const msgs = data.thread?.messages || [];
        const ui: UIMessage[] = msgs.map((m) => ({
          id: m.id,
          role: m.role as UIMessage["role"],
          parts: Array.isArray(m.parts)
            ? (m.parts as UIMessage["parts"])
            : [{ type: "text", text: String(m.parts) }],
          status: "sent",
        }));
        if (ui.length) setMessages(ui);
      } catch {
        /* ignore */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="min-h-0 flex-1">
        <MessageList threadId={threadId} />
      </div>
      <div className="border-t border-hairline bg-white px-4 py-3">
        <div className="mx-auto w-full max-w-3xl">
          <PromptInputBox
            isLoading={isStreaming}
            placeholder="调研进行中…"
            onStop={() => dispatchBrowserEvent(AGENT_STOP_EVENT, { threadId })}
          />
        </div>
      </div>
    </div>
  );
}

/** 对话区：会话态 / 澄清态（工作台首页由 WorkspaceHome 承载） */
export function ChatView() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const [draftCategory, setDraftCategory] = useAtom(draftCategoryAtom);

  const handleStartResearch = (p: SelectionParams) => {
    // 通过 BrowserEvent 总线触发发送（steering §8）；
    // sendSelection 内部会 setActiveThreadId → 切到会话态
    dispatchBrowserEvent<SelectionParams>(AGENT_SEND_EVENT, p);
    setTimeout(() => setDraftCategory(null), 300);
  };

  if (activeId) {
    return <ActiveThread threadId={activeId} />;
  }
  if (draftCategory) {
    return (
      <ClarifyState
        category={draftCategory}
        onSubmit={handleStartResearch}
        onReset={() => setDraftCategory(null)}
      />
    );
  }
  return null;
}
