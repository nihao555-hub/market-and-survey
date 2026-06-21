"use client";
import React, { useRef, useEffect, useCallback } from "react";
import {
  TrendingUp, RefreshCw, Package, Flame, BarChart3,
  Clock, ChevronDown, Music2, Twitter, Citrus, Globe,
} from "lucide-react";
import type { EChartsOption } from "echarts";
import { fetchDataSnapshots, fetchAllSnapshots, fetchDailyRefreshStatus, triggerDailyRefresh, backfillGoogleTrends } from "@/lib/api";
import type { DataSnapshot } from "@/lib/api";
import { cn } from "@/lib/utils";

// ─── ECharts wrapper (lazy import) ─────────────────────────────────
function MiniChart({ option, height = 280 }: { option: EChartsOption; height?: number }) {
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
        grid: { left: 48, right: 16, top: 36, bottom: 32, containLabel: true },
        tooltip: {
          trigger: "axis",
          backgroundColor: "var(--gray-1)",
          borderColor: "var(--gray-5)",
          textStyle: { color: "var(--gray-12)", fontSize: 12 },
        },
        ...option,
      } as EChartsOption);
      inst.current = chart;
      const ro = new ResizeObserver(() => chart.resize());
      ro.observe(ref.current);
      return () => ro.disconnect();
    });
    return () => {
      disposed = true;
      if (inst.current) (inst.current as { dispose: () => void }).dispose();
      inst.current = null;
    };
  }, [option]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}

// ─── Constants ─────────────────────────────────────────────────────
const CATEGORY_TERM = "📦 品类榜单";
const SOCIAL_TREND_TERM = "🔥 实时社媒趋势";

const SOCIAL_PLATFORMS: { source: string; label: string; icon: React.ReactNode; color: string }[] = [
  { source: "trend_tiktok", label: "TikTok", icon: <Music2 className="h-3 w-3" />, color: "#ec4899" },
  { source: "trend_twitter", label: "X", icon: <Twitter className="h-3 w-3" />, color: "#3b82f6" },
  { source: "trend_lemon8", label: "Lemon8", icon: <Citrus className="h-3 w-3" />, color: "#84cc16" },
];

type TimeRange = "24h" | "7d" | "30d";
type ChartTab = "category" | "social" | "google";

function fmtTime(iso?: string | null): string {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); } catch { return "—"; }
}

function fmtShortTime(iso?: string | null): string {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); } catch { return ""; }
}

// ─── Build ECharts options from snapshot data ──────────────────────

interface CategoryPoint {
  time: string;
  categories: Record<string, { avgPrice: number; count: number; avgRating: number }>;
}

