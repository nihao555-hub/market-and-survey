"use client";
import React from "react";
import { Flame, RefreshCw, Clock, Hash, Layers, Music2, Sparkles, MessageCircle, BookOpen, Video, Tv, Twitter, Citrus } from "lucide-react";
import {
  fetchDailyRefreshStatus, fetchDataSnapshots,
  type DataSnapshot, type RefreshStatus,
} from "@/lib/api";
import {
  PageContainer, PageHeader, StatTile, Button, StatusBadge, EmptyState, Skeleton,
  type StatusKind,
} from "./primitives";
import { cn } from "@/lib/utils";

// 后端落库时社媒趋势统一挂在该聚合词下（daily_refresh.SOCIAL_TREND_TERM）
const SOCIAL_TREND_TERM = "🔥 实时社媒趋势";

// 平台展示元数据（顺序即展示顺序）
const PLATFORMS: { source: string; label: string; icon: React.ReactNode; accent: string }[] = [
  { source: "trend_tiktok", label: "TikTok 趋势搜索词", icon: <Music2 className="h-4 w-4" />, accent: "text-pink-500" },
  { source: "trend_douyin", label: "抖音热榜", icon: <Sparkles className="h-4 w-4" />, accent: "text-rose-500" },
  { source: "trend_weibo", label: "微博热搜", icon: <MessageCircle className="h-4 w-4" />, accent: "text-orange-500" },
  { source: "trend_xiaohongshu", label: "小红书热词", icon: <BookOpen className="h-4 w-4" />, accent: "text-red-500" },
  { source: "trend_kuaishou", label: "快手热榜", icon: <Video className="h-4 w-4" />, accent: "text-amber-500" },
  { source: "trend_bilibili", label: "B站热搜", icon: <Tv className="h-4 w-4" />, accent: "text-sky-500" },
  { source: "trend_twitter", label: "X / Twitter 趋势", icon: <Twitter className="h-4 w-4" />, accent: "text-blue-500" },
  { source: "trend_lemon8", label: "Lemon8 热词", icon: <Citrus className="h-4 w-4" />, accent: "text-lime-500" },
];

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

interface TrendItem { keyword?: string; heat?: number | null; views?: number | null; label?: string | null; }

function fmtHeat(n?: number | null): string | null {
  if (typeof n !== "number" || !isFinite(n) || n <= 0) return null;
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  return String(n);
}

export function SocialTrendsPage() {
  const [status, setStatus] = React.useState<RefreshStatus | null>(null);
  const [snapshots, setSnapshots] = React.useState<DataSnapshot[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [reloading, setReloading] = React.useState(false);

  const reload = React.useCallback(async () => {
    setReloading(true);
    try {
      const [st, snaps] = await Promise.all([
        fetchDailyRefreshStatus(),
        fetchDataSnapshots({ term: SOCIAL_TREND_TERM, limit: 50 }),
      ]);
      setStatus(st);
      setSnapshots(snaps);
    } catch { /* 静默 */ }
    finally { setLoading(false); setReloading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  // source → snapshot 映射，便于按固定平台顺序渲染
  const bySource = React.useMemo(() => {
    const m = new Map<string, DataSnapshot>();
    for (const s of snapshots) m.set(s.source, s);
    return m;
  }, [snapshots]);

  const okPlatforms = PLATFORMS.filter((p) => bySource.get(p.source)?.realData).length;
  const totalKeywords = React.useMemo(
    () => snapshots.reduce((acc, s) => acc + (Array.isArray(s.payload?.items) ? s.payload.items.length : 0), 0),
    [snapshots],
  );
  const channelOk = status?.tier2ChannelOk ?? false;
  const hasAny = snapshots.length > 0;

  return (
    <PageContainer>
      <PageHeader
        icon={<Flame className="h-5 w-5" />}
        title="社媒趋势"
        subtitle="TikTok / 抖音 / 微博 / 小红书 / 快手 / B站 / X / Lemon8 实时热搜与趋势词，每 2 小时自动刷新一次，落库作为选品与内容的风向标。"
        actions={
          <Button variant="secondary" size="sm" loading={reloading} onClick={reload}>
            <RefreshCw className="h-3.5 w-3.5" />刷新
          </Button>
        }
      />

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <div className="grid gap-3 sm:grid-cols-2">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-44 w-full" />)}
          </div>
        </div>
      ) : (
        <>
          {/* 概览 */}
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="最近更新" value={fmtTime(status?.finishedAt)} icon={<Clock className="h-4 w-4" />} />
            <StatTile label="覆盖平台" value={`${okPlatforms} / ${PLATFORMS.length}`} icon={<Layers className="h-4 w-4" />} />
            <StatTile label="热词总数" value={String(totalKeywords)} icon={<Hash className="h-4 w-4" />} />
            <StatTile
              label="趋势通道"
              value={channelOk ? "已就绪" : "未就绪"}
              tone={channelOk ? "text-success" : "text-ink-subtle"}
              icon={<Flame className="h-4 w-4" />}
            />
          </div>

          {!channelOk && (
            <div className="mb-5 rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-xs text-ink-subtle">
              社媒趋势通道（TikHub）需配置 <span className="font-medium text-ink-muted">TIKHUB_API_KEY</span>；通道未就绪时如实标注，<span className="font-medium text-ink-muted">不编造数据</span>，接入后自动补齐。
            </div>
          )}

          {!hasAny ? (
            <EmptyState
              icon={<Flame className="h-6 w-6" />}
              title="还没有社媒趋势数据"
              hint="等待每 2 小时一次的自动刷新，或在「监控与订阅」页点击「立即刷新」抓取一次真实数据。"
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {PLATFORMS.map((p) => {
                const snap = bySource.get(p.source);
                const info = statusInfo(snap?.status ?? "empty");
                const items: TrendItem[] = Array.isArray(snap?.payload?.items) ? snap!.payload.items : [];
                return (
                  <div key={p.source} className="rounded-2xl border border-hairline bg-white p-4">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-2 text-sm font-semibold text-ink">
                        <span className={p.accent}>{p.icon}</span>{p.label}
                        {items.length > 0 && (
                          <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] font-normal text-ink-subtle">
                            {items.length} 词
                          </span>
                        )}
                      </span>
                      <StatusBadge status={info.kind} label={info.label} />
                    </div>
                    {snap?.realData && items.length > 0 ? (
                      <ol className="space-y-1.5">
                        {items.slice(0, 15).map((it, i) => {
                          const heat = fmtHeat(it.heat) ?? fmtHeat(it.views);
                          return (
                            <li key={i} className="flex items-center gap-2.5 rounded-lg bg-surface-1 px-2.5 py-1.5">
                              <span className={cn(
                                "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-[11px] font-semibold",
                                i < 3 ? "bg-brand/15 text-brand" : "bg-surface-2 text-ink-subtle"
                              )}>
                                {i + 1}
                              </span>
                              <span className="min-w-0 flex-1 truncate text-xs text-ink">{it.keyword}</span>
                              {heat && (
                                <span className="inline-flex flex-shrink-0 items-center gap-0.5 text-[10px] text-ink-subtle">
                                  <Flame className="h-2.5 w-2.5 text-orange-400" />{heat}
                                </span>
                              )}
                            </li>
                          );
                        })}
                      </ol>
                    ) : (
                      <div className="rounded-lg bg-surface-1 px-3 py-6 text-center text-xs text-ink-subtle">
                        {snap?.summary || "暂无数据"}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </PageContainer>
  );
}
