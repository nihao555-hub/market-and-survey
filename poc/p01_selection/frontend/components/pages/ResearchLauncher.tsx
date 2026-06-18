"use client";
import React from "react";
import { useSetAtom } from "jotai";
import { ArrowUp, Sparkles, History, Star, Trash2, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  draftCategoryAtom,
  draftKindAtom,
  activeThreadIdAtom,
} from "@/lib/atoms";
import { fetchThreadsByKind, toggleFavorite, deleteThread } from "@/lib/api";
import { formatDate, parseTitle } from "@/lib/thread-format";
import type { ThreadSummary, ResearchKind } from "@/lib/agent-types";
import {
  PageContainer,
  PageHeader,
  Panel,
  EmptyState,
  StatusBadge,
  DataTable,
  Skeleton,
  type Column,
} from "./primitives";

export interface ResearchConfig {
  key: ResearchKind;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  placeholder: string;
  examples: string[];
  dimensions: { title: string; desc: string; icon: React.ReactNode }[];
}

export function ResearchLauncher({ config }: { config: ResearchConfig }) {
  const setDraft = useSetAtom(draftCategoryAtom);
  const setDraftKind = useSetAtom(draftKindAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const [input, setInput] = React.useState("");

  const start = (text: string) => {
    const c = text.trim();
    if (!c) return;
    setDraftKind(config.key);
    setDraft(c);
  };

  return (
    <PageContainer>
      <PageHeader icon={config.icon} title={config.title} subtitle={config.subtitle} />

      {/* 调研入口 */}
      <section className="relative overflow-hidden rounded-2xl border border-brand/20 bg-gradient-to-br from-brand via-brand-light to-brand2 p-6 text-white shadow-md">
        <div className="pointer-events-none absolute -right-10 -top-12 h-44 w-44 rounded-full bg-white/10 blur-2xl" />
        <div className="relative max-w-2xl">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-xs font-medium">
            <Sparkles className="h-3.5 w-3.5" />
            AI 驱动 · {config.title}
          </div>
          <h2 className="mt-3 text-xl font-semibold">{config.placeholder}</h2>

          <div className="mt-4 flex items-center gap-2 rounded-xl border border-white/20 bg-white/95 p-1.5 shadow-lg backdrop-blur">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && start(input)}
              placeholder="输入一个品类、品牌或市场关键词…"
              className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none"
            />
            <button
              onClick={() => start(input)}
              disabled={!input.trim()}
              className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand text-white transition-colors hover:bg-brand-hover disabled:opacity-40"
            >
              <ArrowUp className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {config.examples.map((ex) => (
              <button
                key={ex}
                onClick={() => start(ex)}
                className="rounded-full bg-white/15 px-2.5 py-1 text-xs text-white transition-colors hover:bg-white/25"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 分析维度 */}
      <h3 className="mb-3 mt-7 text-sm font-semibold text-ink">分析维度</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {config.dimensions.map((d) => (
          <Panel key={d.title} className="transition-shadow hover:shadow-sm" bodyClassName="p-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand/10 text-brand">
              {d.icon}
            </span>
            <div className="mt-3 text-sm font-medium text-ink">{d.title}</div>
            <div className="mt-1 text-xs leading-relaxed text-ink-subtle">{d.desc}</div>
          </Panel>
        ))}
      </div>

      {/* 本类型历史调研 */}
      <ResearchHistory
        kind={config.key}
        title={config.title}
        onOpen={(id) => setActiveId(id)}
      />
    </PageContainer>
  );
}

/** 该功能页专属的历史调研列表（按 kind 过滤，可重看 / 收藏 / 删除） */
function ResearchHistory({
  kind,
  title,
  onOpen,
}: {
  kind: ResearchKind;
  title: string;
  onOpen: (threadId: string) => void;
}) {
  const [items, setItems] = React.useState<ThreadSummary[]>([]);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    try {
      setItems(await fetchThreadsByKind(kind));
    } catch {
      /* 后端未启动时静默 */
    } finally {
      setLoading(false);
    }
  }, [kind]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  const onFav = async (t: ThreadSummary) => {
    setItems((prev) => prev.map((x) => (x.id === t.id ? { ...x, isFavorite: !x.isFavorite } : x)));
    try {
      await toggleFavorite(t.id);
    } catch {
      reload();
    }
  };

  const onDelete = async (t: ThreadSummary) => {
    setItems((prev) => prev.filter((x) => x.id !== t.id));
    try {
      await deleteThread(t.id);
    } catch {
      reload();
    }
  };

  const columns: Column<ThreadSummary>[] = [
    {
      key: "name",
      header: "调研名称",
      render: (t) => <span className="font-medium text-ink">{parseTitle(t.title).name}</span>,
    },
    {
      key: "market",
      header: "目标市场",
      render: (t) => <span className="text-ink-muted">{parseTitle(t.title).market}</span>,
    },
    {
      key: "time",
      header: "创建时间",
      render: (t) => <span className="text-ink-subtle">{formatDate(t.updatedAt)}</span>,
    },
    {
      key: "status",
      header: "状态",
      render: (t) =>
        t.activeStreamId ? (
          <StatusBadge status="running" label="分析中" />
        ) : (
          <StatusBadge status="done" label="已完成" />
        ),
    },
    {
      key: "actions",
      header: "操作",
      align: "right",
      render: (t) => (
        <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => onFav(t)}
            title={t.isFavorite ? "取消收藏" : "收藏"}
            className={cn(
              "rounded p-1.5 transition-colors hover:bg-surface-2",
              t.isFavorite ? "text-brand" : "text-ink-subtle hover:text-ink"
            )}
          >
            <Star className={cn("h-4 w-4", t.isFavorite && "fill-current")} />
          </button>
          <button
            onClick={() => onDelete(t)}
            title="移入回收站"
            className="rounded p-1.5 text-ink-subtle transition-colors hover:bg-danger/10 hover:text-danger"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <section className="mt-7">
      <div className="mb-3 flex items-center gap-2">
        <History className="h-4 w-4 text-ink-subtle" />
        <h3 className="text-sm font-semibold text-ink">{title}历史</h3>
        {!loading && items.length > 0 && (
          <span className="rounded-full bg-surface-2 px-1.5 text-[11px] text-ink-subtle">
            {items.length}
          </span>
        )}
      </div>
      <Panel bodyClassName="p-0">
        {loading ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <DataTable
            columns={columns}
            rows={items}
            getRowKey={(t) => t.id}
            onRowClick={(t) => onOpen(t.id)}
            empty={
              <EmptyState
                icon={<Inbox className="h-6 w-6" />}
                title={`暂无${title}记录`}
                hint="在上方输入一个关键词即可发起调研，完成后会出现在这里。"
              />
            }
          />
        )}
      </Panel>
    </section>
  );
}
