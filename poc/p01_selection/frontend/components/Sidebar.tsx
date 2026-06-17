"use client";
import React from "react";
import { useAtom } from "jotai";
import { Plus, MessageSquare, Loader2, Compass, PanelLeftClose, PanelLeft, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { activeThreadIdAtom, threadsAtom, sidebarCollapsedAtom } from "@/lib/atoms";
import { gqlRequest } from "@/lib/graphql-client";
import type { ThreadSummary } from "@/lib/agent-types";

const THREADS_QUERY = /* GraphQL */ `
  query Threads { threads { id title updatedAt activeStreamId } }
`;

const DELETE_MUTATION = /* GraphQL */ `
  mutation DeleteThread($threadId: String!) { deleteThread(threadId: $threadId) }
`;

export function Sidebar() {
  const [activeId, setActiveId] = useAtom(activeThreadIdAtom);
  const [threads, setThreads] = useAtom(threadsAtom);
  const [collapsed, setCollapsed] = useAtom(sidebarCollapsedAtom);
  const [loading, setLoading] = React.useState(false);

  // 折叠态持久化
  React.useEffect(() => {
    const saved = localStorage.getItem("sidebar-collapsed");
    if (saved === "1") setCollapsed(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const toggle = () => {
    setCollapsed((c) => {
      localStorage.setItem("sidebar-collapsed", c ? "0" : "1");
      return !c;
    });
  };

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await gqlRequest<{ threads: ThreadSummary[] }>(THREADS_QUERY);
      setThreads(data.threads || []);
    } catch {
      /* 后端没起时静默 */
    } finally {
      setLoading(false);
    }
  }, [setThreads]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  // 删除单条会话记录（乐观：先从列表移除，失败再回滚刷新）
  const [pendingDelete, setPendingDelete] = React.useState<string | null>(null);
  const handleDelete = React.useCallback(
    async (e: React.MouseEvent, id: string) => {
      e.stopPropagation(); // 别触发选中
      const prev = threads;
      setThreads((list) => list.filter((t) => t.id !== id));
      if (activeId === id) setActiveId(null); // 删的是当前会话 → 回到新建态
      try {
        await gqlRequest(DELETE_MUTATION, { threadId: id });
      } catch {
        setThreads(prev); // 失败回滚
        refresh();
      } finally {
        setPendingDelete(null);
      }
    },
    [threads, activeId, setThreads, setActiveId, refresh]
  );

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-hairline bg-surface-1 transition-[width] duration-200 ease-out",
        collapsed ? "w-[56px]" : "w-64"
      )}
    >
      {/* 顶部：品牌 + 折叠按钮 */}
      <div className="flex h-14 items-center justify-between px-3">
        <div className={cn("flex items-center gap-2 overflow-hidden", collapsed && "w-0")}>
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-accent text-white">
            <Compass className="h-4 w-4" />
          </div>
          {!collapsed && <span className="whitespace-nowrap text-sm font-semibold text-ink">蓝海罗盘</span>}
        </div>
        <button
          onClick={toggle}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {/* 新建任务 */}
      <div className="px-3 pb-2">
        <button
          onClick={() => setActiveId(null)}
          className={cn(
            "flex items-center justify-center gap-2 rounded-lg bg-accent text-sm font-medium text-white transition-colors hover:bg-accent-hover active:scale-[0.99]",
            collapsed ? "h-9 w-9" : "w-full px-4 py-2"
          )}
          title="新建任务"
        >
          <Plus className="h-4 w-4 flex-shrink-0" />
          {!collapsed && "新建任务"}
        </button>
      </div>

      {!collapsed && (
        <div className="flex items-center justify-between px-4 py-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">历史任务</span>
          {loading && <Loader2 className="h-3 w-3 animate-spin text-ink-subtle" />}
        </div>
      )}

      {/* 任务列表 */}
      <div className="scroll-area flex-1 overflow-y-auto px-2 pb-3">
        {threads.length === 0 ? (
          !collapsed && <div className="px-2 py-6 text-center text-xs text-ink-subtle">暂无历史任务</div>
        ) : (
          threads.map((t) => (
            <div
              key={t.id}
              onClick={() => setActiveId(t.id)}
              onMouseLeave={() => pendingDelete === t.id && setPendingDelete(null)}
              title={t.title || "未命名任务"}
              className={cn(
                "group mb-0.5 flex w-full cursor-pointer items-start gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                activeId === t.id ? "bg-surface-2 text-ink" : "text-ink-muted hover:bg-surface-2/60",
                collapsed && "justify-center px-0"
              )}
            >
              <div className="relative">
                <MessageSquare className="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-subtle" />
                {collapsed && t.activeStreamId && (
                  <span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-success" />
                )}
              </div>
              {!collapsed && (
                <>
                  <span className="line-clamp-2 flex-1 leading-snug">{t.title || "未命名任务"}</span>
                  {t.activeStreamId && (
                    <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-success" />
                  )}
                  {/* 删除按钮：悬停显示；点一次进入确认态，再点确认删除 */}
                  {pendingDelete === t.id ? (
                    <button
                      onClick={(e) => handleDelete(e, t.id)}
                      title="确认删除"
                      className="mt-0.5 flex-shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium text-danger transition-colors hover:bg-danger/10"
                    >
                      确认
                    </button>
                  ) : (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setPendingDelete(t.id);
                      }}
                      title="删除记录"
                      className="mt-0.5 flex-shrink-0 rounded p-0.5 text-ink-subtle opacity-0 transition-all hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </>
              )}
            </div>
          ))
        )}
      </div>

      {!collapsed && (
        <div className="border-t border-hairline px-4 py-3 text-[11px] text-ink-subtle">
          DeepSeek · 8 阶段实时调研
        </div>
      )}
    </aside>
  );
}
