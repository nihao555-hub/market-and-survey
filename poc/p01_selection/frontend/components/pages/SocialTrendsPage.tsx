"use client";
import React, { useRef, useEffect } from "react";
import { Flame, RefreshCw, Clock, Hash, Layers, Music2, Twitter, Citrus, BarChart3, TrendingUp } from "lucide-react";
import type { EChartsOption } from "echarts";
import {
  fetchDailyRefreshStatus, fetchDataSnapshots, fetchAllSnapshots,
  type DataSnapshot, type RefreshStatus,
} from "@/lib/api";
import {
  PageContainer, PageHeader, StatTile, Button, StatusBadge, EmptyState, Skeleton,
  type StatusKind,
} from "./primitives";
import { cn } from "@/lib/utils";

const SOCIAL_TREND_TERM = "🔥 实时社媒趋势";

const PLATFORMS: { source: string; label: string; icon: React.ReactNode; accent: string; color: string }[] = [
  { source: "trend_tiktok", label: "TikTok", icon: <Music2 className="h-4 w-4" />, accent: "text-pink-500", color: "#ec4899" },
  { source: "trend_twitter", label: "X / Twitter", icon: <Twitter className="h-4 w-4" />, accent: "text-blue-500", color: "#3b82f6" },
  { source: "trend_lemon8", label: "Lemon8", icon: <Citrus className="h-4 w-4" />, accent: "text-lime-500", color: "#84cc16" },
];

const STATUS_MAP: Record<string, { kind: StatusKind; label: string }> = {
  ok: { kind: "done", label: "已获取" },
  empty: { kind: "neutral", label: "暂无数据" },
  error: { kind: "error", label: "获取失败" },
  unavailable: { kind: "pending", label: "通道未就绪" },
};
const statusInfo = (s: string) => STATUS_MAP[s] ?? { kind: "neutral" as StatusKind, label: s };

function fmtTime(iso?: string | null): string {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("zh-CN", { hour12: false }); } catch { return iso ?? "—"; }
}
function fmtShortTime(iso?: string | null): string {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); } catch { return ""; }
}

interface TrendItem { keyword?: string; heat?: number | null; views?: number | null; label?: string | null; }

function fmtHeat(n?: number | null): string | null {
  if (typeof n !== "number" || !isFinite(n) || n <= 0) return null;
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  return String(n);
}

