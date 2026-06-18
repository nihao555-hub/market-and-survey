"use client";
import React from "react";
import { BellRing, Plus, TrendingUp, Tag, Swords, X, Trash2 } from "lucide-react";
import { fetchMonitors, createMonitor, setMonitorEnabled, deleteMonitor, type Monitor } from "@/lib/api";
import {
  PageContainer, PageHeader, Panel, EmptyState, Button, Switch, Skeleton,
} from "./primitives";

const ICONS: Record<string, React.ReactNode> = {
  trend: <TrendingUp className="h-4 w-4" />,
  competitor: <Swords className="h-4 w-4" />,
  price: <Tag className="h-4 w-4" />,
};
const iconFor = (kind: string) => ICONS[kind] ?? <BellRing className="h-4 w-4" />;

const KINDS: { value: string; label: string }[] = [
  { value: "trend", label: "趋势" },
  { value: "competitor", label: "竞品" },
  { value: "price", label: "价格" },
];
const CADENCES = ["实时", "每日", "每周"];

export function MonitorPage() {
  const [rules, setRules] = React.useState<Monitor[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [adding, setAdding] = React.useState(false);
  const [name, setName] = React.useState("");
  const [desc, setDesc] = React.useState("");
  const [kind, setKind] = React.useState("trend");
  const [cadence, setCadence] = React.useState("每日");
  const [saving, setSaving] = React.useState(false);

  const reload = React.useCallback(async () => {
    try { setRules(await fetchMonitors()); }
    catch { /* 静默 */ }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  const toggle = async (r: Monitor) => {
    setRules((prev) => prev.map((x) => (x.id === r.id ? { ...x, enabled: !x.enabled } : x)));
    try { await setMonitorEnabled(r.id, !r.enabled); } catch { reload(); }
  };
  const remove = async (id: string) => {
    setRules((prev) => prev.filter((x) => x.id !== id));
    try { await deleteMonitor(id); } catch { reload(); }
  };
  const submit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const created = await createMonitor({ name: name.trim(), description: desc.trim(), kind, cadence });
      setRules((prev) => [...prev, created]);
      setName(""); setDesc(""); setKind("trend"); setCadence("每日"); setAdding(false);
    } catch { /* 静默 */ }
    finally { setSaving(false); }
  };

  const activeCount = rules.filter((r) => r.enabled).length;

  return (
    <PageContainer>
      <PageHeader
        icon={<BellRing className="h-5 w-5" />}
        title="监控与订阅"
        subtitle="为关键品类、竞品与价格设置自动监控规则，变化发生时第一时间收到提醒。"
        actions={<Button onClick={() => setAdding((v) => !v)}><Plus className="h-4 w-4" />新建监控</Button>}
      />

      {adding && (
        <div className="mb-4 rounded-2xl border border-hairline bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-semibold text-ink">新建监控规则</span>
            <button onClick={() => setAdding(false)} className="rounded p-1 text-ink-subtle hover:bg-surface-1 hover:text-ink">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="space-y-3">
            <input
              value={name} onChange={(e) => setName(e.target.value)} placeholder="规则名称，如 充电宝价格监控"
              className="w-full rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
            />
            <input
              value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="触发条件描述"
              className="w-full rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
            />
            <div className="grid grid-cols-2 gap-3">
              <select value={kind} onChange={(e) => setKind(e.target.value)}
                className="rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40">
                {KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
              </select>
              <select value={cadence} onChange={(e) => setCadence(e.target.value)}
                className="rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40">
                {CADENCES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setAdding(false)}>取消</Button>
            <Button size="sm" loading={saving} onClick={submit}>创建</Button>
          </div>
        </div>
      )}

      <Panel title={`监控规则 · ${activeCount} 条生效`} bodyClassName="p-0">
        {loading ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : rules.length === 0 ? (
          <EmptyState
            icon={<BellRing className="h-6 w-6" />}
            title="还没有监控规则"
            hint="新建一条规则，Agent 会按设定的频率自动巡检并在触发条件时提醒你。"
          />
        ) : (
          <div className="divide-y divide-hairline">
            {rules.map((r) => (
              <div key={r.id} className="group flex items-center gap-4 px-5 py-4">
                <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand/10 text-brand">
                  {iconFor(r.kind)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-ink">{r.name}</span>
                    <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-subtle">{r.cadence}</span>
                  </div>
                  <div className="mt-0.5 truncate text-xs text-ink-subtle">{r.description}</div>
                </div>
                <button
                  onClick={() => remove(r.id)}
                  title="删除规则"
                  className="rounded p-1.5 text-ink-subtle opacity-0 transition-opacity hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <Switch checked={r.enabled} onChange={() => toggle(r)} />
              </div>
            ))}
          </div>
        )}
      </Panel>
    </PageContainer>
  );
}
