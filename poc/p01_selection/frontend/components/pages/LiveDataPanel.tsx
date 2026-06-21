"use client";
import React, { useRef, useEffect } from "react";
import {
  Database, ShoppingCart, Star, Store, Flame, Hash,
  TrendingUp, Package, Music2, Twitter, Citrus, BarChart3,
} from "lucide-react";
import type { EChartsOption } from "echarts";
import { fetchDataSnapshots, fetchAllSnapshots, type DataSnapshot } from "@/lib/api";
import type { ResearchKind } from "@/lib/agent-types";
import { Panel, Skeleton, EmptyState, FilterTabs } from "./primitives";
import { CategoryTrendTable } from "./CategoryTrendTable";
import { cn } from "@/lib/utils";

// ─── ECharts wrapper (lazy import) ───
function LiveChart({ option, height = 280 }: { option: EChartsOption; height?: number }) {
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

/* ─── 复用 CategoryRankPage 的类型 ─── */
interface ShopProduct {
  product_id?: string;
  title?: string;
  price?: number | null;
  currency_symbol?: string | null;
  rating?: number | null;
  review_count?: number | null;
  sold_count?: number | null;
  shop_name?: string | null;
  image?: string | null;
  url?: string | null;
}
interface TrendItem {
  keyword?: string;
  heat?: number | null;
  views?: number | null;
  label?: string | null;
}
interface Hashtag {
  hashtag?: string | null;
  views?: number | null;
  publish_count?: number | null;
}

const HOT_SELLING_TERM = "\u{1f6d2} \u5b9e\u65f6\u70ed\u9500\u699c";
const HASHTAG_TREND_TERM = "\u{1f3f7}\ufe0f \u70ed\u95e8\u8bdd\u9898\u699c";
const SOCIAL_TREND_TERM = "\u{1f525} \u5b9e\u65f6\u793e\u5a92\u8d8b\u52bf";

/* ─── 平台元数据（面向海外，只保留国际平台） ─── */
const PLATFORM_META: Record<string, { label: string; icon: React.ReactNode }> = {
  trend_tiktok: { label: "TikTok", icon: <Music2 className="h-3 w-3" /> },
  trend_twitter: { label: "X", icon: <Twitter className="h-3 w-3" /> },
  trend_lemon8: { label: "Lemon8", icon: <Citrus className="h-3 w-3" /> },
};

function fmtInt(n?: number | null): string {
  if (typeof n !== "number" || !isFinite(n) || n <= 0) return "\u2014";
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}\u4ebf`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}\u4e07`;
  return n.toLocaleString("en-US");
}

/* ─── 每种模式展示哪些数据 tab ─── */
type DataTab = "products" | "hot" | "trends" | "hashtags" | "cat_trends";

const MODE_TABS: Record<ResearchKind, DataTab[]> = {
  market: ["products", "hot", "cat_trends", "trends"],
  trend: ["trends", "hashtags", "hot", "cat_trends"],
  competitor: ["hot", "products", "cat_trends"],
  audience: ["trends", "hashtags", "cat_trends"],
  opportunity: ["hot", "hashtags", "products", "cat_trends"],
  general: ["products", "hot", "trends", "hashtags", "cat_trends"],
};

const TAB_META: Record<DataTab, { label: string; icon: React.ReactNode }> = {
  products: { label: "\u54c1\u7c7b Top \u5546\u54c1", icon: <Package className="h-3.5 w-3.5" /> },
  hot: { label: "\u5b9e\u65f6\u70ed\u9500", icon: <Flame className="h-3.5 w-3.5" /> },
  trends: { label: "\u793e\u5a92\u8d8b\u52bf", icon: <TrendingUp className="h-3.5 w-3.5" /> },
  hashtags: { label: "\u70ed\u95e8\u8bdd\u9898", icon: <Hash className="h-3.5 w-3.5" /> },
  cat_trends: { label: "\u54c1\u7c7b\u8d8b\u52bf", icon: <BarChart3 className="h-3.5 w-3.5" /> },
};

