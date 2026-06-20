"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import {
  Sparkles,
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
import { HeroArt } from "@/components/HeroArt";
import { HotProductsSection } from "@/components/HotProductsSection";
import { formatDate, parseTitle } from "@/lib/thread-format";

// 调研工具入口：与「调研中心」一一对应，点击直达对应功能页（同一个 agent 的 5 个聚焦入口）。
const TOOLS: { key: PageKey; label: string; desc: string; icon: React.ReactNode }[] = [
  { key: "market", label: "市场调研", desc: "规模 / 趋势 / 竞争全景", icon: <Search className="h-4 w-4" /> },
  { key: "trend", label: "趋势探索", desc: "Google Trends 热度走势", icon: <TrendingUp className="h-4 w-4" /> },
  { key: "competitor", label: "竞品分析", desc: "对手 listing 与定价", icon: <Swords className="h-4 w-4" /> },
  { key: "audience", label: "受众洞察", desc: "目标人群画像", icon: <Users className="h-4 w-4" /> },
  { key: "opportunity", label: "机会挖掘", desc: "需求缺口与蓝海", icon: <Lightbulb className="h-4 w-4" /> },
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
    // Check usage limit before starting
    try {
      const { checkUsage: check } = await import("@/lib/auth");
      const info = await check();
      if (info && !info.can_use) {
        alert(`本月 AI 调研次数已用完（${info.reports_used}/${info.reports_limit}）。请升级套餐获取更多次数。`);
        return;
      }
    } catch { /* allow if check fails */ }
    setDraftKind("general");
    setDraft(c);
  };

  const deep = mounted && params.modelChoice === "pro";
  const firstMarket = (params.markets[0] as string) || "US";

  // 真实历史任务行（不再有任何 demo 兜底）。
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

  // 真实「最近调研品类」：从历史任务标题里去重提取，无历史则不展示。
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
    <div className="mx-auto w-full max-w-[1180px] px-8 py-7">
      {/* Hero 调研入口 */}
      <section className="relative overflow-hidden rounded-2xl border border-brand/20 bg-gradient-to-br from-brand via-brand-light to-brand2 p-7 text-white shadow-md">
        <div className="pointer-events-none absolute -right-10 -top-12 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-12 right-32 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
        {/* 半透明矢量插画：天然融入橙色渐变（无栅格底/无硬边） */}
        <HeroArt className="pointer-events-none absolute -right-4 top-1/2 hidden h-[280px] w-auto -translate-y-1/2 lg:block" />
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
              className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand text-white transition-colors hover:bg-brand-hover disabled:opacity-40"
            >
              <ArrowRight className="h-5 w-5" />
            </button>
          </div>

          {/* 筛选 chips */}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/95 px-3 py-1.5 text-xs font-medium text-ink shadow-sm">
              <Flag iso={marketIso(firstMarket)} size={14} />
              {marketLabel(firstMarket)}
              <ChevronDown className="h-3 w-3 text-ink-subtle" />
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/95 px-3 py-1.5 text-xs font-medium text-ink shadow-sm">
              <Clock className="h-3.5 w-3.5 text-violet-500" />
              近 30 天
              <ChevronDown className="h-3 w-3 text-ink-subtle" />
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/95 px-3 py-1.5 text-xs font-medium text-ink shadow-sm">
              <Database className="h-3.5 w-3.5 text-sky-500" />
              全部数据源
              <ChevronDown className="h-3 w-3 text-ink-subtle" />
            </span>
            <button
              onClick={() => setParams((p) => ({ ...p, modelChoice: deep ? "flash" : "pro" }))}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium shadow-sm transition-colors",
                deep ? "bg-white text-brand" : "bg-white/95 text-ink hover:bg-white"
              )}
            >
              <Sparkles className="h-3.5 w-3.5 text-brand" />
              深度调研
              <ChevronDown className="h-3 w-3 text-ink-subtle" />
            </button>
          </div>
        </div>
      </section>

      {/* 实时社媒选品榜：工作台醒目位（Hero 正下方），TikTok Shop 海外实时爆款 */}
      <HotProductsSection />

      {/* 最近调研品类（真实历史，去重；无历史时不展示） */}
      {recentCategories.length > 0 && (
        <section className="mt-5">
          <div className="mb-2.5 text-xs font-medium text-ink-subtle">最近调研品类</div>
          <div className="flex flex-wrap items-center gap-2.5">
            {recentCategories.map((label) => (
              <button
                key={label}
                onClick={() => start(label)}
                className="flex min-w-[120px] items-center gap-2.5 rounded-xl border border-hairline bg-white px-4 py-2.5 transition-all hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-sm"
              >
                <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-brand/10 text-brand">
                  <Search className="h-4 w-4" />
                </span>
                <span className="text-sm font-medium text-ink">{label}</span>
              </button>
            ))}
            <button
              onClick={() => start(input || "自定义品类")}
              className="flex flex-shrink-0 items-center gap-1.5 rounded-xl border border-dashed border-hairline-strong bg-white px-4 py-2.5 text-sm font-medium text-ink-subtle transition-all hover:-translate-y-0.5 hover:border-brand/40 hover:text-brand"
            >
              <ChevronDown className="h-4 w-4" />
              自定义调研
            </button>
          </div>
        </section>
      )}

      {/* 调研工具：直达 5 个聚焦入口 */}
      <section className="mt-6">
        <div className="mb-3">
          <h2 className="text-base font-semibold text-ink">调研工具</h2>
          <p className="text-xs text-ink-subtle">同一个 AI 调研 Agent 的 5 个聚焦入口，点击直达。</p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {TOOLS.map((t) => (
            <button
              key={t.key}
              onClick={() => setPage(t.key)}
              className="group flex items-center gap-3 rounded-xl border border-hairline bg-white p-3.5 text-left transition-all hover:border-brand/30 hover:shadow-sm"
            >
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand/10 text-brand">
                {t.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-ink">{t.label}</div>
                <div className="truncate text-[11px] text-ink-subtle">{t.desc}</div>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* 最近任务（真实历史） */}
      <section className="mt-6 rounded-2xl border border-hairline bg-white">
        <div className="flex items-center justify-between border-b border-hairline px-5 py-3.5">
          <h2 className="text-base font-semibold text-ink">最近任务</h2>
          <button onClick={() => setPage("tasks")} className="text-xs text-brand hover:underline">查看全部任务</button>
        </div>
        {recentRows.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-5 py-14 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-2 text-ink-tertiary">
              <Inbox className="h-6 w-6" />
            </span>
            <div className="mt-3 text-sm font-medium text-ink">还没有调研任务</div>
            <div className="mt-1 max-w-sm text-xs text-ink-subtle">
              在上方输入一个品类或市场，发起你的第一个真实调研，结果会自动出现在这里。
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-hairline bg-surface-1 text-left text-[11px] text-ink-subtle">
                  <th className="px-5 py-2.5 font-medium">任务名称</th>
                  <th className="px-3 py-2.5 font-medium">目标市场</th>
                  <th className="px-3 py-2.5 font-medium">创建时间</th>
                  <th className="px-3 py-2.5 font-medium">进度</th>
                  <th className="px-5 py-2.5 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {recentRows.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => setActiveId(t.id)}
                    className="cursor-pointer border-t border-hairline transition-colors hover:bg-surface-1"
                  >
                    <td className="px-5 py-3 font-medium text-ink">{t.name}</td>
                    <td className="px-3 py-3">
                      <span className="inline-flex items-center gap-2 text-ink-muted">
                        {t.iso ? <Flag iso={t.iso} size={16} /> : null}
                        {t.iso ? `${t.iso.toUpperCase()} ${t.market}` : t.market}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-ink-subtle">{t.time}</td>
                    <td className="px-3 py-3">
                      {t.state === "running" ? (
                        <div className="max-w-[170px]">
                          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-muted">
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-brand" />
                            分析中 <span className="text-ink-subtle">{t.progress}%</span>
                          </span>
                          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
                            <div
                              className="h-full rounded-full bg-brand"
                              style={{ width: `${t.progress}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-success">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          已完成
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
