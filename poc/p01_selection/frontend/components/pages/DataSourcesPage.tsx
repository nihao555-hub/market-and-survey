"use client";
import React from "react";
import { Database, TrendingUp, ShoppingCart, Search, Globe, Share2, CheckCircle2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageContainer, PageHeader, StatTile } from "./primitives";

type Source = {
  name: string;
  desc: string;
  icon: React.ReactNode;
  freq: string;
  connected: boolean;
};

const SOURCES: Source[] = [
  { name: "Google Trends", desc: "搜索热度与上升趋势", icon: <TrendingUp className="h-5 w-5" />, freq: "实时", connected: true },
  { name: "Amazon Best Sellers", desc: "BSR 榜单与销量估算", icon: <ShoppingCart className="h-5 w-5" />, freq: "实时", connected: true },
  { name: "社媒数据", desc: "TikTok / Reddit 声量", icon: <Share2 className="h-5 w-5" />, freq: "实时", connected: true },
  { name: "Semrush", desc: "关键词搜索量与难度", icon: <Search className="h-5 w-5" />, freq: "每日", connected: false },
  { name: "SimilarWeb", desc: "站点流量与受众画像", icon: <Globe className="h-5 w-5" />, freq: "每日", connected: false },
];

export function DataSourcesPage() {
  const connected = SOURCES.filter((s) => s.connected).length;

  return (
    <PageContainer>
      <PageHeader
        icon={<Database className="h-5 w-5" />}
        title="数据源管理"
        subtitle="调研所依赖的外部数据源与连接状态。Agent 仅基于真实抓取数据分析，绝不编造。"
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile label="已接入" value={`${connected} / ${SOURCES.length}`} icon={<Database className="h-4 w-4" />} tone="text-brand" />
        <StatTile label="实时数据源" value={`${SOURCES.filter((s) => s.freq === "实时").length}`} delta="低延迟" icon={<TrendingUp className="h-4 w-4" />} tone="text-success" />
        <StatTile label="数据可信度" value="A 级" delta="真实抓取池" icon={<CheckCircle2 className="h-4 w-4" />} tone="text-info" />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {SOURCES.map((s) => (
          <div key={s.name} className="flex items-center gap-4 rounded-2xl border border-hairline bg-white p-4">
            <span className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
              {s.icon}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-ink">{s.name}</span>
                <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-subtle">{s.freq}</span>
              </div>
              <div className="mt-0.5 truncate text-xs text-ink-subtle">{s.desc}</div>
            </div>
            {s.connected ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-1 text-xs font-medium text-success">
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                已连接
              </span>
            ) : (
              <button className="inline-flex items-center gap-1 rounded-lg border border-brand/30 px-2.5 py-1.5 text-xs font-medium text-brand transition-colors hover:bg-brand/5">
                <Plus className="h-3.5 w-3.5" />
                连接
              </button>
            )}
          </div>
        ))}
        <button className={cn(
          "flex items-center justify-center gap-2 rounded-2xl border border-dashed border-hairline-strong bg-white p-4 text-sm text-ink-subtle transition-colors hover:border-brand/40 hover:text-brand"
        )}>
          <Plus className="h-4 w-4" />
          接入新的数据源
        </button>
      </div>
    </PageContainer>
  );
}
