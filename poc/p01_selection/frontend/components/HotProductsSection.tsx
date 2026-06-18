"use client";
import React from "react";
import { Flame, Star, ShoppingCart, TrendingUp, Store, Tag } from "lucide-react";
import { fetchDataSnapshots } from "@/lib/api";
import { cn } from "@/lib/utils";

// TikTok Shop 实时商品（与 modules/tikhub.shop_search 归一化字段一致）
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
  sku_count?: number | null;
  marketing_labels?: string[] | null;
  shop_name?: string | null;
  shop_logo?: string | null;
  image?: string | null;
  url?: string | null;
}
type RankedProduct = ShopProduct & { _gmv: number; _term: string };

const TOP_N = 8;

// 营销标签：去掉通用广告位「DEALS FOR YOU」（无选品意义），常见活动英转中
const LABEL_ZH: Record<string, string> = {
  "Flash sale": "限时秒杀",
  "Limited time deal": "限时特惠",
  "Free shipping": "包邮",
};
function tidyLabels(labels?: string[] | null): string[] {
  if (!Array.isArray(labels)) return [];
  const out: string[] = [];
  for (const raw of labels) {
    const t = (raw || "").trim();
    if (!t || t.toUpperCase() === "DEALS FOR YOU") continue;
    const zh = LABEL_ZH[t] ?? t;
    if (!out.includes(zh)) out.push(zh);
  }
  return out.slice(0, 2);
}

