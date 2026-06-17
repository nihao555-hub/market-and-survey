"use client";
import React from "react";
import { ChevronDown, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tool, ToolContent } from "@/components/ai-elements/tool";
import { CollapsibleTrigger } from "@/components/ui/collapsible";
import { ShimmeringText } from "./ShimmeringText";
import { ToolOutputView } from "./ToolOutputView";
import { getToolDisplayMessage } from "@/lib/tool-display";
import type { ToolPart } from "@/lib/agent-types";

/**
 * 单工具调用（steering §4）：基于 ai-elements 的 Tool 折叠外壳标准化呈现，
 * 内部保留结构化的 ToolOutputView（商品卡片 / 证据链接 / key-value 树），
 * 不再退化成原始 JSON <pre>。
 *
 * 四态：调用中（行内 shimmer）/ 完成有输出（可展开）/ 完成无输出 / 出错（可展开）。
 */
export function ToolStepRenderer({
  part,
  isStreaming,
}: {
  part: ToolPart;
  isStreaming: boolean;
}) {
  const anyPart = part as ToolPart & { type?: string };
  const toolName = anyPart.toolName || anyPart.type?.replace(/^tool-/, "") || "tool";

  const hasOutput = part.output !== undefined && part.output !== null;
  const hasError = !!part.errorText;
  const inProgress = !hasOutput && !hasError && isStreaming;

  const label = getToolDisplayMessage(toolName, part.input, hasOutput);

  // 态 1：调用中（行内 shimmer，不折叠）
  if (inProgress) {
    return (
      <div className="flex items-center gap-2 py-1 text-sm text-ink-subtle">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-brand" />
        <ShimmeringText>{label}</ShimmeringText>
        <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-ink-tertiary">
          {toolName}
        </code>
      </div>
    );
  }

  const hasBody = hasError || hasOutput || part.input !== undefined;

  // 态 2：完成无输出（罕见）→ 单行
  if (!hasBody) {
    return (
      <div className="flex items-center gap-2 py-1 text-sm text-ink-subtle">
        <CheckCircle2 className="h-3.5 w-3.5 text-ink-subtle" />
        <span>{label}</span>
      </div>
    );
  }

  // 态 3/4：完成有输出 / 出错 → 折叠卡片
  return (
    <Tool className="mb-1.5 border-hairline bg-white shadow-none">
      <CollapsibleTrigger className="group/tool flex w-full items-center gap-2 p-2.5 text-left text-sm">
        {hasError ? (
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-danger" />
        ) : (
          <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-success" />
        )}
        <span
          className={cn(
            "min-w-0 flex-1 truncate",
            hasError ? "text-danger" : "text-ink-muted"
          )}
        >
          {label}
        </span>
        <span
          className={cn(
            "flex-shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium",
            hasError
              ? "border-danger/30 bg-danger/10 text-danger"
              : "border-success/30 bg-success/10 text-success"
          )}
        >
          {hasError ? "失败" : "完成"}
        </span>
        <ChevronDown className="h-4 w-4 flex-shrink-0 text-ink-subtle transition-transform group-data-[state=open]/tool:rotate-180" />
      </CollapsibleTrigger>
      <ToolContent className="space-y-3 border-t border-hairline p-3">
        {part.input !== undefined && (
          <div>
            <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink-subtle">
              输入
            </div>
            <pre className="overflow-x-auto rounded-md border border-hairline bg-surface-1 p-2 font-mono text-xs text-ink-muted">
              {safeStringify(part.input)}
            </pre>
          </div>
        )}
        {hasError && (
          <div>
            <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-danger">
              错误
            </div>
            <pre className="overflow-x-auto rounded-md border border-danger/20 bg-danger/5 p-2 font-mono text-xs text-danger">
              {part.errorText}
            </pre>
          </div>
        )}
        {hasOutput && (
          <div>
            <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink-subtle">
              输出
            </div>
            <div className="rounded-md border border-hairline bg-surface-1 p-2.5">
              <ToolOutputView output={part.output} />
            </div>
          </div>
        )}
      </ToolContent>
    </Tool>
  );
}

function safeStringify(v: unknown): string {
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}
