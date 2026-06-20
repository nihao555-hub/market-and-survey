/**
 * Jotai 状态层（steering §2.5：按 threadId 分 family，多会话互不干扰）。
 */
import { atom } from "jotai";
import { atomFamily } from "jotai/utils";
import type { UIMessage, ThreadSummary, ReportArtifacts, ResearchKind } from "./agent-types";

// 当前激活会话 id（null = 新建任务草稿态）
export const activeThreadIdAtom = atom<string | null>(null);

// 草稿品类（工作台 hero / 品类快捷点击后，进入澄清态等待补参；null = 工作台首页）
export const draftCategoryAtom = atom<string | null>(null);

// 草稿调研类型（从某个功能页发起时带上，澄清态提交后写入 Thread.kind）
export const draftKindAtom = atom<ResearchKind>("general");

// 当前侧边栏页面（home = 工作台首页；其余对应导航 key）
export type PageKey =
  | "home"
  | "market"
  | "trend"
  | "competitor"
  | "audience"
  | "opportunity"
  | "tasks"
  | "reports"
  | "favorites"
  | "trash"
  | "social"
  | "category"
  | "monitor"
  | "settings";
export const activePageAtom = atom<PageKey>("home");

// 输入框快捷参数（市场/定位/模型）—— 与 A2UI 表单共享，localStorage 持久化。
export interface QuickParams {
  markets: string[];
  positioning: string;
  modelChoice: "flash" | "pro";
}
const QUICK_PARAMS_KEY = "bluecompass.quickParams";
function loadQuickParams(): QuickParams {
  if (typeof window === "undefined") return { markets: ["US"], positioning: "中端", modelChoice: "flash" };
  try {
    const raw = window.localStorage.getItem(QUICK_PARAMS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return { markets: ["US"], positioning: "中端", modelChoice: "flash" };
}
const baseQuickParamsAtom = atom<QuickParams>(loadQuickParams());
export const quickParamsAtom = atom(
  (get) => get(baseQuickParamsAtom),
  (get, set, next: QuickParams | ((prev: QuickParams) => QuickParams)) => {
    const prev = get(baseQuickParamsAtom);
    const value = typeof next === "function" ? (next as (p: QuickParams) => QuickParams)(prev) : next;
    set(baseQuickParamsAtom, value);
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(QUICK_PARAMS_KEY, JSON.stringify(value));
      } catch {
        /* ignore */
      }
    }
  }
);

// 侧边栏折叠态（持久化到 localStorage）
export const sidebarCollapsedAtom = atom<boolean>(false);

// 历史任务列表（侧边栏）
export const threadsAtom = atom<ThreadSummary[]>([]);

// ── 按 threadId 切分的运行时状态 ──
export const messagesAtomFamily = atomFamily((_threadId: string) =>
  atom<UIMessage[]>([])
);

export const isStreamingAtomFamily = atomFamily((_threadId: string) =>
  atom<boolean>(false)
);

export const errorAtomFamily = atomFamily((_threadId: string) =>
  atom<string | null>(null)
);

export const usageAtomFamily = atomFamily((_threadId: string) =>
  atom<{ inputTokens: number; outputTokens: number }>({
    inputTokens: 0,
    outputTokens: 0,
  })
);

// 报告产物（5 件套）按 threadId 存
export const artifactsAtomFamily = atomFamily((_threadId: string) =>
  atom<ReportArtifacts | null>(null)
);

// 已见过的最大 seq（去重 / catch-up 衔接）
export const lastSeqAtomFamily = atomFamily((_threadId: string) => atom<number>(0));
