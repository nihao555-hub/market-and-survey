"use client";
import React from "react";
import {
  X, ShoppingCart, Star, Store, ExternalLink, Tag, Package, TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface ProductForModal {
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
  _category?: string;
  _source?: string;
}

function fmtInt(n?: number | null): string {
  if (typeof n !== "number" || !isFinite(n) || n <= 0) return "—";
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  return n.toLocaleString("en-US");
}

interface Props {
  product: ProductForModal | null;
  onClose: () => void;
}

export function ProductDetailModal({ product, onClose }: Props) {
  if (!product) return null;

  const sym = product.currency_symbol || "$";
  const gmv =
    typeof product.price === "number" && typeof product.sold_count === "number"
      ? product.price * product.sold_count
      : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      {/* backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      {/* panel */}
      <div
        className="relative flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-hairline bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* close */}
        <button
          onClick={onClose}
          className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-white/80 text-ink-muted shadow-sm hover:bg-surface-2 hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>

        {/* scrollable body */}
        <div className="overflow-y-auto">
          {/* image */}
          {product.image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.image}
              alt=""
              className="aspect-square w-full object-cover"
            />
          ) : (
            <div className="flex aspect-square w-full items-center justify-center bg-surface-2 text-ink-tertiary">
              <ShoppingCart className="h-12 w-12" />
            </div>
          )}

          <div className="space-y-4 p-5">
            {/* tags */}
            <div className="flex flex-wrap gap-1.5">
              {product._category && (
                <span className="inline-flex items-center gap-0.5 rounded-full bg-brand/10 px-2 py-0.5 text-[11px] font-medium text-brand">
                  <Package className="h-3 w-3" />{product._category}
                </span>
              )}
              {product._source && (
                <span className="inline-flex items-center gap-0.5 rounded-full bg-surface-2 px-2 py-0.5 text-[11px] text-ink-subtle">
                  <Tag className="h-3 w-3" />{product._source}
                </span>
              )}
              {typeof product.discount_pct === "number" && product.discount_pct > 0 && (
                <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-600">
                  -{product.discount_pct}%
                </span>
              )}
            </div>

            {/* title */}
            <h3 className="text-sm font-semibold leading-snug text-ink">{product.title || "—"}</h3>

            {/* price */}
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-ink">{sym}{product.price ?? "—"}</span>
              {product.original_price ? (
                <span className="text-sm text-ink-tertiary line-through">{sym}{product.original_price}</span>
              ) : null}
            </div>

            {/* GMV estimate */}
            {gmv && gmv > 0 && (
              <div className="rounded-lg bg-brand/5 px-3 py-2">
                <div className="flex items-center gap-1.5 text-xs text-ink-subtle">
                  <TrendingUp className="h-3.5 w-3.5 text-brand" /> 估算销售额
                </div>
                <div className="mt-0.5 text-base font-bold text-brand">
                  {sym}{gmv >= 1e4 ? `${(gmv / 1e4).toFixed(1)}万` : gmv.toLocaleString("en-US", { maximumFractionDigits: 0 })}
                </div>
              </div>
            )}

            {/* metrics grid */}
            <div className="grid grid-cols-2 gap-3">
              <MetricBox icon={<ShoppingCart className="h-4 w-4" />} label="已售" value={fmtInt(product.sold_count)} />
              <MetricBox icon={<Star className="h-4 w-4 fill-current text-amber-500" />} label="评分" value={product.rating ? `${product.rating}` : "—"} sub={product.review_count ? `${fmtInt(product.review_count)} 评论` : undefined} />
              {product.sku_count ? <MetricBox icon={<Package className="h-4 w-4" />} label="规格数" value={String(product.sku_count)} /> : null}
            </div>

            {/* marketing labels */}
            {Array.isArray(product.marketing_labels) && product.marketing_labels.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {product.marketing_labels.filter(Boolean).map((l) => (
                  <span key={l} className="rounded-full bg-surface-2 px-2.5 py-0.5 text-[11px] text-ink-subtle">{l}</span>
                ))}
              </div>
            )}

            {/* shop */}
            <div className="flex items-center gap-2 rounded-lg border border-hairline p-3">
              {product.shop_logo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={product.shop_logo} alt="" className="h-8 w-8 rounded-full object-cover" />
              ) : (
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-2">
                  <Store className="h-4 w-4 text-ink-tertiary" />
                </div>
              )}
              <span className="min-w-0 truncate text-sm text-ink">{product.shop_name || "未知店铺"}</span>
            </div>
          </div>
        </div>

        {/* footer: external link */}
        {product.url && (
          <div className="border-t border-hairline p-4">
            <a
              href={product.url}
              target="_blank"
              rel="noreferrer"
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition-colors",
                "bg-brand/10 text-brand hover:bg-brand/20",
              )}
            >
              <ExternalLink className="h-4 w-4" />
              在 TikTok Shop 查看
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricBox({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-hairline p-2.5">
      <div className="flex items-center gap-1.5 text-[11px] text-ink-subtle">{icon}{label}</div>
      <div className="mt-0.5 text-sm font-semibold text-ink">{value}</div>
      {sub && <div className="text-[10px] text-ink-tertiary">{sub}</div>}
    </div>
  );
}
