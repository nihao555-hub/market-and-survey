"use client";
import React from "react";
import { Check, ArrowRight, Sparkles } from "lucide-react";
import { useAtom } from "jotai";
import { quickParamsAtom } from "@/lib/atoms";
import { marketLabel, marketIso } from "@/lib/markets";
import { Flag } from "@/components/ui/Flag";
import type { SelectionParams, ResearchKind } from "@/lib/agent-types";

/**
 * A2UI 澄清表单 —— 只负责"需要用户填写"的自由文本参数（月度预算 / 排除大牌）。
 * 可选择类参数（市场 / 定位 / 模型）已在输入框底部用 chip 选过，这里只读展示，不重复让用户操作。
 * 提交后整卡折叠为只读摘要，并回调 onSubmit 触发真正的调研任务。
 */
export function ClarifyForm({
  category,
  kind = "general",
  onSubmit,
}: {
  category: string;
  kind?: ResearchKind;
  onSubmit: (params: SelectionParams) => void;
}) {
  const [quick] = useAtom(quickParamsAtom);
  const markets = quick.markets.length ? quick.markets : ["US"];
  const positioning = quick.positioning || "中端";
  const modelChoice = quick.modelChoice || "flash";

  const [submitted, setSubmitted] = React.useState(false);
  const [budget, setBudget] = React.useState("");
  const [exclude, setExclude] = React.useState("");

  const submit = () => {
    setSubmitted(true);
    onSubmit({
      category,
      markets,
      positioning,
      monthlyBudget: budget.trim(),
      exclude: exclude.trim(),
      modelChoice,
      kind,
    });
  };

  // 提交后：只读摘要条
  if (submitted) {
    return (
      <div className="animate-fade-in-up rounded-xl border border-[var(--gray-5)] bg-[var(--gray-3)] px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-[var(--gray-8)]">
          <Check className="h-4 w-4 text-success" />
          <span className="font-medium text-[var(--gray-12)]">调研参数已确认</span>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-[var(--gray-9)]">
          <SummaryChip>{category}</SummaryChip>
          <span className="inline-flex items-center gap-1 rounded-md bg-[var(--gray-4)] px-2 py-0.5 text-[var(--gray-8)]">
            {markets.map((c) => (
              <Flag key={c} iso={marketIso(c)} size={13} />
            ))}
            {markets.map(marketLabel).join(" / ")}
          </span>
          <SummaryChip>{positioning}</SummaryChip>
          {budget && <SummaryChip>预算 {budget}</SummaryChip>}
          {exclude && <SummaryChip>排除 {exclude}</SummaryChip>}
          <SummaryChip>{modelChoice === "pro" ? "Pro 高质量" : "Flash 快速"}</SummaryChip>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in-up rounded-xl border border-[var(--gray-5)] bg-[var(--gray-1)] shadow-[0_2px_12px_rgba(26,29,33,0.05)]">
      <div className="flex items-center gap-2 border-b border-[var(--gray-5)] px-4 py-3">
        <Sparkles className="h-4 w-4 text-[var(--gray-12)]" />
        <span className="text-sm font-medium text-[var(--gray-12)]">
          再补充两项，<span className="text-[var(--gray-12)]">「{category}」</span> 就开抓
        </span>
      </div>

      <div className="space-y-4 p-4">
        {/* 已选参数只读回显（在输入框底部选的） */}
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg bg-[var(--gray-3)] px-3 py-2 text-xs text-[var(--gray-9)]">
          <span className="text-[var(--gray-8)]">已选</span>
          <span className="inline-flex items-center gap-1">
            {markets.map((c) => (
              <Flag key={c} iso={marketIso(c)} size={14} />
            ))}
            {markets.map(marketLabel).join(" / ")}
          </span>
          <span>·</span>
          <span>{positioning}</span>
          <span>·</span>
          <span>{modelChoice === "pro" ? "Pro 高质量" : "Flash 快速"}</span>
          <span className="ml-auto text-[var(--gray-9)]">想改？在下方输入框旁调整</span>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="月度预算" hint="选填">
            <input
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="如 5万美元/月"
              className="w-full rounded-lg border border-[var(--gray-5)] px-3 py-2 text-sm text-[var(--gray-12)] placeholder:text-[var(--gray-9)] focus:border-[var(--gray-8)] focus:outline-none focus:ring-2 focus:ring-[var(--gray-6)]"
            />
          </Field>
          <Field label="排除大牌" hint="选填">
            <input
              value={exclude}
              onChange={(e) => setExclude(e.target.value)}
              placeholder="如 Lululemon"
              className="w-full rounded-lg border border-[var(--gray-5)] px-3 py-2 text-sm text-[var(--gray-12)] placeholder:text-[var(--gray-9)] focus:border-[var(--gray-8)] focus:outline-none focus:ring-2 focus:ring-[var(--gray-6)]"
            />
          </Field>
        </div>

        <button
          onClick={submit}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--gray-12)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--gray-11)] active:scale-[0.99]"
        >
          开始调研
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-2">
        <span className="text-xs font-medium text-[var(--gray-8)]">{label}</span>
        {hint && <span className="text-[11px] text-[var(--gray-9)]">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function SummaryChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-md bg-[var(--gray-4)] px-2 py-0.5 text-[var(--gray-8)]">{children}</span>
  );
}
