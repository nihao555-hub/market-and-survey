"use client";
import React from "react";
import { useAtom, useAtomValue, useSetAtom } from "jotai";
import {
  Plus,
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
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { activeThreadIdAtom, draftCategoryAtom, activePageAtom, threadsAtom, type PageKey } from "@/lib/atoms";
import { clearAuth } from "@/lib/auth";

type NavItem = { key: PageKey; label: string; icon: React.ReactNode };
type NavGroup = { title?: string; items: NavItem[] };

const NAV: NavGroup[] = [
  {
    items: [{ key: "home", label: "工作台", icon: <LayoutGrid className="h-4 w-4" /> }],
  },
  {
    title: "调研",
    items: [
      { key: "market", label: "市场扫描", icon: <Search className="h-4 w-4" /> },
      { key: "trend", label: "趋势分析", icon: <TrendingUp className="h-4 w-4" /> },
      { key: "competitor", label: "竞品分析", icon: <Swords className="h-4 w-4" /> },
      { key: "audience", label: "受众分析", icon: <Users className="h-4 w-4" /> },
      { key: "opportunity", label: "机会发现", icon: <Lightbulb className="h-4 w-4" /> },
    ],
  },
  {
    title: "任务",
    items: [
      { key: "tasks", label: "我的任务", icon: <ListTodo className="h-4 w-4" /> },
      { key: "reports", label: "报告", icon: <FileText className="h-4 w-4" /> },
      { key: "favorites", label: "收藏", icon: <Star className="h-4 w-4" /> },
      { key: "trash", label: "回收站", icon: <Trash2 className="h-4 w-4" /> },
    ],
  },
  {
    title: "数据",
    items: [
      { key: "category", label: "品类库", icon: <LayoutList className="h-4 w-4" /> },
      { key: "social", label: "社交趋势", icon: <Flame className="h-4 w-4" /> },
      { key: "monitor", label: "监控", icon: <BellRing className="h-4 w-4" /> },
    ],
  },
];

export function Sidebar() {
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const [, setDraft] = useAtom(draftCategoryAtom);
  const [active, setActive] = useAtom(activePageAtom);
  const threads = useAtomValue(threadsAtom);

  const onNav = (key: PageKey) => {
    setActive(key);
    setActiveId(null);
    setDraft(null);
  };
  const goHome = () => onNav("home");

  return (
    <aside className="flex h-full w-[220px] flex-shrink-0 flex-col border-r border-neutral-200 bg-white">
      {/* Brand */}
      <div className="flex h-[60px] items-center gap-2 px-4">
        <img src="/images/logo-icon.png" alt="SelectPilot" className="h-6 w-6 rounded-md" />
        <span className="text-[14px] font-semibold text-neutral-900 tracking-tight">SelectPilot</span>
      </div>

      {/* New research button */}
      <div className="px-3 pb-3">
        <button
          onClick={goHome}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-neutral-200 bg-white px-4 py-2 text-[13px] font-medium text-neutral-700 transition-colors hover:bg-neutral-50 active:bg-neutral-100"
        >
          <Plus className="h-3.5 w-3.5" />
          新建调研
        </button>
      </div>

      {/* Navigation */}
      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-1">
        {NAV.map((group, gi) => (
          <div key={gi} className="mb-1">
            {group.title && (
              <div className="px-2 pb-1 pt-3 text-[11px] font-medium uppercase tracking-wider text-neutral-400">
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
                    "mb-0.5 flex w-full items-center gap-2.5 rounded-md px-2 py-[7px] text-left text-[13px] transition-colors",
                    isActive
                      ? "bg-neutral-100 font-medium text-neutral-900"
                      : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900"
                  )}
                >
                  <span className={isActive ? "text-neutral-900" : "text-neutral-400"}>{it.icon}</span>
                  {it.label}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom: settings + logout */}
      <div className="border-t border-neutral-200 px-3 py-2 space-y-0.5">
        <button
          onClick={() => onNav("settings")}
          className={cn(
            "flex w-full items-center gap-2.5 rounded-md px-2 py-[7px] text-[13px] transition-colors",
            active === "settings"
              ? "bg-neutral-100 font-medium text-neutral-900"
              : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900"
          )}
        >
          <Settings className={cn("h-4 w-4", active === "settings" ? "text-neutral-900" : "text-neutral-400")} />
          设置
        </button>
        <button
          onClick={() => { clearAuth(); window.location.href = "/"; }}
          className="flex w-full items-center gap-2.5 rounded-md px-2 py-[7px] text-[13px] text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900 transition-colors"
        >
          <LogOut className="h-4 w-4 text-neutral-400" />
          退出
        </button>
      </div>
    </aside>
  );
}
