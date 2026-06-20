/**
 * 主编排 hook（steering §7）：发送选品任务 + 停止流 + 乐观 UI。
 */
"use client";
import { useCallback } from "react";
import { useSetAtom, useStore } from "jotai";
import { v4 as uuid } from "uuid";
import {
  messagesAtomFamily,
  isStreamingAtomFamily,
  activeThreadIdAtom,
  threadsAtom,
} from "@/lib/atoms";
import { gqlRequest } from "@/lib/graphql-client";
import {
  AGENT_SEND_EVENT,
  AGENT_STOP_EVENT,
  useListenToBrowserEvent,
} from "@/lib/browser-events";
import type { SelectionParams, UIMessage } from "@/lib/agent-types";

const SEND_MUTATION = /* GraphQL */ `
  mutation Send(
    $category: String!, $markets: [String!]!, $positioning: String!,
    $monthlyBudget: String!, $exclude: String!, $modelChoice: String!,
    $threadId: String, $title: String, $kind: String!
  ) {
    sendSelectionMessage(
      category: $category, markets: $markets, positioning: $positioning,
      monthlyBudget: $monthlyBudget, exclude: $exclude, modelChoice: $modelChoice,
      threadId: $threadId, title: $title, kind: $kind
    ) { threadId streamId status }
  }
`;

const STOP_MUTATION = /* GraphQL */ `
  mutation Stop($threadId: String!) { stopStream(threadId: $threadId) }
`;

export function useAgentChat() {
  const store = useStore();
  const setActiveThreadId = useSetAtom(activeThreadIdAtom);
  const setThreads = useSetAtom(threadsAtom);

  const sendSelection = useCallback(
    async (params: SelectionParams) => {
      const threadId = uuid();
      const title = `${params.category} · ${params.markets.join("/") || "全球"}`;
      const kind = params.kind ?? "general";

      // 乐观 UI：立即建会话 + 塞 user message（steering §7.1）
      const userText = buildUserSummary(params);
      const optimisticUser: UIMessage = {
        id: uuid(),
        role: "user",
        parts: [{ type: "text", text: userText, state: "done" }],
        status: "sent",
      };
      store.set(messagesAtomFamily(threadId), [optimisticUser]);
      store.set(isStreamingAtomFamily(threadId), true);
      setActiveThreadId(threadId);
      setThreads((prev) => [
        { id: threadId, title, activeStreamId: "pending", kind },
        ...prev,
      ]);

      try {
        await gqlRequest(SEND_MUTATION, {
          category: params.category,
          markets: params.markets,
          positioning: params.positioning,
          monthlyBudget: params.monthlyBudget,
          exclude: params.exclude,
          modelChoice: params.modelChoice,
          threadId,
          title,
          kind,
        });
      } catch (e) {
        // 失败回滚（steering §7.1）
        store.set(messagesAtomFamily(threadId), []);
        store.set(isStreamingAtomFamily(threadId), false);
        throw e;
      }
      return threadId;
    },
    [store, setActiveThreadId, setThreads]
  );

  const stopStream = useCallback(async (threadId: string) => {
    try {
      await gqlRequest(STOP_MUTATION, { threadId });
    } catch {
      /* UI 不等待，靠后端 stream-error 收尾 */
    }
  }, []);

  // BrowserEvent 总线（steering §8）：UI 各处命令式触发，不走 props
  useListenToBrowserEvent<SelectionParams>(AGENT_SEND_EVENT, (params) => {
    if (params) sendSelection(params);
  });
  useListenToBrowserEvent<{ threadId: string }>(AGENT_STOP_EVENT, (d) => {
    if (d?.threadId) stopStream(d.threadId);
  });

  return { sendSelection, stopStream };
}

function buildUserSummary(p: SelectionParams): string {
  const lines = [`品类：${p.category}`];
  if (p.markets.length) lines.push(`市场：${p.markets.join(" / ")}`);
  if (p.positioning) lines.push(`定位：${p.positioning}`);
  if (p.monthlyBudget) lines.push(`预算：${p.monthlyBudget}`);
  if (p.exclude) lines.push(`排除：${p.exclude}`);
  lines.push(`模型：${p.modelChoice === "pro" ? "Pro（高质量）" : "Flash（快速）"}`);
  return lines.join("\n");
}
