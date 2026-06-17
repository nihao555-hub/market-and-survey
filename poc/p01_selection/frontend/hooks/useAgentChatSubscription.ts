/**
 * 订阅 hook（steering §9.3）：消费后端原生 SSE /events。
 * - EventSource 直连后端 :8001/events（绕过 Next dev 代理对 SSE 的缓冲）
 * - 后端原始 chunk → ClientChunkAdapter → ai-sdk 风格 chunk → MessageAccumulator
 * - 100ms throttle flush 到 Jotai atom（首个 chunk 立即 flush）
 */
"use client";
import { useEffect, useRef } from "react";
import { useSetAtom } from "jotai";
import {
  messagesAtomFamily,
  isStreamingAtomFamily,
  errorAtomFamily,
  artifactsAtomFamily,
} from "@/lib/atoms";
import { MessageAccumulator } from "@/lib/message-accumulator";
import { ClientChunkAdapter } from "@/lib/chunk-adapter";
import { BACKEND_BASE } from "@/lib/graphql-client";
import type { UIMessage } from "@/lib/agent-types";

export function useAgentChatSubscription(threadId: string | null) {
  const setMessages = useSetAtom(messagesAtomFamily(threadId || "__none__"));
  const setStreaming = useSetAtom(isStreamingAtomFamily(threadId || "__none__"));
  const setError = useSetAtom(errorAtomFamily(threadId || "__none__"));
  const setArtifacts = useSetAtom(artifactsAtomFamily(threadId || "__none__"));

  const accRef = useRef<MessageAccumulator | null>(null);
  const adapterRef = useRef<ClientChunkAdapter | null>(null);
  const latestRef = useRef<UIMessage | null>(null);
  const throttleRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!threadId) return;
    accRef.current = new MessageAccumulator();
    adapterRef.current = new ClientChunkAdapter();
    setStreaming(true);
    setError(null);

    const flushToAtom = () => {
      const msg = latestRef.current;
      if (!msg) return;
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === msg.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = msg;
          return next;
        }
        return [...prev, msg];
      });
    };
    const scheduleFlush = (msg: UIMessage) => {
      latestRef.current = msg;
      if (!throttleRef.current) {
        flushToAtom();
        throttleRef.current = setTimeout(() => {
          throttleRef.current = null;
          flushToAtom();
        }, 100);
      }
    };

    const handleRawChunk = (raw: any) => {
      const stdChunks = adapterRef.current!.feed(raw);
      let changed = false;
      for (const c of stdChunks) {
        if (c.type === "data-report-artifacts") {
          setArtifacts((c as any).data);
        }
        if (accRef.current!.feed(c)) changed = true;
      }
      if (changed) scheduleFlush(accRef.current!.getMessage());
    };

    // seq 去重：catch-up 和（重连后的）重放都带 seq，已处理过的直接跳过，
    // 避免 EventSource 断线重连时把整个对话从头重放一遍（表现为"又回到第一步"）。
    const seenSeq = new Set<number>();
    let maxSeq = 0;
    const handleSeqChunk = (chunk: any, seq: number | undefined) => {
      if (typeof seq === "number") {
        if (seenSeq.has(seq) || seq <= maxSeq) return; // 已见过/旧的，跳过
        seenSeq.add(seq);
        maxSeq = Math.max(maxSeq, seq);
      }
      handleRawChunk(chunk);
    };

    // EventSource → 直连后端 /events（不走 Next 代理，避免 SSE 被缓冲）
    const es = new EventSource(`${BACKEND_BASE}/events?thread_id=${encodeURIComponent(threadId)}`);

    // catch-up：重放历史 chunk（后端 event: stream-chunk，带 seq）
    es.addEventListener("stream-chunk", (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.chunk) handleSeqChunk(payload.chunk, payload.seq);
      } catch {}
    });

    // 实时事件（后端 event: agent-event，data 是顶层 event JSON）
    es.addEventListener("agent-event", (e: MessageEvent) => {
      try {
        const evt = JSON.parse(e.data);
        if (evt.type === "stream-chunk") {
          handleSeqChunk(evt.chunk, evt.seq);
        } else if (evt.type === "message-persisted") {
          if (throttleRef.current) {
            clearTimeout(throttleRef.current);
            throttleRef.current = null;
          }
          flushToAtom();
          setStreaming(false);
          es.close();
        } else if (evt.type === "stream-error") {
          setError(evt.chunk?.reason || "stream error");
          setStreaming(false);
        }
      } catch {}
    });

    es.onerror = () => {
      // 网络抖动时 EventSource 自动重连；持续失败才提示
      // 不立即报错，避免误伤短暂断连
    };

    return () => {
      es.close();
      if (throttleRef.current) clearTimeout(throttleRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);
}