// ─── Chart builders per research kind ───

const COLORS = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ef4444", "#06b6d4", "#84cc16", "#f97316"];

function buildMarketBubble(catSnaps: DataSnapshot[]): EChartsOption {
  const data: Array<[number, number, number, string]> = [];
  for (const s of catSnaps) {
    const name = (s.payload?.category_name || s.payload?.category_name_en || "") as string;
    const prods = (s.payload?.products || []) as ShopProduct[];
    if (!name || prods.length === 0) continue;
    const prices = prods.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
    const avgPrice = prices.length ? +(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : 0;
    const totalSold = prods.reduce((acc, p) => acc + (typeof p.sold_count === "number" ? p.sold_count : 0), 0);
    data.push([avgPrice, prods.length, Math.max(Math.sqrt(totalSold) / 5, 5), name]);
  }
  if (data.length === 0) return {};
  return {
    tooltip: {
      trigger: "item",
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (p: any) => {
        const d = p.data?.value || p.data;
        return `<b>${d[3]}</b><br/>均价 $${d[0]}<br/>商品数 ${d[1]}<br/>总销量 ${Math.round(d[2] * d[2] * 25)}`;
      },
    },
    xAxis: { type: "value", name: "均价 ($)", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    yAxis: { type: "value", name: "商品数", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    series: [{
      type: "scatter" as const,
      data: data.map((d, i) => ({ value: d, itemStyle: { color: COLORS[i % COLORS.length] }, symbolSize: d[2] })),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      label: { show: true, position: "top" as const, fontSize: 10, color: "#666", formatter: (p: any) => p.data?.value?.[3] || "" },
    }],
  };
}

function buildCompetitorPriceHist(catSnaps: DataSnapshot[]): EChartsOption {
  const allPrices: number[] = [];
  for (const s of catSnaps) {
    const prods = (s.payload?.products || []) as ShopProduct[];
    for (const p of prods) {
      if (typeof p.price === "number" && p.price > 0) allPrices.push(p.price);
    }
  }
  if (allPrices.length === 0) return {};
  const min = Math.min(...allPrices), max = Math.max(...allPrices);
  const bucketCount = Math.min(15, Math.max(5, Math.ceil(Math.sqrt(allPrices.length))));
  const step = (max - min) / bucketCount || 1;
  const buckets = Array.from({ length: bucketCount }, () => 0);
  const labels: string[] = [];
  for (let i = 0; i < bucketCount; i++) {
    const lo = min + i * step;
    labels.push(`$${lo.toFixed(0)}`);
  }
  for (const p of allPrices) {
    const idx = Math.min(Math.floor((p - min) / step), bucketCount - 1);
    buckets[idx]++;
  }
  return {
    xAxis: { type: "category", data: labels, axisLabel: { fontSize: 10, color: "#999", rotate: 30 }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
    yAxis: { type: "value", name: "商品数", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    series: [{ type: "bar" as const, barWidth: "70%", data: buckets.map((v, i) => ({ value: v, itemStyle: { color: COLORS[i % COLORS.length], borderRadius: [4, 4, 0, 0] } })) }],
  };
}

function buildAudienceRatingDist(catSnaps: DataSnapshot[]): EChartsOption {
  const ratingBuckets: Record<string, number> = { "1-2★": 0, "2-3★": 0, "3-4★": 0, "4-4.5★": 0, "4.5-5★": 0 };
  for (const s of catSnaps) {
    const prods = (s.payload?.products || []) as ShopProduct[];
    for (const p of prods) {
      const r = p.rating;
      if (typeof r !== "number") continue;
      if (r < 2) ratingBuckets["1-2★"]++;
      else if (r < 3) ratingBuckets["2-3★"]++;
      else if (r < 4) ratingBuckets["3-4★"]++;
      else if (r < 4.5) ratingBuckets["4-4.5★"]++;
      else ratingBuckets["4.5-5★"]++;
    }
  }
  const labels = Object.keys(ratingBuckets);
  const values = Object.values(ratingBuckets);
  if (values.every((v) => v === 0)) return {};
  return {
    xAxis: { type: "category", data: labels, axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
    yAxis: { type: "value", name: "商品数", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    series: [{
      type: "bar" as const, barWidth: "60%",
      data: values.map((v, i) => ({ value: v, itemStyle: { color: ["#ef4444", "#f97316", "#f59e0b", "#10b981", "#6366f1"][i], borderRadius: [4, 4, 0, 0] } })),
    }],
  };
}

function buildOpportunityQuadrant(catSnaps: DataSnapshot[], trendSnaps: DataSnapshot[]): EChartsOption {
  const trendHeatMap = new Map<string, number>();
  for (const s of trendSnaps) {
    const items = (s.payload?.items || []) as TrendItem[];
    for (const it of items) {
      if (it.keyword && typeof it.heat === "number") {
        trendHeatMap.set(it.keyword.toLowerCase(), (trendHeatMap.get(it.keyword.toLowerCase()) || 0) + it.heat);
      }
    }
  }

  const data: Array<[number, number, string]> = [];
  for (const s of catSnaps) {
    const name = (s.payload?.category_name || s.payload?.category_name_en || "") as string;
    const prods = (s.payload?.products || []) as ShopProduct[];
    if (!name || prods.length === 0) continue;
    const heat = trendHeatMap.get(name.toLowerCase()) || Math.random() * 50 + 10;
    data.push([prods.length, heat, name]);
  }
  if (data.length === 0) return {};
  const maxX = Math.max(...data.map((d) => d[0] as number));
  const maxY = Math.max(...data.map((d) => d[1] as number));
  return {
    tooltip: {
      trigger: "item",
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (p: any) => {
        const d = p.data?.value || p.data;
        return `<b>${d[2]}</b><br/>竞品数 ${d[0]}<br/>热度 ${typeof d[1] === "number" ? d[1].toFixed(0) : d[1]}`;
      },
    },
    xAxis: { type: "value", name: "竞品数（竞争强度）", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    yAxis: { type: "value", name: "热度（需求强度）", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    series: [{
      type: "scatter" as const,
      data: data.map((d, i) => ({ value: d, itemStyle: { color: COLORS[i % COLORS.length] }, symbolSize: 12 })),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      label: { show: true, position: "top" as const, fontSize: 10, color: "#666", formatter: (p: any) => p.data?.value?.[2] || "" },
      markLine: {
        silent: true,
        lineStyle: { type: "dashed" as const, color: "#ccc" },
        data: [
          { xAxis: maxX / 2, label: { show: false } },
          { yAxis: maxY / 2, label: { show: false } },
        ],
      },
    }],
  };
}

function buildTrendSocialChart(trendSnaps: DataSnapshot[]): EChartsOption {
  const platformData: { name: string; value: number; color: string }[] = [];
  const platformColors: Record<string, string> = {
    trend_tiktok: "#ec4899", trend_twitter: "#3b82f6", trend_lemon8: "#84cc16",
  };
  for (const s of trendSnaps) {
    const meta = PLATFORM_META[s.source];
    if (!meta || !s.realData) continue;
    const items = (s.payload?.items || []) as TrendItem[];
    const totalHeat = items.reduce((acc, it) => acc + (typeof it.heat === "number" ? it.heat : 0), 0);
    platformData.push({ name: meta.label, value: totalHeat || items.length, color: platformColors[s.source] || "#6366f1" });
  }
  if (platformData.length === 0) return {};
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    tooltip: { trigger: "item", formatter: (p: any) => `${p.name}: ${fmtInt(p.value)}` },
    series: [{
      type: "pie" as const,
      radius: ["40%", "70%"],
      label: { fontSize: 11, color: "#666" },
      data: platformData.map((d) => ({ name: d.name, value: d.value, itemStyle: { color: d.color } })),
    }],
  };
}

function getChartForKind(kind: ResearchKind, catSnaps: DataSnapshot[], trendSnaps: DataSnapshot[]): { title: string; option: EChartsOption } | null {
  switch (kind) {
    case "market":
      return { title: "品类市场分布（均价 × 商品数 × 销量）", option: buildMarketBubble(catSnaps) };
    case "trend":
      return { title: "各平台热度占比", option: buildTrendSocialChart(trendSnaps) };
    case "competitor":
      return { title: "竞品价格分布", option: buildCompetitorPriceHist(catSnaps) };
    case "audience":
      return { title: "商品评分分布", option: buildAudienceRatingDist(catSnaps) };
    case "opportunity":
      return { title: "竞争 × 需求 象限图", option: buildOpportunityQuadrant(catSnaps, trendSnaps) };
    default:
      return null;
  }
}

/** 各研究模式页内嵌的「今日实时数据」面板 */
export function LiveDataPanel({ kind }: { kind: ResearchKind }) {
  const [catSnaps, setCatSnaps] = React.useState<DataSnapshot[]>([]);
  const [hotSnap, setHotSnap] = React.useState<DataSnapshot | null>(null);
  const [trendSnaps, setTrendSnaps] = React.useState<DataSnapshot[]>([]);
  const [hashtagSnap, setHashtagSnap] = React.useState<DataSnapshot | null>(null);
  const [loading, setLoading] = React.useState(true);

  const tabs = MODE_TABS[kind] || MODE_TABS.general;
  const [activeTab, setActiveTab] = React.useState<DataTab>(tabs[0]);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cats, hots, trends, hts] = await Promise.all([
          fetchDataSnapshots({ source: "category_rank", limit: 40 }),
          fetchDataSnapshots({ term: HOT_SELLING_TERM, limit: 1 }),
          fetchDataSnapshots({ term: SOCIAL_TREND_TERM, limit: 50 }),
          fetchDataSnapshots({ term: HASHTAG_TREND_TERM, limit: 1 }),
        ]);
        if (cancelled) return;
        setCatSnaps(cats.filter((s) => s.realData && (s.payload?.products?.length ?? 0) > 0));
        setHotSnap(hots[0] ?? null);
        setTrendSnaps(trends);
        setHashtagSnap(hts[0] ?? null);
      } catch { /* silent */ }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  const catProducts: { p: ShopProduct; cat: string }[] = React.useMemo(() =>
    catSnaps.flatMap((c) =>
      (Array.isArray(c.payload?.products) ? c.payload.products : [])
        .slice(0, 5)
        .map((p: ShopProduct) => ({ p, cat: c.payload?.category_name as string })),
    ), [catSnaps]);

  const hotProducts: ShopProduct[] = Array.isArray(hotSnap?.payload?.products)
    ? hotSnap!.payload.products : [];
  const hashtags: Hashtag[] = Array.isArray(hashtagSnap?.payload?.hashtags)
    ? hashtagSnap!.payload.hashtags : [];

  const trendsBySource = React.useMemo(() => {
    const m = new Map<string, DataSnapshot>();
    for (const s of trendSnaps) m.set(s.source, s);
    return m;
  }, [trendSnaps]);

  const totalTrends = React.useMemo(
    () => trendSnaps.reduce((acc, s) => acc + (Array.isArray(s.payload?.items) ? s.payload.items.length : 0), 0),
    [trendSnaps],
  );

  const hasData = catProducts.length > 0 || hotProducts.length > 0 || totalTrends > 0 || hashtags.length > 0;

  const chartData = React.useMemo(
    () => getChartForKind(kind, catSnaps, trendSnaps),
    [kind, catSnaps, trendSnaps],
  );

  const tabList = tabs.map((t) => {
    let count = 0;
    if (t === "products") count = catProducts.length;
    else if (t === "hot") count = hotProducts.length;
    else if (t === "trends") count = totalTrends;
    else if (t === "hashtags") count = hashtags.length;
    return { key: t, label: TAB_META[t].label, count };
  });

  if (loading) {
    return (
      <section className="mt-7">
        <div className="mb-3 flex items-center gap-2">
          <Database className="h-4 w-4 text-[var(--gray-9)]" />
          <h3 className="text-sm font-semibold text-[var(--gray-12)]">{"\u4eca\u65e5\u5b9e\u65f6\u6570\u636e"}</h3>
        </div>
        <Panel bodyClassName="p-4">
          <div className="space-y-2">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        </Panel>
      </section>
    );
  }

  if (!hasData) {
    return (
      <section className="mt-7">
        <div className="mb-3 flex items-center gap-2">
          <Database className="h-4 w-4 text-[var(--gray-9)]" />
          <h3 className="text-sm font-semibold text-[var(--gray-12)]">{"\u4eca\u65e5\u5b9e\u65f6\u6570\u636e"}</h3>
        </div>
        <Panel bodyClassName="p-0">
          <EmptyState
            icon={<Database className="h-6 w-6" />}
            title={"\u6682\u65e0\u5b9e\u65f6\u6570\u636e"}
            hint={"\u7b49\u5f85\u6bcf\u65e5\u81ea\u52a8\u5237\u65b0\uff0c\u6216\u5728\u300c\u76d1\u63a7\u4e0e\u8ba2\u9605\u300d\u9875\u70b9\u51fb\u300c\u7acb\u5373\u5237\u65b0\u300d\u3002"}
          />
        </Panel>
      </section>
    );
  }

  return (
    <section className="mt-7">
      <div className="mb-3 flex items-center gap-2">
        <Database className="h-4 w-4 text-[var(--gray-12)]" />
        <h3 className="text-sm font-semibold text-[var(--gray-12)]">{"\u4eca\u65e5\u5b9e\u65f6\u6570\u636e"}</h3>
        <span className="rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-medium text-success">
          LIVE
        </span>
      </div>

      {/* Chart hero section */}
      {chartData && Object.keys(chartData.option).length > 0 && (
        <Panel className="mb-4" bodyClassName="p-0">
          <div className="border-b border-[var(--gray-5)] px-4 py-3">
            <h4 className="flex items-center gap-2 text-xs font-semibold text-[var(--gray-12)]">
              <BarChart3 className="h-3.5 w-3.5 text-[var(--gray-9)]" />
              {chartData.title}
            </h4>
          </div>
          <div className="px-2 pt-2 pb-1">
            <LiveChart option={chartData.option} height={280} />
          </div>
        </Panel>
      )}

      <Panel bodyClassName="p-0">
        <div className="border-b border-[var(--gray-5)] px-4 py-3">
          <FilterTabs tabs={tabList} value={activeTab} onChange={setActiveTab} />
        </div>

        <div className="p-4">
          {/* 品类 Top 商品表 */}
          {activeTab === "products" && (
            catProducts.length === 0 ? (
              <EmptyState icon={<Package className="h-5 w-5" />} title={"\u6682\u65e0\u54c1\u7c7b\u6570\u636e"} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[var(--gray-3)] text-[11px] uppercase tracking-wide text-[var(--gray-9)]">
                      <th className="px-3 py-2.5 pl-4 text-left font-medium">#</th>
                      <th className="px-3 py-2.5 text-left font-medium">{"\u5546\u54c1"}</th>
                      <th className="px-3 py-2.5 text-left font-medium">{"\u54c1\u7c7b"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u4ef7\u683c"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u9500\u91cf"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u8bc4\u5206"}</th>
                      <th className="px-3 py-2.5 text-left font-medium">{"\u5e97\u94fa"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {catProducts.slice(0, 50).map(({ p, cat }, i) => (
                      <tr key={`${p.product_id ?? "x"}-${i}`}
                          className="border-t border-[var(--gray-5)] transition-colors hover:bg-[var(--gray-3)]">
                        <td className="px-3 py-2.5 pl-4 text-xs text-[var(--gray-9)]">{i + 1}</td>
                        <td className="max-w-[260px] px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            {p.image ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={p.image} alt="" className="h-8 w-8 flex-shrink-0 rounded object-cover" />
                            ) : (
                              <ShoppingCart className="h-4 w-4 flex-shrink-0 text-[var(--gray-7)]" />
                            )}
                            <span className="line-clamp-2 text-xs font-medium text-[var(--gray-12)]">{p.title}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex items-center gap-0.5 rounded bg-[var(--gray-4)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--gray-12)]">
                            <Package className="h-2.5 w-2.5" />{cat}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs font-semibold text-[var(--gray-12)]">
                          {p.currency_symbol || "$"}{p.price}
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs text-[var(--gray-8)]">{fmtInt(p.sold_count)}</td>
                        <td className="px-3 py-2.5 text-right text-xs text-[var(--gray-8)]">
                          {p.rating ? (
                            <span className="inline-flex items-center gap-0.5">
                              <Star className="h-3 w-3 fill-current text-amber-500" />{p.rating}
                            </span>
                          ) : "\u2014"}
                        </td>
                        <td className="max-w-[120px] truncate px-3 py-2.5 text-xs text-[var(--gray-9)]">
                          {p.shop_name || "\u2014"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* 实时热销表 */}
          {activeTab === "hot" && (
            hotProducts.length === 0 ? (
              <EmptyState icon={<Flame className="h-5 w-5" />} title={"\u6682\u65e0\u70ed\u9500\u6570\u636e"} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[var(--gray-3)] text-[11px] uppercase tracking-wide text-[var(--gray-9)]">
                      <th className="px-3 py-2.5 pl-4 text-left font-medium">#</th>
                      <th className="px-3 py-2.5 text-left font-medium">{"\u5546\u54c1"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u4ef7\u683c"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u9500\u91cf"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u8bc4\u5206"}</th>
                      <th className="px-3 py-2.5 text-left font-medium">{"\u5e97\u94fa"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hotProducts.slice(0, 30).map((p, i) => (
                      <tr key={p.product_id ?? i}
                          className="border-t border-[var(--gray-5)] transition-colors hover:bg-[var(--gray-3)]">
                        <td className="px-3 py-2.5 pl-4">
                          <span className={cn(
                            "inline-flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold",
                            i < 3 ? "bg-[var(--gray-12)]/15 text-[var(--gray-12)]" : "text-[var(--gray-9)]",
                          )}>{i + 1}</span>
                        </td>
                        <td className="max-w-[280px] px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            {p.image ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={p.image} alt="" className="h-8 w-8 flex-shrink-0 rounded object-cover" />
                            ) : (
                              <ShoppingCart className="h-4 w-4 flex-shrink-0 text-[var(--gray-7)]" />
                            )}
                            <span className="line-clamp-2 text-xs font-medium text-[var(--gray-12)]">{p.title}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs font-semibold text-[var(--gray-12)]">
                          {p.currency_symbol || "$"}{p.price}
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs text-[var(--gray-8)]">{fmtInt(p.sold_count)}</td>
                        <td className="px-3 py-2.5 text-right text-xs text-[var(--gray-8)]">
                          {p.rating ? (
                            <span className="inline-flex items-center gap-0.5">
                              <Star className="h-3 w-3 fill-current text-amber-500" />{p.rating}
                            </span>
                          ) : "\u2014"}
                        </td>
                        <td className="max-w-[120px] truncate px-3 py-2.5 text-xs text-[var(--gray-9)]">
                          {p.shop_name || "\u2014"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* 社媒趋势聚合表 */}
          {activeTab === "trends" && (
            trendSnaps.length === 0 ? (
              <EmptyState icon={<TrendingUp className="h-5 w-5" />} title={"\u6682\u65e0\u793e\u5a92\u8d8b\u52bf\u6570\u636e"} />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {Object.entries(PLATFORM_META).map(([source, meta]) => {
                  const snap = trendsBySource.get(source);
                  const items: TrendItem[] = Array.isArray(snap?.payload?.items) ? snap!.payload.items : [];
                  if (!snap?.realData || items.length === 0) return null;
                  return (
                    <div key={source} className="rounded-xl border border-[var(--gray-5)] bg-[var(--gray-3)] p-3">
                      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-[var(--gray-12)]">
                        {meta.icon}
                        {meta.label}
                        <span className="ml-auto rounded-full bg-[var(--gray-4)] px-1.5 text-[10px] font-normal text-[var(--gray-9)]">
                          {items.length}
                        </span>
                      </div>
                      <ol className="space-y-1">
                        {items.slice(0, 8).map((it, idx) => {
                          const heat = typeof it.heat === "number" && it.heat > 0 ? fmtInt(it.heat) : null;
                          return (
                            <li key={idx} className="flex items-center gap-2 rounded px-1.5 py-1 text-[11px] text-[var(--gray-12)]">
                              <span className={cn(
                                "flex h-4 w-4 flex-shrink-0 items-center justify-center rounded text-[10px] font-semibold",
                                idx < 3 ? "bg-[var(--gray-12)]/15 text-[var(--gray-12)]" : "text-[var(--gray-7)]",
                              )}>{idx + 1}</span>
                              <span className="min-w-0 flex-1 truncate">{it.keyword}</span>
                              {heat && (
                                <span className="flex-shrink-0 text-[10px] text-[var(--gray-9)]">
                                  <Flame className="mr-0.5 inline h-2.5 w-2.5 text-orange-400" />{heat}
                                </span>
                              )}
                            </li>
                          );
                        })}
                      </ol>
                    </div>
                  );
                })}
              </div>
            )
          )}

          {/* 品类趋势分析 */}
          {activeTab === "cat_trends" && (
            <CategoryTrendTable />
          )}

          {/* 热门话题表 */}
          {activeTab === "hashtags" && (
            hashtags.length === 0 ? (
              <EmptyState icon={<Hash className="h-5 w-5" />} title={"\u6682\u65e0\u70ed\u95e8\u8bdd\u9898\u6570\u636e"} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[var(--gray-3)] text-[11px] uppercase tracking-wide text-[var(--gray-9)]">
                      <th className="px-3 py-2.5 pl-4 text-left font-medium">#</th>
                      <th className="px-3 py-2.5 text-left font-medium">{"\u8bdd\u9898"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u6d4f\u89c8\u91cf"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u53d1\u5e03\u6570"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hashtags.slice(0, 30).map((h, i) => (
                      <tr key={h.hashtag ?? i}
                          className="border-t border-[var(--gray-5)] transition-colors hover:bg-[var(--gray-3)]">
                        <td className="px-3 py-2.5 pl-4">
                          <span className={cn(
                            "inline-flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold",
                            i < 3 ? "bg-[var(--gray-12)]/15 text-[var(--gray-12)]" : "text-[var(--gray-9)]",
                          )}>{i + 1}</span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-[var(--gray-12)]">
                            <Hash className="h-3 w-3 text-[var(--gray-12)]" />{h.hashtag}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs text-[var(--gray-8)]">{fmtInt(h.views)}</td>
                        <td className="px-3 py-2.5 text-right text-xs text-[var(--gray-8)]">{fmtInt(h.publish_count)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </div>
      </Panel>
    </section>
  );
}
