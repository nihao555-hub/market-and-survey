"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import { FileText, ArrowRight, FileBarChart, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { activeThreadIdAtom, threadsAtom } from "@/lib/atoms";
import { fetchThreads, toggleFavorite } from "@/lib/api";
import { formatDate, parseTitle } from "@/lib/thread-format";
import { PageContainer, PageHeader, Panel, EmptyState, Skeleton } from "./primitives";

export function ReportsPage() {
  const [threads, setThreads] = useAtom(threadsAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    try { setThreads(await fetchThreads()); }
    catch { /* 静默 */ }
    finally { setLoading(false); }
  }, [setThreads]);
  React.useEffect(() => { reload(); }, [reload]);

  const reports = threads.filter((t) => !t.activeStreamId);

  const onFav = async (id: string) => {
    setThreads((prev) => prev.map((x) => (x.id === id ? { ...x, isFavorite: !x.isFavorite } : x)));
    try { await toggleFavorite(id); } catch { reload(); }
  };

  return (
    <PageContainer>
      <PageHeader
        icon={<FileText className="h-5 w-5" />}
        title="报告中心"
        subtitle="已完成调研任务产出的选品决策报告，可回看完整分析与证据链。"
      />

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-36 w-full rounded-2xl" />)}
        </div>
      ) : reports.length === 0 ? (
        <Panel bodyClassName="p-0">
          <EmptyState
            icon={<FileBarChart className="h-6 w-6" />}
            title="还没有可查看的报告"
            hint="完成一个调研任务后，AI 生成的选品报告会自动归档在这里。"
          />
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((t) => {
            const { name, market } = parseTitle(t.title);
            return (
              <div
                key={t.id}
                className="group flex flex-col rounded-2xl border border-hairline bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand">
                    <FileText className="h-5 w-5" />
                  </span>
                  <button
                    onClick={() => onFav(t.id)}
                    title={t.isFavorite ? "取消收藏" : "收藏"}
                    className={cn(
                      "rounded p-1.5 transition-colors hover:bg-surface-2",
                      t.isFavorite ? "text-brand" : "text-ink-subtle hover:text-ink"
                    )}
                  >
                    <Star className={cn("h-4 w-4", t.isFavorite && "fill-current")} />
                  </button>
                </div>
                <button onClick={() => setActiveId(t.id)} className="mt-3 text-left">
                  <div className="line-clamp-1 text-sm font-semibold text-ink">{name}</div>
                  <div className="mt-1 text-xs text-ink-subtle">{market}</div>
                </button>
                <div className="mt-4 flex items-center justify-between border-t border-hairline pt-3 text-[11px] text-ink-tertiary">
                  <span>{formatDate(t.updatedAt)}</span>
                  <button
                    onClick={() => setActiveId(t.id)}
                    className="inline-flex items-center gap-0.5 text-brand opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    查看报告 <ArrowRight className="h-3.5 w-3.5" />
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
