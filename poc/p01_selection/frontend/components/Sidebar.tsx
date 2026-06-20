"use client";
import React from "react";
import { useAtom, useAtomValue, useSetAtom } from "jotai";
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
  BellRing,
  Flame,
  LayoutList,
  Settings,
  Crown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { activeThreadIdAtom, draftCategoryAtom, activePageAtom, threadsAtom, type PageKey } from "@/lib/atoms";

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
    title: "榜单与监控",
    items: [
      { key: "category", label: "品类榜单", icon: <LayoutList className="h-4 w-4" /> },
      { key: "social", label: "社媒趋势", icon: <Flame className="h-4 w-4" /> },
      { key: "monitor", label: "监控与订阅", icon: <BellRing className="h-4 w-4" /> },
    ],
  },
];

export function Sidebar() {
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const [, setDraft] = useAtom(draftCategoryAtom);
  const [active, setActive] = useAtom(activePageAtom);
  const threads = useAtomValue(threadsAtom);
  const runningCount = threads.filter((t) => t.activeStreamId).length;

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
          <div className="mt-3 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-white/60 px-2.5 py-1.5">
              <div className="text-base font-semibold leading-none text-ink">{threads.length}</div>
              <div className="mt-1 text-[10px] text-ink-subtle">累计调研</div>
            </div>
            <div className="rounded-lg bg-white/60 px-2.5 py-1.5">
              <div className="text-base font-semibold leading-none text-ink">{runningCount}</div>
              <div className="mt-1 text-[10px] text-ink-subtle">进行中</div>
            </div>
          </div>
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
