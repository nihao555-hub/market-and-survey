"use client";
import React from "react";
import {
  TrendingUp,
  ShieldCheck,
  Flame,
  Star,
  ChevronRight,
  Circle,
  Plus,
  CheckCircle2,
  Gift,
} from "lucide-react";
import { cn } from "@/lib/utils";

const INSIGHTS = [
  { label: "高需求品类", value: "↑ 25%", tone: "text-success", icon: <Flame className="h-4 w-4" /> },
  { label: "竞争较低", value: "蓝海", tone: "text-info", icon: <ShieldCheck className="h-4 w-4" /> },
  { label: "上升趋势", value: "↑ 120%", tone: "text-brand", icon: <TrendingUp className="h-4 w-4" /> },
  { label: "机会评分最高", value: "8.6 / 10", tone: "text-amber-600", icon: <Star className="h-4 w-4" /> },
];

const SOURCES = [
  { name: "Google Trends", freq: "实时", live: true },
  { name: "Amazon Best Sellers", freq: "实时", live: true },
  { name: "Semrush", freq: "每日", live: false },
  { name: "SimilarWeb", freq: "每日", live: false },
  { name: "社媒数据", freq: "实时", live: true },
];

const ONBOARDING = [
  { label: "完成新手教程", done: true },
  { label: "创建第一个调研任务", done: false },
  { label: "查看示例报告", done: false },
];

function SectionCard({
  title,
  action,
  children,
}: {
  title: string;
  action?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-hairline bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {action && (
          <button className="inline-flex items-center gap-0.5 text-[11px] text-brand hover:underline">
            {action}
            <ChevronRight className="h-3 w-3" />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

export function RightRail() {
  return (
    <aside className="hidden w-80 flex-shrink-0 overflow-y-auto border-l border-hairline bg-surface-1 px-4 py-6 xl:block">
      <div className="space-y-4">
        {/* AI 洞察 */}
        <SectionCard title="AI 洞察" action="更多洞察">
          <div className="grid grid-cols-2 gap-2.5">
            {INSIGHTS.map((it) => (
              <div key={it.label} className="rounded-xl border border-hairline bg-surface-1 p-3">
                <div className={cn("flex items-center gap-1.5", it.tone)}>
                  {it.icon}
                  <span className="text-sm font-semibold">{it.value}</span>
                </div>
                <div className="mt-1 text-[11px] text-ink-subtle">{it.label}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        {/* 数据源 */}
        <SectionCard title="数据源" action="管理">
          <div className="space-y-1">
            {SOURCES.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between rounded-lg px-1.5 py-1.5 text-sm"
              >
                <span className="text-ink-muted">{s.name}</span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 text-[11px]",
                    s.live ? "text-success" : "text-ink-subtle"
                  )}
                >
                  <Circle
                    className={cn("h-2 w-2 fill-current", s.live ? "text-success" : "text-ink-tertiary")}
                  />
                  {s.freq}
                </span>
              </div>
            ))}
            <button className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-hairline-strong py-2 text-xs text-ink-subtle transition-colors hover:border-brand/40 hover:text-brand">
              <Plus className="h-3.5 w-3.5" />
              添加数据源
            </button>
          </div>
        </SectionCard>

        {/* 新手引导 */}
        <SectionCard title="新手引导">
          <div className="space-y-2">
            {ONBOARDING.map((o) => (
              <div key={o.label} className="flex items-center gap-2.5 text-sm">
                {o.done ? (
                  <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-success" />
                ) : (
                  <Circle className="h-4 w-4 flex-shrink-0 text-ink-tertiary" />
                )}
                <span className={o.done ? "text-ink-subtle line-through" : "text-ink-muted"}>
                  {o.label}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-start gap-2.5 rounded-xl bg-gradient-to-br from-brand/10 to-brand2/10 p-3">
            <Gift className="h-5 w-5 flex-shrink-0 text-brand" />
            <div className="text-[11px] leading-relaxed text-ink-muted">
              完成全部任务可获得 <span className="font-medium text-brand">专属数据报告模版</span>
            </div>
          </div>
        </SectionCard>
      </div>
    </aside>
  );
}
