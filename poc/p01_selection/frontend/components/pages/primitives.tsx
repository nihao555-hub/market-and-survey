"use client";
import React from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

/** 统一页面外壳：左对齐内容区 + 一致留白（8pt 网格） */
export function PageContainer({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto w-full max-w-[1180px] px-8 py-7">{children}</div>;
}

/** 页面标题区（图标 + 标题 + 副标题 + 右侧操作） */
export function PageHeader({
  icon,
  title,
  subtitle,
  actions,
}: {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon && (
          <span className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-subtle">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

/** 带标题的卡片面板 */
export function Panel({
  title,
  action,
  onAction,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  action?: string;
  onAction?: () => void;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("rounded-2xl border border-hairline bg-white", className)}>
      {title && (
        <div className="flex items-center justify-between border-b border-hairline px-5 py-3.5">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {action && (
            <button
              onClick={onAction}
              className="inline-flex items-center gap-0.5 text-xs text-brand transition-colors hover:text-brand-hover"
            >
              {action}
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

/** 空状态 */
export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-1 text-ink-tertiary">
        {icon}
      </span>
      <div>
        <div className="text-sm font-medium text-ink">{title}</div>
        {hint && <div className="mt-1 max-w-sm text-xs text-ink-subtle">{hint}</div>}
      </div>
      {action}
    </div>
  );
}

/** 指标小卡 */
export function StatTile({
  label,
  value,
  delta,
  icon,
  tone = "text-brand",
}: {
  label: string;
  value: string;
  delta?: string;
  icon: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className="rounded-xl border border-hairline bg-white p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-ink-subtle">{label}</span>
        <span className={cn("flex h-7 w-7 items-center justify-center rounded-lg bg-surface-1", tone)}>
          {icon}
        </span>
      </div>
      <div className="mt-2 text-xl font-semibold text-ink">{value}</div>
      {delta && <div className={cn("mt-0.5 text-xs", tone)}>{delta}</div>}
    </div>
  );
}