function fmtMoney(n: number, symbol = "$"): string {
  if (!isFinite(n) || n <= 0) return "—";
  if (n >= 1e8) return `${symbol}${(n / 1e8).toFixed(2)}亿`;
  if (n >= 1e4) return `${symbol}${(n / 1e4).toFixed(1)}万`;
  return `${symbol}${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}
function fmtInt(n?: number | null): string {
  if (typeof n !== "number" || !isFinite(n) || n <= 0) return "—";
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  return n.toLocaleString("en-US");
}

function rankBadge(i: number): string {
  if (i === 0) return "bg-amber-400 text-white";
  if (i === 1) return "bg-slate-400 text-white";
  if (i === 2) return "bg-amber-700 text-white";
  return "bg-white/90 text-ink";
}

export function HotProductsSection() {
  const [products, setProducts] = React.useState<RankedProduct[] | null>(null);
  const [scanned, setScanned] = React.useState(0);

  React.useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const snaps = await fetchDataSnapshots({ source: "tiktok_shop", limit: 100 });
        const best = new Map<string, RankedProduct>();
        for (const s of snaps) {
          const arr: ShopProduct[] = Array.isArray(s.payload?.products) ? s.payload.products : [];
          for (const p of arr) {
            if (!p.product_id) continue;
            const price = typeof p.price === "number" ? p.price : 0;
            const sold = typeof p.sold_count === "number" ? p.sold_count : 0;
            const gmv = price * sold;
            const prev = best.get(p.product_id);
            if (!prev || gmv > prev._gmv) best.set(p.product_id, { ...p, _gmv: gmv, _term: s.term });
          }
        }
        const ranked = [...best.values()].filter((p) => p._gmv > 0).sort((a, b) => b._gmv - a._gmv);
        if (alive) {
          setProducts(ranked.slice(0, TOP_N));
          setScanned(best.size);
        }
      } catch {
        if (alive) setProducts([]);
      }
    })();
    return () => { alive = false; };
  }, []);

  // 加载中：骨架；无数据：整块隐藏，避免破坏工作台
  if (products !== null && products.length === 0) return null;

  return (
    <section className="mt-6">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
            <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-brand/10 text-brand">
              <Flame className="h-4 w-4" />
            </span>
            实时社媒选品榜 · TikTok Shop 全球爆款
          </h2>
          <p className="mt-1 text-xs text-ink-subtle">
            来自 TikHub 的 TikTok Shop 海外实时商品，按「估算销售额 = 价格 × 销量」排序，辅助选品决策（销量 / 评分为平台公开数据，销售额为估算）。
          </p>
        </div>
        {scanned > 0 && (
          <span className="hidden flex-shrink-0 items-center gap-1 rounded-full bg-surface-2 px-2.5 py-1 text-[11px] text-ink-subtle sm:inline-flex">
            <TrendingUp className="h-3 w-3" /> 已扫描 {scanned} 件在售
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
        {products === null
          ? Array.from({ length: TOP_N }).map((_, i) => (
              <div key={i} className="overflow-hidden rounded-2xl border border-hairline bg-white">
                <div className="aspect-square w-full animate-pulse bg-surface-2" />
                <div className="space-y-2 p-3">
                  <div className="h-3 w-full animate-pulse rounded bg-surface-2" />
                  <div className="h-8 w-2/3 animate-pulse rounded bg-surface-2" />
                  <div className="h-3 w-1/2 animate-pulse rounded bg-surface-2" />
                </div>
              </div>
            ))
          : products.map((p, i) => {
              const labels = tidyLabels(p.marketing_labels);
              const sym = p.currency_symbol || "$";
              return (
                <a
                  key={p.product_id}
                  href={p.url || undefined}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex flex-col overflow-hidden rounded-2xl border border-hairline bg-white transition-all hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-md"
                >
                  {/* 商品图 */}
                  <div className="relative aspect-square w-full overflow-hidden bg-surface-2">
                    {p.image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={p.image}
                        alt=""
                        loading="lazy"
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-ink-tertiary">
                        <ShoppingCart className="h-8 w-8" />
                      </div>
                    )}
                    <span
                      className={cn(
                        "absolute left-2 top-2 flex h-6 w-6 items-center justify-center rounded-full text-[12px] font-bold shadow-sm",
                        rankBadge(i),
                      )}
                    >
                      {i + 1}
                    </span>
                    {typeof p.discount_pct === "number" && p.discount_pct > 0 && (
                      <span className="absolute right-2 top-2 rounded-md bg-rose-500 px-1.5 py-0.5 text-[11px] font-semibold text-white shadow-sm">
                        -{p.discount_pct}%
                      </span>
                    )}
                    {labels.length > 0 && (
                      <div className="absolute bottom-2 left-2 flex flex-wrap gap-1">
                        {labels.map((l) => (
                          <span
                            key={l}
                            className="inline-flex items-center rounded bg-black/55 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm"
                          >
                            {l}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 信息区 */}
                  <div className="flex flex-1 flex-col p-3">
                    <div className="line-clamp-2 min-h-[32px] text-[12px] font-medium leading-tight text-ink">
                      {p.title}
                    </div>

                    {/* 估算销售额：选品头条指标 */}
                    <div className="mt-2 rounded-lg bg-brand/5 px-2.5 py-1.5">
                      <div className="flex items-center gap-1 text-[10px] text-ink-subtle">
                        <TrendingUp className="h-3 w-3 text-brand" /> 估算销售额
                      </div>
                      <div className="text-sm font-bold text-brand">{fmtMoney(p._gmv, sym)}</div>
                    </div>

                    {/* 价格 + 原价 */}
                    <div className="mt-2 flex items-baseline gap-1.5">
                      <span className="text-sm font-semibold text-ink">
                        {sym}
                        {p.price}
                      </span>
                      {p.original_price ? (
                        <span className="text-[11px] text-ink-tertiary line-through">
                          {sym}
                          {p.original_price}
                        </span>
                      ) : null}
                    </div>

                    {/* 销量 / 评分 / 评论 / SKU */}
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-ink-subtle">
                      <span className="inline-flex items-center gap-0.5">
                        <ShoppingCart className="h-3 w-3" /> 已售 {fmtInt(p.sold_count)}
                      </span>
                      {p.rating ? (
                        <span className="inline-flex items-center gap-0.5">
                          <Star className="h-3 w-3 fill-current text-amber-500" />
                          {p.rating}
                          {p.review_count ? <span className="text-ink-tertiary">({fmtInt(p.review_count)})</span> : null}
                        </span>
                      ) : null}
                      {p.sku_count ? <span>{p.sku_count} 规格</span> : null}
                    </div>

                    {/* 店铺 + 关联关键词 */}
                    <div className="mt-2 flex items-center justify-between gap-2 border-t border-hairline pt-2">
                      <span className="inline-flex min-w-0 items-center gap-1 text-[11px] text-ink-muted">
                        {p.shop_logo ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={p.shop_logo} alt="" className="h-4 w-4 flex-shrink-0 rounded-full object-cover" />
                        ) : (
                          <Store className="h-3 w-3 flex-shrink-0" />
                        )}
                        <span className="truncate">{p.shop_name || "—"}</span>
                      </span>
                      <span className="inline-flex flex-shrink-0 items-center gap-0.5 rounded bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-subtle">
                        <Tag className="h-2.5 w-2.5" />
                        {p._term}
                      </span>
                    </div>
                  </div>
                </a>
              );
            })}
      </div>
    </section>
  );
}
