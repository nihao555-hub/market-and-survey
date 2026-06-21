"use client";
import React from "react";
import { ChevronDown, ChevronUp, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tool, ToolContent } from "@/components/ai-elements/tool";
import { CollapsibleTrigger } from "@/components/ui/collapsible";
import { ShimmeringText } from "./ShimmeringText";
import { ToolOutputView } from "./ToolOutputView";
import { getToolDisplayMessage } from "@/lib/tool-display";
import type { ToolPart } from "@/lib/agent-types";

type TabType = "output" | "input";

export function ToolStepRenderer({
  part,
  isStreaming,
}: {
  part: ToolPart;
  isStreaming: boolean;
}) {
  const [activeTab, setActiveTab] = React.useState<TabType>("output");
  const anyPart = part as ToolPart & { type?: string };
  const toolName = anyPart.toolName || anyPart.type?.replace(/^tool-/, "") || "tool";

  const hasOutput = part.output !== undefined && part.output !== null;
  const hasError = !!part.errorText;
  const inProgress = !hasOutput && !hasError && isStreaming;
  const hasInput = part.input !== undefined;

  const label = getToolDisplayMessage(toolName, part.input, hasOutput);

  const statusColor = hasError ? "text-red-500" : "text-emerald-500";
  const StatusIcon = hasError ? AlertCircle : CheckCircle2;

  if (inProgress) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-md px-1 py-1.5 text-[14px] text-[var(--gray-9)] transition-colors hover:bg-[var(--gray-3)]/30">
        <div className="flex min-w-0 items-center gap-2">
          <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin" />
          <ShimmeringText>{label}</ShimmeringText>
        </div>
        <span className="flex-shrink-0 rounded-[3px] bg-[var(--gray-3)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--gray-8)]">
          {toolName}
        </span>
      </div>
    );
  }

  const isExpandable = hasError || hasOutput || hasInput;

  if (!isExpandable) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-md px-1 py-1.5 text-[14px] text-[var(--gray-9)]">
        <div className="flex min-w-0 items-center gap-2">
          <StatusIcon className={cn("h-3.5 w-3.5 flex-shrink-0", statusColor)} />
          <span className="truncate">{label}</span>
        </div>
        <span className="flex-shrink-0 rounded-[3px] bg-[var(--gray-3)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--gray-8)]">
          {toolName}
        </span>
      </div>
    );
  }

  return (
    <Tool className="mb-1 rounded-md border-[var(--gray-4)] bg-transparent shadow-none">
      <CollapsibleTrigger className="group/tool flex w-full items-center gap-2 rounded-md px-1 py-1.5 text-left text-[14px] text-[var(--gray-9)] transition-colors hover:bg-[var(--gray-3)]/30">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <StatusIcon className={cn("h-3.5 w-3.5 flex-shrink-0", statusColor)} />
          <span className={cn("min-w-0 flex-1 truncate", hasError && "text-red-600")}>
            {label}
          </span>
        </div>
        <span className="flex-shrink-0 rounded-[3px] bg-[var(--gray-3)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--gray-8)]">
          {toolName}
        </span>
        <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 text-[var(--gray-7)] transition-transform group-data-[state=open]/tool:rotate-180" />
      </CollapsibleTrigger>
      <ToolContent className="mt-1 rounded-md border border-[var(--gray-4)] bg-[var(--gray-2)]">
        {hasError ? (
          <div className="p-3 text-[13px] text-red-600 whitespace-pre-wrap">{part.errorText}</div>
        ) : (
          <>
            {/* Twenty CRM tab bar */}
            <div className="flex gap-3 border-b border-[var(--gray-4)] px-3">
              <button
                type="button"
                className={cn(
                  "pb-2 pt-2.5 text-[12px] transition-colors",
                  activeTab === "output"
                    ? "border-b-2 border-[var(--gray-12)] font-medium text-[var(--gray-12)]"
                    : "text-[var(--gray-8)] hover:text-[var(--gray-12)]",
                )}
                onClick={() => setActiveTab("output")}
              >
                输出
              </button>
              {hasInput && (
                <button
                  type="button"
                  className={cn(
                    "pb-2 pt-2.5 text-[12px] transition-colors",
                    activeTab === "input"
                      ? "border-b-2 border-[var(--gray-12)] font-medium text-[var(--gray-12)]"
                      : "text-[var(--gray-8)] hover:text-[var(--gray-12)]",
                  )}
                  onClick={() => setActiveTab("input")}
                >
                  输入
                </button>
              )}
            </div>
            <div className="max-h-[300px] overflow-y-auto p-3">
              {activeTab === "output" && hasOutput ? (
                <ToolOutputView output={part.output} />
              ) : activeTab === "output" ? (
                <span className="text-[12px] italic text-[var(--gray-7)]">无输出</span>
              ) : (
                <pre className="overflow-x-auto font-mono text-[12px] text-[var(--gray-11)] whitespace-pre-wrap break-words">
                  {safeStringify(part.input)}
                </pre>
              )}
            </div>
          </>
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
