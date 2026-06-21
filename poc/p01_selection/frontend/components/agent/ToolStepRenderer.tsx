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

  if (inProgress) {
    return (
      <div className="flex items-center justify-between gap-1 py-1 text-[16px] font-medium text-[var(--gray-9)]">
        <div className="flex items-center gap-1">
          <Loader2 className="h-4 w-4 animate-spin" />
          <ShimmeringText>{label}</ShimmeringText>
        </div>
        <span className="rounded-[2px] bg-[var(--bg-transparent-light)] px-1 py-0.5 font-mono text-[13px] text-[var(--gray-8)]">
          {toolName}
        </span>
      </div>
    );
  }

  const hasBody = hasError || hasOutput || part.input !== undefined;

  if (!hasBody) {
    return (
      <div className="flex items-center justify-between gap-1 py-1 text-[16px] font-medium text-[var(--gray-9)]">
        <div className="flex items-center gap-1">
          <CheckCircle2 className="h-4 w-4" />
          <span>{label}</span>
        </div>
        <span className="rounded-[2px] bg-[var(--bg-transparent-light)] px-1 py-0.5 font-mono text-[13px] text-[var(--gray-8)]">
          {toolName}
        </span>
      </div>
    );
  }

  return (
    <Tool className="mb-1.5 border-[var(--gray-4)] bg-[var(--gray-1)] shadow-none">
      <CollapsibleTrigger className="group/tool flex w-full items-center gap-1 p-2.5 text-left text-[16px] font-medium text-[var(--gray-9)] transition-colors hover:text-[var(--gray-12)]">
        <div className="flex min-w-0 flex-1 items-center gap-1">
          {hasError ? (
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-600" />
          ) : (
            <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-[var(--gray-9)]" />
          )}
          <span className={cn("min-w-0 flex-1 truncate", hasError && "text-red-600")}>
            {label}
          </span>
        </div>
        <span className="flex-shrink-0 rounded-[2px] bg-[var(--bg-transparent-light)] px-1 py-0.5 font-mono text-[13px] text-[var(--gray-8)]">
          {toolName}
        </span>
        <ChevronDown className="h-4 w-4 flex-shrink-0 transition-transform group-data-[state=open]/tool:rotate-180" />
      </CollapsibleTrigger>
      <ToolContent className="space-y-3 border-t border-[var(--gray-4)] p-3">
        {/* Tabs: output/input (Twenty CRM pattern) */}
        {part.input !== undefined && (
          <div>
            <div className="mb-1 text-[14px] font-medium text-[var(--gray-9)]">输入</div>
            <pre className="overflow-x-auto rounded-[4px] border border-[var(--gray-4)] bg-[var(--bg-transparent-lighter)] p-3 font-mono text-[13px] text-[var(--gray-11)]">
              {safeStringify(part.input)}
            </pre>
          </div>
        )}
        {hasError && (
          <div>
            <div className="mb-1 text-[14px] font-medium text-red-600">错误</div>
            <pre className="overflow-x-auto rounded-[4px] border border-red-200 bg-red-50 p-3 font-mono text-[13px] text-red-700">
              {part.errorText}
            </pre>
          </div>
        )}
        {hasOutput && (
          <div>
            <div className="mb-1 text-[14px] font-medium text-[var(--gray-9)]">输出</div>
            <div className="rounded-[4px] border border-[var(--gray-4)] bg-[var(--bg-transparent-lighter)] p-3">
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
