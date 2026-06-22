"use client";
import React from "react";
import {
  LayoutList, RefreshCw, Clock, ShoppingCart, Star, Store, Flame, Hash,
  TrendingUp, Package, Users, Search, X, Filter, ChevronDown,
} from "lucide-react";
import { zhCat, matchCategory } from "@/lib/category-i18n";
import {
  fetchDailyRefreshStatus, fetchDataSnapshots, fetchAllSnapshots,
  fetchCategorySparklines,
  type DataSnapshot, type RefreshStatus, type CategorySparkData,
} from "@/lib/api";
import {
  PageContainer, PageHeader, StatTile, Button, EmptyState, Skeleton, FilterTabs,
} from "./primitives";
import { cn } from "@/lib/utils";
import { CategoryTrendTable } from "./CategoryTrendTable";
import { ProductDetailModal, type ProductForModal } from "./ProductDetailModal";
import { CategoryDetailModal } from "./CategoryDetailModal";

// (CatChart + buildCatTrendChart removed — replaced by PerCategoryCards below)

// ─── Per-category sparkline (SVG) ───
function CatSparkline({ values }: { values: number[] }) {
  if (values.length === 0) return null;
  const W = 100, H = 28;
  // Single point: show a dot + flat line
  if (values.length === 1) {
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="h-7 w-[100px]" preserveAspectRatio="none">
        <line x1="0" y1={H / 2} x2={W} y2={H / 2} stroke="#a1a1aa" strokeWidth="1" strokeDasharray="3,3" />
        <circle cx={W / 2} cy={H / 2} r="3" fill="#6366f1" />
      </svg>
    );
  }
  const max = Math.max(...values), min = Math.min(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - min) / span) * (H - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const rising = values[values.length - 1] >= values[0];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-7 w-[100px]" preserveAspectRatio="none">
      <polyline points={pts.join(" ")} fill="none" stroke={rising ? "#10b981" : "#f43f5e"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Mini price distribution bar chart (5 buckets) */
function PriceDistBar({ products }: { products: ShopProduct[] }) {
  const prices = products.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
  if (prices.length < 3) return null;
  const buckets = [0, 0, 0, 0, 0]; // $0-10, $10-25, $25-50, $50-100, $100+
  for (const p of prices) {
    if (p <= 10) buckets[0]++;
    else if (p <= 25) buckets[1]++;
    else if (p <= 50) buckets[2]++;
    else if (p <= 100) buckets[3]++;
    else buckets[4]++;
  }
  const maxB = Math.max(...buckets) || 1;
  const labels = ["≤10", "10-25", "25-50", "50-100", "100+"];
  return (
    <div className="flex items-end gap-[2px] h-5">
      {buckets.map((b, i) => (
        <div key={i} className="flex flex-col items-center gap-0" title={`$${labels[i]}: ${b}件`}>
          <div
            className="w-[10px] rounded-t-sm bg-indigo-400/70"
            style={{ height: `${Math.max(2, (b / maxB) * 18)}px` }}
          />
        </div>
      ))}
    </div>
  );
}

interface CatCardData {
  name: string;
  catId: string;
  latestAvgPrice: number;
  latestCount: number;
  latestAvgRating: number;
  priceHistory: number[];
  countHistory: number[];
  ratingHistory: number[];
  trendsHistory: number[];
  top5: Array<{ title: string; price: number; sold: number; rating: number; image?: string }>;
  allProducts: ShopProduct[];
}

/** Map Google Trends keywords to their most relevant category slug */
const KEYWORD_TO_CATEGORY: Record<string, string> = {
  "garlic press": "kitchenware",
  "kitchen scale": "kitchenware",
  "wireless earbuds": "phones-electronics",
  "bluetooth speaker": "phones-electronics",
  "phone holder": "phones-electronics",
  "yoga mat": "sports-outdoor",
  "resistance bands": "sports-outdoor",
  "pet hair remover": "pet-supplies",
  "cat litter mat": "pet-supplies",
  "jade roller": "beauty-personal-care",
  "makeup organizer": "beauty-personal-care",
  "humidifier": "household-appliances",
  "air purifier": "household-appliances",
  "desk organizer": "computers-office-equipment",
  "led strip lights": "home-improvement",
  "massage gun": "health",
};

/** Extract stats from a single snapshot — handles both live (products[]) and backfill (avg_price/product_count/avg_rating) */
function _extractStats(s: DataSnapshot): { avgPrice: number; count: number; avgRating: number } | null {
  const p = s.payload;
  if (!p) return null;
  if (typeof p.avg_price === "number" || typeof p.product_count === "number") {
    return {
      avgPrice: (p.avg_price as number) || 0,
      count: (p.product_count as number) || 0,
      avgRating: (p.avg_rating as number) || 0,
    };
  }
  const prods = (p.products || []) as ShopProduct[];
  if (prods.length === 0) return null;
  const prices = prods.map((pr) => pr.price).filter((v): v is number => typeof v === "number" && v > 0);
  const ratings = prods.map((pr) => pr.rating).filter((v): v is number => typeof v === "number" && v > 0);
  return {
    avgPrice: prices.length ? +(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : 0,
    count: prods.length,
    avgRating: ratings.length ? +(ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : 0,
  };
}

function buildPerCatCards(latestSnaps: DataSnapshot[], historySnaps: DataSnapshot[]): CatCardData[] {
  // Group history by day for backfill aggregation
  const byRun = new Map<string, DataSnapshot[]>();
  for (const s of historySnaps) {
    const key = s.capturedAt?.slice(0, 10) || s.id;
    if (!byRun.has(key)) byRun.set(key, []);
    byRun.get(key)!.push(s);
  }
  const entries = [...byRun.entries()].sort((a, b) => a[0].localeCompare(b[0]));

  // Collect all category names from both latest and history
  const catNames = new Map<string, string>();
  for (const s of [...latestSnaps, ...historySnaps]) {
    const name = (s.payload?.category_name || s.payload?.category_name_en || "") as string;
    const catId = (s.payload?.category_id || "") as string;
    if (name && !catNames.has(name)) catNames.set(name, catId);
  }

  const cards: CatCardData[] = [];
  for (const [name, catId] of catNames) {
    // Find latest snapshot with products array for Top 5
    const latestSnap = latestSnaps.find((s) => (s.payload?.category_name || s.payload?.category_name_en) === name);
    const prods = (latestSnap?.payload?.products || []) as ShopProduct[];

    const latestStats = latestSnap ? _extractStats(latestSnap) : null;
    let latestAvgPrice = latestStats?.avgPrice ?? 0;
    let latestCount = latestStats?.count ?? prods.length;
    let latestAvgRating = latestStats?.avgRating ?? 0;

    const priceHistory: number[] = [];
    const countHistory: number[] = [];
    const ratingHistory: number[] = [];
    for (const [, snaps] of entries) {
      const s = snaps.find((s2) => (s2.payload?.category_name || s2.payload?.category_name_en) === name);
      if (!s) continue;
      const stats = _extractStats(s);
      if (!stats) continue;
      priceHistory.push(stats.avgPrice);
      countHistory.push(stats.count);
      ratingHistory.push(stats.avgRating);
    }

    if (!latestStats && priceHistory.length > 0) {
      latestAvgPrice = priceHistory[priceHistory.length - 1];
      latestCount = countHistory[countHistory.length - 1];
      latestAvgRating = ratingHistory[ratingHistory.length - 1];
    }

    const top5 = prods
      .filter((p) => p.title)
      .sort((a, b) => (b.sold_count ?? 0) - (a.sold_count ?? 0))
      .slice(0, 5)
      .map((p) => ({
        title: p.title || "",
        price: p.price || 0,
        sold: p.sold_count || 0,
        rating: p.rating || 0,
        image: p.image ?? undefined,
      }));

    cards.push({
      name, catId,
      latestAvgPrice, latestCount, latestAvgRating,
      priceHistory, countHistory, ratingHistory, top5,
      allProducts: prods,
    });
  }
  return cards.sort((a, b) => b.latestCount - a.latestCount);
}

/** Build cards from pre-aggregated sparkline data (server-side). Much faster than raw snapshots. */
function buildPerCatCardsFromSpark(latestSnaps: DataSnapshot[], sparkData: CategorySparkData[], gtSnaps?: DataSnapshot[]): CatCardData[] {
  const cards: CatCardData[] = [];
  const sparkMap = new Map(sparkData.map((s) => [s.name, s]));

  // Build Google Trends history per category from keyword mapping
  const catTrendsMap = new Map<string, number[]>();
  if (gtSnaps && gtSnaps.length > 0) {
    // Group GT snaps by keyword → time series
    const kwPoints = new Map<string, { ts: string; val: number }[]>();
    for (const s of gtSnaps) {
      const kw = (s.payload?.keyword as string) || "";
      if (!kw) continue;
      const val = (s.payload?.late_avg as number) || 0;
      const ts = (s.payload?.backfill_ts as string) || s.capturedAt || "";
      if (!kwPoints.has(kw)) kwPoints.set(kw, []);
      kwPoints.get(kw)!.push({ ts, val });
    }
    // Map keywords to categories and aggregate
    for (const [kw, pts] of kwPoints) {
      const catSlug = KEYWORD_TO_CATEGORY[kw];
      if (!catSlug) continue;
      pts.sort((a, b) => a.ts.localeCompare(b.ts));
      const existing = catTrendsMap.get(catSlug) || [];
      if (pts.length > existing.length) {
        catTrendsMap.set(catSlug, pts.map((p) => p.val));
      }
    }
  }

  // Build from sparkData (covers all categories including backfill-only ones)
  const allNames = new Set([
    ...sparkData.map((s) => s.name),
    ...latestSnaps.map((s) => (s.payload?.category_name || s.payload?.category_name_en || "") as string).filter(Boolean),
  ]);

  for (const name of allNames) {
    const spark = sparkMap.get(name);
    const latestSnap = latestSnaps.find((s) => (s.payload?.category_name || s.payload?.category_name_en) === name);
    const prods = (latestSnap?.payload?.products || []) as ShopProduct[];

    const priceHistory = spark?.points.map((p) => p.avgPrice) ?? [];
    const countHistory = spark?.points.map((p) => p.productCount) ?? [];
    const ratingHistory = spark?.points.map((p) => p.avgRating) ?? [];
    // Google Trends sparkline: match category slug from latestSnap or name
    const catSlug = (latestSnap?.payload?.category_name_en as string) || name;
    const trendsHistory = catTrendsMap.get(catSlug) || [];

    const latestStats = latestSnap ? _extractStats(latestSnap) : null;
    const latestAvgPrice = latestStats?.avgPrice ?? (priceHistory.length ? priceHistory[priceHistory.length - 1] : 0);
    const latestCount = latestStats?.count ?? (countHistory.length ? countHistory[countHistory.length - 1] : prods.length);
    const latestAvgRating = latestStats?.avgRating ?? (ratingHistory.length ? ratingHistory[ratingHistory.length - 1] : 0);

    const top5 = prods
      .filter((p) => p.title)
      .sort((a, b) => (b.sold_count ?? 0) - (a.sold_count ?? 0))
      .slice(0, 5)
      .map((p) => ({
        title: p.title || "",
        price: p.price || 0,
        sold: p.sold_count || 0,
        rating: p.rating || 0,
        image: p.image ?? undefined,
      }));

    cards.push({
      name,
      catId: spark?.categoryId || (latestSnap?.payload?.category_id as string) || "",
      latestAvgPrice, latestCount, latestAvgRating,
      priceHistory, countHistory, ratingHistory, trendsHistory, top5,
      allProducts: prods,
    });
  }
  return cards.sort((a, b) => b.latestCount - a.latestCount);
}

function fmtSold(n: number): string {
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return String(n);
}

type CatSortKey = "count" | "price" | "rating" | "name";

function PerCategoryCards({ latestSnaps, sparkData, googleTrendsSnaps, onSelectCat }: {
  latestSnaps: DataSnapshot[];
  sparkData: CategorySparkData[];
  googleTrendsSnaps?: DataSnapshot[];
  onSelectCat: (id: string) => void;
}) {
  const cards = React.useMemo(() => buildPerCatCardsFromSpark(latestSnaps, sparkData, googleTrendsSnaps), [latestSnaps, sparkData, googleTrendsSnaps]);
  const [catSearch, setCatSearch] = React.useState("");
  const [sortKey, setSortKey] = React.useState<CatSortKey>("count");
  const [viewMode, setViewMode] = React.useState<"card" | "table">("card");

  const filtered = React.useMemo(() => {
    let list = cards.filter((c) => matchCategory(c.name, catSearch));
    const sorters: Record<CatSortKey, (a: CatCardData, b: CatCardData) => number> = {
      count: (a, b) => b.latestCount - a.latestCount,
      price: (a, b) => b.latestAvgPrice - a.latestAvgPrice,
      rating: (a, b) => b.latestAvgRating - a.latestAvgRating,
      name: (a, b) => zhCat(a.name).localeCompare(zhCat(b.name), "zh-CN"),
    };
    list.sort(sorters[sortKey]);
    return list;
  }, [cards, catSearch, sortKey]);

  if (cards.length === 0) return null;

  return (
    <section className="mb-6">
      {/* Twenty CRM style header bar */}
      <div className="mb-4 rounded-lg border border-[var(--gray-5)] bg-[var(--gray-2)] p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-[var(--gray-9)]" />
            <h2 className="text-sm font-semibold text-[var(--gray-12)]">品类趋势</h2>
            <span className="rounded-[4px] bg-[var(--gray-4)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--gray-9)]">
              {filtered.length} / {cards.length}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Search input */}
            <div className="relative">
              <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--gray-7)]" />
              <input
                value={catSearch}
                onChange={(e) => setCatSearch(e.target.value)}
                placeholder="搜索品类（中文/英文）…"
                className="w-48 rounded-md border border-[var(--gray-5)] bg-[var(--gray-1)] py-1.5 pl-7 pr-7 text-xs text-[var(--gray-12)] outline-none transition-all focus:w-64 focus:border-[var(--gray-8)]/40 focus:ring-2 focus:ring-brand/15"
              />
              {catSearch && (
                <button onClick={() => setCatSearch("")} className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-[var(--gray-7)] hover:text-[var(--gray-12)]">
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
            {/* Sort dropdown */}
            <div className="relative">
              <select
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as CatSortKey)}
                className="appearance-none rounded-md border border-[var(--gray-5)] bg-[var(--gray-1)] py-1.5 pl-2 pr-6 text-xs text-[var(--gray-11)] outline-none hover:border-[var(--gray-6)]"
              >
                <option value="count">按商品数</option>
                <option value="price">按均价</option>
                <option value="rating">按评分</option>
                <option value="name">按名称</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 text-[var(--gray-7)]" />
            </div>
            {/* View toggle */}
            <div className="flex rounded-md border border-[var(--gray-5)] bg-[var(--gray-1)]">
              <button
                onClick={() => setViewMode("card")}
                className={cn("rounded-l-md px-2 py-1.5 text-xs transition-colors", viewMode === "card" ? "bg-[var(--gray-4)] text-[var(--gray-12)]" : "text-[var(--gray-8)] hover:text-[var(--gray-12)]")}
                title="卡片视图"
              >
                <LayoutList className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={cn("rounded-r-md px-2 py-1.5 text-xs transition-colors", viewMode === "table" ? "bg-[var(--gray-4)] text-[var(--gray-12)]" : "text-[var(--gray-8)] hover:text-[var(--gray-12)]")}
                title="表格视图"
              >
                <Filter className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {filtered.length === 0 && catSearch ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[var(--gray-5)] py-12 text-center">
          <Search className="mb-2 h-6 w-6 text-[var(--gray-7)]" />
          <p className="text-sm text-[var(--gray-9)]">没有匹配「{catSearch}」的品类</p>
          <p className="mt-1 text-xs text-[var(--gray-7)]">试试其他中文或英文关键词</p>
        </div>
      ) : viewMode === "table" ? (
        /* Twenty CRM style table view */
        <div className="overflow-hidden rounded-lg border border-[var(--gray-5)]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--gray-5)] bg-[var(--gray-3)] text-[11px] uppercase tracking-wider text-[var(--gray-8)]">
                  <th className="px-3 py-2.5 font-medium">品类名称</th>
                  <th className="px-3 py-2.5 font-medium text-right">商品数</th>
                  <th className="px-3 py-2.5 font-medium text-right">均价</th>
                  <th className="px-3 py-2.5 font-medium text-right">均评分</th>
                  <th className="px-3 py-2.5 font-medium">均价趋势</th>
                  <th className="px-3 py-2.5 font-medium">评分趋势</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((card) => (
                  <tr
                    key={card.catId || card.name}
                    className="border-b border-[var(--gray-4)] last:border-0 cursor-pointer transition-colors hover:bg-[var(--gray-3)]/50"
                    onClick={() => onSelectCat(card.catId)}
                  >
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-[var(--gray-12)]">{zhCat(card.name)}</div>
                      <div className="text-[10px] text-[var(--gray-7)]">{card.name}</div>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--gray-11)]">{card.latestCount}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--gray-11)]">${card.latestAvgPrice}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--gray-11)]">{card.latestAvgRating}</td>
                    <td className="px-3 py-2.5"><CatSparkline values={card.priceHistory} /></td>
                    <td className="px-3 py-2.5"><CatSparkline values={card.ratingHistory} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Card grid view */
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((card) => (
            <button
              key={card.catId || card.name}
              type="button"
              onClick={() => onSelectCat(card.catId)}
              className="rounded-lg border border-[var(--gray-5)] bg-[var(--gray-1)] overflow-hidden text-left transition-all hover:-translate-y-0.5 hover:border-[var(--gray-6)] hover:shadow-md"
            >
              <div className="border-b border-[var(--gray-4)] px-4 py-3">
                <div className="flex items-center justify-between">
                  <h3 className="truncate text-[13px] font-semibold text-[var(--gray-12)]">{zhCat(card.name)}</h3>
                  <span className="flex-shrink-0 rounded-[4px] bg-[var(--gray-4)] px-1.5 py-0.5 text-[10px] text-[var(--gray-9)]">{card.latestCount} 商品</span>
                </div>
                <div className="mt-0.5 text-[10px] text-[var(--gray-7)]">{card.name}</div>
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
                  {card.trendsHistory.length >= 2 && (
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="h-3 w-3 text-blue-500" />
                      <CatSparkline values={card.trendsHistory} />
                    </div>
                  )}
                  <PriceDistBar products={card.allProducts} />
                </div>
              </div>
              {card.top5.length > 0 && (
                <div className="px-4 py-2">
                  <div className="mb-1.5 text-[10px] font-medium text-[var(--gray-7)]">TOP 5 热销</div>
                  <div className="space-y-1.5">
                    {card.top5.map((p, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded text-[10px] font-bold text-[var(--gray-9)]">{i + 1}</span>
                        {p.image ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={p.image} alt="" className="h-7 w-7 flex-shrink-0 rounded object-cover" />
                        ) : (
                          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded bg-[var(--gray-4)]">
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
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

/** 品类总览表：聚合所有品类的关键指标 */
function CategoryOverviewTable({ cats, onSelectCat }: { cats: DataSnapshot[]; onSelectCat: (id: string) => void }) {
  if (cats.length === 0) return null;
  const rows = cats.map((c) => {
    const stats = _extractStats(c);
    const prods: ShopProduct[] = c.payload?.products ?? [];
    const prices = prods.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
    return {
      id: c.payload?.category_id as string,
      name: (c.payload?.category_name ?? c.payload?.category_name_en ?? "—") as string,
      parentCat: (c.payload?.parent_category ?? null) as string | null,
      count: stats?.count ?? prods.length,
      priceMin: prices.length ? Math.min(...prices) : null,
      priceMax: prices.length ? Math.max(...prices) : null,
      avgPrice: stats?.avgPrice ?? null,
      avgRating: stats?.avgRating ?? null,
      topProduct: prods[0] ?? null,
    };
  });
  return (
    <div className="mb-5 overflow-hidden rounded-xl border border-[var(--gray-5)]">
      <div className="bg-[var(--gray-3)] px-4 py-2.5 text-xs font-semibold text-[var(--gray-8)]">品类总览（{rows.length} 个品类）</div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-[var(--gray-5)] bg-[var(--gray-3)]/50 text-[11px] text-[var(--gray-9)]">
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
                className="border-b border-[var(--gray-5)] last:border-0 hover:bg-[var(--gray-3)]/30 cursor-pointer transition-colors"
                onClick={() => onSelectCat(r.id)}
              >
                <td className="px-3 py-2 font-medium text-[var(--gray-12)]">
                  <div>{zhCat(r.name)}</div>
                  {r.parentCat && <div className="text-[10px] text-[var(--gray-7)]">{zhCat(r.parentCat)}</div>}
                </td>
                <td className="px-3 py-2 text-right text-[var(--gray-9)]">{r.count}</td>
                <td className="px-3 py-2 text-right text-[var(--gray-9)]">
                  {r.priceMin !== null ? `$${r.priceMin}–$${r.priceMax}` : "—"}
                </td>
                <td className="px-3 py-2 text-right text-[var(--gray-9)]">{r.avgPrice !== null ? `$${r.avgPrice}` : "—"}</td>
                <td className="px-3 py-2 text-right text-[var(--gray-9)]">{r.avgRating ?? "—"}</td>
                <td className="px-3 py-2 max-w-[180px] truncate text-[var(--gray-9)]">{r.topProduct?.title ?? "—"}</td>
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

type Tab = "category" | "hot" | "hashtag" | "trends";

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
  if (i === 1) return "bg-[var(--gray-8)] text-white";
  if (i === 2) return "bg-amber-700 text-white";
  return "bg-[var(--gray-1)]/90 text-[var(--gray-12)]";
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
      className="group flex flex-col overflow-hidden rounded-2xl border border-[var(--gray-5)] bg-[var(--gray-1)] text-left transition-all hover:-translate-y-0.5 hover:border-[var(--gray-6)] hover:shadow-md"
    >
      <div className="relative aspect-square w-full overflow-hidden bg-[var(--gray-4)]">
        {p.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={p.image} alt="" loading="lazy"
               className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[var(--gray-7)]">
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
          <span className="mb-1.5 inline-flex w-fit items-center gap-0.5 rounded bg-[var(--gray-4)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--gray-12)]">
            <Package className="h-2.5 w-2.5" />{catTag}
          </span>
        )}
        <div className="line-clamp-2 min-h-[32px] text-[12px] font-medium leading-tight text-[var(--gray-12)]">{p.title}</div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-sm font-semibold text-[var(--gray-12)]">{sym}{p.price}</span>
          {p.original_price ? (
            <span className="text-[11px] text-[var(--gray-7)] line-through">{sym}{p.original_price}</span>
          ) : null}
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-[var(--gray-9)]">
          <span className="inline-flex items-center gap-0.5">
            <ShoppingCart className="h-3 w-3" /> 已售 {fmtInt(p.sold_count)}
          </span>
          {p.rating ? (
            <span className="inline-flex items-center gap-0.5">
              <Star className="h-3 w-3 fill-current text-amber-500" />{p.rating}
              {p.review_count ? <span className="text-[var(--gray-7)]">({fmtInt(p.review_count)})</span> : null}
            </span>
          ) : null}
        </div>
        <div className="mt-2 flex items-center gap-1 border-t border-[var(--gray-5)] pt-2 text-[11px] text-[var(--gray-8)]">
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

/** Google Trends 搜索热度展示组件 */
function GoogleTrendsSection({ items }: { items: { keyword: string; direction: string; value: number; ts: string }[] }) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<TrendingUp className="h-6 w-6" />}
        title="暂无 Google Trends 数据"
        hint="等待每日自动刷新收集搜索热度数据，或在工作台页面点击「回填趋势」。"
      />
    );
  }

  // Group by keyword and compute time series
  const byKw = new Map<string, { ts: string; val: number }[]>();
  for (const it of items) {
    if (!byKw.has(it.keyword)) byKw.set(it.keyword, []);
    byKw.get(it.keyword)!.push({ ts: it.ts, val: it.value });
  }
  // Sort each keyword's points by time
  for (const pts of byKw.values()) {
    pts.sort((a, b) => a.ts.localeCompare(b.ts));
  }
  // Compute latest value and trend direction for each keyword
  const kwStats = [...byKw.entries()].map(([kw, pts]) => {
    const latest = pts[pts.length - 1]?.val ?? 0;
    const first = pts[0]?.val ?? 0;
    const direction = latest > first ? "上升" : latest < first ? "下降" : "平稳";
    const pctChange = first > 0 ? ((latest - first) / first) * 100 : 0;
    return { keyword: kw, pts, latest, direction, pctChange };
  }).sort((a, b) => b.latest - a.latest);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-[var(--gray-9)]">
        <TrendingUp className="h-3.5 w-3.5 text-[var(--gray-12)]" />
        <span className="font-medium text-[var(--gray-12)]">Google 搜索热度</span>
        <span>· {kwStats.length} 个关键词</span>
      </div>

      {/* Keyword cards with sparkline */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {kwStats.map(({ keyword, pts, latest, direction, pctChange }) => {
          const values = pts.map((p) => p.val);
          const max = Math.max(...values);
          const min = Math.min(...values);
          const range = max - min || 1;
          const W = 160, H = 40;
          const svgPts = values.length >= 2
            ? values.map((v, i) => {
                const x = (i / (values.length - 1)) * W;
                const y = H - ((v - min) / range) * (H - 4) - 2;
                return `${x.toFixed(1)},${y.toFixed(1)}`;
              })
            : null;
          const rising = direction === "上升";
          const color = rising ? "#10b981" : direction === "下降" ? "#f43f5e" : "#6366f1";

          return (
            <div key={keyword} className="rounded-lg border border-[var(--gray-5)] bg-[var(--gray-1)] p-3">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-xs font-medium text-[var(--gray-12)] truncate">{keyword}</span>
                <span className={cn(
                  "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-semibold",
                  rising ? "bg-emerald-50 text-emerald-600" : direction === "下降" ? "bg-rose-50 text-rose-600" : "bg-[var(--gray-4)] text-[var(--gray-9)]",
                )}>
                  {rising ? <TrendingUp className="h-2.5 w-2.5" /> : direction === "下降" ? <TrendingUp className="h-2.5 w-2.5 rotate-180" /> : null}
                  {direction}
                  {Math.abs(pctChange) > 1 && ` ${pctChange > 0 ? "+" : ""}${pctChange.toFixed(0)}%`}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <div className="text-lg font-bold text-[var(--gray-12)] tabular-nums">{latest.toFixed(0)}</div>
                {svgPts ? (
                  <svg viewBox={`0 0 ${W} ${H}`} className="h-8 w-[120px] flex-shrink-0" preserveAspectRatio="none">
                    <polyline points={svgPts.join(" ")} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <div className="flex items-center h-8 w-[120px]">
                    <svg viewBox={`0 0 ${W} ${H}`} className="h-8 w-full" preserveAspectRatio="none">
                      <line x1="0" y1={H / 2} x2={W} y2={H / 2} stroke="#a1a1aa" strokeWidth="1" strokeDasharray="3,3" />
                      <circle cx={W / 2} cy={H / 2} r="4" fill={color} />
                    </svg>
                  </div>
                )}
              </div>
              {pts.length > 1 && (
                <div className="mt-1.5 text-[10px] text-[var(--gray-7)]">
                  {pts.length} 个数据点 · {pts[0].ts.slice(0, 10)} ~ {pts[pts.length - 1].ts.slice(0, 10)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
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
  const [selectedCatDetail, setSelectedCatDetail] = React.useState<DataSnapshot | null>(null);
  const [catHistory, setCatHistory] = React.useState<DataSnapshot[]>([]);
  const [sparkData, setSparkData] = React.useState<CategorySparkData[]>([]);
  const [googleTrendsSnaps, setGoogleTrendsSnaps] = React.useState<DataSnapshot[]>([]);

  const q = query.trim().toLowerCase();

  const openProduct = (p: ShopProduct, opts?: { category?: string; source?: string }) => {
    setSelectedProduct({ ...p, _category: opts?.category, _source: opts?.source });
  };

  const reload = React.useCallback(async () => {
    setReloading(true);
    try {
      const [st, catSnaps, hotSnaps, htSnaps, sparks, gtSnaps] = await Promise.all([
        fetchDailyRefreshStatus(),
        fetchDataSnapshots({ source: "category_rank", limit: 500 }),
        fetchDataSnapshots({ term: HOT_SELLING_TERM, limit: 1 }),
        fetchDataSnapshots({ term: HASHTAG_TREND_TERM, limit: 1 }),
        fetchCategorySparklines(),
        fetchAllSnapshots({ source: "google_trends", limit: 1000 }),
      ]);
      setStatus(st);
      const okCats = catSnaps.filter((s) => s.realData && ((s.payload?.products?.length ?? 0) > 0 || typeof s.payload?.product_count === "number"));
      setCats(okCats);
      setHot(hotSnaps[0] ?? null);
      setHashtagSnap(htSnaps[0] ?? null);
      setSparkData(sparks);
      setGoogleTrendsSnaps(gtSnaps);
      setCatHistory([]);  // no longer needed for sparklines
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



  // Google Trends parsed data
  const googleTrendsItems = React.useMemo(() => {
    const items: { keyword: string; direction: string; value: number; ts: string }[] = [];
    for (const s of googleTrendsSnaps) {
      // Individual point snapshot (from backfill)
      if (s.payload?.keyword) {
        items.push({
          keyword: s.payload.keyword as string,
          direction: (s.payload.direction as string) || "",
          value: (s.payload.late_avg as number) || 0,
          ts: (s.payload.backfill_ts as string) || s.capturedAt || "",
        });
        continue;
      }
      // Batch snapshot with keywords array
      const kws = (s.payload?.keywords || []) as Array<{ keyword?: string; direction?: string; recent_3m_avg?: number }>;
      for (const k of kws) {
        if (k.keyword) items.push({ keyword: k.keyword, direction: k.direction || "", value: k.recent_3m_avg || 0, ts: s.capturedAt || "" });
      }
    }
    return items;
  }, [googleTrendsSnaps]);

  const channelOk = status?.tier2ChannelOk ?? false;
  const hasAny = cats.length > 0 || hotProducts.length > 0 || hashtags.length > 0 || googleTrendsItems.length > 0;

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "category", label: "品类 Top", count: searching ? crossCatHits.length : cats.length },
    { key: "hot", label: "实时热销榜", count: hotFiltered.length },
    { key: "hashtag", label: "热门话题", count: hashtagsFiltered.length },
    { key: "trends", label: "Google Trends", count: googleTrendsItems.length > 0 ? new Set(googleTrendsItems.map((i) => i.keyword)).size : 0 },
  ];

  return (
    <PageContainer>
      <PageHeader
        icon={<LayoutList className="h-5 w-5" />}
        title="品类榜单"
        subtitle="TikTok Shop 按品类实时 Top 商品 + 全站热销榜 + 热门话题声量曲线，作为选品与机会挖掘的实时榜单底盘。"
        actions={
          <span className="flex items-center gap-1.5 rounded-md bg-[var(--gray-3)] px-2.5 py-1 text-xs text-[var(--gray-9)]">
            <Clock className="h-3.5 w-3.5" />每日自动刷新
          </span>
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
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatTile label="最近更新" value={fmtTime(status?.finishedAt)} icon={<Clock className="h-4 w-4" />} />
            <StatTile label="覆盖品类" value={String(cats.length)} icon={<Package className="h-4 w-4" />} />
            <StatTile label="热销商品" value={String(hotProducts.length)} icon={<Flame className="h-4 w-4" />} />
            <StatTile label="热门话题" value={String(hashtags.length)} icon={<Hash className="h-4 w-4" />} />
            <StatTile label="搜索趋势" value={String(new Set(googleTrendsItems.map((i) => i.keyword)).size)} icon={<TrendingUp className="h-4 w-4" />} />
          </div>

          {!channelOk && (
            <div className="mb-5 rounded-lg border border-[var(--gray-5)] bg-[var(--gray-3)] px-3 py-2 text-xs text-[var(--gray-9)]">
              榜单通道（TikHub）需配置 <span className="font-medium text-[var(--gray-8)]">TIKHUB_API_KEY</span>；通道未就绪时如实标注，<span className="font-medium text-[var(--gray-8)]">不编造数据</span>，接入后自动补齐。
            </div>
          )}

          {/* ═══ Per-Category Trend Cards (hero section) ═══ */}
          <PerCategoryCards
            latestSnaps={cats}
            sparkData={sparkData}
            googleTrendsSnaps={googleTrendsSnaps}
            onSelectCat={(id) => {
              const snap = cats.find((c) => c.payload?.category_id === id);
              if (snap) setSelectedCatDetail(snap);
              setActiveCat(id); setTab("category");
            }}
          />

          {!hasAny ? (
            <EmptyState
              icon={<LayoutList className="h-6 w-6" />}
              title="还没有榜单数据"
              hint="品类数据每天 EST 0:00 自动全量刷新，请耐心等待。"
            />
          ) : (
            <>
              {/* 品类总览表 */}
              {tab === "category" && !searching && (
                <CategoryOverviewTable cats={cats} onSelectCat={(id) => {
                  const snap = cats.find((c) => c.payload?.category_id === id);
                  if (snap) setSelectedCatDetail(snap);
                  setActiveCat(id); setTab("category");
                }} />
              )}

              {/* 品类趋势分析表格（跨日期对比） */}
              <div className="mb-5">
                <CategoryTrendTable />
              </div>

              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <FilterTabs tabs={tabs} value={tab} onChange={setTab} />
                <div className="relative w-full sm:w-64">
                  <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--gray-7)]" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="搜品类 / 商品 / 店铺 / 话题…"
                    className="w-full rounded-lg border border-[var(--gray-5)] bg-[var(--gray-3)] py-1.5 pl-8 pr-8 text-sm text-[var(--gray-12)] outline-none focus:border-[var(--gray-8)]/40 focus:ring-2 focus:ring-brand/15"
                  />
                  {query && (
                    <button
                      onClick={() => setQuery("")}
                      className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-[var(--gray-7)] hover:bg-[var(--gray-4)] hover:text-[var(--gray-12)]"
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
                      <div className="mb-3 flex items-center gap-2 text-xs text-[var(--gray-9)]">
                        <Search className="h-3.5 w-3.5 text-[var(--gray-12)]" />
                        在全部 {cats.length} 个品类中搜「<span className="font-medium text-[var(--gray-8)]">{query.trim()}</span>」· 命中 {crossCatHits.length} 个商品
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
                                ? "border-[var(--gray-12)]/30 bg-[var(--gray-4)] font-medium text-[var(--gray-12)]"
                                : "border-[var(--gray-5)] bg-[var(--gray-1)] text-[var(--gray-8)] hover:bg-[var(--gray-3)] hover:text-[var(--gray-12)]",
                            )}
                          >
                            {zhCat((c.payload?.category_name ?? "") as string)}
                            <span className={cn("ml-1.5 text-[10px]", active ? "text-[var(--gray-12)]/70" : "text-[var(--gray-7)]")}>
                              {c.payload?.products?.length ?? 0}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                    {activeCatSnap && (
                      <div className="mb-3 flex items-center gap-2 text-xs text-[var(--gray-9)]">
                        <TrendingUp className="h-3.5 w-3.5 text-[var(--gray-12)]" />
                        <span className="font-medium text-[var(--gray-8)]">{zhCat((activeCatSnap.payload?.category_name ?? "") as string)}</span>
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
                      <div className="mb-3 flex items-center gap-2 text-xs text-[var(--gray-9)]">
                        <Search className="h-3.5 w-3.5 text-[var(--gray-12)]" />
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
                      <div key={h.hashtag ?? i} className="rounded-2xl border border-[var(--gray-5)] bg-[var(--gray-1)] p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5 text-sm font-semibold text-[var(--gray-12)]">
                              <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-[11px] font-bold text-[var(--gray-12)]">
                                {i + 1}
                              </span>
                              <Hash className="h-3.5 w-3.5 flex-shrink-0 text-[var(--gray-12)]" />
                              <span className="truncate">{h.hashtag}</span>
                            </div>
                            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[var(--gray-9)]">
                              <span className="inline-flex items-center gap-0.5">
                                <TrendingUp className="h-3 w-3" /> 浏览 {fmtInt(h.views)}
                              </span>
                              <span>发布 {fmtInt(h.publish_count)}</span>
                            </div>
                          </div>
                          <Sparkline curve={h.popularity_curve ?? []} />
                        </div>
                        {Array.isArray(h.top_creators) && h.top_creators.length > 0 && (
                          <div className="mt-3 flex items-center gap-2 border-t border-[var(--gray-5)] pt-2.5">
                            <Users className="h-3.5 w-3.5 flex-shrink-0 text-[var(--gray-7)]" />
                            <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                              {h.top_creators.slice(0, 4).map((c, ci) => (
                                <span key={ci} className="inline-flex items-center gap-1 rounded-full bg-[var(--gray-3)] py-0.5 pl-0.5 pr-2 text-[11px] text-[var(--gray-8)]">
                                  {c.avatar ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={c.avatar} alt="" className="h-4 w-4 rounded-full object-cover" />
                                  ) : (
                                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[var(--gray-4)]"><Users className="h-2.5 w-2.5" /></span>
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

              {/* Google Trends 搜索热度 */}
              {tab === "trends" && (
                <GoogleTrendsSection items={googleTrendsItems} />
              )}
            </>
          )}
        </>
      )}
      <ProductDetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      <CategoryDetailModal snapshot={selectedCatDetail} onClose={() => setSelectedCatDetail(null)} />
    </PageContainer>
  );
}
