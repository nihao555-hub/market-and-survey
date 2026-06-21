"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import {
  Clock,
  Database,
  ChevronDown,
  Search,
  TrendingUp,
  Swords,
  Users,
  Lightbulb,
  MoreHorizontal,
  ArrowRight,
  Inbox,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  draftCategoryAtom,
  draftKindAtom,
  activeThreadIdAtom,
  threadsAtom,
  quickParamsAtom,
  activePageAtom,
  type PageKey,
} from "@/lib/atoms";
import { marketIso, marketLabel } from "@/lib/markets";
import { Flag } from "@/components/ui/Flag";
import { HotProductsSection } from "@/components/HotProductsSection";
import { formatDate, parseTitle } from "@/lib/thread-format";

const TOOLS: { key: PageKey; label: string; desc: string; icon: React.ReactNode }[] = [
  { key: "market", label: "市场扫描", desc: "规模 / 趋势 / 竞争格局", icon: <Search className="h-4 w-4" /> },
  { key: "trend", label: "趋势分析", desc: "Google Trends 与社交信号", icon: <TrendingUp className="h-4 w-4" /> },
  { key: "competitor", label: "竞品分析", desc: "Listing 与定价深度研究", icon: <Swords className="h-4 w-4" /> },
  { key: "audience", label: "受众分析", desc: "目标用户画像洞察", icon: <Users className="h-4 w-4" /> },
  { key: "opportunity", label: "机会发现", desc: "差异化与蓝海市场", icon: <Lightbulb className="h-4 w-4" /> },
];

