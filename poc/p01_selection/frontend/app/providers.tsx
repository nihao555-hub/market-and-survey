"use client";
import React from "react";
import { Provider as JotaiProvider } from "jotai";
import { useAgentChat } from "@/hooks/useAgentChat";

/** 挂载主编排 hook，激活 BrowserEvent 监听（steering §8 / §9.7 纯副作用组件） */
function AgentChatEffect() {
  useAgentChat();
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <JotaiProvider>
      <AgentChatEffect />
      {children}
    </JotaiProvider>
  );
}
