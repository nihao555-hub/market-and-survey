"use client";
import React, { useRef, useEffect } from "react";
import { RefreshCw, Database, Clock, ListChecks, Search, TrendingUp, CalendarDays, ShoppingCart, Flame, Star, BarChart3 } from "lucide-react";
import type { EChartsOption } from "echarts";
import {
  fetchDailyRefreshStatus, fetchDataSnapshots, triggerDailyRefresh, fetchAllSnapshots,
  type DataSnapshot, type RefreshStatus,
} from "@/lib/api";
import { Button, StatusBadge, StatTile, Skeleton, EmptyState, type StatusKind } from "./primitives";
import { ProductDetailModal, type ProductForModal } from "./ProductDetailModal";

function DataChart({ option, height = 280 }: { option: EChartsOption; height?: number }) {
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
        grid: { left: 50, right: 20, top: 35, bottom: 35, containLabel: true },
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

interface GTrendItem { keyword: string; direction: string; latest: number; ts: string; }
function buildGoogleTrendChart(snaps: DataSnapshot[]): { option: EChartsOption; items: GTrendItem[] } {
  const items: GTrendItem[] = [];
  for (const s of snaps) {
    const kws = (s.payload?.keywords || []) as Array<{ keyword?: string; direction?: string; recent_3m_avg?: number }>;
    for (const k of kws) {
      if (k.keyword) items.push({ keyword: k.keyword, direction: k.direction || "", latest: k.recent_3m_avg || 0, ts: s.capturedAt || "" });
    }
  }
  const byKw = new Map<string, { ts: string; val: number }[]>();
  for (const it of items) {
    if (!byKw.has(it.keyword)) byKw.set(it.keyword, []);
    byKw.get(it.keyword)!.push({ ts: it.ts, val: it.latest });
  }
  const kwList = [...byKw.keys()].slice(0, 8);
  if (kwList.length === 0) return { option: {}, items };

  const allTimes = [...new Set(items.map((i) => i.ts.slice(0, 16)))].sort();
  const COLORS = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ef4444", "#06b6d4"];
  return {
    items,
    option: {
      legend: { data: kwList, bottom: 0, textStyle: { fontSize: 11, color: "#888" }, type: "scroll" },
      xAxis: { type: "category", data: allTimes.map((t) => {
        try { return new Date(t).toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); } catch { return t; }
      }), axisLabel: { fontSize: 10, color: "#999" }, axisLine: { lineStyle: { color: "#e5e5e5" } } },
      yAxis: { type: "value", name: "搜索热度", nameTextStyle: { fontSize: 11, color: "#999" }, axisLabel: { fontSize: 10, color: "#999" }, splitLine: { lineStyle: { color: "#f5f5f5" } } },
      series: kwList.map((kw, i) => {
        const pts = byKw.get(kw) || [];
        return {
          name: kw, type: "line" as const, smooth: true, symbol: "circle", symbolSize: 4,
          lineStyle: { width: 2 }, itemStyle: { color: COLORS[i % COLORS.length] },
          data: allTimes.map((t) => { const p = pts.find((x) => x.ts.slice(0, 16) === t); return p?.val ?? null; }),
        };
      }),
    },
  };
}

// 数据源中文名 + 图标
const SOURCE_META: Record<string, { label: string; icon: React.ReactNode }> = {
  amazon_keywords: { label: "买家搜索词", icon: <Search className="h-3.5 w-3.5" /> },
  google_trends: { label: "搜索趋势", icon: <TrendingUp className="h-3.5 w-3.5" /> },
  seasonality: { label: "季节性", icon: <CalendarDays className="h-3.5 w-3.5" /> },
  bestsellers: { label: "电商榜单", icon: <ShoppingCart className="h-3.5 w-3.5" /> },
  tiktok_shop: { label: "TikTok Shop 实时商品", icon: <ShoppingCart className="h-3.5 w-3.5" /> },
  trend_tiktok: { label: "TikTok 趋势词", icon: <Flame className="h-3.5 w-3.5" /> },
  trend_twitter: { label: "X/Twitter 趋势", icon: <Flame className="h-3.5 w-3.5" /> },
  trend_lemon8: { label: "Lemon8 热词", icon: <Flame className="h-3.5 w-3.5" /> },
  social_trends: { label: "社媒趋势", icon: <Flame className="h-3.5 w-3.5" /> },
};
const sourceMeta = (s: string) => SOURCE_META[s] ?? { label: s, icon: <Database className="h-3.5 w-3.5" /> };

// 快照状态 → 徽章样式
const STATUS_MAP: Record<string, { kind: StatusKind; label: string }> = {
  ok: { kind: "done", label: "已获取" },
  empty: { kind: "neutral", label: "暂无数据" },
  error: { kind: "error", label: "获取失败" },
  unavailable: { kind: "pending", label: "通道未就绪" },
};
const statusInfo = (s: string) => STATUS_MAP[s] ?? { kind: "neutral" as StatusKind, label: s };

function fmtTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("zh-CN", { hour12: false });
  } catch { return iso; }
}

export function DailyDataPanel() {
  const [status, setStatus] = React.useState<RefreshStatus | null>(null);
  const [snapshots, setSnapshots] = React.useState<DataSnapshot[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [selectedProduct, setSelectedProduct] = React.useState<ProductForModal | null>(null);
  const [googleSnaps, setGoogleSnaps] = React.useState<DataSnapshot[]>([]);

  const reload = React.useCallback(async () => {
    try {
      const [st, snaps, gSnaps] = await Promise.all([
        fetchDailyRefreshStatus(),
        fetchDataSnapshots({ limit: 200 }),
        fetchAllSnapshots({ source: "google_trends", limit: 200 }),
      ]);
      setStatus(st);
      setSnapshots(snaps);
      setGoogleSnaps(gSnaps);
    } catch { /* 静默 */ }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  // 触发刷新后轮询，直到 done/failed
  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerDailyRefresh();
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 2500));
        const st = await fetchDailyRefreshStatus();
        setStatus(st);
        if (st.status === "done" || st.status === "failed") break;
      }
      setSnapshots(await fetchDataSnapshots({ limit: 200 }));
    } catch { /* 静默 */ }
    finally { setRefreshing(false); }
  };

  const running = refreshing || status?.status === "running";
  const counts = status?.counts || {};
  const realCount = counts.real ?? 0;
  const termCount = counts.terms ?? status?.terms?.length ?? 0;

  // 按追踪词分组；社媒趋势组置顶
  const groups = React.useMemo(() => {
    const m = new Map<string, DataSnapshot[]>();
    for (const s of snapshots) {
      if (!m.has(s.term)) m.set(s.term, []);
      m.get(s.term)!.push(s);
    }
    return Array.from(m.entries()).sort((a, b) => {
      const av = a[0].includes("社媒趋势") ? 0 : 1;
      const bv = b[0].includes("社媒趋势") ? 0 : 1;
      return av - bv;
    });
  }, [snapshots]);

  return (
    <section className="mb-4 rounded-2xl border border-[var(--gray-5)] bg-[var(--gray-1)]">
      <div className="flex items-start justify-between gap-3 border-b border-[var(--gray-5)] px-5 py-3.5">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-[var(--gray-12)]">实时数据刷新 · 真实数据底子</h2>
          <p className="mt-0.5 text-xs text-[var(--gray-9)]">
            每 2 小时自动刷新一次：TikTok Shop 实时商品 + 社媒趋势（TikTok/X/Lemon8）+ Google Trends 搜索热度，落库作为选品与调研的底子。
          </p>
        </div>
        <span className="flex items-center gap-1.5 rounded-md bg-[var(--gray-3)] px-2.5 py-1 text-xs text-[var(--gray-9)]">
          <Clock className="h-3.5 w-3.5" />定时自动刷新
        </span>
      </div>
      <div className="p-5">
      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : (
        <>
          {/* 概览行 */}
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile
              label="最近刷新"
              value={status?.status === "running" ? "进行中…" : fmtTime(status?.finishedAt)}
              icon={<Clock className="h-4 w-4" />}
            />
            <StatTile label="真实数据条数" value={String(realCount)} icon={<Database className="h-4 w-4" />} />
            <StatTile label="追踪词" value={String(termCount)} icon={<ListChecks className="h-4 w-4" />} />
            <StatTile
              label="电商商品级通道"
              value={status?.tier2ChannelOk ? "已就绪" : "未就绪"}
              tone={status?.tier2ChannelOk ? "text-success" : "text-[var(--gray-9)]"}
              icon={<ShoppingCart className="h-4 w-4" />}
            />
          </div>

          {!status?.tier2ChannelOk && (
            <div className="mb-4 rounded-lg border border-[var(--gray-5)] bg-[var(--gray-3)] px-3 py-2 text-xs text-[var(--gray-9)]">
              实时电商通道（TikTok Shop）需配置 <span className="font-medium text-[var(--gray-8)]">TIKHUB_API_KEY</span>；通道未就绪时如实标注，<span className="font-medium text-[var(--gray-8)]">不编造数据</span>，接入后自动补齐。
            </div>
          )}

          {/* ═══ Google Trends 走势图═══ */}
          {googleSnaps.length > 0 && (() => {
            const { option: gtOpt, items: gtItems } = buildGoogleTrendChart(googleSnaps);
            if (gtItems.length === 0) return null;
            return (
              <section className="mb-4 rounded-[8px] border border-[var(--gray-5)] bg-[var(--gray-1)] overflow-hidden">
                <div className="flex items-center justify-between border-b border-surface-3 px-5 py-3">
                  <h2 className="flex items-center gap-2 text-sm font-semibold text-[var(--gray-12)]">
                    <BarChart3 className="h-4 w-4 text-[var(--gray-9)]" />
                    品类搜索热度走势
                  </h2>
                </div>
                <div className="px-2 pt-2 pb-1">
                  <DataChart option={gtOpt} height={280} />
                </div>
                <div className="border-t border-surface-3 px-5 py-3">
                  <div className="flex flex-wrap gap-2">
                    {[...new Map(gtItems.map((it) => [it.keyword, it])).values()].slice(0, 10).map((it) => (
                      <span key={it.keyword} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        it.direction === "上升" ? "bg-green-50 text-green-600" : it.direction === "下降" ? "bg-red-50 text-red-600" : "bg-[var(--gray-4)] text-[var(--gray-9)]"
                      }`}>
                        {it.direction === "上升" ? "↑" : it.direction === "下降" ? "↓" : "→"} {it.keyword}
                      </span>
                    ))}
                  </div>
                </div>
              </section>
            );
          })()}

          {/* 快照分组 */}
          {groups.length === 0 ? (
            <EmptyState
              icon={<Database className="h-6 w-6" />}
              title="还没有数据快照"
              hint="数据每 2 小时自动刷新一次，请耐心等待下一次定时刷新。"
            />
          ) : (
            <div className="space-y-3">
              {groups.map(([term, items]) => (
                <div key={term} className="rounded-xl border border-[var(--gray-5)] bg-[var(--gray-1)] p-4">
                  <div className="mb-3 text-sm font-semibold text-[var(--gray-12)]">{term}</div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {items.map((s) => {
                      const meta = sourceMeta(s.source);
                      const info = statusInfo(s.status);
                      return (
                        <div key={s.id} className="rounded-lg border border-[var(--gray-5)] bg-[var(--gray-3)] p-3">
                          <div className="mb-1 flex items-center justify-between gap-2">
                            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--gray-8)]">
                              <span className="text-[var(--gray-12)]">{meta.icon}</span>{meta.label}
                              <span className="rounded bg-[var(--gray-4)] px-1 text-[10px] text-[var(--gray-9)]">T{s.tier}</span>
                            </span>
                            <StatusBadge status={info.kind} label={info.label} />
                          </div>
                          <div className="text-xs leading-relaxed text-[var(--gray-9)]">{s.summary || "—"}</div>
                          {s.source === "amazon_keywords" && s.realData && Array.isArray(s.payload?.suggestions) && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {s.payload.suggestions.slice(0, 8).map((k: any, i: number) => (
                                <span key={i} className="rounded-full bg-[var(--gray-4)] px-2 py-0.5 text-[11px] text-[var(--gray-12)]">
                                  {k.keyword ?? k}
                                </span>
                              ))}
                            </div>
                          )}
                          {s.source.startsWith("trend_") && s.realData && Array.isArray(s.payload?.items) && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {s.payload.items.slice(0, 12).map((it: any, i: number) => (
                                <span key={i} className="rounded-full bg-[var(--gray-4)] px-2 py-0.5 text-[11px] text-[var(--gray-12)]">
                                  {it.keyword ?? it}
                                </span>
                              ))}
                            </div>
                          )}
                          {s.source === "tiktok_shop" && s.realData && Array.isArray(s.payload?.products) && (
                            <div className="mt-2 space-y-1.5">
                              {s.payload.products.slice(0, 6).map((p: any, i: number) => (
                                <button
                                  type="button"
                                  key={i}
                                  onClick={() => setSelectedProduct({ ...p, _source: s.term })}
                                  className="flex w-full items-center gap-2 rounded-lg border border-[var(--gray-5)] bg-[var(--gray-1)] p-1.5 text-left transition hover:border-[var(--gray-6)]"
                                >
                                  {p.image ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={p.image} alt="" className="h-9 w-9 flex-shrink-0 rounded object-cover" />
                                  ) : (
                                    <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded bg-[var(--gray-4)]">
                                      <ShoppingCart className="h-4 w-4 text-[var(--gray-9)]" />
                                    </div>
                                  )}
                                  <div className="min-w-0 flex-1">
                                    <div className="truncate text-[11px] font-medium text-[var(--gray-12)]">{p.title}</div>
                                    <div className="flex items-center gap-2 text-[10px] text-[var(--gray-9)]">
                                      {typeof p.price === "number" && (
                                        <span className="font-semibold text-[var(--gray-12)]">{p.currency_symbol || "$"}{p.price}</span>
                                      )}
                                      {p.rating ? (
                                        <span className="inline-flex items-center gap-0.5">
                                          <Star className="h-2.5 w-2.5 fill-current text-amber-500" />{p.rating}
                                        </span>
                                      ) : null}
                                      {p.sold_count ? <span>已售 {p.sold_count}</span> : null}
                                    </div>
                                  </div>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      </div>
      <ProductDetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
    </section>
  );
}
