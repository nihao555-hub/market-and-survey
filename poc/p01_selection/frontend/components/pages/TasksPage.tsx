"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import { ListTodo, Plus, MoreHorizontal, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";
import { activeThreadIdAtom, draftCategoryAtom, threadsAtom, activePageAtom } from "@/lib/atoms";
import { gqlRequest } from "@/lib/graphql-client";
import { formatDate, parseTitle } from "@/lib/thread-format";
import type { ThreadSummary } from "@/lib/agent-types";
import { PageContainer, PageHeader, Panel, EmptyState } from "./primitives";

const THREADS_QUERY = /* GraphQL */ `
  query Threads { threads { id title updatedAt activeStreamId } }
`;

type Filter = "all" | "running" | "done";

export function TasksPage() {
  const [threads, setThreads] = useAtom(threadsAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const setDraft = useSetAtom(draftCategoryAtom);
  const setPage = useSetAtom(activePageAtom);
  const [filter, setFilter] = React.useState<Filter>("all");

  React.useEffect(() => {
    (async () => {
      try {
        const data = await gqlRequest<{ threads: ThreadSummary[] }>(THREADS_QUERY);
        setThreads(data.threads || []);
      } catch {
        /* 后端未启动时静默 */
      }
    })();
  }, [setThreads]);

  const running = threads.filter((t) => t.activeStreamId).length;
  const filtered = threads.filter((t) =>
    filter === "all" ? true : filter === "running" ? !!t.activeStreamId : !t.activeStreamId
  );

  const newTask = () => {
    setPage("home");
    setActiveId(null);
    setDraft(null);
  };

  const FILTERS: { key: Filter; label: string; count: number }[] = [
    { key: "all", label: "全部", count: threads.length },
    { key: "running", label: "分析中", count: running },
    { key: "done", label: "已完成", count: threads.length - running },
  ];

  return (
    <PageContainer>
      <PageHeader
        icon={<ListTodo className="h-5 w-5" />}
        title="我的任务"
        subtitle="管理你发起的全部调研任务，点击任意任务查看实时进度与报告。"
        actions={
          <button
            onClick={newTask}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-hover"
          >
            <Plus className="h-4 w-4" />
            新建任务
          </button>
        }
      />

      <div className="mb-4 flex items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
              filter === f.key
                ? "bg-brand/10 font-medium text-brand"
                : "text-ink-muted hover:bg-surface-1 hover:text-ink"
            )}
          >
            {f.label}
            <span
              className={cn(
                "rounded-full px-1.5 text-[11px]",
                filter === f.key ? "bg-brand/15 text-brand" : "bg-surface-2 text-ink-subtle"
              )}
            >
              {f.count}
            </span>
          </button>
        ))}
      </div>

      <Panel bodyClassName="p-0">
        {filtered.length === 0 ? (
          <EmptyState
            icon={<Inbox className="h-6 w-6" />}
            title="暂无任务"
            hint="从工作台输入一个品类或市场即可发起你的第一个调研任务。"
            action={
              <button
                onClick={newTask}
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-hover"
              >
                <Plus className="h-4 w-4" />
                新建任务
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-ink-subtle">
                  <th className="px-5 py-3 font-medium">任务名称</th>
                  <th className="px-3 py-3 font-medium">目标市场</th>
                  <th className="px-3 py-3 font-medium">创建时间</th>
                  <th className="px-3 py-3 font-medium">进度状态</th>
                  <th className="px-5 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => {
                  const { name, market } = parseTitle(t.title);
                  const isRunning = !!t.activeStreamId;
                  return (
                    <tr
                      key={t.id}
                      onClick={() => setActiveId(t.id)}
                      className="cursor-pointer border-t border-hairline transition-colors hover:bg-surface-1"
                    >
                      <td className="px-5 py-3 font-medium text-ink">{name}</td>
                      <td className="px-3 py-3 text-ink-muted">{market}</td>
                      <td className="px-3 py-3 text-ink-subtle">{formatDate(t.updatedAt)}</td>
                      <td className="px-3 py-3">
                        {isRunning ? (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-info/10 px-2 py-0.5 text-xs font-medium text-info">
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info" />
                            分析中
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
                            <span className="h-1.5 w-1.5 rounded-full bg-success" />
                            已完成
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveId(t.id);
                          }}
                          className="rounded p-1 text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </PageContainer>
  );
}
