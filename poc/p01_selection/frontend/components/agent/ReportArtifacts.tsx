"use client";
import React from "react";
import { FileText, FileDown, Layers, File, Package } from "lucide-react";
import { BACKEND_BASE } from "@/lib/graphql-client";
import type { ReportArtifacts as Artifacts } from "@/lib/agent-types";

const ITEMS: { key: keyof Artifacts; label: string; icon: React.ReactNode; primary?: boolean }[] = [
  { key: "merchant_md", label: "商家版（推荐）", icon: <FileText className="h-4 w-4" />, primary: true },
  { key: "one_pager_md", label: "一页速览", icon: <File className="h-4 w-4" /> },
  { key: "detail_md", label: "5 页详情", icon: <Layers className="h-4 w-4" /> },
  { key: "full_md", label: "完整版", icon: <FileText className="h-4 w-4" /> },
  { key: "pdf", label: "PDF 下载", icon: <FileDown className="h-4 w-4" /> },
];

/** 报告产物卡片（5 件套），渲染在 assistant 消息末尾 */
export function ReportArtifacts({ artifacts }: { artifacts: Artifacts }) {
  const open = (path?: string | null) => {
    if (!path) return;
    window.open(`${BACKEND_BASE}/report-file?path=${encodeURIComponent(path)}`, "_blank");
  };
  return (
    <div className="my-3 rounded-xl border border-hairline bg-white p-3">
      <div className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink-muted">
        <Package className="h-4 w-4 text-accent" />
        报告产物
      </div>
      <div className="flex flex-wrap gap-2">
        {ITEMS.filter((it) => artifacts[it.key]).map((it) => (
          <button
            key={it.key}
            onClick={() => open(artifacts[it.key] as string)}
            className={
              "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors " +
              (it.primary
                ? "border-accent bg-accent text-white hover:bg-accent-hover"
                : "border-hairline text-ink-muted hover:bg-surface-2")
            }
          >
            {it.icon}
            {it.label}
          </button>
        ))}
      </div>
    </div>
  );
}
