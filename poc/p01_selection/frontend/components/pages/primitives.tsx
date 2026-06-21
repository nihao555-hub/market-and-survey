"use client";
import React from "react";
import { ChevronRight, Loader2 } from "lucide-react";
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
          <span className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--gray-4)] text-[var(--gray-12)]">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight text-[var(--gray-12)]">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-[var(--gray-9)]">{subtitle}</p>}
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
    <section className={cn("rounded-2xl border border-[var(--gray-5)] bg-[var(--gray-1)]", className)}>
      {title && (
        <div className="flex items-center justify-between border-b border-[var(--gray-5)] px-5 py-3.5">
          <h2 className="text-sm font-semibold text-[var(--gray-12)]">{title}</h2>
          {action && (
            <button
              onClick={onAction}
              className="inline-flex items-center gap-0.5 text-xs text-[var(--gray-12)] transition-colors hover:text-[var(--gray-11)]"
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
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--gray-3)] text-[var(--gray-7)]">
        {icon}
      </span>
      <div>
        <div className="text-sm font-medium text-[var(--gray-12)]">{title}</div>
        {hint && <div className="mt-1 max-w-sm text-xs text-[var(--gray-9)]">{hint}</div>}
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
  tone = "text-[var(--gray-12)]",
}: {
  label: string;
  value: string;
  delta?: string;
  icon: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className="rounded-xl border border-[var(--gray-5)] bg-[var(--gray-1)] p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-[var(--gray-9)]">{label}</span>
        <span className={cn("flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--gray-3)]", tone)}>
          {icon}
        </span>
      </div>
      <div className="mt-2 text-xl font-semibold text-[var(--gray-12)]">{value}</div>
      {delta && <div className={cn("mt-0.5 text-xs", tone)}>{delta}</div>}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
 * 统一 UI 规范 · 共享组件库（全站复用，详见 DESIGN.md）
 * ════════════════════════════════════════════════════════════════════ */

/** 统一按钮：主/次/幽灵/危险/描边 五态 + 两档尺寸 */
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type ButtonSize = "sm" | "md";

const BTN_BASE =
  "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30 disabled:pointer-events-none disabled:opacity-50";
const BTN_SIZE: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-3.5 py-2 text-sm",
};
const BTN_VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-[var(--gray-12)] text-white shadow-sm hover:bg-[var(--gray-11)]",
  secondary: "border border-[var(--gray-5)] bg-[var(--gray-1)] text-[var(--gray-8)] hover:bg-[var(--gray-3)] hover:text-[var(--gray-12)]",
  ghost: "text-[var(--gray-8)] hover:bg-[var(--gray-3)] hover:text-[var(--gray-12)]",
  danger: "bg-danger text-white shadow-sm hover:bg-danger/90",
  outline: "border border-[var(--gray-12)]/30 bg-[var(--gray-1)] text-[var(--gray-12)] hover:bg-[var(--gray-3)]",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}) {
  return (
    <button
      className={cn(BTN_BASE, BTN_SIZE[size], BTN_VARIANT[variant], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  );
}

/** 状态徽章：分析中 / 已完成 / 待开始 / 失败 / 信息 / 中性 */
export type StatusKind = "running" | "done" | "pending" | "error" | "info" | "neutral";

const STATUS_STYLE: Record<StatusKind, { box: string; dot: string }> = {
  running: { box: "bg-info/10 text-info", dot: "bg-info animate-pulse" },
  done: { box: "bg-success/10 text-success", dot: "bg-success" },
  pending: { box: "bg-[var(--gray-4)] text-[var(--gray-9)]", dot: "bg-ink-tertiary" },
  error: { box: "bg-danger/10 text-danger", dot: "bg-danger" },
  info: { box: "bg-info/10 text-info", dot: "bg-info" },
  neutral: { box: "bg-[var(--gray-4)] text-[var(--gray-9)]", dot: "bg-ink-tertiary" },
};

export function StatusBadge({ status, label }: { status: StatusKind; label: string }) {
  const s = STATUS_STYLE[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium", s.box)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} />
      {label}
    </span>
  );
}

/** 过滤标签栏（带计数胶囊） */
export function FilterTabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { key: T; label: string; count?: number }[];
  value: T;
  onChange: (key: T) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      {tabs.map((t) => {
        const active = value === t.key;
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
              active ? "bg-[var(--gray-4)] font-medium text-[var(--gray-12)]" : "text-[var(--gray-8)] hover:bg-[var(--gray-3)] hover:text-[var(--gray-12)]"
            )}
          >
            {t.label}
            {typeof t.count === "number" && (
              <span
                className={cn(
                  "rounded-full px-1.5 text-[11px]",
                  active ? "bg-[var(--gray-12)]/15 text-[var(--gray-12)]" : "bg-[var(--gray-4)] text-[var(--gray-9)]"
                )}
              >
                {t.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/** 开关 */
export function Switch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors disabled:opacity-50",
        checked ? "bg-[var(--gray-12)]" : "bg-[var(--gray-3)]-3"
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-[var(--gray-1)] shadow transition-transform",
          checked ? "translate-x-4" : "translate-x-0.5"
        )}
      />
    </button>
  );
}

/** 骨架屏占位 */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-[var(--gray-4)]", className)} />;
}

/** 通用数据表格（列配置 + 行数据 + 行点击 + 空态） */
export interface Column<T> {
  key: string;
  header: React.ReactNode;
  align?: "left" | "right" | "center";
  headClassName?: string;
  cellClassName?: string;
  render: (row: T) => React.ReactNode;
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  onRowClick,
  empty,
}: {
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  empty?: React.ReactNode;
}) {
  const alignCls = (a?: "left" | "right" | "center") =>
    a === "right" ? "text-right" : a === "center" ? "text-center" : "text-left";

  if (rows.length === 0 && empty) return <>{empty}</>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[var(--gray-3)] text-[11px] uppercase tracking-wide text-[var(--gray-9)]">
            {columns.map((c, i) => (
              <th
                key={c.key}
                className={cn(
                  "px-3 py-2.5 font-medium",
                  i === 0 && "pl-5",
                  i === columns.length - 1 && "pr-5",
                  alignCls(c.align),
                  c.headClassName
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={getRowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                "border-t border-[var(--gray-5)] transition-colors",
                onRowClick && "cursor-pointer hover:bg-[var(--gray-3)]"
              )}
            >
              {columns.map((c, i) => (
                <td
                  key={c.key}
                  className={cn(
                    "px-3 py-3",
                    i === 0 && "pl-5",
                    i === columns.length - 1 && "pr-5",
                    alignCls(c.align),
                    c.cellClassName
                  )}
                >
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
