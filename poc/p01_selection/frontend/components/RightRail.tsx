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
    <div className="rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-[var(--gray-12)]">{title}</h3>
        {action && (
          <button
            onClick={onAction}
            className="inline-flex items-center gap-0.5 text-[11px] text-[var(--gray-9)] hover:text-[var(--gray-12)] transition-colors"
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
    { label: "累计调研", value: threads.length, tone: "text-[var(--gray-12)]" },
    { label: "进行中", value: running.length, tone: "text-[var(--gray-11)]" },
    { label: "已完成", value: completed, tone: "text-green-700" },
    { label: "收藏", value: favorites.length, tone: "text-[var(--gray-11)]" },
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
        className="flex w-full items-center gap-2.5 rounded-[4px] px-1.5 py-2 text-left transition-colors hover:bg-[var(--bg-transparent-light)]"
      >
        {iso ? (
          <Flag iso={iso} size={16} />
        ) : (
          <span className="h-4 w-4 flex-shrink-0 rounded-full bg-[var(--gray-5)]" />
        )}
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-medium text-[var(--gray-12)]">{name}</div>
          <div className="text-[11px] text-[var(--gray-9)]">{formatDate(updatedAt)}</div>
        </div>
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin text-[var(--gray-8)]" />
        ) : (
          <Star className="h-3.5 w-3.5 flex-shrink-0 fill-[var(--gray-6)] text-[var(--gray-6)]" />
        )}
      </button>
    );
  };

  return (
    <aside className="hidden w-72 flex-shrink-0 overflow-y-auto border-l border-[var(--gray-5)] bg-[var(--gray-3)] px-4 py-5 xl:block">
      <div className="space-y-4">
        <SectionCard title="调研概览">
          <div className="grid grid-cols-2 gap-2.5">
            {stats.map((s) => (
              <div key={s.label} className="rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-3)] px-3 py-2.5">
                <div className={`text-xl font-semibold leading-none ${s.tone}`}>{s.value}</div>
                <div className="mt-1.5 text-[11px] text-[var(--gray-9)]">{s.label}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="进行中">
          {running.length === 0 ? (
            <div className="flex flex-col items-center py-5 text-center">
              <Activity className="h-5 w-5 text-[var(--gray-8)]" />
              <div className="mt-2 text-[11px] text-[var(--gray-9)]">暂无进行中的调研</div>
            </div>
          ) : (
            <div className="space-y-0.5">
              {running.slice(0, 5).map((t) => (
                <Row key={t.id} id={t.id} title={t.title} updatedAt={t.updatedAt} running />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="收藏报告"
          action={favorites.length > 0 ? "全部收藏" : undefined}
          onAction={() => setPage("favorites")}
        >
          {favorites.length === 0 ? (
            <div className="flex flex-col items-center py-5 text-center">
              <Inbox className="h-5 w-5 text-[var(--gray-8)]" />
              <div className="mt-2 text-[11px] text-[var(--gray-9)]">暂无收藏报告</div>
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
