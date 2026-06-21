"use client";
import React from "react";
import { useAtomValue, useSetAtom, useStore, useAtom } from "jotai";
import { ArrowLeft } from "lucide-react";
import {
  activeThreadIdAtom,
  draftCategoryAtom,
  draftKindAtom,
  isStreamingAtomFamily,
  messagesAtomFamily,
  errorAtomFamily,
} from "@/lib/atoms";
import { useAgentChatSubscription } from "@/hooks/useAgentChatSubscription";
import { dispatchBrowserEvent, AGENT_SEND_EVENT, AGENT_STOP_EVENT } from "@/lib/browser-events";
import { gqlRequest } from "@/lib/graphql-client";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { ClarifyForm } from "@/components/agent/ClarifyForm";
import { MessageList } from "@/components/agent/MessageList";
import type { SelectionParams, UIMessage, ResearchKind } from "@/lib/agent-types";

const THREAD_QUERY = /* GraphQL */ `
  query Thread($id: String!) {
    thread(id: $id) {
      id title activeStreamId
      messages { id role parts createdAt }
    }
  }
`;

function ClarifyState({
  category,
  kind,
  onSubmit,
  onReset,
}: {
  category: string;
  kind: ResearchKind;
  onSubmit: (p: SelectionParams) => void;
  onReset: () => void;
}) {
  return (
    <div className="flex h-full flex-col bg-[var(--gray-1)]">
      <div className="scroll-area flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl space-y-4 px-4 py-6">
          <button
            onClick={onReset}
            className="inline-flex items-center gap-1.5 text-[12px] text-[var(--gray-9)] transition-colors hover:text-[var(--gray-12)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            返回工作台
          </button>
          {/* User message bubble — Twenty style: right-aligned, bg-tertiary */}
          <div className="flex justify-end">
            <div className="rounded-[4px] bg-[var(--gray-4)] px-4 py-2.5 text-[15px] text-[var(--gray-11)]">
              {category}
            </div>
          </div>
          <div className="flex justify-start">
            <div className="w-full max-w-xl">
              <ClarifyForm category={category} kind={kind} onSubmit={onSubmit} />
            </div>
          </div>
        </div>
      </div>
      <div className="border-t border-[var(--gray-5)] bg-[var(--gray-1)] px-4 py-3">
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

function ActiveThread({ threadId }: { threadId: string }) {
  useAgentChatSubscription(threadId);
  const isStreaming = useAtomValue(isStreamingAtomFamily(threadId));
  const error = useAtomValue(errorAtomFamily(threadId));
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
    <div className="flex h-full flex-col bg-[var(--gray-1)]">
      <div className="min-h-0 flex-1">
        <MessageList threadId={threadId} />
        {error && (
          <div className="mx-auto max-w-3xl px-4 py-3">
            <div className="rounded-[4px] border border-red-200 bg-red-50 px-4 py-3 text-[14px] text-red-700">
              {error}
              <button
                onClick={() => window.location.reload()}
                className="ml-2 underline hover:text-red-900"
              >刷新重试</button>
            </div>
          </div>
        )}
      </div>
      <div className="border-t border-[var(--gray-5)] bg-[var(--gray-1)] px-4 py-3">
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

export function ChatView() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const [draftCategory, setDraftCategory] = useAtom(draftCategoryAtom);
  const [draftKind, setDraftKind] = useAtom(draftKindAtom);

  const handleStartResearch = (p: SelectionParams) => {
    dispatchBrowserEvent<SelectionParams>(AGENT_SEND_EVENT, p);
    setTimeout(() => {
      setDraftCategory(null);
      setDraftKind("general");
    }, 300);
  };

  const reset = () => {
    setDraftCategory(null);
    setDraftKind("general");
  };

  if (activeId) {
    return <ActiveThread threadId={activeId} />;
  }
  if (draftCategory) {
    return (
      <ClarifyState
        category={draftCategory}
        kind={draftKind}
        onSubmit={handleStartResearch}
        onReset={reset}
      />
    );
  }
  return null;
}
