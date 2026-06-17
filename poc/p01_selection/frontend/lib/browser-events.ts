/**
 * 自定义 BrowserEvent 总线（steering §8）。
 * UI 各处命令式触发"发送/停止"，不走 props 链路。
 */
import { useEffect } from "react";

export const AGENT_SEND_EVENT = "agent:send-selection";
export const AGENT_STOP_EVENT = "agent:stop-stream";

export function dispatchBrowserEvent<T = unknown>(name: string, detail?: T) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(name, { detail }));
}

/** 监听 BrowserEvent（自动注册/卸载） */
export function useListenToBrowserEvent<T = unknown>(
  name: string,
  onEvent: (detail: T) => void
) {
  useEffect(() => {
    const handler = (e: Event) => onEvent((e as CustomEvent).detail as T);
    window.addEventListener(name, handler);
    return () => window.removeEventListener(name, handler);
  }, [name, onEvent]);
}
