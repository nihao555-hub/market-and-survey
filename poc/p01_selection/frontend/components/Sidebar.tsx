"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import {
  Plus,
  Compass,
  LayoutGrid,
  TrendingUp,
  Swords,
  Users,
  Lightbulb,
  Search,
  ListTodo,
  FileText,
  Star,
  Trash2,
  Database,
  BellRing,
  Plug,
  Settings,
  Crown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { activeThreadIdAtom, draftCategoryAtom, activePageAtom, type PageKey } from "@/lib/atoms";

type NavItem = { key: PageKey; label: string; icon: React.ReactNode };
type NavGroup = { title?: string; items: NavItem[] };

const NAV: NavGroup[] = [
  {
    items: [{ key: "home", label: "工作台", icon: <LayoutGrid className="h-4 w-4" /> }],
  },
  {
    title: "调研中心",
    items: [
      { key: "market", label: "市场调研", icon: <Search className="h-4 w-4" /> },
      { key: "trend", label: "趋势探索", icon: <TrendingUp className="h-4 w-4" /> },
      { key: "competitor", label: "竞品分析", icon: <Swords className="h-4 w-4" /> },
      { key: "audience", label: "受众洞察", icon: <Users className="h-4 w-4" /> },
      { key: "opportunity", label: "机会挖掘", icon: <Lightbulb className="h-4 w-4" /> },
    ],
  },
  {
    title: "任务管理",
    items: [
      { key: "tasks", label: "我的任务", icon: <ListTodo className="h-4 w-4" /> },
      { key: "reports", label: "报告中心", icon: <FileText className="h-4 w-4" /> },
      { key: "favorites", label: "收藏夹", icon: <Star className="h-4 w-4" /> },
      { key: "trash", label: "回收站", icon: <Trash2 className="h-4 w-4" /> },
    ],
  },
  {
    title: "数据与工具",
    items: [
      { key: "datasources", label: "数据源管理", icon: <Database className="h-4 w-4" /> },
      { key: "monitor", label: "监控与订阅", icon: <BellRing className="h-4 w-4" /> },
      { key: "api", label: "API 接入", icon: <Plug className="h-4 w-4" /> },
    ],
  },
];

export function Sidebar() {
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const [, setDraft] = useAtom(draftCategoryAtom);
  const [active, setActive] = useAtom(activePageAtom);

  // 切换页面：清空会话与草稿，退出聊天态
  const onNav = (key: PageKey) => {
    setActive(key);
    setActiveId(null);
    setDraft(null);
  };
  const goHome = () => onNav("home");

  return (
    <aside className="flex h-full w-60 flex-shrink-0 flex-col border-r border-hairline bg-white">
      {/* 品牌 */}
      <div className="flex h-16 items-center gap-2.5 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white shadow-sm">
          <Compass className="h-5 w-5" strokeWidth={2} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold text-ink">MarketAgent</div>
          <div className="text-[10px] text-ink-subtle">选品 &amp; 市场调研 Agent</div>
        </div>
      </div>

      {/* 新建调研任务 */}
      <div className="px-3 pb-1.5">
        <button
          onClick={goHome}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-hover active:scale-[0.99]"
        >
          <Plus className="h-4 w-4" />
          新建调研任务
        </button>
      </div>

      {/* 导航分组 */}
      <nav className="scroll-area min-h-0 flex-1 overflow-y-auto px-3 py-2">
        {NAV.map((group, gi) => (
          <div key={gi} className="mb-1">
            {group.title && (
              <div className="px-2 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wider text-ink-tertiary">
                {group.title}
              </div>
            )}
            {group.items.map((it) => {
              const isActive = active === it.key;
              return (
                <button
                  key={it.key}
                  onClick={() => onNav(it.key)}
                  className={cn(
                    "mb-0.5 flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                    isActive
                      ? "bg-brand/10 font-medium text-brand"
                      : "text-ink-muted hover:bg-surface-1 hover:text-ink"
                  )}
                >
                  <span className={isActive ? "text-brand" : "text-ink-subtle"}>{it.icon}</span>
                  {it.label}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Pro 计划卡 */}
      <div className="px-3 pb-2">
        <div className="rounded-xl border border-hairline bg-gradient-to-br from-brand/5 to-brand2/10 p-3">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-brand text-white">
              <Crown className="h-3.5 w-3.5" />
            </span>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-ink">Pro 计划</div>
              <div className="text-[10px] text-ink-subtle">专业版</div>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-ink-subtle">
            <span>使用量</span>
            <span className="font-medium text-ink-muted">68%</span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
            <div className="h-full rounded-full bg-brand" style={{ width: "68%" }} />
          </div>
          <div className="mt-1.5 text-[10px] text-ink-tertiary">重置于 12 天后</div>
          <button className="mt-2.5 w-full rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-colors hover:bg-brand-hover">
            升级计划
          </button>
        </div>
      </div>

      {/* 设置 */}
      <div className="border-t border-hairline px-3 py-2">
        <button
          onClick={() => onNav("settings")}
          className={cn(
            "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
            active === "settings"
              ? "bg-brand/10 font-medium text-brand"
              : "text-ink-muted hover:bg-surface-1 hover:text-ink"
          )}
        >
          <Settings className={cn("h-4 w-4", active === "settings" ? "text-brand" : "text-ink-subtle")} />
          设置
        </button>
      </div>
    </aside>
  );
}
