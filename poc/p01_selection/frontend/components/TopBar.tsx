"use client";
import React from "react";
import { useAtomValue } from "jotai";
import { Search, Bell } from "lucide-react";
import { activeThreadIdAtom, draftCategoryAtom, activePageAtom, type PageKey } from "@/lib/atoms";

const PAGE_TITLES: Record<PageKey, string> = {
  home: "工作台",
  market: "市场扫描",
  trend: "趋势分析",
  competitor: "竞品分析",
  audience: "受众分析",
  opportunity: "机会发现",
  tasks: "我的任务",
  reports: "报告",
  favorites: "收藏",
  trash: "回收站",
  social: "社交趋势",
  category: "品类库",
  monitor: "监控",
  settings: "设置",
};

export function TopBar() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const draft = useAtomValue(draftCategoryAtom);
  const page = useAtomValue(activePageAtom);
  const isChat = !!activeId || !!draft;

  return (
    <header className="flex h-[52px] flex-shrink-0 items-center gap-4 border-b border-neutral-200 bg-white px-5">
      {/* Page title */}
      <div className="text-[14px] font-medium text-neutral-900">
        {isChat ? "调研" : PAGE_TITLES[page]}
      </div>

      {/* Search */}
      <div className="ml-auto hidden w-[280px] items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-[6px] text-[13px] text-neutral-400 md:flex">
        <Search className="h-3.5 w-3.5 flex-shrink-0" />
        <span className="flex-1 truncate">搜索...</span>
        <kbd className="rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] text-neutral-400">
          ⌘K
        </kbd>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        <button className="flex h-8 w-8 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-50 hover:text-neutral-700">
          <Bell className="h-4 w-4" />
        </button>
        <div className="ml-2 flex h-7 w-7 items-center justify-center rounded-full bg-neutral-900 text-[11px] font-medium text-white">
          U
        </div>
      </div>
    </header>
  );
}
