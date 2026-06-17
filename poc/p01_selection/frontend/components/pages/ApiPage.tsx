"use client";
import React from "react";
import { Plug, Copy, Check } from "lucide-react";
import { PageContainer, PageHeader, Panel, StatTile } from "./primitives";

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
  const [copied, setCopied] = React.useState(false);
  const token = "msk_live_••••••••••••••••6e5da";

  const copy = () => {
    navigator.clipboard?.writeText(token).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <PageContainer>
      <PageHeader
        icon={<Plug className="h-5 w-5" />}
        title="API 接入"
        subtitle="通过 API 将选品调研能力嵌入你自己的系统。所有请求需携带租户 API Key。"
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile label="本月调用" value="1,284" delta="额度 68%" icon={<Plug className="h-4 w-4" />} tone="text-brand" />
        <StatTile label="平均时延" value="2.1s" icon={<Plug className="h-4 w-4" />} tone="text-success" />
        <StatTile label="成功率" value="99.4%" icon={<Check className="h-4 w-4" />} tone="text-info" />
      </div>

      <Panel title="API Key" className="mb-4">
        <div className="flex items-center gap-2 rounded-lg border border-hairline bg-surface-1 px-3 py-2.5">
          <code className="flex-1 truncate font-mono text-sm text-ink">{token}</code>
          <button
            onClick={copy}
            className="inline-flex items-center gap-1 rounded-md border border-hairline bg-white px-2 py-1 text-xs text-ink-muted transition-colors hover:text-ink"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "已复制" : "复制"}
          </button>
        </div>
        <p className="mt-2 text-xs text-ink-subtle">
          请妥善保管 Key，请勿提交到代码仓库或暴露在前端。通过请求头 <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[11px]">X-API-Key</code> 传递。
        </p>
      </Panel>

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