// ─── ECharts wrapper ───
function TrendChart({ option, height = 320 }: { option: EChartsOption; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inst = useRef<unknown>(null);
  useEffect(() => {
    if (!ref.current) return;
    let disposed = false;
    import("echarts").then((ec) => {
      if (disposed || !ref.current) return;
      if (inst.current) (inst.current as { dispose: () => void }).dispose();
      const chart = ec.init(ref.current, undefined, { renderer: "canvas" });
      chart.setOption({
        backgroundColor: "transparent",
        grid: { left: 50, right: 20, top: 40, bottom: 40, containLabel: true },
        tooltip: { trigger: "axis", backgroundColor: "#fff", borderColor: "#e5e5e5", textStyle: { color: "#333", fontSize: 12 } },
        ...option,
      } as EChartsOption);
      inst.current = chart;
      const ro = new ResizeObserver(() => chart.resize());
      ro.observe(ref.current);
      return () => ro.disconnect();
    });
    return () => { disposed = true; if (inst.current) (inst.current as { dispose: () => void }).dispose(); inst.current = null; };
  }, [option]);
  return <div ref={ref} style={{ width: "100%", height }} />;
}

// ─── Build chart options from historical data ───
function buildHotwordCountChart(history: DataSnapshot[]): EChartsOption {
  const byRun = new Map<string, DataSnapshot[]>();
  for (const s of history) {
    const key = s.capturedAt?.slice(0, 16) || s.id;
    if (!byRun.has(key)) byRun.set(key, []);
    byRun.get(key)!.push(s);
  }
  const entries = [...byRun.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  if (entries.length < 1) return {};

  const times = entries.map(([t]) => fmtShortTime(t) || t);
  return {
    legend: { data: PLATFORMS.map((p) => p.label), bottom: 0, textStyle: { fontSize: 11, color: "#888" }, type: "scroll" },
    xAxis: { type: "category", data: times, axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
    yAxis: { type: "value", name: "热词数量", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f5f5f5" } } },
    series: PLATFORMS.map((p) => ({
      name: p.label,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      areaStyle: { opacity: 0.06 },
      itemStyle: { color: p.color },
      data: entries.map(([, snaps]) => {
        const snap = snaps.find((s) => s.source === p.source);
        const items = (snap?.payload?.items || []) as unknown[];
        return items.length || null;
      }),
    })),
  };
}

function buildTopHeatChart(history: DataSnapshot[]): EChartsOption {
  const byRun = new Map<string, DataSnapshot[]>();
  for (const s of history) {
    const key = s.capturedAt?.slice(0, 16) || s.id;
    if (!byRun.has(key)) byRun.set(key, []);
    byRun.get(key)!.push(s);
  }
  const entries = [...byRun.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  if (entries.length < 1) return {};

  const times = entries.map(([t]) => fmtShortTime(t) || t);
  return {
    legend: { data: PLATFORMS.map((p) => p.label), bottom: 0, textStyle: { fontSize: 11, color: "#888" }, type: "scroll" },
    xAxis: { type: "category", data: times, axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
    yAxis: { type: "value", name: "Top1 热度", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f5f5f5" } } },
    series: PLATFORMS.map((p) => ({
      name: p.label,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: p.color },
      data: entries.map(([, snaps]) => {
        const snap = snaps.find((s) => s.source === p.source);
        const items = (snap?.payload?.items || []) as TrendItem[];
        const top = items[0];
        return (top?.heat ?? top?.views ?? null) as number | null;
      }),
    })),
  };
}

type ChartMode = "count" | "heat";

export function SocialTrendsPage() {
  const [status, setStatus] = React.useState<RefreshStatus | null>(null);
  const [snapshots, setSnapshots] = React.useState<DataSnapshot[]>([]);
  const [history, setHistory] = React.useState<DataSnapshot[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [reloading, setReloading] = React.useState(false);
  const [chartMode, setChartMode] = React.useState<ChartMode>("count");

  const reload = React.useCallback(async () => {
    setReloading(true);
    try {
      const [st, snaps, hist] = await Promise.all([
        fetchDailyRefreshStatus(),
        fetchDataSnapshots({ term: SOCIAL_TREND_TERM, limit: 50 }),
        fetchAllSnapshots({ term: SOCIAL_TREND_TERM, limit: 500 }),
      ]);
      setStatus(st);
      setSnapshots(snaps);
      setHistory(hist);
    } catch { /* silent */ }
    finally { setLoading(false); setReloading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  const bySource = React.useMemo(() => {
    const m = new Map<string, DataSnapshot>();
    for (const s of snapshots) m.set(s.source, s);
    return m;
  }, [snapshots]);

  const countChartOpt = React.useMemo(() => buildHotwordCountChart(history), [history]);
  const heatChartOpt = React.useMemo(() => buildTopHeatChart(history), [history]);

  const okPlatforms = PLATFORMS.filter((p) => bySource.get(p.source)?.realData).length;
  const totalKeywords = React.useMemo(
    () => snapshots.reduce((acc, s) => acc + (Array.isArray(s.payload?.items) ? s.payload.items.length : 0), 0),
    [snapshots],
  );
  const channelOk = status?.tier2ChannelOk ?? false;
  const hasAny = snapshots.length > 0;
  const hasHistory = history.length > 0;

  return (
    <PageContainer>
      <PageHeader
        icon={<Flame className="h-5 w-5" />}
        title="社媒趋势"
        subtitle="8 大平台热搜走势 · 像看K线一样看热搜趋势 · 每 2 小时自动刷新"
        actions={
          <Button variant="secondary" size="sm" loading={reloading} onClick={reload}>
            <RefreshCw className="h-3.5 w-3.5" />刷新
          </Button>
        }
      />

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-[320px] w-full" />
        </div>
      ) : (
        <>
          {/* Stats overview */}
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="最近更新" value={fmtTime(status?.finishedAt)} icon={<Clock className="h-4 w-4" />} />
            <StatTile label="覆盖平台" value={`${okPlatforms} / ${PLATFORMS.length}`} icon={<Layers className="h-4 w-4" />} />
            <StatTile label="热词总数" value={String(totalKeywords)} icon={<Hash className="h-4 w-4" />} />
            <StatTile
              label="趋势通道"
              value={channelOk ? "已就绪" : "未就绪"}
              tone={channelOk ? "text-success" : "text-[var(--gray-9)]"}
              icon={<Flame className="h-4 w-4" />}
            />
          </div>

          {!channelOk && (
            <div className="mb-5 rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-3)] px-3 py-2 text-xs text-[var(--gray-9)]">
              社媒趋势通道（TikHub）需配置 <span className="font-medium text-[var(--gray-8)]">TIKHUB_API_KEY</span>；通道未就绪时如实标注，<span className="font-medium text-[var(--gray-8)]">不编造数据</span>，接入后自动补齐。
            </div>
          )}

          {/* ═══ Trend Charts (hero section) ═══ */}
          {hasHistory && (
            <section className="mb-6 rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] overflow-hidden">
              <div className="flex items-center justify-between border-b border-surface-3 px-5 py-3">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-[var(--gray-12)]">
                  <TrendingUp className="h-4 w-4 text-[var(--gray-9)]" />
                  平台趋势走势
                </h2>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setChartMode("count")}
                    className={cn(
                      "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                      chartMode === "count" ? "bg-ink text-white" : "text-[var(--gray-9)] hover:bg-[var(--gray-3)] hover:text-[var(--gray-12)]"
                    )}
                  >
                    热词数量
                  </button>
                  <button
                    onClick={() => setChartMode("heat")}
                    className={cn(
                      "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                      chartMode === "heat" ? "bg-ink text-white" : "text-[var(--gray-9)] hover:bg-[var(--gray-3)] hover:text-[var(--gray-12)]"
                    )}
                  >
                    Top1 热度
                  </button>
                </div>
              </div>
              <div className="px-2 pt-2 pb-1">
                <TrendChart
                  option={chartMode === "count" ? countChartOpt : heatChartOpt}
                  height={320}
                />
              </div>
            </section>
          )}

          {/* ═══ Platform cards (with keyword lists below chart) ═══ */}
          {!hasAny ? (
            <EmptyState
              icon={<Flame className="h-6 w-6" />}
              title="还没有社媒趋势数据"
              hint="等待每 2 小时一次的自动刷新，或点击「立即刷新」获取一次真实数据。"
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {PLATFORMS.map((p) => {
                const snap = bySource.get(p.source);
                const info = statusInfo(snap?.status ?? "empty");
                const items: TrendItem[] = Array.isArray(snap?.payload?.items) ? snap!.payload.items : [];
                return (
                  <div key={p.source} className="rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] p-4">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--gray-12)]">
                        <span className={p.accent}>{p.icon}</span>{p.label}
                        {items.length > 0 && (
                          <span className="rounded-full bg-[var(--gray-4)] px-1.5 py-0.5 text-[10px] font-normal text-[var(--gray-9)]">
                            {items.length} 词
                          </span>
                        )}
                      </span>
                      <StatusBadge status={info.kind} label={info.label} />
                    </div>
                    {snap?.realData && items.length > 0 ? (
                      <ol className="space-y-1.5">
                        {items.slice(0, 15).map((it, i) => {
                          const heat = fmtHeat(it.heat) ?? fmtHeat(it.views);
                          return (
                            <li key={i} className="flex items-center gap-2.5 rounded-[4px] bg-[var(--gray-3)] px-2.5 py-1.5">
                              <span className={cn(
                                "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-[11px] font-semibold",
                                i < 3 ? "bg-[var(--gray-12)]/15 text-[var(--gray-12)]" : "bg-[var(--gray-4)] text-[var(--gray-9)]"
                              )}>
                                {i + 1}
                              </span>
                              <span className="min-w-0 flex-1 truncate text-xs text-[var(--gray-12)]">{it.keyword}</span>
                              {heat && (
                                <span className="inline-flex flex-shrink-0 items-center gap-0.5 text-[10px] text-[var(--gray-9)]">
                                  <Flame className="h-2.5 w-2.5 text-orange-400" />{heat}
                                </span>
                              )}
                            </li>
                          );
                        })}
                      </ol>
                    ) : (
                      <div className="rounded-[4px] bg-[var(--gray-3)] px-3 py-6 text-center text-xs text-[var(--gray-9)]">
                        {snap?.summary || "暂无数据"}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </PageContainer>
  );
}
