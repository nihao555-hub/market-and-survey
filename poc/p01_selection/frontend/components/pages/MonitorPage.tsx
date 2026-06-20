"use client";
import React from "react";
import { CreditCard, Crown, Zap, Check, ArrowUpRight } from "lucide-react";
import { PageContainer, PageHeader, Panel, Button } from "./primitives";

const PLANS = [
  {
    id: "free",
    name: "免费版",
    price: "¥0",
    period: "/月",
    features: ["5 次 AI 调研/月", "1 个品类数据", "基础报告导出", "社区支持"],
    highlight: false,
  },
  {
    id: "pro",
    name: "专业版",
    price: "¥99",
    period: "/月",
    features: [
      "100 次 AI 调研/月",
      "10 个品类数据",
      "ECharts 交互式图表",
      "26 国市场数据",
      "优先数据刷新",
      "邮件通知",
    ],
    highlight: true,
  },
  {
    id: "enterprise",
    name: "企业版",
    price: "¥299",
    period: "/月",
    features: [
      "无限 AI 调研",
      "全部品类数据",
      "API 接入",
      "多人协作",
      "专属客服",
      "自定义报告模板",
      "数据导出 (CSV/Excel)",
    ],
    highlight: false,
  },
];

export function MonitorPage() {
  const [currentPlan, setCurrentPlan] = React.useState("free");

  React.useEffect(() => {
    const plan = typeof window !== "undefined" ? localStorage.getItem("user_plan") || "free" : "free";
    setCurrentPlan(plan);
  }, []);

  return (
    <PageContainer>
      <PageHeader
        icon={<CreditCard className="h-5 w-5" />}
        title="订阅管理"
        subtitle="管理你的订阅计划，升级解锁更多 AI 调研次数和高级功能。"
      />

      {/* Current plan status */}
      <Panel title="当前订阅" bodyClassName="p-5">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/10">
            {currentPlan === "free" ? (
              <Zap className="h-6 w-6 text-brand" />
            ) : (
              <Crown className="h-6 w-6 text-amber-500" />
            )}
          </div>
          <div>
            <div className="text-base font-semibold text-ink">
              {currentPlan === "free" ? "免费版" : currentPlan === "pro" ? "专业版" : "企业版"}
            </div>
            <div className="text-sm text-ink-subtle">
              {currentPlan === "free"
                ? "每月 5 次 AI 调研，升级解锁更多功能"
                : currentPlan === "pro"
                  ? "每月 100 次 AI 调研 · 26 国数据 · ECharts 图表"
                  : "无限调研 · API 接入 · 多人协作"}
            </div>
          </div>
        </div>
      </Panel>

      {/* Plan cards */}
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {PLANS.map((plan) => (
          <div
            key={plan.id}
            className={`rounded-2xl border p-6 transition-all ${
              plan.highlight
                ? "border-brand bg-brand/5 shadow-md shadow-brand/10"
                : "border-hairline bg-white"
            } ${currentPlan === plan.id ? "ring-2 ring-brand/30" : ""}`}
          >
            <div className="mb-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-ink">{plan.name}</span>
                {currentPlan === plan.id && (
                  <span className="rounded-full bg-brand/10 px-2 py-0.5 text-[10px] font-medium text-brand">
                    当前
                  </span>
                )}
                {plan.highlight && currentPlan !== plan.id && (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                    推荐
                  </span>
                )}
              </div>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="text-3xl font-bold text-ink">{plan.price}</span>
                <span className="text-sm text-ink-subtle">{plan.period}</span>
              </div>
            </div>

            <ul className="mb-6 space-y-2">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-ink-subtle">
                  <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-500" />
                  {f}
                </li>
              ))}
            </ul>

            {currentPlan === plan.id ? (
              <Button variant="secondary" className="w-full" disabled>
                当前计划
              </Button>
            ) : (
              <Button
                className="w-full"
                variant={plan.highlight ? "primary" : "secondary"}
                onClick={() => {
                  window.open("https://market-survey-nu.vercel.app/#pricing", "_blank");
                }}
              >
                {plan.id === "free" ? "降级" : "升级"}
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        ))}
      </div>

      {/* Usage info */}
      <Panel title="使用量统计" bodyClassName="p-5" className="mt-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <UsageStat
            label="本月 AI 调研"
            used={0}
            total={currentPlan === "free" ? 5 : currentPlan === "pro" ? 100 : -1}
          />
          <UsageStat
            label="品类数据"
            used={1}
            total={currentPlan === "free" ? 1 : currentPlan === "pro" ? 10 : -1}
          />
          <UsageStat
            label="报告导出"
            used={0}
            total={currentPlan === "free" ? 3 : -1}
          />
        </div>
      </Panel>
    </PageContainer>
  );
}

function UsageStat({ label, used, total }: { label: string; used: number; total: number }) {
  const isUnlimited = total === -1;
  const pct = isUnlimited ? 0 : total > 0 ? Math.min((used / total) * 100, 100) : 0;
  return (
    <div className="rounded-xl border border-hairline bg-surface-1 p-4">
      <div className="text-xs text-ink-subtle">{label}</div>
      <div className="mt-1 text-lg font-semibold text-ink">
        {used} / {isUnlimited ? "∞" : total}
      </div>
      {!isUnlimited && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div
            className={`h-full rounded-full transition-all ${pct > 80 ? "bg-amber-500" : "bg-brand"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
