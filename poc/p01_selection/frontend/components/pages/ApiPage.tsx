"use client";
import React from "react";
import { Plug, Copy, Check, Plus, KeyRound, Trash2, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchApiKeys, createApiKey, revokeApiKey, type ApiKey } from "@/lib/api";
import { formatDate } from "@/lib/thread-format";
import {
  PageContainer, PageHeader, Panel, StatTile, Button, Skeleton, StatusBadge,
} from "./primitives";

const ENDPOINTS: { method: string; path: string; desc: string }[] = [
  { method: "POST", path: "/selection/start", desc: "发起一次结构化选品调研任务" },
  { method: "POST", path: "/chat", desc: "对话式调研（自然语言入口）" },
  { method: "GET", path: "/events", desc: "SSE 实时事件流（思考 / 工具 / 报告）" },
  { method: "POST", path: "/graphql", desc: "查询任务、线程与历史消息" },
];

function MethodBadge({ method }: { method: string }) {
  const tone = method === "GET" ? "bg-info/10 text-info" : "bg-success/10 text-success";
  return <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${tone}`}>{method}</span>;
}

export function ApiPage() {
  const [keys, setKeys] = React.useState<ApiKey[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [creating, setCreating] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [freshToken, setFreshToken] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);

  const reload = React.useCallback(async () => {
    try { setKeys(await fetchApiKeys()); }
    catch { /* 静默 */ }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { reload(); }, [reload]);

  const submit = async () => {
    if (!newName.trim()) return;
    setSaving(true);
    try {
      const { key, token } = await createApiKey(newName.trim());
      setKeys((prev) => [key, ...prev]);
      setFreshToken(token);
      setNewName(""); setCreating(false);
    } catch { /* 静默 */ }
    finally { setSaving(false); }
  };

  const revoke = async (id: string) => {
    setKeys((prev) => prev.map((k) => (k.id === id ? { ...k, revoked: true } : k)));
    try { await revokeApiKey(id); } catch { reload(); }
  };

  const copy = (text: string) => {
    navigator.clipboard?.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const activeKeys = keys.filter((k) => !k.revoked).length;

  return (
    <PageContainer>
      <PageHeader
        icon={<Plug className="h-5 w-5" />}
        title="API 接入"
        subtitle="通过 API 将选品调研能力嵌入你自己的系统。所有请求需携带租户 API Key。"
        actions={<Button onClick={() => setCreating((v) => !v)}><Plus className="h-4 w-4" />创建 API Key</Button>}
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile label="有效 Key" value={`${activeKeys}`} icon={<KeyRound className="h-4 w-4" />} tone="text-brand" />
        <StatTile label="平均时延" value="2.1s" icon={<Plug className="h-4 w-4" />} tone="text-success" />
        <StatTile label="成功率" value="99.4%" icon={<Check className="h-4 w-4" />} tone="text-info" />
      </div>

      {freshToken && (
        <div className="mb-4 rounded-2xl border border-warning/30 bg-warning/5 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
            <AlertTriangle className="h-4 w-4 text-warning" />
            请立即复制并妥善保管，该明文 Key 只显示这一次
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-hairline bg-white px-3 py-2.5">
            <code className="flex-1 truncate font-mono text-sm text-ink">{freshToken}</code>
            <button onClick={() => copy(freshToken)} className="inline-flex items-center gap-1 rounded-md border border-hairline bg-white px-2 py-1 text-xs text-ink-muted transition-colors hover:text-ink">
              {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "已复制" : "复制"}
            </button>
            <button onClick={() => setFreshToken(null)} className="rounded p-1 text-ink-subtle hover:bg-surface-1 hover:text-ink">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {creating && (
        <div className="mb-4 rounded-2xl border border-hairline bg-white p-4">
          <div className="flex items-center gap-3">
            <input
              value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Key 名称，如 生产环境 / CI 脚本"
              className="flex-1 rounded-lg border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
            />
            <Button variant="secondary" size="sm" onClick={() => setCreating(false)}>取消</Button>
            <Button size="sm" loading={saving} onClick={submit}>生成</Button>
          </div>
        </div>
      )}

      <Panel title="API Key" className="mb-4" bodyClassName="p-0">
        {loading ? (
          <div className="space-y-2 p-5">
            {[0, 1].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : keys.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-ink-subtle">还没有 API Key，点击右上角创建第一个。</div>
        ) : (
          <div className="divide-y divide-hairline">
            {keys.map((k) => (
              <div key={k.id} className={cn("flex items-center gap-4 px-5 py-3.5", k.revoked && "opacity-50")}>
                <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand/10 text-brand">
                  <KeyRound className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-ink">{k.name}</div>
                  <code className="font-mono text-xs text-ink-subtle">{k.prefix}…{k.last4}</code>
                  <span className="ml-2 text-[11px] text-ink-tertiary">创建于 {formatDate(k.createdAt ?? undefined)}</span>
                </div>
                {k.revoked ? (
                  <StatusBadge status="error" label="已吊销" />
                ) : (
                  <>
                    <StatusBadge status="done" label="生效中" />
                    <Button variant="ghost" size="sm" onClick={() => revoke(k.id)} className="text-danger hover:bg-danger/10 hover:text-danger">
                      <Trash2 className="h-3.5 w-3.5" />吊销
                    </Button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>

      <p className="mb-4 text-xs text-ink-subtle">
        请妥善保管 Key，请勿提交到代码仓库或暴露在前端。通过请求头 <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[11px]">X-API-Key</code> 传递。
      </p>

      <Panel title="接口端点" bodyClassName="p-0">
        <div className="divide-y divide-hairline">
          {ENDPOINTS.map((e) => (
            <div key={e.path} className="flex items-center gap-3 px-5 py-3.5">
              <MethodBadge method={e.method} />
              <code className="font-mono text-sm text-ink">{e.path}</code>
              <span className="ml-auto text-xs text-ink-subtle">{e.desc}</span>
            </div>
          ))}
        </div>
      </Panel>
    </PageContainer>
  );
}
