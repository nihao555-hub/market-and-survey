"use client";
import React from "react";
import {
  TrendingUp, TrendingDown, Minus, Calendar, DollarSign,
  Star, ShoppingCart, Package, BarChart3,
} from "lucide-react";
import { fetchAllSnapshots, type DataSnapshot } from "@/lib/api";
import { Panel, Skeleton, EmptyState, FilterTabs } from "./primitives";
import { cn } from "@/lib/utils";

interface CategoryDayStats {
  date: string;
  productCount: number;
  avgPrice: number | null;
  minPrice: number | null;
  maxPrice: number | null;
  avgRating: number | null;
  totalSold: number;
  topProduct: string | null;
}

interface CategoryTrend {
  categoryId: string;
  categoryName: string;
  days: CategoryDayStats[];
}

function fmtDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch { return iso; }
}

function fmtFullDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("zh-CN", { month: "short", day: "numeric", weekday: "short" });
  } catch { return iso; }
}

function fmtNum(n: number | null): string {
  if (n === null || !isFinite(n)) return "\u2014";
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}\u4e07`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return n.toLocaleString("en-US");
}

function fmtPrice(n: number | null, sym = "$"): string {
  if (n === null || !isFinite(n)) return "\u2014";
  return `${sym}${n.toFixed(2)}`;
}

function TrendArrow({ current, previous }: { current: number | null; previous: number | null }) {
  if (current === null || previous === null || !isFinite(current) || !isFinite(previous)) {
    return <Minus className="h-3 w-3 text-ink-tertiary" />;
  }
  const diff = current - previous;
  if (Math.abs(diff) < 0.01) return <Minus className="h-3 w-3 text-ink-tertiary" />;
  if (diff > 0) return <TrendingUp className="h-3 w-3 text-emerald-500" />;
  return <TrendingDown className="h-3 w-3 text-rose-500" />;
}

function DeltaBadge({ current, previous, suffix = "" }: { current: number | null; previous: number | null; suffix?: string }) {
  if (current === null || previous === null || !isFinite(current) || !isFinite(previous) || previous === 0) {
    return null;
  }
  const pct = ((current - previous) / Math.abs(previous)) * 100;
  if (Math.abs(pct) < 0.5) return null;
  const positive = pct > 0;
  return (
    <span className={cn(
      "ml-1 inline-flex items-center rounded px-1 py-0.5 text-[9px] font-semibold",
      positive ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600",
    )}>
      {positive ? "+" : ""}{pct.toFixed(1)}%{suffix}
    </span>
  );
}

function extractDayStats(snaps: DataSnapshot[]): CategoryDayStats[] {
  const byDate = new Map<string, DataSnapshot[]>();
  for (const s of snaps) {
    const dateKey = s.capturedAt ? s.capturedAt.split("T")[0] : "unknown";
    if (!byDate.has(dateKey)) byDate.set(dateKey, []);
    byDate.get(dateKey)!.push(s);
  }

  const days: CategoryDayStats[] = [];
  for (const [date, daySnaps] of byDate) {
    const allProducts: { price?: number | null; rating?: number | null; sold_count?: number | null; title?: string }[] = [];
    for (const s of daySnaps) {
      if (Array.isArray(s.payload?.products)) {
        allProducts.push(...s.payload.products);
      }
    }
    const prices = allProducts.map((p) => p.price).filter((p): p is number => typeof p === "number" && isFinite(p) && p > 0);
    const ratings = allProducts.map((p) => p.rating).filter((r): r is number => typeof r === "number" && isFinite(r) && r > 0);
    const soldCounts = allProducts.map((p) => p.sold_count).filter((s): s is number => typeof s === "number" && isFinite(s));

    days.push({
      date,
      productCount: allProducts.length,
      avgPrice: prices.length > 0 ? prices.reduce((a, b) => a + b, 0) / prices.length : null,
      minPrice: prices.length > 0 ? Math.min(...prices) : null,
      maxPrice: prices.length > 0 ? Math.max(...prices) : null,
      avgRating: ratings.length > 0 ? Math.round((ratings.reduce((a, b) => a + b, 0) / ratings.length) * 100) / 100 : null,
      totalSold: soldCounts.reduce((a, b) => a + b, 0),
      topProduct: allProducts.length > 0 ? (allProducts[0].title ?? null) : null,
    });
  }

  return days.sort((a, b) => b.date.localeCompare(a.date));
}

export function CategoryTrendTable() {
  const [allSnaps, setAllSnaps] = React.useState<DataSnapshot[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [activeCat, setActiveCat] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const snaps = await fetchAllSnapshots({ source: "category_rank", limit: 500 });
        if (!cancelled) {
          setAllSnaps(snaps);
        }
      } catch { /* silent */ }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  const trends: CategoryTrend[] = React.useMemo(() => {
    const byCat = new Map<string, DataSnapshot[]>();
    for (const s of allSnaps) {
      const catId = s.payload?.category_id || s.payload?.category_name || s.term;
      if (!byCat.has(catId)) byCat.set(catId, []);
      byCat.get(catId)!.push(s);
    }

    const result: CategoryTrend[] = [];
    for (const [catId, snaps] of byCat) {
      const catName = snaps[0]?.payload?.category_name || catId;
      const days = extractDayStats(snaps);
      if (days.length > 0) {
        result.push({ categoryId: catId, categoryName: catName, days });
      }
    }
    return result.sort((a, b) => {
      const aTotal = a.days.reduce((acc, d) => acc + d.totalSold, 0);
      const bTotal = b.days.reduce((acc, d) => acc + d.totalSold, 0);
      return bTotal - aTotal;
    });
  }, [allSnaps]);

  const selectedTrend = trends.find((t) => t.categoryId === activeCat) ?? trends[0];

  React.useEffect(() => {
    if (!activeCat && trends.length > 0) {
      setActiveCat(trends[0].categoryId);
    }
  }, [activeCat, trends]);

  if (loading) {
    return (
      <Panel title={"\u54c1\u7c7b\u8d8b\u52bf\u5206\u6790"} bodyClassName="p-4">
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
        </div>
      </Panel>
    );
  }

  if (trends.length === 0) {
    return (
      <Panel title={"\u54c1\u7c7b\u8d8b\u52bf\u5206\u6790"} bodyClassName="p-0">
        <EmptyState
          icon={<BarChart3 className="h-6 w-6" />}
          title={"\u6682\u65e0\u5386\u53f2\u8d8b\u52bf\u6570\u636e"}
          hint={"\u9700\u8981\u591a\u6b21\u6570\u636e\u5237\u65b0\u540e\u624d\u80fd\u5c55\u793a\u8d8b\u52bf\u53d8\u5316\u3002\u8bf7\u5728\u300c\u76d1\u63a7\u4e0e\u8ba2\u9605\u300d\u9875\u70b9\u51fb\u300c\u7acb\u5373\u5237\u65b0\u300d\u6216\u7b49\u5f85\u81ea\u52a8\u5237\u65b0\u3002"}
        />
      </Panel>
    );
  }

  return (
    <Panel title={"\u54c1\u7c7b\u8d8b\u52bf\u5206\u6790"} bodyClassName="p-0">
      {/* Category selector */}
      <div className="border-b border-hairline px-4 py-3">
        <div className="flex flex-wrap gap-1.5">
          {trends.map((t) => {
            const active = t.categoryId === selectedTrend?.categoryId;
            return (
              <button
                key={t.categoryId}
                onClick={() => setActiveCat(t.categoryId)}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                  active
                    ? "border-brand/30 bg-brand/10 font-medium text-brand"
                    : "border-hairline bg-white text-ink-muted hover:bg-surface-1 hover:text-ink",
                )}
              >
                {t.categoryName}
                <span className={cn("ml-1 text-[10px]", active ? "text-brand/70" : "text-ink-tertiary")}>
                  {t.days.length}d
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Trend table */}
      {selectedTrend && (
        <div className="p-4">
          <div className="mb-3 flex items-center gap-2 text-xs text-ink-subtle">
            <BarChart3 className="h-3.5 w-3.5 text-brand" />
            <span className="font-medium text-ink">{selectedTrend.categoryName}</span>
            <span>{"\u00b7"} {"\u8fd1"} {selectedTrend.days.length} {"\u6b21\u6570\u636e\u5feb\u7167"}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-1 text-[11px] uppercase tracking-wide text-ink-subtle">
                  <th className="px-3 py-2.5 pl-4 text-left font-medium">
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="h-3 w-3" />{"\u65e5\u671f"}
                    </span>
                  </th>
                  <th className="px-3 py-2.5 text-right font-medium">
                    <span className="inline-flex items-center gap-1">
                      <Package className="h-3 w-3" />{"\u5546\u54c1\u6570"}
                    </span>
                  </th>
                  <th className="px-3 py-2.5 text-right font-medium">
                    <span className="inline-flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />{"\u5747\u4ef7"}
                    </span>
                  </th>
                  <th className="px-3 py-2.5 text-right font-medium">{"\u4ef7\u683c\u533a\u95f4"}</th>
                  <th className="px-3 py-2.5 text-right font-medium">
                    <span className="inline-flex items-center gap-1">
                      <Star className="h-3 w-3" />{"\u5747\u5206"}
                    </span>
                  </th>
                  <th className="px-3 py-2.5 text-right font-medium">
                    <span className="inline-flex items-center gap-1">
                      <ShoppingCart className="h-3 w-3" />{"\u603b\u9500\u91cf"}
                    </span>
                  </th>
                  <th className="px-3 py-2.5 text-center font-medium">{"\u8d8b\u52bf"}</th>
                </tr>
              </thead>
              <tbody>
                {selectedTrend.days.map((day, idx) => {
                  const prev = idx < selectedTrend.days.length - 1 ? selectedTrend.days[idx + 1] : null;
                  return (
                    <tr key={day.date} className={cn(
                      "border-t border-hairline transition-colors hover:bg-surface-1",
                      idx === 0 && "bg-brand/[0.03]",
                    )}>
                      <td className="px-3 py-2.5 pl-4">
                        <div className="text-xs font-medium text-ink">
                          {fmtFullDate(day.date)}
                          {idx === 0 && (
                            <span className="ml-1.5 rounded bg-brand/10 px-1 py-0.5 text-[9px] font-semibold text-brand">
                              {"\u6700\u65b0"}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <span className="text-xs font-medium text-ink">{day.productCount}</span>
                        <DeltaBadge current={day.productCount} previous={prev?.productCount ?? null} />
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <span className="text-xs font-medium text-ink">{fmtPrice(day.avgPrice)}</span>
                        <DeltaBadge current={day.avgPrice} previous={prev?.avgPrice ?? null} />
                      </td>
                      <td className="px-3 py-2.5 text-right text-[11px] text-ink-subtle">
                        {day.minPrice !== null && day.maxPrice !== null
                          ? `${fmtPrice(day.minPrice)} - ${fmtPrice(day.maxPrice)}`
                          : "\u2014"}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {day.avgRating !== null ? (
                          <span className="inline-flex items-center gap-0.5 text-xs text-ink">
                            <Star className="h-3 w-3 fill-current text-amber-500" />
                            {day.avgRating}
                            <DeltaBadge current={day.avgRating} previous={prev?.avgRating ?? null} />
                          </span>
                        ) : (
                          <span className="text-xs text-ink-subtle">{"\u2014"}</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <span className="text-xs font-medium text-ink">{fmtNum(day.totalSold)}</span>
                        <DeltaBadge current={day.totalSold} previous={prev?.totalSold ?? null} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <TrendArrow current={day.totalSold} previous={prev?.totalSold ?? null} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Summary row */}
          {selectedTrend.days.length >= 2 && (() => {
            const latest = selectedTrend.days[0];
            const oldest = selectedTrend.days[selectedTrend.days.length - 1];
            return (
              <div className="mt-3 flex flex-wrap gap-3 rounded-lg bg-surface-1 px-3 py-2 text-[11px] text-ink-subtle">
                <span>{"\u5468\u671f"}: {selectedTrend.days.length} {"\u6b21\u5feb\u7167"}</span>
                {latest.avgPrice !== null && oldest.avgPrice !== null && (
                  <span className="inline-flex items-center gap-1">
                    {"\u5747\u4ef7\u53d8\u5316"}:
                    <TrendArrow current={latest.avgPrice} previous={oldest.avgPrice} />
                    {fmtPrice(oldest.avgPrice)} {"\u2192"} {fmtPrice(latest.avgPrice)}
                  </span>
                )}
                {latest.totalSold > 0 && oldest.totalSold > 0 && (
                  <span className="inline-flex items-center gap-1">
                    {"\u9500\u91cf\u53d8\u5316"}:
                    <TrendArrow current={latest.totalSold} previous={oldest.totalSold} />
                    {fmtNum(oldest.totalSold)} {"\u2192"} {fmtNum(latest.totalSold)}
                  </span>
                )}
              </div>
            );
          })()}
        </div>
      )}
    </Panel>
  );
}
