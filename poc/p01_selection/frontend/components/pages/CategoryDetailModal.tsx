"use client";
import React from "react";
import {
  X, ShoppingCart, Star, Package, TrendingUp, DollarSign,
  BarChart3, ArrowUp, ArrowDown, Minus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { zhCat } from "@/lib/category-i18n";
import type { DataSnapshot } from "@/lib/api";

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

function fmtSold(n: number): string {
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return String(n);
}

interface Props {
  snapshot: DataSnapshot | null;
  onClose: () => void;
}

export function CategoryDetailModal({ snapshot, onClose }: Props) {
  if (!snapshot) return null;

  const payload = snapshot.payload || {};
  const categoryName = (payload.category_name || payload.category_name_en || "未知品类") as string;
  const products: ShopProduct[] = Array.isArray(payload.products) ? payload.products : [];
  const stats = payload.stats as { price_min?: number; price_max?: number; weighted_avg_rating?: number } | undefined;

  // Compute stats
  const prices = products.map((p) => p.price).filter((v): v is number => typeof v === "number" && v > 0);
  const ratings = products.map((p) => p.rating).filter((v): v is number => typeof v === "number" && v > 0);
  const soldCounts = products.map((p) => p.sold_count).filter((v): v is number => typeof v === "number" && v > 0);

  const avgPrice = prices.length ? (prices.reduce((a, b) => a + b, 0) / prices.length) : 0;
  const minPrice = prices.length ? Math.min(...prices) : 0;
  const maxPrice = prices.length ? Math.max(...prices) : 0;
  const avgRating = stats?.weighted_avg_rating || (ratings.length ? (ratings.reduce((a, b) => a + b, 0) / ratings.length) : 0);
  const totalSold = soldCounts.reduce((a, b) => a + b, 0);

  // Price distribution buckets
  const buckets = [
    { label: "$0-10", min: 0, max: 10 },
    { label: "$10-25", min: 10, max: 25 },
    { label: "$25-50", min: 25, max: 50 },
    { label: "$50-100", min: 50, max: 100 },
    { label: "$100+", min: 100, max: Infinity },
  ];
  const priceDist = buckets.map((b) => ({
    ...b,
    count: prices.filter((p) => p >= b.min && p < b.max).length,
  }));
  const maxBucket = Math.max(...priceDist.map((d) => d.count), 1);

  // Sort products by sold_count desc
  const sortedProducts = [...products].sort((a, b) => (b.sold_count ?? 0) - (a.sold_count ?? 0));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 pt-8 pb-8" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-4xl rounded-2xl border border-[var(--gray-5)] bg-[var(--gray-1)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--gray-5)] px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-[var(--gray-12)]">{zhCat(categoryName)}</h2>
            <p className="text-sm text-[var(--gray-8)]">{categoryName}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-[var(--gray-8)] hover:bg-[var(--gray-3)] hover:text-[var(--gray-12)]">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3 border-b border-[var(--gray-5)] px-6 py-4 sm:grid-cols-5">
          <div className="rounded-lg bg-[var(--gray-3)] p-3 text-center">
            <div className="text-[11px] text-[var(--gray-8)]">商品数</div>
            <div className="mt-1 text-lg font-bold text-[var(--gray-12)]">{products.length}</div>
          </div>
          <div className="rounded-lg bg-[var(--gray-3)] p-3 text-center">
            <div className="text-[11px] text-[var(--gray-8)]">均价</div>
            <div className="mt-1 text-lg font-bold text-[var(--gray-12)]">${avgPrice.toFixed(2)}</div>
          </div>
          <div className="rounded-lg bg-[var(--gray-3)] p-3 text-center">
            <div className="text-[11px] text-[var(--gray-8)]">价格区间</div>
            <div className="mt-1 text-sm font-bold text-[var(--gray-12)]">${minPrice} - ${maxPrice}</div>
          </div>
          <div className="rounded-lg bg-[var(--gray-3)] p-3 text-center">
            <div className="text-[11px] text-[var(--gray-8)]">均评分</div>
            <div className="mt-1 text-lg font-bold text-[var(--gray-12)]">{avgRating.toFixed(1)}</div>
          </div>
          <div className="rounded-lg bg-[var(--gray-3)] p-3 text-center">
            <div className="text-[11px] text-[var(--gray-8)]">总销量</div>
            <div className="mt-1 text-lg font-bold text-[var(--gray-12)]">{fmtSold(totalSold)}</div>
          </div>
        </div>

        {/* Price distribution */}
        {prices.length > 0 && (
          <div className="border-b border-[var(--gray-5)] px-6 py-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--gray-12)]">
              <BarChart3 className="h-4 w-4" /> 价格分布
            </h3>
            <div className="flex items-end gap-2">
              {priceDist.map((d) => (
                <div key={d.label} className="flex flex-1 flex-col items-center gap-1">
                  <span className="text-[10px] text-[var(--gray-8)]">{d.count}</span>
                  <div
                    className="w-full rounded-t bg-blue-500/70"
                    style={{ height: `${Math.max((d.count / maxBucket) * 60, 4)}px` }}
                  />
                  <span className="text-[10px] text-[var(--gray-8)]">{d.label}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Product list */}
        <div className="px-6 py-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--gray-12)]">
            <Package className="h-4 w-4" /> 全部商品 ({products.length})
          </h3>
          <div className="max-h-[400px] overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 z-10 bg-[var(--gray-2)]">
                <tr className="border-b border-[var(--gray-5)] text-[11px] text-[var(--gray-8)]">
                  <th className="px-2 py-2 font-medium w-8">#</th>
                  <th className="px-2 py-2 font-medium">商品</th>
                  <th className="px-2 py-2 font-medium text-right">价格</th>
                  <th className="px-2 py-2 font-medium text-right">已售</th>
                  <th className="px-2 py-2 font-medium text-right">评分</th>
                  <th className="px-2 py-2 font-medium">店铺</th>
                </tr>
              </thead>
              <tbody>
                {sortedProducts.map((p, i) => (
                  <tr key={p.product_id || i} className="border-b border-[var(--gray-4)] last:border-0 hover:bg-[var(--gray-3)]/50">
                    <td className="px-2 py-2 text-[var(--gray-8)]">{i + 1}</td>
                    <td className="px-2 py-2">
                      <div className="flex items-center gap-2">
                        {p.image ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={p.image} alt="" className="h-8 w-8 flex-shrink-0 rounded object-cover" />
                        ) : (
                          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded bg-[var(--gray-4)]">
                            <ShoppingCart className="h-3 w-3 text-[var(--gray-7)]" />
                          </div>
                        )}
                        <span className="line-clamp-2 max-w-[300px] text-[var(--gray-12)]">{p.title || "—"}</span>
                      </div>
                    </td>
                    <td className="px-2 py-2 text-right font-medium text-[var(--gray-12)]">
                      ${p.price ?? "—"}
                      {p.original_price && p.original_price > (p.price ?? 0) && (
                        <span className="ml-1 text-[10px] text-[var(--gray-7)] line-through">${p.original_price}</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-right text-[var(--gray-9)]">
                      {typeof p.sold_count === "number" && p.sold_count > 0 ? fmtSold(p.sold_count) : "—"}
                    </td>
                    <td className="px-2 py-2 text-right">
                      {p.rating ? (
                        <span className="inline-flex items-center gap-0.5">
                          <Star className="h-3 w-3 fill-current text-amber-500" />{p.rating}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-2 py-2 text-[var(--gray-8)] max-w-[120px] truncate">{p.shop_name || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
