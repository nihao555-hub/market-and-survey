"use client";
import React from "react";
import { FileText, FileDown, Layers, File, Package, ArrowUpRight } from "lucide-react";
import { BACKEND_BASE } from "@/lib/graphql-client";
import type { ReportArtifacts as Artifacts } from "@/lib/agent-types";

const ITEMS: {
  key: keyof Artifacts;
  label: string;
  desc: string;
  icon: React.ReactNode;
  primary?: boolean;
}[] = [
  { key: "merchant_md", label: "商家版", desc: "推荐 · 决策摘要", icon: <FileText className="h-4 w-4" />, primary: true },
  { key: "one_pager_md", label: "一页速览", desc: "核心结论一页看完", icon: <File className="h-4 w-4" /> },
  { key: "detail_md", label: "5 页详情", desc: "分章节展开", icon: <Layers className="h-4 w-4" /> },
  { key: "full_md", label: "完整版", desc: "全量数据与论证", icon: <FileText className="h-4 w-4" /> },
  { key: "pdf", label: "PDF 下载", desc: "可分享文档", icon: <FileDown className="h-4 w-4" /> },
];

/** 报告产物卡片（5 件套），渲染在 assistant 消息末尾 */
export function ReportArtifacts({ artifacts }: { artifacts: Artifacts }) {
  const open = (path?: string | null) => {
    if (!path) return;
    window.open(`${BACKEND_BASE}/report-file?path=${encodeURIComponent(path)}`, "_blank");
  };
  const available = ITEMS.filter((it) => artifacts[it.key]);
  if (available.length === 0) return null;

  return (
    <div className="my-3 rounded-xl border border-hairline bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-ink">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-brand/10 text-brand">
          <Package className="h-3.5 w-3.5" />
        </span>
        报告产物
        <span className="text-xs font-normal text-ink-subtle">· 多版本可选</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {available.map((it) => (
          <button
            key={it.key}
            onClick={() => open(artifacts[it.key] as string)}
            className={
              "group flex items-start gap-2.5 rounded-lg border p-2.5 text-left transition-all " +
              (it.primary
                ? "border-brand bg-brand text-white hover:bg-brand-hover"
                : "border-hairline bg-white text-ink-muted hover:border-brand/40 hover:bg-brand/5")
            }
          >
            <span
              className={
                "mt-0.5 flex-shrink-0 " + (it.primary ? "text-white" : "text-brand")
              }
            >
              {it.icon}
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-1 text-sm font-medium">
                <span className={it.primary ? "text-white" : "text-ink"}>{it.label}</span>
                <ArrowUpRight
                  className={
                    "h-3 w-3 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100 " +
                    (it.primary ? "text-white" : "text-brand")
                  }
                />
              </span>
              <span
                className={
                  "mt-0.5 block truncate text-[11px] " +
                  (it.primary ? "text-white/80" : "text-ink-subtle")
                }
              >
                {it.desc}
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
