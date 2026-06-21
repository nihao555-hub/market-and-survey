"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import { ListTodo, Plus, Inbox, Star, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { activeThreadIdAtom, draftCategoryAtom, threadsAtom, activePageAtom } from "@/lib/atoms";
import { fetchThreads, toggleFavorite, deleteThread } from "@/lib/api";
import { formatDate, parseTitle } from "@/lib/thread-format";
import {
  PageContainer, PageHeader, Panel, EmptyState,
  Button, FilterTabs, StatusBadge, DataTable, Skeleton, type Column,
} from "./primitives";
import type { ThreadSummary } from "@/lib/agent-types";

type Filter = "all" | "running" | "done";

export function TasksPage() {
  const [threads, setThreads] = useAtom(threadsAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const setDraft = useSetAtom(draftCategoryAtom);
  const setPage = useSetAtom(activePageAtom);
  const [filter, setFilter] = React.useState<Filter>("all");
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    try {
      setThreads(await fetchThreads());
    } catch {
      /* 后端未启动时静默 */
    } finally {
      setLoading(false);
    }
  }, [setThreads]);

  React.useEffect(() => { reload(); }, [reload]);

  const running = threads.filter((t) => t.activeStreamId).length;
  const filtered = threads.filter((t) =>
    filter === "all" ? true : filter === "running" ? !!t.activeStreamId : !t.activeStreamId
  );

  const newTask = () => {
    setPage("home");
    setActiveId(null);
    setDraft(null);
  };

  const onFav = async (t: ThreadSummary) => {
    setThreads((prev) => prev.map((x) => (x.id === t.id ? { ...x, isFavorite: !x.isFavorite } : x)));
    try { await toggleFavorite(t.id); } catch { reload(); }
  };

  const onDelete = async (t: ThreadSummary) => {
    setThreads((prev) => prev.filter((x) => x.id !== t.id));
    try { await deleteThread(t.id); } catch { reload(); }
  };

  const columns: Column<ThreadSummary>[] = [
    {
      key: "name", header: "任务名称",
      render: (t) => <span className="font-medium text-[var(--gray-12)]">{parseTitle(t.title).name}</span>,
    },
    { key: "market", header: "目标市场", render: (t) => <span className="text-[var(--gray-8)]">{parseTitle(t.title).market}</span> },
    { key: "time", header: "创建时间", render: (t) => <span className="text-[var(--gray-9)]">{formatDate(t.updatedAt)}</span> },
    {
      key: "status", header: "进度状态",
      render: (t) => (t.activeStreamId
        ? <StatusBadge status="running" label="分析中" />
        : <StatusBadge status="done" label="已完成" />),
    },
    {
      key: "actions", header: "操作", align: "right",
      render: (t) => (
        <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => onFav(t)}
            title={t.isFavorite ? "取消收藏" : "收藏"}
            className={cn(
              "rounded p-1.5 transition-colors hover:bg-[var(--gray-4)]",
              t.isFavorite ? "text-[var(--gray-12)]" : "text-[var(--gray-9)] hover:text-[var(--gray-12)]"
            )}
          >
            <Star className={cn("h-4 w-4", t.isFavorite && "fill-current")} />
          </button>
          <button
            onClick={() => onDelete(t)}
            title="移入回收站"
            className="rounded p-1.5 text-[var(--gray-9)] transition-colors hover:bg-danger/10 hover:text-danger"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

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
        actions={<Button onClick={newTask}><Plus className="h-4 w-4" />新建任务</Button>}
      />

      <div className="mb-4">
        <FilterTabs tabs={FILTERS} value={filter} onChange={setFilter} />
      </div>

      <Panel bodyClassName="p-0">
        {loading ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : (
          <DataTable
            columns={columns}
            rows={filtered}
            getRowKey={(t) => t.id}
            onRowClick={(t) => setActiveId(t.id)}
            empty={
              <EmptyState
                icon={<Inbox className="h-6 w-6" />}
                title="暂无任务"
                hint="从工作台输入一个品类或市场即可发起你的第一个调研任务。"
                action={<Button onClick={newTask}><Plus className="h-4 w-4" />新建任务</Button>}
              />
            }
          />
        )}
      </Panel>
    </PageContainer>
  );
}
