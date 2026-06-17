"use client";
import React from "react";
import { BellRing, Plus, TrendingUp, Tag, Swords } from "lucide-react";
import { PageContainer, PageHeader, Panel, EmptyState } from "./primitives";

type Rule = { name: string; desc: string; icon: React.ReactNode; cadence: string; on: boolean };

const RULES: Rule[] = [
  { name: "趋势异动提醒", desc: "关注品类搜索热度周环比 > 20% 时通知", icon: <TrendingUp className="h-4 w-4" />, cadence: "每日", on: true },
  { name: "竞品上新监控", desc: "Top 竞品新增 listing 时推送", icon: <Swords className="h-4 w-4" />, cadence: "实时", on: true },
  { name: "价格波动订阅", desc: "目标 ASIN 价格变动 > 10% 时提醒", icon: <Tag className="h-4 w-4" />, cadence: "每日", on: false },
];

function Toggle({ on }: { on: boolean }) {
  return (
    <span
      className={
        "relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors " +
        (on ? "bg-brand" : "bg-surface-3")
      }
    >
      <span
        className={
          "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform " +
          (on ? "translate-x-4" : "translate-x-0.5")
        }
      />
    </span>
  );
}

export function MonitorPage() {
  return (
    <PageContainer>
      <PageHeader
        icon={<BellRing className="h-5 w-5" />}
        title="监控与订阅"
        subtitle="为关键品类、竞品与价格设置自动监控规则，变化发生时第一时间收到提醒。"
        actions={
          <button className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-hover">
            <Plus className="h-4 w-4" />
            新建监控
          </button>
        }
      />

      <Panel title="监控规则" bodyClassName="p-0">
        <div className="divide-y divide-hairline">
          {RULES.map((r) => (
            <div key={r.name} className="flex items-center gap-4 px-5 py-4">
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand/10 text-brand">
                {r.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-ink">{r.name}</span>
                  <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-subtle">{r.cadence}</span>
                </div>
                <div className="mt-0.5 truncate text-xs text-ink-subtle">{r.desc}</div>
              </div>
              <Toggle on={r.on} />
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-4">
        <Panel bodyClassName="p-0">
          <EmptyState
            icon={<BellRing className="h-6 w-6" />}
            title="暂无新的提醒"
            hint="监控规则触发后，相关提醒会显示在这里。"
          />
        </Panel>
      </div>
    </PageContainer>
  );
}
