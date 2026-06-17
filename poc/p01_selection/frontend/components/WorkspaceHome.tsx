"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import {
  ArrowUp,
  Sparkles,
  Clock,
  Database,
  ChevronDown,
  Home,
  Mountain,
  Sparkle,
  PawPrint,
  Plug,
  Plus,
  TrendingUp,
  Swords,
  Users,
  KeyRound,
  Tag,
  PieChart,
  MoreHorizontal,
  ArrowRight,
  Target,
  BarChart3,
  Lightbulb,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  draftCategoryAtom,
  activeThreadIdAtom,
  threadsAtom,
  quickParamsAtom,
  activePageAtom,
} from "@/lib/atoms";
import { gqlRequest } from "@/lib/graphql-client";
import { marketIso, marketLabel } from "@/lib/markets";
import { Flag } from "@/components/ui/Flag";
import { formatDate, parseTitle } from "@/lib/thread-format";
import type { ThreadSummary } from "@/lib/agent-types";

const THREADS_QUERY = /* GraphQL */ `
  query Threads { threads { id title updatedAt activeStreamId } }
`;

const QUICK_CATEGORIES = [
  { label: "智能家居", icon: <Home className="h-5 w-5" />, tone: "text-brand bg-brand/10" },
  { label: "户外装备", icon: <Mountain className="h-5 w-5" />, tone: "text-emerald-600 bg-emerald-50" },
  { label: "美妆个护", icon: <Sparkle className="h-5 w-5" />, tone: "text-pink-600 bg-pink-50" },
  { label: "宠物用品", icon: <PawPrint className="h-5 w-5" />, tone: "text-amber-600 bg-amber-50" },
  { label: "3C 配件", icon: <Plug className="h-5 w-5" />, tone: "text-cyan-600 bg-cyan-50" },
];

const WORKFLOW = [
  { n: 1, label: "定义调研", desc: "明确品类与目标市场", icon: <Target className="h-4 w-4" /> },
  { n: 2, label: "市场分析", desc: "规模 / 趋势 / 需求", icon: <BarChart3 className="h-4 w-4" /> },
  { n: 3, label: "竞品洞察", desc: "对手 / 定价 / 评论", icon: <Swords className="h-4 w-4" /> },
  { n: 4, label: "机会挖掘", desc: "痛点 / 差异化空间", icon: <Lightbulb className="h-4 w-4" /> },
  { n: 5, label: "报告生成", desc: "可决策结论产出", icon: <FileText className="h-4 w-4" /> },
];

const TOOLS = [
  { label: "趋势探索", desc: "Google Trends 热度", icon: <TrendingUp className="h-4 w-4" /> },
  { label: "竞品分析", desc: "对手 listing 对比", icon: <Swords className="h-4 w-4" /> },
  { label: "受众洞察", desc: "目标人群画像", icon: <Users className="h-4 w-4" /> },
  { label: "关键词分析", desc: "搜索量与难度", icon: <KeyRound className="h-4 w-4" /> },
  { label: "定价分析", desc: "价格带与利润", icon: <Tag className="h-4 w-4" /> },
  { label: "市场规模", desc: "TAM / SAM 估算", icon: <PieChart className="h-4 w-4" /> },
];

