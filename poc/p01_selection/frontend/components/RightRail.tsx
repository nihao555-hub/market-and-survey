"use client";
import React from "react";
import { useAtomValue, useSetAtom } from "jotai";
import { ChevronRight, Loader2, Star, Inbox, Activity } from "lucide-react";
import { threadsAtom, activeThreadIdAtom, activePageAtom } from "@/lib/atoms";
import { parseTitle, formatDate } from "@/lib/thread-format";
import { marketIso } from "@/lib/markets";
import { Flag } from "@/components/ui/Flag";

function SectionCard({
  title,
  action,
  onAction,
  children,
}: {
  title: string;
  action?: string;
  onAction?: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-hairline bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {action && (
          <button
            onClick={onAction}
            className="inline-flex items-center gap-0.5 text-[11px] text-brand hover:underline"
          >
            {action}
            <ChevronRight className="h-3 w-3" />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

export function RightRail() {
  const threads = useAtomValue(threadsAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const setPage = useSetAtom(activePageAtom);

  const running = threads.filter((t) => t.activeStreamId);
  const favorites = threads.filter((t) => t.isFavorite);
  const completed = threads.filter((t) => !t.activeStreamId).length;

  const stats = [
    { label: "累计调研", value: threads.length, tone: "text-ink" },
    { label: "进行中", value: running.length, tone: "text-brand" },
    { label: "已完成", value: completed, tone: "text-success" },
    { label: "收藏", value: favorites.length, tone: "text-amber-600" },
  ];

  const Row = ({
    id,
    title,
    updatedAt,
    running: isRunning,
  }: {
    id: string;
    title: string;
    updatedAt?: string;
    running?: boolean;
  }) => {
    const { name, market } = parseTitle(title);
    const iso = marketIso(market);
    return (
      <button
        onClick={() => setActiveId(id)}
        className="flex w-full items-center gap-2.5 rounded-lg px-1.5 py-2 text-left transition-colors hover:bg-surface-1"
      >
        {iso ? (
          <Flag iso={iso} size={16} />
        ) : (
          <span className="h-4 w-4 flex-shrink-0 rounded-full bg-surface-3" />
        )}
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-ink">{name}</div>
          <div className="text-[11px] text-ink-subtle">{formatDate(updatedAt)}</div>
        </div>
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin text-brand" />
        ) : (
          <Star className="h-3.5 w-3.5 flex-shrink-0 fill-amber-400 text-amber-400" />
        )}
      </button>
    );
  };

  return (
    <aside className="hidden w-80 flex-shrink-0 overflow-y-auto border-l border-hairline bg-surface-1 px-4 py-6 xl:block">
      <div className="space-y-4">
        {/* 调研概览（真实统计） */}
        <SectionCard title="调研概览">
          <div className="grid grid-cols-2 gap-2.5">
            {stats.map((s) => (
              <div key={s.label} className="rounded-xl border border-hairline bg-surface-1 px-3 py-2.5">
                <div className={`text-xl font-semibold leading-none ${s.tone}`}>{s.value}</div>
                <div className="mt-1.5 text-[11px] text-ink-subtle">{s.label}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        {/* 进行中（真实运行任务） */}
        <SectionCard title="进行中">
          {running.length === 0 ? (
            <div className="flex flex-col items-center py-5 text-center">
              <Activity className="h-5 w-5 text-ink-tertiary" />
              <div className="mt-2 text-[11px] text-ink-subtle">暂无进行中的调研</div>
            </div>
          ) : (
            <div className="space-y-0.5">
              {running.slice(0, 5).map((t) => (
                <Row key={t.id} id={t.id} title={t.title} updatedAt={t.updatedAt} running />
              ))}
            </div>
          )}
        </SectionCard>

        {/* 收藏报告（真实收藏） */}
        <SectionCard
          title="收藏报告"
          action={favorites.length > 0 ? "全部收藏" : undefined}
          onAction={() => setPage("favorites")}
        >
          {favorites.length === 0 ? (
            <div className="flex flex-col items-center py-5 text-center">
              <Inbox className="h-5 w-5 text-ink-tertiary" />
              <div className="mt-2 text-[11px] text-ink-subtle">暂无收藏报告</div>
            </div>
          ) : (
            <div className="space-y-0.5">
              {favorites.slice(0, 5).map((t) => (
                <Row key={t.id} id={t.id} title={t.title} updatedAt={t.updatedAt} />
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </aside>
  );
}
