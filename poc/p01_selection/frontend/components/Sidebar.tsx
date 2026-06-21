"use client";
import React, { useState } from "react";
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
  ChevronsLeft,
  ChevronsRight,
  MessageCirclePlus,
  Home,
  MessageSquare,
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

type SidebarTab = "nav" | "chat";

export function Sidebar() {
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const [, setDraft] = useAtom(draftCategoryAtom);
  const [active, setActive] = useAtom(activePageAtom);
  const threads = useAtomValue(threadsAtom);
  const [collapsed, setCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<SidebarTab>("nav");

  const onNav = (key: PageKey) => {
    setActive(key);
    setActiveId(null);
    setDraft(null);
  };
  const goHome = () => onNav("home");

  if (collapsed) {
    return (
      <aside className="flex h-full w-[52px] flex-shrink-0 flex-col items-center py-2 pl-2">
        <button
          onClick={() => setCollapsed(false)}
          className="flex h-7 w-7 items-center justify-center rounded-[4px] text-[var(--gray-9)] transition-colors hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
          title="展开侧边栏"
        >
          <ChevronsRight className="h-4 w-4" />
        </button>
        <div className="mt-3 flex flex-col items-center gap-0.5">
          {NAV.flatMap((g) => g.items).slice(0, 6).map((it) => (
            <button
              key={it.key}
              onClick={() => onNav(it.key)}
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-[4px] transition-colors",
                active === it.key
                  ? "bg-[var(--bg-transparent-light)] text-[var(--gray-12)]"
                  : "text-[var(--gray-11)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
              )}
              title={it.label}
            >
              {it.icon}
            </button>
          ))}
        </div>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-[236px] flex-shrink-0 flex-col gap-3 py-2 pl-2">
      {/* Header: workspace name + search + collapse */}
      <div className="flex min-h-[32px] items-center gap-1 pr-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <img src="/images/logo-icon.png" alt="SelectPilot" className="h-6 w-6 flex-shrink-0 rounded-[4px]" />
          <span className="truncate text-[14px] font-semibold text-[var(--gray-12)] tracking-tight">SelectPilot</span>
        </div>
        <button
          className="flex h-6 w-6 items-center justify-center rounded-[4px] text-[var(--gray-9)] transition-colors hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
          title="搜索"
        >
          <Search className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => setCollapsed(true)}
          className="flex h-6 w-6 items-center justify-center rounded-[4px] text-[var(--gray-9)] transition-colors hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
          title="收起侧边栏"
        >
          <ChevronsLeft className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Tab row: Navigation / AI Chat + New Chat button (Twenty CRM pattern) */}
      <div className="flex items-center gap-2 pr-2">
        <div className="flex h-7 flex-shrink-0 items-center gap-0.5 rounded-full border border-[var(--gray-5)] bg-[var(--gray-2)] p-[3px]">
          <button
            onClick={() => setActiveTab("nav")}
            className={cn(
              "flex h-full items-center justify-center rounded-full px-2 transition-colors",
              activeTab === "nav"
                ? "bg-[var(--bg-transparent-light)] text-[var(--gray-12)]"
                : "text-[var(--gray-9)] hover:bg-[var(--bg-transparent-lighter)]"
            )}
            title="导航"
          >
            <Home className="h-4 w-4" />
          </button>
          <button
            onClick={() => setActiveTab("chat")}
            className={cn(
              "flex h-full items-center justify-center rounded-full px-2 transition-colors",
              activeTab === "chat"
                ? "bg-[var(--bg-transparent-light)] text-[var(--gray-12)]"
                : "text-[var(--gray-9)] hover:bg-[var(--bg-transparent-lighter)]"
            )}
            title="AI 对话"
          >
            <MessageSquare className="h-4 w-4" />
          </button>
        </div>
        <button
          onClick={goHome}
          className="flex h-7 items-center gap-1 rounded-full border border-[var(--gray-5)] bg-[var(--gray-2)] px-2 text-[var(--gray-11)] transition-colors hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
        >
          <MessageCirclePlus className="h-4 w-4" />
          <span className="text-[13px] font-medium">新建</span>
        </button>
      </div>

      {activeTab === "nav" ? (
        <>
          {/* Navigation items */}
          <nav className="min-h-0 flex-1 overflow-y-auto pr-1.5">
            <div className="flex flex-col gap-3">
              {NAV.map((group, gi) => (
                <div key={gi}>
                  {group.title && (
                    <div className="mb-0.5 px-1 text-[11px] font-medium uppercase tracking-wider text-[var(--gray-9)]">
                      {group.title}
                    </div>
                  )}
                  <div className="flex flex-col gap-[2px]">
                    {group.items.map((it) => {
                      const isActive = active === it.key;
                      return (
                        <button
                          key={it.key}
                          onClick={() => onNav(it.key)}
                          className={cn(
                            "flex w-full items-center gap-2 rounded-[4px] px-1 text-left text-[14px] transition-colors",
                            "h-7",
                            isActive
                              ? "bg-[var(--bg-transparent-light)] font-medium text-[var(--gray-12)]"
                              : "text-[var(--gray-11)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
                          )}
                        >
                          <span className={cn(
                            "flex h-4 w-4 items-center justify-center",
                            isActive ? "text-[var(--gray-12)]" : "text-current"
                          )}>
                            {it.icon}
                          </span>
                          <span className="font-medium">{it.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </nav>

          {/* Bottom: settings + logout */}
          <div className="flex flex-col gap-[2px] pr-1.5 pb-2">
            <button
              onClick={() => onNav("settings")}
              className={cn(
                "flex w-full items-center gap-2 rounded-[4px] px-1 h-7 text-[14px] transition-colors",
                active === "settings"
                  ? "bg-[var(--bg-transparent-light)] font-medium text-[var(--gray-12)]"
                  : "text-[var(--gray-11)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
              )}
            >
              <Settings className={cn("h-4 w-4", active === "settings" ? "text-[var(--gray-12)]" : "text-current")} />
              <span className="font-medium">设置</span>
            </button>
            <button
              onClick={() => { clearAuth(); window.location.href = "/"; }}
              className="flex w-full items-center gap-2 rounded-[4px] px-1 h-7 text-[14px] text-[var(--gray-9)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)] transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span className="font-medium">退出</span>
            </button>
          </div>
        </>
      ) : (
        /* AI Chat history tab */
        <div className="min-h-0 flex-1 overflow-y-auto pr-1.5">
          <div className="flex flex-col gap-3">
            <div className="mb-0.5 px-1 text-[11px] font-medium uppercase tracking-wider text-[var(--gray-9)]">
              最近对话
            </div>
            {threads.length === 0 ? (
              <div className="px-1 text-[13px] text-[var(--gray-9)]">暂无对话记录</div>
            ) : (
              <div className="flex flex-col gap-[2px]">
                {threads.slice(0, 20).map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveId(t.id)}
                    className="flex w-full items-center gap-2 rounded-[4px] px-1 h-7 text-left text-[14px] text-[var(--gray-11)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)] transition-colors"
                  >
                    <MessageSquare className="h-4 w-4 flex-shrink-0" />
                    <span className="truncate font-medium">{t.title || "未命名对话"}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
