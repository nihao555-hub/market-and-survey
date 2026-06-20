"use client";
import React from "react";
import { useAtomValue } from "jotai";
import { Search, Bell, HelpCircle, ChevronDown } from "lucide-react";
import { activeThreadIdAtom, draftCategoryAtom, activePageAtom, type PageKey } from "@/lib/atoms";

const PAGE_TITLES: Record<PageKey, string> = {
  home: "调研工作区",
  market: "市场调研",
  trend: "趋势探索",
  competitor: "竞品分析",
  audience: "受众洞察",
  opportunity: "机会挖掘",
  tasks: "我的任务",
  reports: "报告中心",
  favorites: "收藏夹",
  trash: "回收站",
  social: "社媒趋势",
  category: "品类榜单",
  monitor: "监控与订阅",
  settings: "设置",
};

export function TopBar() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const draft = useAtomValue(draftCategoryAtom);
  const page = useAtomValue(activePageAtom);
  const isChat = !!activeId || !!draft;
  const isHome = !isChat && page === "home";

  return (
    <header className="flex h-16 flex-shrink-0 items-center gap-4 border-b border-hairline bg-white px-5">
      {/* 问候（仅工作台首页显示） */}
      {isHome ? (
        <div className="min-w-0 leading-tight">
          <div className="flex items-center gap-1.5 text-[15px] font-semibold text-ink">
            早上好，产品经理 <span aria-hidden>👋</span>
          </div>
          <div className="truncate text-xs text-ink-subtle">
            今天想调研什么品类或市场？我可以帮你发现有潜力的机会。
          </div>
        </div>
      ) : (
        <div className="text-sm font-medium text-ink-muted">{isChat ? "调研工作区" : PAGE_TITLES[page]}</div>
      )}

      {/* 全局搜索 */}
      <div className="ml-auto hidden w-[clamp(220px,32vw,420px)] items-center gap-2 rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink-subtle md:flex">
        <Search className="h-4 w-4 flex-shrink-0" />
        <span className="flex-1 truncate">搜索品类、市场、关键词或过去的报告</span>
        <kbd className="rounded border border-hairline bg-white px-1.5 py-0.5 text-[10px] text-ink-tertiary">
          ⌘K
        </kbd>
      </div>

      {/* 右侧操作 */}
      <div className="flex items-center gap-1.5">
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg text-ink-subtle transition-colors hover:bg-surface-1 hover:text-ink">
          <Bell className="h-[18px] w-[18px]" />
        </button>
        <button className="flex h-9 w-9 items-center justify-center rounded-lg text-ink-subtle transition-colors hover:bg-surface-1 hover:text-ink">
          <HelpCircle className="h-[18px] w-[18px]" />
        </button>
        <div className="ml-1 flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 transition-colors hover:bg-surface-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand to-brand2 text-xs font-semibold text-white">
            产
          </div>
          <div className="hidden items-center gap-1.5 sm:flex">
            <span className="text-xs font-medium text-ink">产品经理</span>
            <span className="rounded bg-brand/10 px-1.5 py-0.5 text-[10px] font-semibold text-brand">
              Pro
            </span>
          </div>
          <ChevronDown className="hidden h-3.5 w-3.5 text-ink-subtle sm:block" />
        </div>
      </div>
    </header>
  );
}
