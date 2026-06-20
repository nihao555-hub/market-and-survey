"use client";
import React from "react";
import { useAtom } from "jotai";
import { Settings, Zap, Gauge, ShieldCheck, Check, Globe, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { quickParamsAtom } from "@/lib/atoms";
import { fetchSettings, updateSettings, type Settings as TSettings } from "@/lib/api";
import {
  PageContainer, PageHeader, Panel, Button, Switch, Skeleton,
} from "./primitives";

const MARKETS = ["US", "GB", "DE", "JP", "FR", "CA", "AU"];
const ALL_COUNTRIES = [
  "US", "GB", "DE", "JP", "FR", "CA", "AU",
  "KR", "SG", "MY", "TH", "VN", "ID", "PH",
  "BR", "MX", "IT", "ES", "NL", "SE", "PL",
  "SA", "AE", "TR", "IN", "TW",
];
const COUNTRY_NAMES: Record<string, string> = {
  US: "美国", GB: "英国", DE: "德国", JP: "日本", FR: "法国", CA: "加拿大", AU: "澳大利亚",
  KR: "韩国", SG: "新加坡", MY: "马来西亚", TH: "泰国", VN: "越南", ID: "印尼", PH: "菲律宾",
  BR: "巴西", MX: "墨西哥", IT: "意大利", ES: "西班牙", NL: "荷兰", SE: "瑞典", PL: "波兰",
  SA: "沙特", AE: "阿联酋", TR: "土耳其", IN: "印度", TW: "中国台湾",
};
const MARKET_NAMES = COUNTRY_NAMES;
const POSITIONINGS = ["低价", "中端", "高端"];

const REFRESH_HOURS = [
  { utc: 16, label: "北京 0:00（UTC 16:00）" },
  { utc: 0, label: "北京 8:00（UTC 0:00）" },
  { utc: 4, label: "北京 12:00（UTC 4:00）" },
  { utc: 8, label: "北京 16:00（UTC 8:00）" },
  { utc: 12, label: "北京 20:00（UTC 12:00）" },
];

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
  const toggleCountry = (code: string) => {
    const current = settings?.targetCountries ?? ["US"];
    const next = current.includes(code)
      ? current.filter((c) => c !== code)
      : [...current, code];
    if (next.length === 0) return;
    patch({ targetCountries: next });
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

          <Panel title="数据采集设置" bodyClassName="px-5 py-1">
            <div className="divide-y divide-hairline">
              <div className="py-3.5">
                <div className="mb-2 flex items-center gap-2">
                  <Globe className="h-4 w-4 text-brand" />
                  <div>
                    <div className="text-sm font-medium text-ink">目标国家（多选）</div>
                    <div className="mt-0.5 text-xs text-ink-subtle">每日自动刷新时会对每个勾选的国家采集热销榜、品类榜单、话题趋势等数据</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {ALL_COUNTRIES.map((code) => {
                    const selected = (settings?.targetCountries ?? ["US"]).includes(code);
                    return (
                      <button
                        key={code}
                        onClick={() => toggleCountry(code)}
                        className={cn(
                          "rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all",
                          selected
                            ? "border-brand bg-brand/10 text-brand shadow-sm"
                            : "border-hairline bg-surface-1 text-ink-subtle hover:border-brand/30 hover:text-ink"
                        )}
                      >
                        {code} · {COUNTRY_NAMES[code] || code}
                      </button>
                    );
                  })}
                </div>
              </div>
              <Row title="定时刷新时间" desc="每天自动触发数据刷新的时间（每 2 小时一次，包含此时刻）">
                <div className="flex items-center gap-2">
                  <Clock className="h-3.5 w-3.5 text-ink-subtle" />
                  <select
                    value={settings?.refreshHourUtc ?? 16}
                    onChange={(e) => patch({ refreshHourUtc: Number(e.target.value) })}
                    className="rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 text-xs text-ink-muted outline-none focus:border-brand/40"
                  >
                    {REFRESH_HOURS.map((h) => (
                      <option key={h.utc} value={h.utc}>{h.label}</option>
                    ))}
                  </select>
                </div>
              </Row>
            </div>
          </Panel>

          <Panel title="通知" bodyClassName="px-5 py-1">
            <div className="divide-y divide-hairline">
              <Row title="邮件通知" desc="订阅提醒与报告完成时发送邮件">
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
                已启用<span className="font-medium text-ink">「零幻觉铁律」</span>：候选品的 ASIN / 价格 / 销量必须来自真实获取数据并通过校验，
                成本来自 1688 实价，无法获取的数据会被诚实标注而非编造。该策略为强制开启，保障调研结论可追溯。
              </div>
            </div>
          </Panel>
        </div>
      )}
    </PageContainer>
  );
}
