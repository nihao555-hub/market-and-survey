"use client";
import React from "react";
import { Globe, ExternalLink, Package } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * 工具执行结果的结构化美化渲染（替代原始 <pre> JSON）。
 * - 自动抽取证据 URL → 渲染成带 favicon 的链接 chip（让用户看到 agent 在处理哪些平台）
 * - 商品列表 → 紧凑卡片
 * - 普通对象 → key/value 折叠树
 * - 未知形态 → 退化为格式化 JSON
 */

// ── favicon（Google 公共 favicon 服务，纯 UI 装饰，失败回退 Globe 图标）──
function Favicon({ host }: { host: string }) {
  const [failed, setFailed] = React.useState(false);
  if (failed || !host) {
    return <Globe className="h-3.5 w-3.5 text-ink-subtle" />;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=32`}
      alt=""
      width={14}
      height={14}
      className="h-3.5 w-3.5 rounded-sm"
      onError={() => setFailed(true)}
    />
  );
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/** 平台域名 → 友好中文名（让用户一眼看懂在抓哪个平台） */
const PLATFORM_LABELS: Record<string, string> = {
  "amazon.com": "Amazon US",
  "amazon.co.uk": "Amazon UK",
  "amazon.de": "Amazon DE",
  "amazon.fr": "Amazon FR",
  "amazon.co.jp": "Amazon JP",
  "amazon.in": "Amazon IN",
  "amazon.com.mx": "Amazon MX",
  "amazon.com.br": "Amazon BR",
  "1688.com": "1688",
  "detail.1688.com": "1688 详情",
  "made-in-china.com": "MIC",
  "keepa.com": "Keepa",
  "mercadolibre.com.mx": "MercadoLibre MX",
  "mercadolivre.com.br": "MercadoLivre BR",
  "lazada.sg": "Lazada SG",
  "shopee.sg": "Shopee SG",
  "ozon.ru": "Ozon",
  "wildberries.ru": "Wildberries",
  "trends.google.com": "Google Trends",
};

function LinkChip({ url }: { url: string }) {
  const host = hostOf(url);
  const label = PLATFORM_LABELS[host] || host || url;
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      title={url}
      className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-hairline bg-white px-2 py-1 text-xs text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink"
    >
      <Favicon host={host} />
      <span className="truncate">{label}</span>
      <ExternalLink className="h-3 w-3 flex-shrink-0 text-ink-subtle" />
    </a>
  );
}

// ── URL 抽取（递归，去重，上限放宽到 60）──
const URL_RE = /^https?:\/\//i;
function collectUrls(value: unknown, acc: Set<string>, depth = 0) {
  if (depth > 6 || acc.size >= 60) return;
  if (typeof value === "string") {
    if (URL_RE.test(value)) acc.add(value);
    return;
  }
  if (Array.isArray(value)) {
    for (const v of value) collectUrls(v, acc, depth + 1);
    return;
  }
  if (value && typeof value === "object") {
    for (const v of Object.values(value as Record<string, unknown>)) {
      collectUrls(v, acc, depth + 1);
    }
  }
}

// ── 商品列表判定（用于紧凑卡片）──
function isProductList(v: unknown): v is Array<Record<string, unknown>> {
  if (!Array.isArray(v) || v.length === 0) return false;
  const first = v[0];
  return (
    !!first &&
    typeof first === "object" &&
    ("title" in first || "asin" in first || "name" in first)
  );
}

function ProductCards({ items }: { items: Array<Record<string, unknown>> }) {
  const [showAll, setShowAll] = React.useState(false);
  const COLLAPSED = 8;
  const shown = showAll ? items : items.slice(0, COLLAPSED);
  return (
    <div className="space-y-1.5">
      {shown.map((p, i) => {
        const title = String(p.title || p.name || p.asin || "商品");
        const price = p.price ?? p.price_usd ?? p.sale_price;
        const rating = p.rating ?? p.stars;
        const reviews = p.review_count ?? p.reviews ?? p.ratings_total;
        const bought = p.bought_past_month ?? p.sales_volume_text;
        const brand = p.brand ?? p.seller ?? p.store;
        const sponsored = p.sponsored === true;
        const url = (p.url || p.link || p.dp_url) as string | undefined;
        const img = (p.image_url || p.image || p.thumbnail) as string | undefined;
        return (
          <div
            key={i}
            className="flex items-start gap-2 rounded-md border border-hairline bg-surface-1 px-2.5 py-1.5"
          >
            {img ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={img}
                alt=""
                className="mt-0.5 h-9 w-9 flex-shrink-0 rounded border border-hairline object-cover"
                onError={(e) => ((e.currentTarget as HTMLImageElement).style.display = "none")}
              />
            ) : (
              <Package className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-ink-subtle" />
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="truncate text-xs text-ink" title={title}>
                  {title}
                </span>
                {sponsored && (
                  <span className="flex-shrink-0 rounded bg-surface-2 px-1 py-0.5 text-[9px] text-ink-subtle">
                    广告位
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex flex-wrap gap-x-2.5 gap-y-0.5 text-[11px] text-ink-subtle">
                {price != null && <span className="text-accent">价 {String(price)}</span>}
                {rating != null && <span>★ {String(rating)}</span>}
                {reviews != null && <span>{String(reviews)} 评价</span>}
                {bought != null && <span className="text-success">月销 {String(bought)}</span>}
                {brand != null && <span>品牌 {String(brand)}</span>}
                {p.asin != null && <span className="font-mono">{String(p.asin)}</span>}
                {url && (
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-0.5 text-ink-muted hover:text-accent"
                  >
                    打开 <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                )}
              </div>
            </div>
          </div>
        );
      })}
      {items.length > COLLAPSED && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="px-1 text-[11px] text-accent hover:underline"
        >
          {showAll ? "收起" : `展开全部 ${items.length} 个`}
        </button>
      )}
    </div>
  );
}

// ── 通用结构化值渲染 ──
function formatPrimitive(v: unknown): string {
  if (v === null) return "—";
  if (typeof v === "boolean") return v ? "是" : "否";
  return String(v);
}

const HIDDEN_KEYS = new Set(["markdown", "markdown_remote", "markdown_local"]);

function StructuredValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined) {
    return <span className="text-ink-subtle">—</span>;
  }
  if (typeof value !== "object") {
    const s = formatPrimitive(value);
    if (URL_RE.test(s)) return <LinkChip url={s} />;
    return <span className="break-words text-ink-muted">{s}</span>;
  }
  if (isProductList(value)) {
    return <ProductCards items={value as Array<Record<string, unknown>>} />;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-ink-subtle">空</span>;
    // 基础类型数组 → 内联 chips
    if (value.every((v) => typeof v !== "object")) {
      return (
        <div className="flex flex-wrap gap-1">
          {value.slice(0, 100).map((v, i) => (
            <span key={i} className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-muted">
              {formatPrimitive(v)}
            </span>
          ))}
          {value.length > 100 && (
            <span className="text-[11px] text-ink-subtle">…共 {value.length} 项</span>
          )}
        </div>
      );
    }
    return (
      <div className="space-y-1">
        {value.slice(0, 50).map((v, i) => (
          <div key={i} className="rounded border border-hairline/60 p-1.5">
            <StructuredValue value={v} depth={depth + 1} />
          </div>
        ))}
        {value.length > 50 && (
          <div className="px-1 text-[11px] text-ink-subtle">…共 {value.length} 项</div>
        )}
      </div>
    );
  }
  // 对象 → key/value 行
  const entries = Object.entries(value as Record<string, unknown>).filter(
    ([k, v]) => !HIDDEN_KEYS.has(k) && v !== null && v !== undefined && v !== ""
  );
  if (entries.length === 0) return <span className="text-ink-subtle">空</span>;
  return (
    <div className="space-y-1">
      {entries.map(([k, v]) => (
        <div key={k} className="grid grid-cols-[minmax(72px,auto)_1fr] gap-2 text-xs">
          <span className="font-medium text-ink-subtle">{k}</span>
          <div className="min-w-0">
            <StructuredValue value={v} depth={depth + 1} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ToolOutputView({ output }: { output: unknown }) {
  // 抽证据 URL
  const urls = React.useMemo(() => {
    const set = new Set<string>();
    collectUrls(output, set);
    return Array.from(set);
  }, [output]);

  // 字符串输出（少见）：直接显示
  if (typeof output === "string") {
    return <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-ink-muted">{output}</pre>;
  }

  return (
    <div className="space-y-2">
      {urls.length > 0 && (
        <div>
          <div className="mb-1 flex items-center gap-1 text-[10px] font-medium text-ink-subtle">
            <Globe className="h-3 w-3" /> 数据来源 / 证据
          </div>
          <div className="flex flex-wrap gap-1.5">
            {urls.map((u) => (
              <LinkChip key={u} url={u} />
            ))}
          </div>
        </div>
      )}
      <StructuredValue value={output} />
    </div>
  );
}
