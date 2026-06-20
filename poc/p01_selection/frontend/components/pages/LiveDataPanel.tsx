"use client";
import React from "react";
import {
  Database, ShoppingCart, Star, Store, Flame, Hash,
  TrendingUp, Package, Music2, Sparkles, MessageCircle,
  BookOpen, Video, Tv, Twitter, Citrus,
} from "lucide-react";
import { fetchDataSnapshots, type DataSnapshot } from "@/lib/api";
import type { ResearchKind } from "@/lib/agent-types";
import { Panel, Skeleton, EmptyState, FilterTabs } from "./primitives";
import { cn } from "@/lib/utils";

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

/* ─── 平台元数据 ─── */
const PLATFORM_META: Record<string, { label: string; icon: React.ReactNode }> = {
  trend_tiktok: { label: "TikTok", icon: <Music2 className="h-3 w-3" /> },
  trend_douyin: { label: "\u6296\u97f3", icon: <Sparkles className="h-3 w-3" /> },
  trend_weibo: { label: "\u5fae\u535a", icon: <MessageCircle className="h-3 w-3" /> },
  trend_xiaohongshu: { label: "\u5c0f\u7ea2\u4e66", icon: <BookOpen className="h-3 w-3" /> },
  trend_kuaishou: { label: "\u5feb\u624b", icon: <Video className="h-3 w-3" /> },
  trend_bilibili: { label: "B\u7ad9", icon: <Tv className="h-3 w-3" /> },
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
type DataTab = "products" | "hot" | "trends" | "hashtags";

const MODE_TABS: Record<ResearchKind, DataTab[]> = {
  market: ["products", "hot", "trends"],
  trend: ["trends", "hashtags", "hot"],
  competitor: ["hot", "products"],
  audience: ["trends", "hashtags"],
  opportunity: ["hot", "hashtags", "products"],
  general: ["products", "hot", "trends", "hashtags"],
};

const TAB_META: Record<DataTab, { label: string; icon: React.ReactNode }> = {
  products: { label: "\u54c1\u7c7b Top \u5546\u54c1", icon: <Package className="h-3.5 w-3.5" /> },
  hot: { label: "\u5b9e\u65f6\u70ed\u9500", icon: <Flame className="h-3.5 w-3.5" /> },
  trends: { label: "\u793e\u5a92\u8d8b\u52bf", icon: <TrendingUp className="h-3.5 w-3.5" /> },
  hashtags: { label: "\u70ed\u95e8\u8bdd\u9898", icon: <Hash className="h-3.5 w-3.5" /> },
};

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
          <Database className="h-4 w-4 text-ink-subtle" />
          <h3 className="text-sm font-semibold text-ink">{"\u4eca\u65e5\u5b9e\u65f6\u6570\u636e"}</h3>
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
          <Database className="h-4 w-4 text-ink-subtle" />
          <h3 className="text-sm font-semibold text-ink">{"\u4eca\u65e5\u5b9e\u65f6\u6570\u636e"}</h3>
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
        <Database className="h-4 w-4 text-brand" />
        <h3 className="text-sm font-semibold text-ink">{"\u4eca\u65e5\u5b9e\u65f6\u6570\u636e"}</h3>
        <span className="rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-medium text-success">
          LIVE
        </span>
      </div>

      <Panel bodyClassName="p-0">
        <div className="border-b border-hairline px-4 py-3">
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
                    <tr className="bg-surface-1 text-[11px] uppercase tracking-wide text-ink-subtle">
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
                          className="border-t border-hairline transition-colors hover:bg-surface-1">
                        <td className="px-3 py-2.5 pl-4 text-xs text-ink-subtle">{i + 1}</td>
                        <td className="max-w-[260px] px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            {p.image ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={p.image} alt="" className="h-8 w-8 flex-shrink-0 rounded object-cover" />
                            ) : (
                              <ShoppingCart className="h-4 w-4 flex-shrink-0 text-ink-tertiary" />
                            )}
                            <span className="line-clamp-2 text-xs font-medium text-ink">{p.title}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex items-center gap-0.5 rounded bg-brand/10 px-1.5 py-0.5 text-[10px] font-medium text-brand">
                            <Package className="h-2.5 w-2.5" />{cat}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs font-semibold text-ink">
                          {p.currency_symbol || "$"}{p.price}
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs text-ink-muted">{fmtInt(p.sold_count)}</td>
                        <td className="px-3 py-2.5 text-right text-xs text-ink-muted">
                          {p.rating ? (
                            <span className="inline-flex items-center gap-0.5">
                              <Star className="h-3 w-3 fill-current text-amber-500" />{p.rating}
                            </span>
                          ) : "\u2014"}
                        </td>
                        <td className="max-w-[120px] truncate px-3 py-2.5 text-xs text-ink-subtle">
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
                    <tr className="bg-surface-1 text-[11px] uppercase tracking-wide text-ink-subtle">
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
                          className="border-t border-hairline transition-colors hover:bg-surface-1">
                        <td className="px-3 py-2.5 pl-4">
                          <span className={cn(
                            "inline-flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold",
                            i < 3 ? "bg-brand/15 text-brand" : "text-ink-subtle",
                          )}>{i + 1}</span>
                        </td>
                        <td className="max-w-[280px] px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            {p.image ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={p.image} alt="" className="h-8 w-8 flex-shrink-0 rounded object-cover" />
                            ) : (
                              <ShoppingCart className="h-4 w-4 flex-shrink-0 text-ink-tertiary" />
                            )}
                            <span className="line-clamp-2 text-xs font-medium text-ink">{p.title}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs font-semibold text-ink">
                          {p.currency_symbol || "$"}{p.price}
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs text-ink-muted">{fmtInt(p.sold_count)}</td>
                        <td className="px-3 py-2.5 text-right text-xs text-ink-muted">
                          {p.rating ? (
                            <span className="inline-flex items-center gap-0.5">
                              <Star className="h-3 w-3 fill-current text-amber-500" />{p.rating}
                            </span>
                          ) : "\u2014"}
                        </td>
                        <td className="max-w-[120px] truncate px-3 py-2.5 text-xs text-ink-subtle">
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
                    <div key={source} className="rounded-xl border border-hairline bg-surface-1 p-3">
                      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-ink">
                        {meta.icon}
                        {meta.label}
                        <span className="ml-auto rounded-full bg-surface-2 px-1.5 text-[10px] font-normal text-ink-subtle">
                          {items.length}
                        </span>
                      </div>
                      <ol className="space-y-1">
                        {items.slice(0, 8).map((it, idx) => {
                          const heat = typeof it.heat === "number" && it.heat > 0 ? fmtInt(it.heat) : null;
                          return (
                            <li key={idx} className="flex items-center gap-2 rounded px-1.5 py-1 text-[11px] text-ink">
                              <span className={cn(
                                "flex h-4 w-4 flex-shrink-0 items-center justify-center rounded text-[10px] font-semibold",
                                idx < 3 ? "bg-brand/15 text-brand" : "text-ink-tertiary",
                              )}>{idx + 1}</span>
                              <span className="min-w-0 flex-1 truncate">{it.keyword}</span>
                              {heat && (
                                <span className="flex-shrink-0 text-[10px] text-ink-subtle">
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

          {/* 热门话题表 */}
          {activeTab === "hashtags" && (
            hashtags.length === 0 ? (
              <EmptyState icon={<Hash className="h-5 w-5" />} title={"\u6682\u65e0\u70ed\u95e8\u8bdd\u9898\u6570\u636e"} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-surface-1 text-[11px] uppercase tracking-wide text-ink-subtle">
                      <th className="px-3 py-2.5 pl-4 text-left font-medium">#</th>
                      <th className="px-3 py-2.5 text-left font-medium">{"\u8bdd\u9898"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u6d4f\u89c8\u91cf"}</th>
                      <th className="px-3 py-2.5 text-right font-medium">{"\u53d1\u5e03\u6570"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hashtags.slice(0, 30).map((h, i) => (
                      <tr key={h.hashtag ?? i}
                          className="border-t border-hairline transition-colors hover:bg-surface-1">
                        <td className="px-3 py-2.5 pl-4">
                          <span className={cn(
                            "inline-flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold",
                            i < 3 ? "bg-brand/15 text-brand" : "text-ink-subtle",
                          )}>{i + 1}</span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-ink">
                            <Hash className="h-3 w-3 text-brand" />{h.hashtag}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs text-ink-muted">{fmtInt(h.views)}</td>
                        <td className="px-3 py-2.5 text-right text-xs text-ink-muted">{fmtInt(h.publish_count)}</td>
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
