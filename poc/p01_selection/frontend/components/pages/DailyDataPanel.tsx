"use client";
import React from "react";
import { RefreshCw, Database, Clock, ListChecks, Search, TrendingUp, CalendarDays, ShoppingCart, Flame, Star } from "lucide-react";
import {
  fetchDailyRefreshStatus, fetchDataSnapshots, triggerDailyRefresh,
  type DataSnapshot, type RefreshStatus,
} from "@/lib/api";
import { Button, StatusBadge, StatTile, Skeleton, EmptyState, type StatusKind } from "./primitives";

// 数据源中文名 + 图标
const SOURCE_META: Record<string, { label: string; icon: React.ReactNode }> = {
  amazon_keywords: { label: "买家搜索词", icon: <Search className="h-3.5 w-3.5" /> },
  google_trends: { label: "搜索趋势", icon: <TrendingUp className="h-3.5 w-3.5" /> },
  seasonality: { label: "季节性", icon: <CalendarDays className="h-3.5 w-3.5" /> },
  bestsellers: { label: "电商榜单", icon: <ShoppingCart className="h-3.5 w-3.5" /> },
  tiktok_shop: { label: "TikTok Shop 实时商品", icon: <ShoppingCart className="h-3.5 w-3.5" /> },
  trend_tiktok: { label: "TikTok 趋势词", icon: <Flame className="h-3.5 w-3.5" /> },
  trend_douyin: { label: "抖音热榜", icon: <Flame className="h-3.5 w-3.5" /> },
  trend_weibo: { label: "微博热搜", icon: <Flame className="h-3.5 w-3.5" /> },
  trend_xiaohongshu: { label: "小红书热词", icon: <Flame className="h-3.5 w-3.5" /> },
  social_trends: { label: "社媒趋势", icon: <Flame className="h-3.5 w-3.5" /> },
};
const sourceMeta = (s: string) => SOURCE_META[s] ?? { label: s, icon: <Database className="h-3.5 w-3.5" /> };

// 快照状态 → 徽章样式
const STATUS_MAP: Record<string, { kind: StatusKind; label: string }> = {
  ok: { kind: "done", label: "已抓取" },
  empty: { kind: "neutral", label: "暂无数据" },
  error: { kind: "error", label: "抓取失败" },
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

  const reload = React.useCallback(async () => {
    try {
      const [st, snaps] = await Promise.all([
        fetchDailyRefreshStatus(),
        fetchDataSnapshots({ limit: 200 }),
      ]);
      setStatus(st);
      setSnapshots(snaps);
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
    <section className="mb-4 rounded-2xl border border-hairline bg-white">
      <div className="flex items-start justify-between gap-3 border-b border-hairline px-5 py-3.5">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-ink">实时数据刷新 · 真实数据底子</h2>
          <p className="mt-0.5 text-xs text-ink-subtle">
            每 2 小时自动刷新一次：TikTok Shop 实时商品 + 社媒趋势（TikTok/抖音/微博/小红书）+ 搜索词/趋势，落库作为选品与调研的底子。
          </p>
        </div>
        <Button size="sm" loading={running} onClick={onRefresh} className="flex-shrink-0">
          <RefreshCw className="h-3.5 w-3.5" />立即刷新
        </Button>
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
              tone={status?.tier2ChannelOk ? "text-success" : "text-ink-subtle"}
              icon={<ShoppingCart className="h-4 w-4" />}
            />
          </div>

          {!status?.tier2ChannelOk && (
            <div className="mb-4 rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-xs text-ink-subtle">
              实时电商通道（TikTok Shop）需配置 <span className="font-medium text-ink-muted">TIKHUB_API_KEY</span>；通道未就绪时如实标注，<span className="font-medium text-ink-muted">不编造数据</span>，接入后自动补齐。
            </div>
          )}

          {/* 快照分组 */}
          {groups.length === 0 ? (
            <EmptyState
              icon={<Database className="h-6 w-6" />}
              title="还没有数据快照"
              hint="点击右上角「立即刷新」抓取一次真实数据，或等待每 2 小时一次的自动刷新。"
            />
          ) : (
            <div className="space-y-3">
              {groups.map(([term, items]) => (
                <div key={term} className="rounded-xl border border-hairline bg-white p-4">
                  <div className="mb-3 text-sm font-semibold text-ink">{term}</div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {items.map((s) => {
                      const meta = sourceMeta(s.source);
                      const info = statusInfo(s.status);
                      return (
                        <div key={s.id} className="rounded-lg border border-hairline bg-surface-1 p-3">
                          <div className="mb-1 flex items-center justify-between gap-2">
                            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-muted">
                              <span className="text-brand">{meta.icon}</span>{meta.label}
                              <span className="rounded bg-surface-2 px-1 text-[10px] text-ink-subtle">T{s.tier}</span>
                            </span>
                            <StatusBadge status={info.kind} label={info.label} />
                          </div>
                          <div className="text-xs leading-relaxed text-ink-subtle">{s.summary || "—"}</div>
                          {s.source === "amazon_keywords" && s.realData && Array.isArray(s.payload?.suggestions) && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {s.payload.suggestions.slice(0, 8).map((k: any, i: number) => (
                                <span key={i} className="rounded-full bg-brand/10 px-2 py-0.5 text-[11px] text-brand">
                                  {k.keyword ?? k}
                                </span>
                              ))}
                            </div>
                          )}
                          {s.source.startsWith("trend_") && s.realData && Array.isArray(s.payload?.items) && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {s.payload.items.slice(0, 12).map((it: any, i: number) => (
                                <span key={i} className="rounded-full bg-brand/10 px-2 py-0.5 text-[11px] text-brand">
                                  {it.keyword ?? it}
                                </span>
                              ))}
                            </div>
                          )}
                          {s.source === "tiktok_shop" && s.realData && Array.isArray(s.payload?.products) && (
                            <div className="mt-2 space-y-1.5">
                              {s.payload.products.slice(0, 6).map((p: any, i: number) => (
                                <a
                                  key={i}
                                  href={p.url || undefined}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="flex items-center gap-2 rounded-lg border border-hairline bg-white p-1.5 transition hover:border-brand/40"
                                >
                                  {p.image ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={p.image} alt="" className="h-9 w-9 flex-shrink-0 rounded object-cover" />
                                  ) : (
                                    <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded bg-surface-2">
                                      <ShoppingCart className="h-4 w-4 text-ink-subtle" />
                                    </div>
                                  )}
                                  <div className="min-w-0 flex-1">
                                    <div className="truncate text-[11px] font-medium text-ink">{p.title}</div>
                                    <div className="flex items-center gap-2 text-[10px] text-ink-subtle">
                                      {typeof p.price === "number" && (
                                        <span className="font-semibold text-brand">{p.currency_symbol || "$"}{p.price}</span>
                                      )}
                                      {p.rating ? (
                                        <span className="inline-flex items-center gap-0.5">
                                          <Star className="h-2.5 w-2.5 fill-current text-amber-500" />{p.rating}
                                        </span>
                                      ) : null}
                                      {p.sold_count ? <span>已售 {p.sold_count}</span> : null}
                                    </div>
                                  </div>
                                </a>
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
    </section>
  );
}