export function WorkspaceHome() {
  const setDraft = useSetAtom(draftCategoryAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const setPage = useSetAtom(activePageAtom);
  const [threads, setThreads] = useAtom(threadsAtom);
  const [params, setParams] = useAtom(quickParamsAtom);
  const [input, setInput] = React.useState("");
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  React.useEffect(() => {
    (async () => {
      try {
        const data = await gqlRequest<{ threads: ThreadSummary[] }>(THREADS_QUERY);
        setThreads(data.threads || []);
      } catch {
        /* 后端没起时静默 */
      }
    })();
  }, [setThreads]);

  const start = (category: string) => {
    const c = category.trim();
    if (!c) return;
    setDraft(c);
  };

  const deep = mounted && params.modelChoice === "pro";
  const firstMarket = (params.markets[0] as string) || "US";

  return (
    <div className="mx-auto w-full max-w-[1180px] px-8 py-7">
      {/* Hero 调研入口 */}
      <section className="relative overflow-hidden rounded-2xl border border-brand/20 bg-gradient-to-br from-brand via-brand-light to-brand2 p-7 text-white shadow-md">
        <div className="pointer-events-none absolute -right-10 -top-12 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-12 right-32 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/hero-research.png"
          alt=""
          aria-hidden
          className="pointer-events-none absolute right-2 top-1/2 hidden h-[230px] w-auto -translate-y-1/2 select-none drop-shadow-xl lg:block"
        />
        <div className="relative max-w-[640px]">
          <h1 className="text-[28px] font-bold leading-tight tracking-tight">你想调研什么？</h1>
          <p className="mt-2 text-sm text-white/90">
            描述一个品类或市场，AI 自动完成趋势、竞品、痛点、利润与 IP 风险全流程调研。
          </p>

          <div className="mt-5 flex items-center gap-2 rounded-xl border border-white/20 bg-white/95 p-1.5 shadow-lg backdrop-blur">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && start(input)}
              placeholder="例如：智能插座、宠物饮水机、露营装备、北美市场、2024 趋势"
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

          {/* 筛选 chips */}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-xs">
              <Flag iso={marketIso(firstMarket)} size={14} />
              {marketLabel(firstMarket)}
              <ChevronDown className="h-3 w-3 opacity-70" />
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-xs">
              <Clock className="h-3.5 w-3.5" />
              近 30 天
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-xs">
              <Database className="h-3.5 w-3.5" />
              全部数据源
            </span>
            <button
              onClick={() => setParams((p) => ({ ...p, modelChoice: deep ? "flash" : "pro" }))}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-colors",
                deep ? "bg-white text-brand" : "bg-white/15 text-white hover:bg-white/25"
              )}
            >
              <Sparkles className="h-3.5 w-3.5" />
              深度调研
            </button>
          </div>
        </div>
      </section>

      {/* 品类快捷 */}
      <section className="mt-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {QUICK_CATEGORIES.map((c) => (
            <button
              key={c.label}
              onClick={() => start(c.label)}
              className="flex flex-col items-center gap-2 rounded-xl border border-hairline bg-white p-4 transition-all hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-sm"
            >
              <span className={cn("flex h-10 w-10 items-center justify-center rounded-xl", c.tone)}>
                {c.icon}
              </span>
              <span className="text-xs font-medium text-ink">{c.label}</span>
            </button>
          ))}
          <button
            onClick={() => start(input || "自定义品类")}
            className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-hairline-strong bg-white p-4 text-ink-subtle transition-all hover:-translate-y-0.5 hover:border-brand/40 hover:text-brand"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-1">
              <Plus className="h-5 w-5" />
            </span>
            <span className="text-xs font-medium">自定义调研</span>
          </button>
        </div>
      </section>

      {/* 调研工作流 stepper（静态） */}
      <section className="mt-6 rounded-2xl border border-hairline bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-ink">调研工作流</h2>
            <p className="text-xs text-ink-subtle">从问题到洞察，AI 全流程为你就绪</p>
          </div>
        </div>
        <div className="flex flex-col gap-2 md:flex-row md:items-stretch">
          {WORKFLOW.map((s, i) => (
            <React.Fragment key={s.n}>
              <div className="flex flex-1 items-start gap-3 rounded-xl border border-hairline bg-surface-1 p-3.5">
                <span className="relative flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand">
                  {s.icon}
                  <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-brand text-[9px] font-bold text-white">
                    {s.n}
                  </span>
                </span>
                <div className="min-w-0 pt-0.5">
                  <div className="text-sm font-medium text-ink">{s.label}</div>
                  <div className="mt-0.5 text-[11px] leading-snug text-ink-subtle">{s.desc}</div>
                </div>
              </div>
              {i < WORKFLOW.length - 1 && (
                <div className="hidden items-center text-ink-tertiary md:flex">
                  <ArrowRight className="h-4 w-4" />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </section>

      {/* 常用工具 */}
      <section className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">常用工具</h2>
          <button onClick={() => setPage("market")} className="text-xs text-brand hover:underline">更多工具</button>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {TOOLS.map((t) => (
            <button
              key={t.label}
              className="group flex items-center gap-3 rounded-xl border border-hairline bg-white p-3.5 text-left transition-all hover:border-brand/30 hover:shadow-sm"
            >
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand/10 text-brand">
                {t.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-ink">{t.label}</div>
                <div className="truncate text-[11px] text-ink-subtle">{t.desc}</div>
              </div>
              <ArrowRight className="h-4 w-4 flex-shrink-0 text-ink-tertiary opacity-0 transition-opacity group-hover:opacity-100" />
            </button>
          ))}
        </div>
      </section>

      {/* 最近任务 */}
      <section className="mt-6 rounded-2xl border border-hairline bg-white">
        <div className="flex items-center justify-between border-b border-hairline px-5 py-3.5">
          <h2 className="text-base font-semibold text-ink">最近任务</h2>
          <button onClick={() => setPage("tasks")} className="text-xs text-brand hover:underline">查看全部任务</button>
        </div>
        {threads.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-ink-subtle">
            暂无调研任务，从上方输入一个品类即可开始。
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-ink-subtle">
                  <th className="px-5 py-2.5 font-medium">任务名称</th>
                  <th className="px-3 py-2.5 font-medium">目标市场</th>
                  <th className="px-3 py-2.5 font-medium">创建时间</th>
                  <th className="px-3 py-2.5 font-medium">进度状态</th>
                  <th className="px-5 py-2.5 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {threads.slice(0, 8).map((t) => {
                  const { name, market } = parseTitle(t.title);
                  const running = !!t.activeStreamId;
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
                        {running ? (
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
      </section>
    </div>
  );
}