function buildCategoryPoints(snapshots: DataSnapshot[]): CategoryPoint[] {
  const byRun = new Map<string, DataSnapshot[]>();
  for (const s of snapshots) {
    const key = s.capturedAt || s.id;
    const runKey = s.capturedAt?.slice(0, 16) || key; // group by minute
    if (!byRun.has(runKey)) byRun.set(runKey, []);
    byRun.get(runKey)!.push(s);
  }

  const points: CategoryPoint[] = [];
  for (const [time, snaps] of byRun) {
    const categories: Record<string, { avgPrice: number; count: number; avgRating: number }> = {};
    for (const s of snaps) {
      const name = (s.payload?.category_name || s.payload?.category_name_en || "") as string;
      const prods = (s.payload?.products || []) as Array<{ price?: number; rating?: number }>;
      if (!name || prods.length === 0) continue;
      const prices = prods.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
      const ratings = prods.map((p) => p.rating).filter((v): v is number => typeof v === "number" && v > 0);
      categories[name] = {
        avgPrice: prices.length ? +(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : 0,
        count: prods.length,
        avgRating: ratings.length ? +(ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : 0,
      };
    }
    if (Object.keys(categories).length > 0) {
      points.push({ time: fmtShortTime(time) || time, categories });
    }
  }
  return points.sort((a, b) => a.time.localeCompare(b.time));
}

function buildCategoryChartOption(points: CategoryPoint[], metric: "avgPrice" | "count" | "avgRating"): EChartsOption {
  if (points.length === 0) return {};
  const allCats = new Set<string>();
  for (const p of points) for (const c of Object.keys(p.categories)) allCats.add(c);
  const catList = [...allCats].slice(0, 10);
  const times = points.map((p) => p.time);
  const COLORS = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ef4444", "#06b6d4", "#84cc16", "#f97316"];
  const metricLabel = metric === "avgPrice" ? "均价 ($)" : metric === "count" ? "商品数" : "均评分";

  return {
    legend: { data: catList, bottom: 0, textStyle: { fontSize: 11, color: "#888" }, type: "scroll", pageIconColor: "#888" },
    xAxis: { type: "category", data: times, axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
    yAxis: { type: "value", name: metricLabel, nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    series: catList.map((cat, i) => ({
      name: cat,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: COLORS[i % COLORS.length] },
      data: points.map((p) => p.categories[cat]?.[metric] ?? null),
    })),
  };
}

interface SocialPoint {
  time: string;
  platforms: Record<string, number>;
}

function buildSocialPoints(snapshots: DataSnapshot[]): SocialPoint[] {
  const byRun = new Map<string, DataSnapshot[]>();
  for (const s of snapshots) {
    const runKey = s.capturedAt?.slice(0, 16) || s.id;
    if (!byRun.has(runKey)) byRun.set(runKey, []);
    byRun.get(runKey)!.push(s);
  }

  const points: SocialPoint[] = [];
  for (const [time, snaps] of byRun) {
    const platforms: Record<string, number> = {};
    for (const s of snaps) {
      const meta = SOCIAL_PLATFORMS.find((p) => p.source === s.source);
      if (!meta) continue;
      const items = (s.payload?.items || []) as Array<{ heat?: number; views?: number }>;
      platforms[meta.label] = items.length;
    }
    if (Object.keys(platforms).length > 0) {
      points.push({ time: fmtShortTime(time) || time, platforms });
    }
  }
  return points.sort((a, b) => a.time.localeCompare(b.time));
}

function buildSocialChartOption(points: SocialPoint[]): EChartsOption {
  if (points.length === 0) return {};
  const allPlats = new Set<string>();
  for (const p of points) for (const pl of Object.keys(p.platforms)) allPlats.add(pl);
  const platList = [...allPlats];
  const times = points.map((p) => p.time);
  const colors = SOCIAL_PLATFORMS.map((p) => p.color);

  return {
    legend: { data: platList, bottom: 0, textStyle: { fontSize: 11, color: "#888" }, type: "scroll" },
    xAxis: { type: "category", data: times, axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
    yAxis: { type: "value", name: "热词数量", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    series: platList.map((plat, i) => ({
      name: plat,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      areaStyle: { opacity: 0.05 },
      itemStyle: { color: colors[i % colors.length] },
      data: points.map((p) => p.platforms[plat] ?? 0),
    })),
  };
}

// ─── Google Trends chart builders ──────────────────────────────────

interface GoogleTrendItem {
  keyword: string;
  direction: string;
  lateAvg: number;
  earlyAvg: number;
  max: number;
  recent3mAvg: number | null;
  capturedAt: string;
}

function buildGoogleTrendItems(snapshots: DataSnapshot[]): GoogleTrendItem[] {
  const items: GoogleTrendItem[] = [];
  for (const s of snapshots) {
    if (s.source !== "google_trends" || !s.realData) continue;
    const p = s.payload || {};
    items.push({
      keyword: (p.keyword || s.term || "") as string,
      direction: (p.direction || "") as string,
      lateAvg: (p.late_avg || 0) as number,
      earlyAvg: (p.early_avg || 0) as number,
      max: (p.max || 0) as number,
      recent3mAvg: (p.recent_3m_avg ?? null) as number | null,
      capturedAt: s.capturedAt || "",
    });
  }
  return items;
}

function buildGoogleTrendChartOption(items: GoogleTrendItem[]): EChartsOption {
  if (items.length === 0) return {};

  // Group by keyword, show latest late_avg per keyword over time
  const byKw = new Map<string, GoogleTrendItem[]>();
  for (const it of items) {
    if (!byKw.has(it.keyword)) byKw.set(it.keyword, []);
    byKw.get(it.keyword)!.push(it);
  }

  // If we have multiple timestamps per keyword, build time series
  const allTimes = new Set<string>();
  for (const [, kwItems] of byKw) {
    for (const it of kwItems) {
      allTimes.add(it.capturedAt.slice(0, 16));
    }
  }
  const times = [...allTimes].sort();

  if (times.length > 1) {
    const keywords = [...byKw.keys()].slice(0, 12);
    const COLORS = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ef4444", "#06b6d4", "#84cc16", "#f97316", "#14b8a6", "#a855f6"];
    return {
      legend: { data: keywords, bottom: 0, textStyle: { fontSize: 11, color: "#888" }, type: "scroll", pageIconColor: "#888" },
      xAxis: { type: "category", data: times.map((t) => fmtShortTime(t) || t), axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
      yAxis: { type: "value", name: "搜索热度", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
      series: keywords.map((kw, i) => {
        const kwItems = byKw.get(kw) || [];
        const timeMap = new Map<string, number>();
        for (const it of kwItems) timeMap.set(it.capturedAt.slice(0, 16), it.lateAvg);
        return {
          name: kw,
          type: "line" as const,
          smooth: true,
          symbol: "circle",
          symbolSize: 4,
          lineStyle: { width: 2 },
          itemStyle: { color: COLORS[i % COLORS.length] },
          data: times.map((t) => timeMap.get(t) ?? null),
        };
      }),
    };
  }

  // Fallback: single-point bar chart showing all keywords at latest snapshot
  const latest = new Map<string, GoogleTrendItem>();
  for (const it of items) {
    const prev = latest.get(it.keyword);
    if (!prev || it.capturedAt > prev.capturedAt) latest.set(it.keyword, it);
  }
  const sorted = [...latest.values()].sort((a, b) => b.lateAvg - a.lateAvg).slice(0, 15);
  const DIRECTION_COLOR: Record<string, string> = { "上升": "#10b981", "下降": "#ef4444", "平稳": "#6366f1" };

  return {
    xAxis: {
      type: "category",
      data: sorted.map((it) => it.keyword),
      axisLabel: { fontSize: 10, color: "#999", rotate: 30 },
      axisLine: { lineStyle: { color: "#e5e5e5" } },
    },
    yAxis: {
      type: "value", name: "搜索热度",
      nameTextStyle: { fontSize: 11, color: "#999" },
      axisLabel: { fontSize: 10, color: "#999" },
      splitLine: { lineStyle: { color: "#f0f0f0" } },
    },
    series: [{
      type: "bar" as const,
      barWidth: "60%",
      data: sorted.map((it) => ({
        value: it.lateAvg,
        itemStyle: { color: DIRECTION_COLOR[it.direction] || "#6366f1", borderRadius: [4, 4, 0, 0] },
      })),
      label: {
        show: true, position: "top", fontSize: 10, color: "#999",
        formatter: (p: { dataIndex: number }) => sorted[p.dataIndex]?.direction || "",
      },
    }],
  };
}

// Google Trends summary cards
function LatestGoogleSummary({ items }: { items: GoogleTrendItem[] }) {
  if (items.length === 0) return null;
  const latest = new Map<string, GoogleTrendItem>();
  for (const it of items) {
    const prev = latest.get(it.keyword);
    if (!prev || it.capturedAt > prev.capturedAt) latest.set(it.keyword, it);
  }
  const sorted = [...latest.values()].sort((a, b) => b.lateAvg - a.lateAvg).slice(0, 8);
  const DIR_STYLE: Record<string, string> = { "上升": "text-green-600", "下降": "text-red-500", "平稳": "text-[var(--gray-9)]" };

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {sorted.map((it) => (
        <div key={it.keyword} className="rounded-[6px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-3 py-2">
          <div className="truncate text-[12px] font-medium text-[var(--gray-12)]">{it.keyword}</div>
          <div className="mt-1 flex items-center gap-3 text-[11px] text-[var(--gray-9)]">
            <span>热度 {it.lateAvg}</span>
            <span className={DIR_STYLE[it.direction] || ""}>{it.direction}</span>
            {it.recent3mAvg !== null && <span>近3月 {it.recent3mAvg}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Per-category sparkline (SVG) ──────────────────────────────────
function CatSparkline({ values, className }: { values: number[]; className?: string }) {
  if (values.length < 2) return null;
  const max = Math.max(...values), min = Math.min(...values);
  const span = max - min || 1;
  const W = 100, H = 28;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - min) / span) * (H - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const rising = values[values.length - 1] >= values[0];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={cn("h-7 w-[100px]", className)} preserveAspectRatio="none">
      <polyline points={pts.join(" ")} fill="none" stroke={rising ? "#10b981" : "#f43f5e"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

interface CatCardData {
  name: string;
  latestAvgPrice: number;
  latestCount: number;
  latestAvgRating: number;
  priceHistory: number[];
  countHistory: number[];
  ratingHistory: number[];
  top5: Array<{ title: string; price: number; sold: number; rating: number; image?: string }>;
}

function buildCatCards(latestSnaps: DataSnapshot[], historySnaps: DataSnapshot[]): CatCardData[] {
  const byRun = new Map<string, DataSnapshot[]>();
  for (const s of historySnaps) {
    const key = s.capturedAt?.slice(0, 16) || s.id;
    if (!byRun.has(key)) byRun.set(key, []);
    byRun.get(key)!.push(s);
  }
  const entries = [...byRun.entries()].sort((a, b) => a[0].localeCompare(b[0]));

  const catNames = new Set<string>();
  for (const s of latestSnaps) {
    const name = (s.payload?.category_name || s.payload?.category_name_en || "") as string;
    if (name) catNames.add(name);
  }

  const cards: CatCardData[] = [];
  for (const catName of catNames) {
    const latestSnap = latestSnaps.find((s) => (s.payload?.category_name || s.payload?.category_name_en) === catName);
    const prods = (latestSnap?.payload?.products || []) as Array<{ title?: string; price?: number; sold_count?: number; rating?: number; image?: string }>;
    const prices = prods.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
    const ratings = prods.map((p) => p.rating).filter((v): v is number => typeof v === "number" && v > 0);

    const priceHistory: number[] = [];
    const countHistory: number[] = [];
    const ratingHistory: number[] = [];
    for (const [, snaps] of entries) {
      const s = snaps.find((snap) => (snap.payload?.category_name || snap.payload?.category_name_en) === catName);
      if (!s) continue;
      const ps = (s.payload?.products || []) as Array<{ price?: number; rating?: number }>;
      const pr = ps.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
      const rt = ps.map((p) => p.rating).filter((v): v is number => typeof v === "number" && v > 0);
      priceHistory.push(pr.length ? +(pr.reduce((a, b) => a + b, 0) / pr.length).toFixed(2) : 0);
      countHistory.push(ps.length);
      ratingHistory.push(rt.length ? +(rt.reduce((a, b) => a + b, 0) / rt.length).toFixed(1) : 0);
    }

    const top5 = prods
      .filter((p) => p.title)
      .sort((a, b) => (b.sold_count || 0) - (a.sold_count || 0))
      .slice(0, 5)
      .map((p) => ({
        title: p.title || "",
        price: p.price || 0,
        sold: p.sold_count || 0,
        rating: p.rating || 0,
        image: p.image,
      }));

    cards.push({
      name: catName,
      latestAvgPrice: prices.length ? +(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : 0,
      latestCount: prods.length,
      latestAvgRating: ratings.length ? +(ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : 0,
      priceHistory,
      countHistory,
      ratingHistory,
      top5,
    });
  }
  return cards.sort((a, b) => b.latestCount - a.latestCount);
}

function fmtSold(n: number): string {
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return String(n);
}

function CategoryCards({ latestSnaps, historySnaps }: { latestSnaps: DataSnapshot[]; historySnaps: DataSnapshot[] }) {
  const cards = React.useMemo(() => buildCatCards(latestSnaps, historySnaps), [latestSnaps, historySnaps]);
  if (cards.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {cards.map((card) => (
        <div key={card.name} className="rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] overflow-hidden">
          <div className="border-b border-[var(--gray-4)] px-4 py-3">
            <div className="flex items-center justify-between">
              <h3 className="truncate text-[13px] font-semibold text-[var(--gray-12)]">{card.name}</h3>
              <span className="flex-shrink-0 rounded-[4px] bg-[var(--gray-4)] px-1.5 py-0.5 text-[10px] text-[var(--gray-9)]">{card.latestCount} 商品</span>
            </div>
            <div className="mt-2 flex items-center gap-4 text-[11px] text-[var(--gray-9)]">
              <div className="flex items-center gap-1.5">
                <span>均价</span>
                <span className="font-medium text-[var(--gray-12)]">${card.latestAvgPrice}</span>
                <CatSparkline values={card.priceHistory} />
              </div>
              <div className="flex items-center gap-1.5">
                <span>评分</span>
                <span className="font-medium text-[var(--gray-12)]">{card.latestAvgRating}</span>
                <CatSparkline values={card.ratingHistory} />
              </div>
            </div>
          </div>
          {card.top5.length > 0 && (
            <div className="px-4 py-2">
              <div className="mb-1.5 text-[10px] font-medium text-[var(--gray-8)]">TOP 5 热销</div>
              <div className="space-y-1.5">
                {card.top5.map((p, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded text-[10px] font-bold text-[var(--gray-9)]">{i + 1}</span>
                    {p.image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={p.image} alt="" className="h-7 w-7 flex-shrink-0 rounded object-cover" />
                    ) : (
                      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded bg-[var(--gray-3)]">
                        <Package className="h-3 w-3 text-[var(--gray-7)]" />
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[11px] text-[var(--gray-12)]">{p.title}</div>
                    </div>
                    <div className="flex flex-shrink-0 items-center gap-2 text-[10px] text-[var(--gray-9)]">
                      <span className="font-medium">${p.price}</span>
                      {p.sold > 0 && <span>已售 {fmtSold(p.sold)}</span>}
                      {p.rating > 0 && <span>★{p.rating}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Latest snapshot summary cards ─────────────────────────────────
function LatestCategorySummary({ snapshots }: { snapshots: DataSnapshot[] }) {
  if (snapshots.length === 0) return null;
  const cats = snapshots
    .filter((s) => s.realData && s.source === "category_rank")
    .slice(0, 8);
  if (cats.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {cats.map((c) => {
        const name = (c.payload?.category_name || c.payload?.category_name_en || "—") as string;
        const prods = (c.payload?.products || []) as Array<{ price?: number; sold_count?: number }>;
        const prices = prods.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
        const avgPrice = prices.length ? (prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(1) : "—";
        return (
          <div key={c.id} className="rounded-[6px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-3 py-2">
            <div className="truncate text-[12px] font-medium text-[var(--gray-12)]">{name}</div>
            <div className="mt-1 flex items-center gap-3 text-[11px] text-[var(--gray-9)]">
              <span>{prods.length} 商品</span>
              <span>均价 ${avgPrice}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LatestSocialSummary({ snapshots }: { snapshots: DataSnapshot[] }) {
  if (snapshots.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {SOCIAL_PLATFORMS.map((p) => {
        const snap = snapshots.find((s) => s.source === p.source);
        const items = (snap?.payload?.items || []) as Array<{ keyword?: string }>;
        const topKw = items.slice(0, 3).map((i) => i.keyword).filter(Boolean).join("、");
        return (
          <div key={p.source} className="rounded-[6px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-3 py-2">
            <div className="flex items-center gap-1.5 text-[12px] font-medium text-[var(--gray-12)]">
              <span style={{ color: p.color }}>{p.icon}</span>
              {p.label}
              <span className="ml-auto text-[10px] text-[var(--gray-8)]">{items.length} 词</span>
            </div>
            <div className="mt-1 truncate text-[11px] text-[var(--gray-9)]">
              {topKw || (snap?.realData ? "暂无" : "未获取")}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────
export function CategoryTrendsSection() {
  const [tab, setTab] = React.useState<ChartTab>("category");
  // metric state removed — category tab now shows per-category cards
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [backfilling, setBackfilling] = React.useState(false);
  const [lastUpdate, setLastUpdate] = React.useState<string | null>(null);
  const [tierOk, setTierOk] = React.useState(false);

  // Latest snapshots (for summary cards)
  const [latestCats, setLatestCats] = React.useState<DataSnapshot[]>([]);
  const [latestSocial, setLatestSocial] = React.useState<DataSnapshot[]>([]);

  // Historical snapshots (for charts)
  const [historyCats, setHistoryCats] = React.useState<DataSnapshot[]>([]);
  const [historySocial, setHistorySocial] = React.useState<DataSnapshot[]>([]);

  // Google Trends snapshots
  const [googleSnaps, setGoogleSnaps] = React.useState<DataSnapshot[]>([]);

  const load = useCallback(async () => {
    try {
      const [status, catSnaps, socialSnaps, catHistory, socialHistory, gSnaps] = await Promise.all([
        fetchDailyRefreshStatus(),
        fetchDataSnapshots({ source: "category_rank", limit: 40 }),
        fetchDataSnapshots({ term: SOCIAL_TREND_TERM, limit: 50 }),
        fetchAllSnapshots({ source: "category_rank", limit: 300 }),
        fetchAllSnapshots({ term: SOCIAL_TREND_TERM, limit: 300 }),
        fetchAllSnapshots({ source: "google_trends", limit: 300 }),
      ]);
      setLastUpdate(status?.finishedAt ?? null);
      setTierOk(status?.tier2ChannelOk ?? false);
      setLatestCats(catSnaps);
      setLatestSocial(socialSnaps);
      setHistoryCats(catHistory);
      setHistorySocial(socialHistory);
      setGoogleSnaps(gSnaps);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerDailyRefresh();
      setTimeout(() => { load(); setRefreshing(false); }, 5000);
    } catch {
      setRefreshing(false);
    }
  };

  const handleBackfill = async () => {
    setBackfilling(true);
    try {
      await backfillGoogleTrends();
      setTimeout(() => { load(); setBackfilling(false); }, 8000);
    } catch {
      setBackfilling(false);
    }
  };

  // Build chart data
  const socialPoints = React.useMemo(() => buildSocialPoints(historySocial), [historySocial]);
  const googleItems = React.useMemo(() => buildGoogleTrendItems(googleSnaps), [googleSnaps]);
  const socialChartOpt = React.useMemo(() => buildSocialChartOption(socialPoints), [socialPoints]);
  const googleChartOpt = React.useMemo(() => buildGoogleTrendChartOption(googleItems), [googleItems]);

  const hasData = latestCats.length > 0 || latestSocial.length > 0 || googleItems.length > 0;
  const hasHistory = socialPoints.length > 1 || googleItems.length > 0;

  return (
    <section className="mt-6">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-[14px] font-semibold text-[var(--gray-12)]">
            <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-[4px] bg-[var(--gray-4)] text-[var(--gray-11)]">
              <TrendingUp className="h-3.5 w-3.5" />
            </span>
            实时趋势
          </h2>
          <p className="mt-0.5 text-[12px] text-[var(--gray-9)]">
            TikTok Shop 品类 + 跨平台社媒热搜 + Google Trends 搜索热度，每 2 小时刷新，像看K线一样看品类走势
          </p>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          {lastUpdate && (
            <span className="hidden items-center gap-1 text-[11px] text-[var(--gray-8)] sm:inline-flex">
              <Clock className="h-3 w-3" /> {fmtTime(lastUpdate)}
            </span>
          )}
          {tab === "google" && (
            <button
              onClick={handleBackfill}
              disabled={backfilling}
              className="flex h-7 items-center gap-1 rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-2.5 text-[12px] font-medium text-[var(--gray-11)] transition-colors hover:bg-[var(--bg-transparent-light)] disabled:opacity-40"
            >
              <Globe className={cn("h-3 w-3", backfilling && "animate-pulse")} />
              {backfilling ? "回填中…" : "回填近1月"}
            </button>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex h-7 items-center gap-1 rounded-[4px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-2.5 text-[12px] font-medium text-[var(--gray-11)] transition-colors hover:bg-[var(--bg-transparent-light)] disabled:opacity-40"
          >
            <RefreshCw className={cn("h-3 w-3", refreshing && "animate-spin")} />
            {refreshing ? "刷新中…" : "立即刷新"}
          </button>
        </div>
      </div>

      {/* Channel status banner */}
      {!tierOk && !loading && (
        <div className="mb-3 rounded-[6px] border border-[var(--gray-5)] bg-[var(--gray-2)] px-3 py-2 text-[12px] text-[var(--gray-9)]">
          趋势通道（TikHub）需配置 <span className="font-medium text-[var(--gray-11)]">TIKHUB_API_KEY</span>，接入后自动补齐数据并开始积累趋势
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          <div className="h-8 w-full animate-pulse rounded-[6px] bg-[var(--gray-4)]" />
          <div className="h-[280px] w-full animate-pulse rounded-[8px] bg-[var(--gray-3)]" />
          <div className="grid grid-cols-4 gap-2">
            {[0, 1, 2, 3].map((i) => <div key={i} className="h-14 animate-pulse rounded-[6px] bg-[var(--gray-3)]" />)}
          </div>
        </div>
      ) : !hasData ? (
        <div className="flex flex-col items-center rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] px-5 py-10 text-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--gray-4)] text-[var(--gray-8)]">
            <BarChart3 className="h-5 w-5" />
          </span>
          <div className="mt-3 text-[13px] font-medium text-[var(--gray-12)]">还没有趋势数据</div>
          <div className="mt-1 max-w-sm text-[12px] text-[var(--gray-9)]">
            点击「立即刷新」获取第一批数据。随着数据积累，这里将展示品类和社媒的时间序列趋势图表。
          </div>
        </div>
      ) : (
        <div className="rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] overflow-hidden">
          {/* Tabs + metric selector */}
          <div className="flex items-center justify-between border-b border-[var(--gray-4)] px-4 py-2">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setTab("category")}
                className={cn(
                  "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                  tab === "category"
                    ? "bg-[var(--gray-12)] text-[var(--gray-1)]"
                    : "text-[var(--gray-9)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
                )}
              >
                <Package className="mr-1 inline h-3 w-3" />
                品类趋势
              </button>
              <button
                onClick={() => setTab("social")}
                className={cn(
                  "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                  tab === "social"
                    ? "bg-[var(--gray-12)] text-[var(--gray-1)]"
                    : "text-[var(--gray-9)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
                )}
              >
                <Flame className="mr-1 inline h-3 w-3" />
                社媒热搜
              </button>
              <button
                onClick={() => setTab("google")}
                className={cn(
                  "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                  tab === "google"
                    ? "bg-[var(--gray-12)] text-[var(--gray-1)]"
                    : "text-[var(--gray-9)] hover:bg-[var(--bg-transparent-light)] hover:text-[var(--gray-12)]"
                )}
              >
                <Globe className="mr-1 inline h-3 w-3" />
                Google Trends
              </button>
            </div>

            {/* metric selector removed — category tab now shows per-category cards */}
          </div>

          {/* Content area */}
          {tab === "category" ? (
            <div className="p-4">
              <CategoryCards latestSnaps={latestCats} historySnaps={historyCats} />
            </div>
          ) : (
            <>
              <div className="px-2 pt-2">
                {hasHistory ? (
                  tab === "social" ? (
                    <MiniChart option={socialChartOpt} height={280} />
                  ) : (
                    <MiniChart option={googleChartOpt} height={280} />
                  )
                ) : (
                  <div className="flex h-[280px] flex-col items-center justify-center text-center">
                    <BarChart3 className="h-8 w-8 text-[var(--gray-6)]" />
                    <div className="mt-2 text-[12px] text-[var(--gray-9)]">
                      数据积累中…至少需要 2 次刷新才能生成趋势图表
                    </div>
                    <div className="mt-1 text-[11px] text-[var(--gray-8)]">
                      （每 2 小时自动刷新一次，或手动点击「立即刷新」）
                    </div>
                  </div>
                )}
              </div>
              <div className="border-t border-[var(--gray-4)] px-4 py-3">
                <div className="mb-2 text-[11px] font-medium text-[var(--gray-9)]">
                  {tab === "social" ? "最新平台热搜" : "最新搜索热度"}
                </div>
                {tab === "social" ? (
                  <LatestSocialSummary snapshots={latestSocial} />
                ) : (
                  <LatestGoogleSummary items={googleItems} />
                )}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
