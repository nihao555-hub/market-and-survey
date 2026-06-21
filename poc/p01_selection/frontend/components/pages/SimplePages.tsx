"use client";
import React from "react";
import { useSetAtom } from "jotai";
import { Star, Trash2, Plus, RotateCcw, FileText, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { activePageAtom, activeThreadIdAtom, draftCategoryAtom } from "@/lib/atoms";
import {
  fetchFavoriteThreads, toggleFavorite,
  fetchTrashedThreads, restoreThread, purgeThread,
} from "@/lib/api";
import { formatDate, parseTitle } from "@/lib/thread-format";
import type { ThreadSummary } from "@/lib/agent-types";
import {
  PageContainer, PageHeader, Panel, EmptyState, Button, Skeleton, StatusBadge,
} from "./primitives";

export function FavoritesPage() {
  const setPage = useSetAtom(activePageAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const setDraft = useSetAtom(draftCategoryAtom);
  const [items, setItems] = React.useState<ThreadSummary[]>([]);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    try { setItems(await fetchFavoriteThreads()); }
    catch { /* 静默 */ }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  const unfav = async (id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id));
    try { await toggleFavorite(id); } catch { reload(); }
  };

  return (
    <PageContainer>
      <PageHeader
        icon={<Star className="h-5 w-5" />}
        title="收藏夹"
        subtitle="收藏的调研任务与报告，方便随时回看与对比。"
      />
      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-36 w-full rounded-2xl" />)}
        </div>
      ) : items.length === 0 ? (
        <Panel bodyClassName="p-0">
          <EmptyState
            icon={<Star className="h-6 w-6" />}
            title="收藏夹为空"
            hint="在「我的任务」中点击星标，即可把重要任务固定到这里。"
            action={
              <Button onClick={() => { setPage("home"); setActiveId(null); setDraft(null); }}>
                <Plus className="h-4 w-4" />去发起调研
              </Button>
            }
          />
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((t) => {
            const { name, market } = parseTitle(t.title);
            return (
              <div
                key={t.id}
                className="group flex flex-col rounded-2xl border border-[var(--gray-5)] bg-[var(--gray-1)] p-5 transition-all hover:-translate-y-0.5 hover:border-[var(--gray-6)] hover:shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--gray-4)] text-[var(--gray-12)]">
                    <FileText className="h-5 w-5" />
                  </span>
                  <button
                    onClick={() => unfav(t.id)}
                    title="取消收藏"
                    className="rounded p-1.5 text-[var(--gray-12)] transition-colors hover:bg-[var(--gray-4)]"
                  >
                    <Star className="h-4 w-4 fill-current" />
                  </button>
                </div>
                <button onClick={() => setActiveId(t.id)} className="mt-3 text-left">
                  <div className="line-clamp-1 text-sm font-semibold text-[var(--gray-12)]">{name}</div>
                  <div className="mt-1 text-xs text-[var(--gray-9)]">{market}</div>
                </button>
                <div className="mt-4 flex items-center justify-between border-t border-[var(--gray-5)] pt-3 text-[11px] text-[var(--gray-7)]">
                  <span>{formatDate(t.updatedAt)}</span>
                  <button
                    onClick={() => setActiveId(t.id)}
                    className="inline-flex items-center gap-0.5 text-[var(--gray-12)] opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    打开 <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </PageContainer>
  );
}

export function TrashPage() {
  const [items, setItems] = React.useState<ThreadSummary[]>([]);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    try { setItems(await fetchTrashedThreads()); }
    catch { /* 静默 */ }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  const restore = async (id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id));
    try { await restoreThread(id); } catch { reload(); }
  };
  const purge = async (id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id));
    try { await purgeThread(id); } catch { reload(); }
  };

  return (
    <PageContainer>
      <PageHeader
        icon={<Trash2 className="h-5 w-5" />}
        title="回收站"
        subtitle="已删除的任务会在这里保留，可恢复或彻底清除。"
      />
      <Panel bodyClassName="p-0">
        {loading ? (
          <div className="space-y-2 p-5">
            {[0, 1].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Trash2 className="h-6 w-6" />}
            title="回收站是空的"
            hint="在「我的任务」中删除的内容会临时保留在这里。"
          />
        ) : (
          <div className="divide-y divide-hairline">
            {items.map((t) => {
              const { name, market } = parseTitle(t.title);
              return (
                <div key={t.id} className="flex items-center gap-4 px-5 py-4">
                  <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-[var(--gray-4)] text-[var(--gray-9)]">
                    <FileText className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-[var(--gray-12)]">{name}</div>
                    <div className="mt-0.5 text-xs text-[var(--gray-9)]">{market} · 删除于 {formatDate(t.updatedAt)}</div>
                  </div>
                  <StatusBadge status="neutral" label="已删除" />
                  <Button variant="secondary" size="sm" onClick={() => restore(t.id)}>
                    <RotateCcw className="h-3.5 w-3.5" />恢复
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => purge(t.id)} className="text-danger hover:bg-danger/10 hover:text-danger">
                    <Trash2 className="h-3.5 w-3.5" />彻底删除
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </PageContainer>
  );
}
