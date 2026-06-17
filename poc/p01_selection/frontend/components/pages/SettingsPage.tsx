"use client";
import React from "react";
import { useAtom } from "jotai";
import { Settings, Zap, Gauge, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { quickParamsAtom } from "@/lib/atoms";
import { PageContainer, PageHeader, Panel } from "./primitives";

function Row({
  title,
  desc,
  children,
}: {
  title: string;
  desc?: string;
  children: React.ReactNode;
}) {
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
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  const model = mounted ? params.modelChoice : "flash";

  return (
    <PageContainer>
      <PageHeader
        icon={<Settings className="h-5 w-5" />}
        title="设置"
        subtitle="管理账户信息、默认调研偏好与数据真实性策略。"
      />

      <div className="space-y-4">
        <Panel title="账户">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-brand to-brand2 text-base font-semibold text-white">
              产
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold text-ink">产品经理</div>
              <div className="text-xs text-ink-subtle">pm@marketagent.ai · 专业版 Pro</div>
            </div>
            <button className="rounded-lg border border-hairline px-3 py-1.5 text-xs font-medium text-ink-muted transition-colors hover:bg-surface-1 hover:text-ink">
              编辑资料
            </button>
          </div>
        </Panel>

        <Panel title="默认调研偏好" bodyClassName="px-5 py-1">
          <div className="divide-y divide-hairline">
            <Row title="默认分析模型" desc="Flash 更快，Pro 推理更深、用于最终报告">
              <div className="flex items-center gap-1 rounded-lg bg-surface-1 p-1">
                {(["flash", "pro"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setParams((p) => ({ ...p, modelChoice: m }))}
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
              <span className="rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 text-xs text-ink-muted">
                {mounted ? (params.markets[0] || "US") : "US"} · 美国
              </span>
            </Row>
            <Row title="默认产品定位" desc="影响成本与利润测算基准">
              <span className="rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 text-xs text-ink-muted">
                {mounted ? params.positioning : "中端"}
              </span>
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
    </PageContainer>
  );
}
