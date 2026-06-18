"use client";
import React from "react";
import { useAtom } from "jotai";
import { Settings, Zap, Gauge, ShieldCheck, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { quickParamsAtom } from "@/lib/atoms";
import { fetchSettings, updateSettings, type Settings as TSettings } from "@/lib/api";
import {
  PageContainer, PageHeader, Panel, Button, Switch, Skeleton,
} from "./primitives";

const MARKETS = ["US", "GB", "DE", "JP", "FR", "CA", "AU"];
const MARKET_NAMES: Record<string, string> = {
  US: "美国", GB: "英国", DE: "德国", JP: "日本", FR: "法国", CA: "加拿大", AU: "澳大利亚",
};
const POSITIONINGS = ["低价", "中端", "高端"];

function Row({ title, desc, children }: { title: string; desc?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5">
      <div className="min-w-0">
        <div className="text-sm font-medium text-ink">{title}</div>
        {desc && <div className="mt-0.5 text-xs text-ink-subtle">{desc}</div>}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

export function SettingsPage() {
  const [params, setParams] = useAtom(quickParamsAtom);
  const [settings, setSettings] = React.useState<TSettings | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [editing, setEditing] = React.useState(false);
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [savedFlash, setSavedFlash] = React.useState(false);

  React.useEffect(() => {
    (async () => {
      try {
        const s = await fetchSettings();
        setSettings(s);
        setName(s.displayName);
        setEmail(s.email);
      } catch { /* 静默 */ }
      finally { setLoading(false); }
    })();
  }, []);

  const patch = async (p: Partial<TSettings>) => {
    setSettings((prev) => (prev ? { ...prev, ...p } : prev));
    try {
      const next = await updateSettings(p);
      setSettings(next);
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 1200);
    } catch { /* 静默 */ }
  };

  const saveProfile = async () => {
    await patch({ displayName: name.trim(), email: email.trim() });
    setEditing(false);
  };

  const setModel = (m: "flash" | "pro") => {
    setParams((prev) => ({ ...prev, modelChoice: m }));
    patch({ defaultModel: m });
  };
  const setMarket = (mk: string) => {
    setParams((prev) => ({ ...prev, markets: [mk] }));
    patch({ defaultMarket: mk });
  };
  const setPositioning = (p: string) => {
    setParams((prev) => ({ ...prev, positioning: p }));
    patch({ defaultPositioning: p });
  };

  const model = (settings?.defaultModel as "flash" | "pro") || params.modelChoice || "flash";
  const market = settings?.defaultMarket || params.markets[0] || "US";
  const positioning = settings?.defaultPositioning || params.positioning || "中端";
  const initial = (settings?.displayName || "产")[0];

  return (
    <PageContainer>
      <PageHeader
        icon={<Settings className="h-5 w-5" />}
        title="设置"
        subtitle="管理账户信息、默认调研偏好、通知与数据真实性策略。"
        actions={savedFlash ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-success">
            <Check className="h-3.5 w-3.5" />已保存
          </span>
        ) : undefined}
      />

      {loading ? (
        <div className="space-y-4">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-32 w-full rounded-2xl" />)}
        </div>
      ) : (
        <div className="space-y-4">
          <Panel title="账户">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand to-brand2 text-base font-semibold text-white">
                {initial}
              </div>
              {editing ? (
                <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row">
                  <input
                    value={name} onChange={(e) => setName(e.target.value)} placeholder="昵称"
                    className="rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
                  />
                  <input
                    value={email} onChange={(e) => setEmail(e.target.value)} placeholder="邮箱"
                    className="flex-1 rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
                  />
                </div>
              ) : (
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-semibold text-ink">{settings?.displayName}</div>
                  <div className="text-xs text-ink-subtle">{settings?.email} · {settings?.plan}</div>
                </div>
              )}
              {editing ? (
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => { setEditing(false); setName(settings?.displayName || ""); setEmail(settings?.email || ""); }}>取消</Button>
                  <Button size="sm" onClick={saveProfile}>保存</Button>
                </div>
              ) : (
                <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>编辑资料</Button>
              )}
            </div>
          </Panel>

          <Panel title="默认调研偏好" bodyClassName="px-5 py-1">
            <div className="divide-y divide-hairline">
              <Row title="默认分析模型" desc="Flash 更快，Pro 推理更深、用于最终报告">
                <div className="flex items-center gap-1 rounded-lg bg-surface-1 p-1">
                  {(["flash", "pro"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setModel(m)}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                        model === m ? "bg-white text-brand shadow-sm" : "text-ink-subtle hover:text-ink"
                      )}
                    >
                      {m === "flash" ? <Zap className="h-3.5 w-3.5" /> : <Gauge className="h-3.5 w-3.5" />}
                      {m === "flash" ? "Flash 快档" : "Pro 深推档"}
                    </button>
                  ))}
                </div>
              </Row>
              <Row title="默认目标市场" desc="新建任务时预选的市场">
                <select
                  value={market} onChange={(e) => setMarket(e.target.value)}
                  className="rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 text-xs text-ink-muted outline-none focus:border-brand/40"
                >
                  {MARKETS.map((mk) => <option key={mk} value={mk}>{mk} · {MARKET_NAMES[mk]}</option>)}
                </select>
              </Row>
              <Row title="默认产品定位" desc="影响成本与利润测算基准">
                <select
                  value={positioning} onChange={(e) => setPositioning(e.target.value)}
                  className="rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 text-xs text-ink-muted outline-none focus:border-brand/40"
                >
                  {POSITIONINGS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </Row>
            </div>
          </Panel>

          <Panel title="通知" bodyClassName="px-5 py-1">
            <div className="divide-y divide-hairline">
              <Row title="邮件通知" desc="监控触发与报告完成时发送邮件">
                <Switch checked={!!settings?.notifyEmail} onChange={(v) => patch({ notifyEmail: v })} />
              </Row>
              <Row title="站内通知" desc="在应用内显示提醒与动态">
                <Switch checked={!!settings?.notifyInApp} onChange={(v) => patch({ notifyInApp: v })} />
              </Row>
            </div>
          </Panel>

          <Panel title="数据真实性">
            <div className="flex items-start gap-3 rounded-xl bg-success/5 p-3">
              <ShieldCheck className="mt-0.5 h-5 w-5 flex-shrink-0 text-success" />
              <div className="text-xs leading-relaxed text-ink-muted">
                已启用<span className="font-medium text-ink">「零幻觉铁律」</span>：候选品的 ASIN / 价格 / 销量必须来自真实抓取数据并通过校验，
                成本来自 1688 实价，无法获取的数据会被诚实标注而非编造。该策略为强制开启，保障调研结论可追溯。
              </div>
            </div>
          </Panel>
        </div>
      )}
    </PageContainer>
  );
}
