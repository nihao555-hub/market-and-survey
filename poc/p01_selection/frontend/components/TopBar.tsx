"use client";
import React from "react";
import { useAtomValue } from "jotai";
import { Bell } from "lucide-react";
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
    <header className="flex h-10 flex-shrink-0 items-center gap-3 bg-transparent px-5">
      <div className="text-[14px] font-medium text-[var(--gray-12)]">
        {isChat ? "调研" : PAGE_TITLES[page]}
      </div>

      <div className="ml-auto flex items-center gap-1">
        <button className="flex h-6 w-6 items-center justify-center rounded-[4px] text-[var(--gray-9)] transition-colors hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]">
          <Bell className="h-4 w-4" />
        </button>
        <div className="ml-1 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--gray-12)] text-[10px] font-medium text-[var(--gray-1)]">
          U
        </div>
      </div>
    </header>
  );
}