export function WorkspaceHome() {
  const setDraft = useSetAtom(draftCategoryAtom);
  const setDraftKind = useSetAtom(draftKindAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const setPage = useSetAtom(activePageAtom);
  const [threads] = useAtom(threadsAtom);
  const [params, setParams] = useAtom(quickParamsAtom);
  const [input, setInput] = React.useState("");
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  const start = async (category: string) => {
    const c = category.trim();
    if (!c) return;
    try {
      const { checkUsage: check } = await import("@/lib/auth");
      const info = await check();
      if (info && !info.can_use) {
        alert(`Monthly AI research limit reached (${info.reports_used}/${info.reports_limit}). Please upgrade.`);
        return;
      }
    } catch {}
    setDraftKind("general");
    setDraft(c);
  };

  const firstMarket = (params.markets[0] as string) || "US";

  const recentRows = threads.slice(0, 8).map((t) => {
    const { name, market } = parseTitle(t.title);
    return {
      id: t.id,
      name,
      iso: marketIso(market),
      market,
      state: t.activeStreamId ? "running" : "done",
      progress: t.activeStreamId ? 60 : 100,
      time: formatDate(t.updatedAt),
    };
  });

  const recentCategories = React.useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const t of threads) {
      const { name } = parseTitle(t.title);
      if (name && name !== "未命名任务" && !seen.has(name)) {
        seen.add(name);
        out.push(name);
      }
      if (out.length >= 6) break;
    }
    return out;
  }, [threads]);

  return (
    <div className="mx-auto w-full max-w-[1100px]">
      {/* Hero research input */}
      <section className="rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] p-6">
        <h1 className="text-[20px] font-semibold text-[var(--gray-12)]">你想调研什么？</h1>
        <p className="mt-1 text-[13px] text-[var(--gray-11)]">
          输入产品品类或市场。AI 将自动完成趋势、竞品、痛点、利润和知识产权风险分析。
        </p>

        <div className="mt-4 flex items-center gap-2 rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-3)] p-1">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && start(input)}
            placeholder="例如：智能插座、宠物饮水机、户外露营装备、美国市场"
            className="min-w-0 flex-1 bg-transparent px-3 py-2 text-[14px] text-[var(--gray-12)] placeholder:text-[var(--gray-8)] focus:outline-none"
          />
          <button
            onClick={() => start(input)}
            disabled={!input.trim()}
            className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-[4px] bg-[var(--gray-12)] text-[var(--gray-1)] transition-colors hover:bg-[var(--gray-11)] disabled:opacity-30"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {/* Filter chips */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-2.5 py-1 text-[12px] font-medium text-[var(--gray-11)]">
            <Flag iso={marketIso(firstMarket)} size={12} />
            {marketLabel(firstMarket)}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-2.5 py-1 text-[12px] font-medium text-[var(--gray-11)]">
            <Clock className="h-3 w-3 text-[var(--gray-8)]" />
            近 30 天
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-2.5 py-1 text-[12px] font-medium text-[var(--gray-11)]">
            <Database className="h-3 w-3 text-[var(--gray-8)]" />
            所有数据源
          </span>
        </div>
      </section>

      {/* Hot products */}
      <HotProductsSection />

      {/* Recent categories */}
      {recentCategories.length > 0 && (
        <section className="mt-5">
          <div className="mb-2 text-[12px] font-medium text-[var(--gray-9)]">最近调研品类</div>
          <div className="flex flex-wrap items-center gap-2">
            {recentCategories.map((label) => (
              <button
                key={label}
                onClick={() => start(label)}
                className="rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-3 py-2 text-[13px] font-medium text-[var(--gray-11)] transition-colors hover:bg-[var(--bg-transparent-light)]"
              >
                {label}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Research tools */}
      <section className="mt-6">
        <h2 className="text-[14px] font-semibold text-[var(--gray-12)] mb-3">调研工具</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {TOOLS.map((t) => (
            <button
              key={t.key}
              onClick={() => setPage(t.key)}
              className="flex items-center gap-3 rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] p-3 text-left transition-colors hover:bg-[var(--bg-transparent-light)]"
            >
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-[8px] bg-[var(--gray-4)] text-[var(--gray-11)]">
                {t.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium text-[var(--gray-12)]">{t.label}</div>
                <div className="truncate text-[11px] text-[var(--gray-9)]">{t.desc}</div>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* Recent tasks */}
      <section className="mt-6 rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] overflow-hidden">
        <div className="flex items-center justify-between border-b border-[var(--gray-4)] px-5 py-3">
          <h2 className="text-[14px] font-semibold text-[var(--gray-12)]">最近任务</h2>
          <button onClick={() => setPage("tasks")} className="text-[12px] text-[var(--gray-9)] hover:text-[var(--gray-12)] transition-colors">查看全部</button>
        </div>
        {recentRows.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-5 py-14 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--gray-4)] text-[var(--gray-8)]">
              <Inbox className="h-5 w-5" />
            </span>
            <div className="mt-3 text-[13px] font-medium text-[var(--gray-12)]">还没有调研任务</div>
            <div className="mt-1 max-w-sm text-[12px] text-[var(--gray-9)]">
              在上方输入品类开始你的第一次调研。结果将自动显示在此处。
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-[var(--gray-4)] bg-[var(--gray-3)] text-left text-[11px] text-[var(--gray-9)]">
                  <th className="px-5 py-2.5 font-medium">名称</th>
                  <th className="px-3 py-2.5 font-medium">市场</th>
                  <th className="px-3 py-2.5 font-medium">创建时间</th>
                  <th className="px-3 py-2.5 font-medium">状态</th>
                  <th className="px-5 py-2.5 text-right font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {recentRows.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => setActiveId(t.id)}
                    className="cursor-pointer border-t border-[var(--gray-4)] transition-colors hover:bg-[var(--bg-transparent-light)]"
                  >
                    <td className="px-5 py-3 font-medium text-[var(--gray-12)]">{t.name}</td>
                    <td className="px-3 py-3">
                      <span className="inline-flex items-center gap-1.5 text-[var(--gray-11)]">
                        {t.iso ? <Flag iso={t.iso} size={14} /> : null}
                        {t.iso ? t.iso.toUpperCase() : t.market}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-[var(--gray-9)]">{t.time}</td>
                    <td className="px-3 py-3">
                      {t.state === "running" ? (
                        <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[var(--gray-11)]">
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--gray-8)]" />
                          分析中
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-green-700">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          已完成
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); setActiveId(t.id); }}
                        className="rounded-[4px] p-1 text-[var(--gray-8)] transition-colors hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
