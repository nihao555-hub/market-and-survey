"use client";
import React, { useRef, useEffect } from "react";
import {
  LayoutList, RefreshCw, Clock, ShoppingCart, Star, Store, Flame, Hash,
  TrendingUp, Package, Users, Search, X, BarChart3,
} from "lucide-react";
import type { EChartsOption } from "echarts";
import {
  fetchDailyRefreshStatus, fetchDataSnapshots, fetchAllSnapshots,
  type DataSnapshot, type RefreshStatus,
} from "@/lib/api";
import {
  PageContainer, PageHeader, StatTile, Button, EmptyState, Skeleton, FilterTabs,
} from "./primitives";
import { cn } from "@/lib/utils";
import { CategoryTrendTable } from "./CategoryTrendTable";
import { ProductDetailModal, type ProductForModal } from "./ProductDetailModal";

// ─── ECharts wrapper ───
function CatChart({ option, height = 300 }: { option: EChartsOption; height?: number }) {
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

function fmtShortTime(iso?: string | null): string {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); } catch { return ""; }
}

function buildCatTrendChart(history: DataSnapshot[], metric: "avgPrice" | "count" | "avgRating"): EChartsOption {
  const byRun = new Map<string, DataSnapshot[]>();
  for (const s of history) {
    const key = s.capturedAt?.slice(0, 16) || s.id;
    if (!byRun.has(key)) byRun.set(key, []);
    byRun.get(key)!.push(s);
  }
  const entries = [...byRun.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  if (entries.length < 1) return {};

  const allCats = new Set<string>();
  for (const [, snaps] of entries) {
    for (const s of snaps) {
      const name = (s.payload?.category_name || s.payload?.category_name_en || "") as string;
      if (name) allCats.add(name);
    }
  }
  const catList = [...allCats].slice(0, 10);
  const times = entries.map(([t]) => fmtShortTime(t) || t);
  const COLORS = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ef4444", "#06b6d4", "#84cc16", "#f97316"];
  const metricLabel = metric === "avgPrice" ? "均价 ($)" : metric === "count" ? "商品数" : "均评分";

  return {
    legend: { data: catList, bottom: 0, textStyle: { fontSize: 11, color: "#888" }, type: "scroll", pageIconColor: "#888" },
    xAxis: { type: "category", data: times, axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
    yAxis: { type: "value", name: metricLabel, nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f5f5f5" } } },
    series: catList.map((cat, i) => ({
      name: cat,
      type: "line" as const,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: COLORS[i % COLORS.length] },
      data: entries.map(([, snaps]) => {
        const s = snaps.find((snap) => (snap.payload?.category_name || snap.payload?.category_name_en) === cat);
        if (!s) return null;
        const prods = (s.payload?.products || []) as Array<{ price?: number; rating?: number }>;
        if (metric === "count") return prods.length;
        const vals = prods.map((p) => metric === "avgPrice" ? p.price : p.rating).filter((v): v is number => typeof v === "number" && v > 0);
        return vals.length ? +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : null;
      }),
    })),
  };
}

type CatMetric = "avgPrice" | "count" | "avgRating";

/** 品类总览表：聚合所有品类的关键指标 */
function CategoryOverviewTable({ cats, onSelectCat }: { cats: DataSnapshot[]; onSelectCat: (id: string) => void }) {
  if (cats.length === 0) return null;
  const rows = cats.map((c) => {
    const prods: ShopProduct[] = c.payload?.products ?? [];
    const prices = prods.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
    const ratings = prods.map((p) => p.rating).filter((v): v is number => typeof v === "number" && v > 0);
    return {
      id: c.payload?.category_id as string,
      name: (c.payload?.category_name ?? c.payload?.category_name_en ?? "—") as string,
      count: prods.length,
      priceMin: prices.length ? Math.min(...prices) : null,
      priceMax: prices.length ? Math.max(...prices) : null,
      avgPrice: prices.length ? +(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : null,
      avgRating: ratings.length ? +(ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : null,
      topProduct: prods[0] ?? null,
    };
  });
  return (
    <div className="mb-5 overflow-hidden rounded-xl border border-hairline">
      <div className="bg-surface-1 px-4 py-2.5 text-xs font-semibold text-ink-muted">品类总览（{rows.length} 个品类）</div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-hairline bg-surface-1/50 text-[11px] text-ink-subtle">
              <th className="px-3 py-2 font-medium">品类</th>
              <th className="px-3 py-2 font-medium text-right">商品数</th>
              <th className="px-3 py-2 font-medium text-right">价格区间</th>
              <th className="px-3 py-2 font-medium text-right">均价</th>
              <th className="px-3 py-2 font-medium text-right">均评分</th>
              <th className="px-3 py-2 font-medium">TOP 商品</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.id}
                className="border-b border-hairline last:border-0 hover:bg-surface-1/30 cursor-pointer transition-colors"
                onClick={() => onSelectCat(r.id)}
              >
                <td className="px-3 py-2 font-medium text-ink">{r.name}</td>
                <td className="px-3 py-2 text-right text-ink-subtle">{r.count}</td>
                <td className="px-3 py-2 text-right text-ink-subtle">
                  {r.priceMin !== null ? `$${r.priceMin}–$${r.priceMax}` : "—"}
                </td>
                <td className="px-3 py-2 text-right text-ink-subtle">{r.avgPrice !== null ? `$${r.avgPrice}` : "—"}</td>
                <td className="px-3 py-2 text-right text-ink-subtle">{r.avgRating ?? "—"}</td>
                <td className="px-3 py-2 max-w-[180px] truncate text-ink-subtle">{r.topProduct?.title ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// 后端 daily_refresh 落库时的固定 term 标签
const HOT_SELLING_TERM = "🛒 实时热销榜";
const HASHTAG_TREND_TERM = "🏷️ 热门话题榜";

// 与 modules/tikhub._normalize_product 字段一致
interface ShopProduct {
  product_id?: string;
  title?: string;
  price?: number | null;
  original_price?: number | null;
  discount_pct?: number | null;
  currency_symbol?: string | null;
  rating?: number | null;
  review_count?: number | null;
  sold_count?: number | null;
  shop_name?: string | null;
  shop_logo?: string | null;
  image?: string | null;
  url?: string | null;
}
interface CategoryPayload {
  category_id?: string;
  category_name?: string;
  category_name_en?: string;
  products?: ShopProduct[];
  stats?: { price_min?: number | null; price_max?: number | null; weighted_avg_rating?: number | null };
}
interface CurvePoint { t?: string | number | null; v?: number | null; }
interface Creator { nickname?: string | null; avatar?: string | null; followers?: number | null; }
interface Hashtag {
  hashtag?: string | null;
  views?: number | null;
  publish_count?: number | null;
  rank?: number | null;
  popularity_curve?: CurvePoint[];
  top_creators?: Creator[];
}

type Tab = "category" | "hot" | "hashtag";

function fmtInt(n?: number | null): string {
  if (typeof n !== "number" || !isFinite(n) || n <= 0) return "—";
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  return n.toLocaleString("en-US");
}
function fmtTime(iso?: string | null): string {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("zh-CN", { hour12: false }); } catch { return iso; }
}
function rankBadge(i: number): string {
  if (i === 0) return "bg-amber-400 text-white";
  if (i === 1) return "bg-slate-400 text-white";
  if (i === 2) return "bg-amber-700 text-white";
  return "bg-white/90 text-ink";
}
function matchProduct(p: ShopProduct, q: string): boolean {
  if (!q) return true;
  const hay = `${p.title ?? ""} ${p.shop_name ?? ""}`.toLowerCase();
  return hay.includes(q);
}

/** 商品卡（品类榜 / 热销榜共用，紧凑版） */
function ProductCard({ p, rank, catTag, onClick }: { p: ShopProduct; rank: number; catTag?: string; onClick?: () => void }) {
  const sym = p.currency_symbol || "$";
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col overflow-hidden rounded-2xl border border-hairline bg-white text-left transition-all hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-md"
    >
      <div className="relative aspect-square w-full overflow-hidden bg-surface-2">
        {p.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={p.image} alt="" loading="lazy"
               className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-ink-tertiary">
            <ShoppingCart className="h-8 w-8" />
          </div>
        )}
        <span className={cn(
          "absolute left-2 top-2 flex h-6 w-6 items-center justify-center rounded-full text-[12px] font-bold shadow-sm",
          rankBadge(rank),
        )}>
          {rank + 1}
        </span>
        {typeof p.discount_pct === "number" && p.discount_pct > 0 && (
          <span className="absolute right-2 top-2 rounded-md bg-rose-500 px-1.5 py-0.5 text-[11px] font-semibold text-white shadow-sm">
            -{p.discount_pct}%
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col p-3">
        {catTag && (
          <span className="mb-1.5 inline-flex w-fit items-center gap-0.5 rounded bg-brand/10 px-1.5 py-0.5 text-[10px] font-medium text-brand">
            <Package className="h-2.5 w-2.5" />{catTag}
          </span>
        )}
        <div className="line-clamp-2 min-h-[32px] text-[12px] font-medium leading-tight text-ink">{p.title}</div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-sm font-semibold text-ink">{sym}{p.price}</span>
          {p.original_price ? (
            <span className="text-[11px] text-ink-tertiary line-through">{sym}{p.original_price}</span>
          ) : null}
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-ink-subtle">
          <span className="inline-flex items-center gap-0.5">
            <ShoppingCart className="h-3 w-3" /> 已售 {fmtInt(p.sold_count)}
          </span>
          {p.rating ? (
            <span className="inline-flex items-center gap-0.5">
              <Star className="h-3 w-3 fill-current text-amber-500" />{p.rating}
              {p.review_count ? <span className="text-ink-tertiary">({fmtInt(p.review_count)})</span> : null}
            </span>
          ) : null}
        </div>
        <div className="mt-2 flex items-center gap-1 border-t border-hairline pt-2 text-[11px] text-ink-muted">
          {p.shop_logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={p.shop_logo} alt="" className="h-4 w-4 flex-shrink-0 rounded-full object-cover" />
          ) : (
            <Store className="h-3 w-3 flex-shrink-0" />
          )}
          <span className="truncate">{p.shop_name || "—"}</span>
        </div>
      </div>
    </button>
  );
}

/** 声量曲线迷你 sparkline（归一化 popularity_curve） */
function Sparkline({ curve, className }: { curve: CurvePoint[]; className?: string }) {
  const vals = curve.map((c) => (typeof c.v === "number" ? c.v : 0));
  if (vals.length < 2) return null;
  const max = Math.max(...vals), min = Math.min(...vals);
  const span = max - min || 1;
  const W = 120, H = 32;
  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * W;
    const y = H - ((v - min) / span) * H;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const rising = vals[vals.length - 1] >= vals[0];
  const stroke = rising ? "#10b981" : "#f43f5e";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={cn("h-8 w-[120px]", className)} preserveAspectRatio="none">
      <polyline points={pts.join(" ")} fill="none" stroke={stroke} strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function CategoryRankPage() {
  const [status, setStatus] = React.useState<RefreshStatus | null>(null);
  const [cats, setCats] = React.useState<DataSnapshot[]>([]);
  const [hot, setHot] = React.useState<DataSnapshot | null>(null);
  const [hashtagSnap, setHashtagSnap] = React.useState<DataSnapshot | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [reloading, setReloading] = React.useState(false);
  const [tab, setTab] = React.useState<Tab>("category");
  const [activeCat, setActiveCat] = React.useState<string | null>(null);
  const [query, setQuery] = React.useState("");
  const [selectedProduct, setSelectedProduct] = React.useState<ProductForModal | null>(null);
  const [catHistory, setCatHistory] = React.useState<DataSnapshot[]>([]);
  const [catMetric, setCatMetric] = React.useState<CatMetric>("avgPrice");
  const q = query.trim().toLowerCase();

  const openProduct = (p: ShopProduct, opts?: { category?: string; source?: string }) => {
    setSelectedProduct({ ...p, _category: opts?.category, _source: opts?.source });
  };

  const reload = React.useCallback(async () => {
    setReloading(true);
    try {
      const [st, catSnaps, hotSnaps, htSnaps, catHist] = await Promise.all([
        fetchDailyRefreshStatus(),
        fetchDataSnapshots({ source: "category_rank", limit: 40 }),
        fetchDataSnapshots({ term: HOT_SELLING_TERM, limit: 1 }),
        fetchDataSnapshots({ term: HASHTAG_TREND_TERM, limit: 1 }),
        fetchAllSnapshots({ source: "category_rank", limit: 300 }),
      ]);
      setStatus(st);
      const okCats = catSnaps.filter((s) => s.realData && (s.payload?.products?.length ?? 0) > 0);
      setCats(okCats);
      setHot(hotSnaps[0] ?? null);
      setHashtagSnap(htSnaps[0] ?? null);
      setCatHistory(catHist);
      setActiveCat((prev) => prev ?? okCats[0]?.payload?.category_id ?? null);
    } catch { /* 静默 */ }
    finally { setLoading(false); setReloading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  // 热销榜：优先使用专用快照，无数据时从全品类中按已售量排序 fallback
  const hotProducts: ShopProduct[] = React.useMemo(() => {
    const dedicated: ShopProduct[] = Array.isArray(hot?.payload?.products) ? hot!.payload.products : [];
    if (dedicated.length > 0) return dedicated;
    // fallback: aggregate top sellers from all categories
    const all = cats.flatMap((c) => (Array.isArray(c.payload?.products) ? c.payload.products : []) as ShopProduct[]);
    return all
      .filter((p) => typeof p.sold_count === "number" && p.sold_count > 0)
      .sort((a, b) => (b.sold_count ?? 0) - (a.sold_count ?? 0))
      .slice(0, 30);
  }, [hot, cats]);
  const hashtags: Hashtag[] = Array.isArray(hashtagSnap?.payload?.hashtags) ? hashtagSnap!.payload.hashtags : [];
  const activeCatSnap = cats.find((c) => c.payload?.category_id === activeCat) ?? cats[0];
  const activeCatProducts: ShopProduct[] = Array.isArray(activeCatSnap?.payload?.products)
    ? activeCatSnap!.payload.products : [];

  // 搜索（即时、零成本，只过滤已加载的当日榜单数据）
  const searching = q.length > 0;
  // 「品类 Top」tab 搜索时跨全部品类聚合命中（带品类标签），清空则恢复单品类视图
  const crossCatHits: { p: ShopProduct; cat?: string }[] = searching
    ? cats.flatMap((c) =>
        (Array.isArray(c.payload?.products) ? c.payload.products : [])
          .filter((p: ShopProduct) => matchProduct(p, q))
          .map((p: ShopProduct) => ({ p, cat: c.payload?.category_name as string | undefined })),
      )
    : [];
  const hotFiltered = searching ? hotProducts.filter((p) => matchProduct(p, q)) : hotProducts;
  const hashtagsFiltered = searching
    ? hashtags.filter((h) => (h.hashtag ?? "").toLowerCase().includes(q))
    : hashtags;

  const catChartOpt = React.useMemo(() => buildCatTrendChart(catHistory, catMetric), [catHistory, catMetric]);
  const hasCatHistory = catHistory.length > 0;

  const channelOk = status?.tier2ChannelOk ?? false;
  const hasAny = cats.length > 0 || hotProducts.length > 0 || hashtags.length > 0;

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "category", label: "品类 Top", count: searching ? crossCatHits.length : cats.length },
    { key: "hot", label: "实时热销榜", count: hotFiltered.length },
    { key: "hashtag", label: "热门话题", count: hashtagsFiltered.length },
  ];

  return (
    <PageContainer>
      <PageHeader
        icon={<LayoutList className="h-5 w-5" />}
        title="品类榜单"
        subtitle="TikTok Shop 按品类实时 Top 商品 + 全站热销榜 + 热门话题声量曲线，作为选品与机会挖掘的实时榜单底盘。"
        actions={
          <Button variant="secondary" size="sm" loading={reloading} onClick={reload}>
            <RefreshCw className="h-3.5 w-3.5" />刷新
          </Button>
        }
      />

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => <Skeleton key={i} className="h-60 w-full" />)}
          </div>
        </div>
      ) : (
        <>
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="最近更新" value={fmtTime(status?.finishedAt)} icon={<Clock className="h-4 w-4" />} />
            <StatTile label="覆盖品类" value={String(cats.length)} icon={<Package className="h-4 w-4" />} />
            <StatTile label="热销商品" value={String(hotProducts.length)} icon={<Flame className="h-4 w-4" />} />
            <StatTile label="热门话题" value={String(hashtags.length)} icon={<Hash className="h-4 w-4" />} />
          </div>

          {!channelOk && (
            <div className="mb-5 rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-xs text-ink-subtle">
              榜单通道（TikHub）需配置 <span className="font-medium text-ink-muted">TIKHUB_API_KEY</span>；通道未就绪时如实标注，<span className="font-medium text-ink-muted">不编造数据</span>，接入后自动补齐。
            </div>
          )}

          {/* ═══ Category Trend Chart (hero section) ═══ */}
          {hasCatHistory && (
            <section className="mb-6 rounded-[8px] border border-hairline bg-white overflow-hidden">
              <div className="flex items-center justify-between border-b border-surface-3 px-5 py-3">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
                  <BarChart3 className="h-4 w-4 text-ink-subtle" />
                  品类趋势走势
                </h2>
                <div className="flex items-center gap-1">
                  {(["avgPrice", "count", "avgRating"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setCatMetric(m)}
                      className={cn(
                        "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                        catMetric === m ? "bg-ink text-white" : "text-ink-subtle hover:bg-surface-1 hover:text-ink"
                      )}
                    >
                      {m === "avgPrice" ? "均价" : m === "count" ? "商品数" : "评分"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="px-2 pt-2 pb-1">
                <CatChart option={catChartOpt} height={300} />
              </div>
            </section>
          )}

          {!hasAny ? (
            <EmptyState
              icon={<LayoutList className="h-6 w-6" />}
              title="还没有榜单数据"
              hint="等待每日自动刷新，或点击「立即刷新」获取一次真实榜单数据。"
            />
          ) : (
            <>
              {/* 品类总览表 */}
              {tab === "category" && !searching && (
                <CategoryOverviewTable cats={cats} onSelectCat={(id) => { setActiveCat(id); setTab("category"); }} />
              )}

              {/* 品类趋势分析表格（跨日期对比） */}
              <div className="mb-5">
                <CategoryTrendTable />
              </div>

              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <FilterTabs tabs={tabs} value={tab} onChange={setTab} />
                <div className="relative w-full sm:w-64">
                  <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-tertiary" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="搜商品 / 店铺 / 话题…"
                    className="w-full rounded-lg border border-hairline bg-surface-1 py-1.5 pl-8 pr-8 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
                  />
                  {query && (
                    <button
                      onClick={() => setQuery("")}
                      className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-ink-tertiary hover:bg-surface-2 hover:text-ink"
                      title="清空"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* 品类 Top */}
              {tab === "category" && (
                cats.length === 0 ? (
                  <EmptyState icon={<Package className="h-6 w-6" />} title="暂无品类榜单" />
                ) : searching ? (
                  // 搜索态：跨全部品类聚合命中
                  crossCatHits.length === 0 ? (
                    <EmptyState icon={<Search className="h-6 w-6" />} title={`全部品类中没有匹配「${query.trim()}」的商品`} hint="换个关键词，或清空搜索看完整榜单。" />
                  ) : (
                    <>
                      <div className="mb-3 flex items-center gap-2 text-xs text-ink-subtle">
                        <Search className="h-3.5 w-3.5 text-brand" />
                        在全部 {cats.length} 个品类中搜「<span className="font-medium text-ink-muted">{query.trim()}</span>」· 命中 {crossCatHits.length} 个商品
                      </div>
                      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
                        {crossCatHits.map(({ p, cat }, i) => (
                          <ProductCard key={`${p.product_id ?? "x"}-${i}`} p={p} rank={i} catTag={cat} onClick={() => openProduct(p, { category: cat })} />
                        ))}
                      </div>
                    </>
                  )
                ) : (
                  <>
                    <div className="mb-4 flex flex-wrap gap-2">
                      {cats.map((c) => {
                        const cid = c.payload?.category_id;
                        const active = cid === (activeCatSnap?.payload?.category_id);
                        return (
                          <button
                            key={cid}
                            onClick={() => setActiveCat(cid)}
                            className={cn(
                              "rounded-full border px-3 py-1.5 text-xs transition-colors",
                              active
                                ? "border-brand/30 bg-brand/10 font-medium text-brand"
                                : "border-hairline bg-white text-ink-muted hover:bg-surface-1 hover:text-ink",
                            )}
                          >
                            {c.payload?.category_name}
                            <span className={cn("ml-1.5 text-[10px]", active ? "text-brand/70" : "text-ink-tertiary")}>
                              {c.payload?.products?.length ?? 0}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                    {activeCatSnap && (
                      <div className="mb-3 flex items-center gap-2 text-xs text-ink-subtle">
                        <TrendingUp className="h-3.5 w-3.5 text-brand" />
                        <span className="font-medium text-ink-muted">{activeCatSnap.payload?.category_name}</span>
                        · 实时 Top {activeCatProducts.length}
                        {activeCatSnap.payload?.stats?.weighted_avg_rating
                          ? ` · 加权均分 ${activeCatSnap.payload.stats.weighted_avg_rating}` : ""}
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
                      {activeCatProducts.map((p, i) => <ProductCard key={p.product_id ?? i} p={p} rank={i} onClick={() => openProduct(p, { category: activeCatSnap?.payload?.category_name as string })} />)}
                    </div>
                  </>
                )
              )}

              {/* 实时热销榜 */}
              {tab === "hot" && (
                hotProducts.length === 0 ? (
                  <EmptyState icon={<Flame className="h-6 w-6" />} title="暂无热销榜数据" hint={hot?.summary} />
                ) : hotFiltered.length === 0 ? (
                  <EmptyState icon={<Search className="h-6 w-6" />} title={`热销榜中没有匹配「${query.trim()}」的商品`} hint="换个关键词，或清空搜索看完整榜单。" />
                ) : (
                  <>
                    {searching && (
                      <div className="mb-3 flex items-center gap-2 text-xs text-ink-subtle">
                        <Search className="h-3.5 w-3.5 text-brand" />
                        命中 {hotFiltered.length} / {hotProducts.length} 个热销商品
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
                      {hotFiltered.map((p, i) => <ProductCard key={p.product_id ?? i} p={p} rank={i} onClick={() => openProduct(p, { source: "实时热销榜" })} />)}
                    </div>
                  </>
                )
              )}

              {/* 热门话题 + 声量曲线 */}
              {tab === "hashtag" && (
                hashtags.length === 0 ? (
                  <EmptyState icon={<Hash className="h-6 w-6" />} title="暂无热门话题数据" hint={hashtagSnap?.summary} />
                ) : hashtagsFiltered.length === 0 ? (
                  <EmptyState icon={<Search className="h-6 w-6" />} title={`没有匹配「${query.trim()}」的话题`} hint="换个关键词，或清空搜索看完整榜单。" />
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {hashtagsFiltered.map((h, i) => (
                      <div key={h.hashtag ?? i} className="rounded-2xl border border-hairline bg-white p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5 text-sm font-semibold text-ink">
                              <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-[11px] font-bold text-brand">
                                {i + 1}
                              </span>
                              <Hash className="h-3.5 w-3.5 flex-shrink-0 text-brand" />
                              <span className="truncate">{h.hashtag}</span>
                            </div>
                            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-subtle">
                              <span className="inline-flex items-center gap-0.5">
                                <TrendingUp className="h-3 w-3" /> 浏览 {fmtInt(h.views)}
                              </span>
                              <span>发布 {fmtInt(h.publish_count)}</span>
                            </div>
                          </div>
                          <Sparkline curve={h.popularity_curve ?? []} />
                        </div>
                        {Array.isArray(h.top_creators) && h.top_creators.length > 0 && (
                          <div className="mt-3 flex items-center gap-2 border-t border-hairline pt-2.5">
                            <Users className="h-3.5 w-3.5 flex-shrink-0 text-ink-tertiary" />
                            <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                              {h.top_creators.slice(0, 4).map((c, ci) => (
                                <span key={ci} className="inline-flex items-center gap-1 rounded-full bg-surface-1 py-0.5 pl-0.5 pr-2 text-[11px] text-ink-muted">
                                  {c.avatar ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={c.avatar} alt="" className="h-4 w-4 rounded-full object-cover" />
                                  ) : (
                                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-surface-2"><Users className="h-2.5 w-2.5" /></span>
                                  )}
                                  <span className="max-w-[88px] truncate">{c.nickname || "—"}</span>
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )
              )}
            </>
          )}
        </>
      )}
      <ProductDetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
    </PageContainer>
  );
}
