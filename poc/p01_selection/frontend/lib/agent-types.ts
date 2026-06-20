/**
 * 前后端共用的类型契约（steering §2.2：event 用 JSON scalar，类型靠 TS 共享）。
 * 后端 ui_chunks.py 适配器 publish 的 chunk 就是这套 ai-sdk UIMessageChunk 子集。
 */

// ── ai-sdk UIMessageChunk 子集（后端适配器产出这些） ──
export type UIMessageChunk =
  | { type: "start"; messageId?: string }
  | { type: "start-step" }
  | { type: "finish-step" }
  | { type: "finish" }
  | { type: "text-start"; id: string }
  | { type: "text-delta"; id: string; delta: string }
  | { type: "text-end"; id: string }
  | { type: "reasoning-start"; id: string }
  | { type: "reasoning-delta"; id: string; delta: string }
  | { type: "reasoning-end"; id: string }
  | { type: "tool-input-start"; toolCallId: string; toolName: string }
  | { type: "tool-input-available"; toolCallId: string; toolName: string; input: unknown }
  | { type: "tool-output-available"; toolCallId: string; output: unknown }
  | { type: "tool-output-error"; toolCallId: string; errorText: string }
  | { type: "data-report-artifacts"; data: ReportArtifacts }
  | { type: "data-stage-status"; data: unknown };

// ── 订阅层包裹的事件（后端 GraphQL subscription payload.event） ──
export type AgentEvent =
  | { type: "stream-chunk"; chunk: UIMessageChunk; seq: number }
  | { type: "message-persisted"; messageId: string; report_chars?: number }
  | { type: "stream-error"; chunk: { reason: string } }
  | { type: "start"; messageId: string };

// ── 报告产物（data-report-artifacts chunk 的 payload） ──
export interface ReportArtifacts {
  merchant_md?: string;
  full_md?: string;
  one_pager_md?: string;
  detail_md?: string;
  pdf?: string | null;
  pdf_error?: string | null;
  _primary?: string;
}

// ── UIMessage / UIMessagePart（同构模型，DB 和实时流共用，steering §6） ──
export type UIMessagePart =
  | { type: "text"; text: string; state?: "streaming" | "done" }
  | { type: "reasoning"; text: string; state?: "streaming" | "done" }
  | ({ type: `tool-${string}` } & ToolPart)
  | { type: "data-report-artifacts"; data: ReportArtifacts }
  | { type: string; [k: string]: unknown };

export interface ToolPart {
  toolCallId: string;
  toolName?: string;
  state?: "input-streaming" | "input-available" | "output-available" | "output-error";
  input?: unknown;
  output?: unknown;
  errorText?: string;
}

export interface UIMessage {
  id: string;
  role: "user" | "assistant" | "system";
  parts: UIMessagePart[];
  status?: "queued" | "sent" | "streaming";
  createdAt?: string;
}

// ── 调研类型（5 个功能页 + 工作台通用入口）：后端 Thread.kind ──
export type ResearchKind =
  | "market"        // 市场调研
  | "trend"         // 趋势探索
  | "competitor"    // 竞品分析
  | "audience"      // 受众洞察
  | "opportunity"   // 机会挖掘
  | "general";      // 工作台通用

// ── 选品任务参数（输入框「参数设置」→ 后端字段） ──
export interface SelectionParams {
  category: string;       // 品类关键词，如 "瑜伽垫"
  markets: string[];      // 目标市场，如 ["US"]
  positioning: string;    // 商家定位：中端 / 高端 / 低价
  monthlyBudget: string;  // 月度预算
  exclude: string;        // 排除大牌
  modelChoice: "flash" | "pro";  // → 后端 model_choice
  kind?: ResearchKind;    // 调研类型 → 后端打标签，供各功能页分类
}

// ── A2UI 澄清表单（Agent 在流程中向用户索取结构化输入） ──
export interface ClarifyFormData {
  category: string;              // 用户已输入的品类（预填）
  markets?: string[];            // 提交后写回
  positioning?: string;
  monthlyBudget?: string;
  exclude?: string;
  modelChoice?: "flash" | "pro";
  submitted?: boolean;           // 提交后置 true，表单变只读摘要
}

// ── 历史任务（侧边栏） ──
export interface ThreadSummary {
  id: string;
  title: string;
  updatedAt?: string;
  activeStreamId?: string | null;
  isFavorite?: boolean;
  kind?: ResearchKind;
}
