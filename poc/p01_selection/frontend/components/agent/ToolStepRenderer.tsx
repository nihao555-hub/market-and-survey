"use client";
import React from "react";
import { ChevronRight, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { ShimmeringText } from "./ShimmeringText";
import { ToolOutputView } from "./ToolOutputView";
import { getToolDisplayMessage } from "@/lib/tool-display";
import type { ToolPart } from "@/lib/agent-types";

/**
 * 单工具调用卡片（steering §4，四态）：
 * 调用中 / 已完成无输出 / 完成有输出 / 出错
 */
export function ToolStepRenderer({
  part,
  isStreaming,
}: {
  part: ToolPart;
  isStreaming: boolean;
}) {
  const [expanded, setExpanded] = React.useState(false);
  const anyPart = part as ToolPart & { type?: string };
  const toolName = anyPart.toolName || anyPart.type?.replace(/^tool-/, "") || "tool";

  const hasOutput = part.output !== undefined && part.output !== null;
  const hasError = !!part.errorText;
  const inProgress = !hasOutput && !hasError && isStreaming;

  const label = getToolDisplayMessage(toolName, part.input, hasOutput);

  // 态 1：调用中
  if (inProgress) {
    return (
      <div className="flex items-center gap-2 py-1.5 text-sm text-ink-subtle">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
        <ShimmeringText>{label}</ShimmeringText>
        <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-ink-tertiary">
          {toolName}
        </span>
      </div>
    );
  }

  // 态 4：出错
  if (hasError) {
    return (
      <div className="py-1.5">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-2 text-sm text-danger"
        >
          <AlertCircle className="h-3.5 w-3.5" />
          <span>{label} — 执行失败</span>
          <ChevronRight className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-90")} />
        </button>
        {expanded && (
          <pre className="mt-1 overflow-x-auto rounded-md border border-danger/20 bg-red-50 p-2 font-mono text-xs text-danger">
            {part.errorText}
          </pre>
        )}
      </div>
    );
  }

  // 态 3：完成且有输出（可展开）
  if (hasOutput) {
    return (
      <div className="py-1.5">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="group flex w-full items-center gap-2 text-sm text-ink-muted hover:text-ink"
        >
          <CheckCircle2 className="h-3.5 w-3.5 text-success" />
          <span>{label}</span>
          <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-ink-tertiary opacity-0 transition-opacity group-hover:opacity-100">
            {toolName}
          </span>
          <ChevronRight className={cn("ml-auto h-3.5 w-3.5 text-ink-subtle transition-transform", expanded && "rotate-90")} />
        </button>
        {expanded && (
          <div className="mt-1.5 space-y-2 border-l border-hairline pl-3">
            {part.input !== undefined && (
              <div>
                <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink-subtle">输入</div>
                <pre className="overflow-x-auto rounded-md border border-hairline bg-surface-1 p-2 font-mono text-xs text-ink-muted">
                  {safeStringify(part.input)}
                </pre>
              </div>
            )}
            <div>
              <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink-subtle">输出</div>
              <div className="rounded-md border border-hairline bg-surface-1 p-2.5">
                <ToolOutputView output={part.output} />
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 态 2：已完成无输出（罕见）
  return (
    <div className="flex items-center gap-2 py-1.5 text-sm text-ink-subtle">
      <CheckCircle2 className="h-3.5 w-3.5 text-ink-subtle" />
      <span>{label}</span>
    </div>
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
