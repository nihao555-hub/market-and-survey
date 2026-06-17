"use client";
import React from "react";
import { useAtomValue, useSetAtom, useStore } from "jotai";
import { Compass } from "lucide-react";
import {
  activeThreadIdAtom,
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

const SUGGESTIONS = ["瑜伽垫", "智能插座", "户外露营装备", "宠物自动喂食器", "便携榨汁杯"];

/** 空态：居中欢迎 + 输入框 + 快捷品类 */
function EmptyState({ onPick, isLoading }: { onPick: (cat: string) => void; isLoading: boolean }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
      <div className="mb-10 flex flex-col items-center text-center">
        <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl border border-hairline bg-white shadow-sm">
          <Compass className="h-5 w-5 text-accent" strokeWidth={1.75} />
        </div>
        <h1 className="text-[28px] font-semibold tracking-tight text-ink">蓝海罗盘</h1>
        <p className="mt-2.5 max-w-sm text-[15px] leading-relaxed text-ink-subtle">
          输入一个品类，自动完成趋势、竞品、痛点、利润与 IP 风险调研，给出可决策的报告。
        </p>
      </div>
      <div className="w-full max-w-2xl">
        <PromptInputBox onSend={onPick} isLoading={isLoading} showParams />
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs text-ink-subtle">试试</span>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onPick(s)}
              className="rounded-full border border-hairline bg-white px-3 py-1.5 text-xs text-ink-muted transition-colors hover:border-hairline-strong hover:bg-surface-1 hover:text-ink"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

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
          {/* 用户消息气泡 */}
          <div className="flex justify-end">
            <div className="rounded-2xl bg-accent px-4 py-2.5 text-[15px] text-white">{category}</div>
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
          <PromptInputBox onSend={(c) => onReset()} showParams placeholder="想换个品类？在上方表单填完即可开始，或重新输入…" />
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
        const data = await gqlRequest<{ thread: { messages: any[] } | null }>(THREAD_QUERY, {
          id: threadId,
        });
        const msgs = data.thread?.messages || [];
        const ui: UIMessage[] = msgs.map((m) => ({
          id: m.id,
          role: m.role,
          parts: Array.isArray(m.parts) ? m.parts : [{ type: "text", text: String(m.parts) }],
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
    <div className="flex h-full flex-col">
      <div className="scroll-area flex-1 overflow-y-auto">
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

export function ChatView() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const [draftCategory, setDraftCategory] = React.useState<string | null>(null);
  const [sending, setSending] = React.useState(false);

  // 新建态：清掉 draft
  React.useEffect(() => {
    if (activeId === null) setDraftCategory(null);
  }, [activeId]);

  const handleStartResearch = (p: SelectionParams) => {
    setSending(true);
    // 通过 BrowserEvent 总线触发发送（steering §8）
    dispatchBrowserEvent<SelectionParams>(AGENT_SEND_EVENT, p);
    // sendSelection 内部会 setActiveThreadId → 切到会话态
    setTimeout(() => {
      setSending(false);
      setDraftCategory(null);
    }, 300);
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
  return <EmptyState onPick={(cat) => setDraftCategory(cat)} isLoading={sending} />;
}
