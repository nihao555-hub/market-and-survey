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
  { key: "market", label: "Market scan", desc: "Size / trends / competitive landscape", icon: <Search className="h-4 w-4" /> },
  { key: "trend", label: "Trend analysis", desc: "Google Trends & social signals", icon: <TrendingUp className="h-4 w-4" /> },
  { key: "competitor", label: "Competitors", desc: "Listing & pricing deep-dive", icon: <Swords className="h-4 w-4" /> },
  { key: "audience", label: "Audience", desc: "Target persona insights", icon: <Users className="h-4 w-4" /> },
  { key: "opportunity", label: "Opportunities", desc: "Gaps & blue ocean niches", icon: <Lightbulb className="h-4 w-4" /> },
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
      <section className="rounded-xl border border-neutral-200 bg-white p-6">
        <h1 className="text-[20px] font-semibold text-neutral-900">What would you like to research?</h1>
        <p className="mt-1 text-[13px] text-neutral-500">
          Describe a product category or market. AI will automatically complete trend, competitor, pain-point, profit, and IP risk analysis.
        </p>

        <div className="mt-4 flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 p-1">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && start(input)}
            placeholder="e.g. smart plugs, pet water fountain, camping gear, US market"
            className="min-w-0 flex-1 bg-transparent px-3 py-2 text-[13px] text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
          />
          <button
            onClick={() => start(input)}
            disabled={!input.trim()}
            className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-neutral-900 text-white transition-colors hover:bg-neutral-800 disabled:opacity-30"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {/* Filter chips */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-2.5 py-1 text-[12px] font-medium text-neutral-600">
            <Flag iso={marketIso(firstMarket)} size={12} />
            {marketLabel(firstMarket)}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-2.5 py-1 text-[12px] font-medium text-neutral-600">
            <Clock className="h-3 w-3 text-neutral-400" />
            Last 30 days
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-2.5 py-1 text-[12px] font-medium text-neutral-600">
            <Database className="h-3 w-3 text-neutral-400" />
            All sources
          </span>
        </div>
      </section>

      {/* Hot products */}
      <HotProductsSection />

      {/* Recent categories */}
      {recentCategories.length > 0 && (
        <section className="mt-5">
          <div className="mb-2 text-[12px] font-medium text-neutral-500">Recent categories</div>
          <div className="flex flex-wrap items-center gap-2">
            {recentCategories.map((label) => (
              <button
                key={label}
                onClick={() => start(label)}
                className="rounded-md border border-neutral-200 bg-white px-3 py-2 text-[13px] font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
              >
                {label}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Research tools */}
      <section className="mt-6">
        <h2 className="text-[14px] font-semibold text-neutral-900 mb-3">Research tools</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {TOOLS.map((t) => (
            <button
              key={t.key}
              onClick={() => setPage(t.key)}
              className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white p-3 text-left transition-colors hover:bg-neutral-50"
            >
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-neutral-100 text-neutral-600">
                {t.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium text-neutral-900">{t.label}</div>
                <div className="truncate text-[11px] text-neutral-500">{t.desc}</div>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* Recent tasks */}
      <section className="mt-6 rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div className="flex items-center justify-between border-b border-neutral-200 px-5 py-3">
          <h2 className="text-[14px] font-semibold text-neutral-900">Recent tasks</h2>
          <button onClick={() => setPage("tasks")} className="text-[12px] text-neutral-500 hover:text-neutral-900 transition-colors">View all</button>
        </div>
        {recentRows.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-5 py-14 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-100 text-neutral-400">
              <Inbox className="h-5 w-5" />
            </span>
            <div className="mt-3 text-[13px] font-medium text-neutral-900">No research tasks yet</div>
            <div className="mt-1 max-w-sm text-[12px] text-neutral-500">
              Enter a category above to start your first research. Results will appear here automatically.
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-neutral-100 bg-neutral-50 text-left text-[11px] text-neutral-500">
                  <th className="px-5 py-2.5 font-medium">Name</th>
                  <th className="px-3 py-2.5 font-medium">Market</th>
                  <th className="px-3 py-2.5 font-medium">Created</th>
                  <th className="px-3 py-2.5 font-medium">Status</th>
                  <th className="px-5 py-2.5 text-right font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {recentRows.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => setActiveId(t.id)}
                    className="cursor-pointer border-t border-neutral-100 transition-colors hover:bg-neutral-50"
                  >
                    <td className="px-5 py-3 font-medium text-neutral-900">{t.name}</td>
                    <td className="px-3 py-3">
                      <span className="inline-flex items-center gap-1.5 text-neutral-600">
                        {t.iso ? <Flag iso={t.iso} size={14} /> : null}
                        {t.iso ? t.iso.toUpperCase() : t.market}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-neutral-500">{t.time}</td>
                    <td className="px-3 py-3">
                      {t.state === "running" ? (
                        <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-neutral-600">
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-neutral-400" />
                          Analyzing
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-green-700">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Done
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); setActiveId(t.id); }}
                        className="rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
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
