"use client";
import React from "react";
import {
  Database, TrendingUp, ShoppingCart, Search, Globe, Share2,
  CheckCircle2, Plus, Tag, Boxes, X,
} from "lucide-react";
import { fetchDataSources, createDataSource, setDataSourceConnected, type DataSource } from "@/lib/api";
import {
  PageContainer, PageHeader, StatTile, Button, Skeleton, StatusBadge,
} from "./primitives";

const ICONS: Record<string, React.ReactNode> = {
  trends: <TrendingUp className="h-5 w-5" />,
  amazon: <ShoppingCart className="h-5 w-5" />,
  social: <Share2 className="h-5 w-5" />,
  price: <Tag className="h-5 w-5" />,
  sourcing: <Boxes className="h-5 w-5" />,
  keyword: <Search className="h-5 w-5" />,
  web: <Globe className="h-5 w-5" />,
};
const iconFor = (kind: string) => ICONS[kind] ?? <Database className="h-5 w-5" />;

const FREQS = ["实时", "每日", "每周"];

export function DataSourcesPage() {
  const [sources, setSources] = React.useState<DataSource[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [adding, setAdding] = React.useState(false);
  const [name, setName] = React.useState("");
  const [desc, setDesc] = React.useState("");
  const [freq, setFreq] = React.useState("每日");
  const [saving, setSaving] = React.useState(false);

  const reload = React.useCallback(async () => {
    try { setSources(await fetchDataSources()); }
    catch { /* 静默 */ }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  const toggle = async (s: DataSource) => {
    setSources((prev) => prev.map((x) => (x.id === s.id ? { ...x, connected: !x.connected } : x)));
    try { await setDataSourceConnected(s.id, !s.connected); } catch { reload(); }
  };

  const submit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const created = await createDataSource({ name: name.trim(), description: desc.trim(), frequency: freq });
      setSources((prev) => [...prev, created]);
      setName(""); setDesc(""); setFreq("每日"); setAdding(false);
    } catch { /* 静默 */ }
    finally { setSaving(false); }
  };

  const connected = sources.filter((s) => s.connected).length;
  const realtime = sources.filter((s) => s.frequency === "实时").length;

  return (
    <PageContainer>
      <PageHeader
        icon={<Database className="h-5 w-5" />}
        title="数据源管理"
        subtitle="调研所依赖的外部数据源与连接状态。Agent 仅基于真实抓取数据分析，绝不编造。"
        actions={<Button onClick={() => setAdding((v) => !v)}><Plus className="h-4 w-4" />接入数据源</Button>}
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile label="已接入" value={`${connected} / ${sources.length}`} icon={<Database className="h-4 w-4" />} tone="text-brand" />
        <StatTile label="实时数据源" value={`${realtime}`} delta="低延迟" icon={<TrendingUp className="h-4 w-4" />} tone="text-success" />
        <StatTile label="数据可信度" value="A 级" delta="真实抓取池" icon={<CheckCircle2 className="h-4 w-4" />} tone="text-info" />
      </div>

      {adding && (
        <div className="mb-4 rounded-2xl border border-hairline bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-semibold text-ink">接入新的数据源</span>
            <button onClick={() => setAdding(false)} className="rounded p-1 text-ink-subtle hover:bg-surface-1 hover:text-ink">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto]">
            <input
              value={name} onChange={(e) => setName(e.target.value)} placeholder="名称，如 eBay Sold Listings"
              className="rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
            />
            <input
              value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="描述，如 成交价与销量"
              className="rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
            />
            <select
              value={freq} onChange={(e) => setFreq(e.target.value)}
              className="rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40"
            >
              {FREQS.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setAdding(false)}>取消</Button>
            <Button size="sm" loading={saving} onClick={submit}>添加</Button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full rounded-2xl" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {sources.map((s) => (
            <div key={s.id} className="flex items-center gap-4 rounded-2xl border border-hairline bg-white p-4">
              <span className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
                {iconFor(s.kind)}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-ink">{s.name}</span>
                  <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-subtle">{s.frequency}</span>
                </div>
                <div className="mt-0.5 truncate text-xs text-ink-subtle">{s.description}</div>
              </div>
              {s.connected ? (
                <button onClick={() => toggle(s)} className="group inline-flex" title="点击断开">
                  <StatusBadge status="done" label="已连接" />
                </button>
              ) : (
                <Button variant="outline" size="sm" onClick={() => toggle(s)}>
                  <Plus className="h-3.5 w-3.5" />连接
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
