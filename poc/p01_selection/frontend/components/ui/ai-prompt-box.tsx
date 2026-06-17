"use client";
import React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { ArrowUp, Square, Paperclip, Globe, Sparkles, SlidersHorizontal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAtom } from "jotai";
import { quickParamsAtom } from "@/lib/atoms";
import { POSITIONINGS, marketIso, marketsByContinent } from "@/lib/markets";
import { Flag } from "@/components/ui/Flag";

// className 合并
const cn = (...classes: (string | undefined | null | false)[]) =>
  classes.filter(Boolean).join(" ");

// ── Textarea（白底黑字）──
const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    className={cn(
      "flex w-full resize-none rounded-md border-none bg-transparent px-3 py-2.5 text-base text-ink placeholder:text-ink-subtle focus-visible:outline-none focus-visible:ring-0 disabled:cursor-not-allowed disabled:opacity-50 min-h-[44px]",
      className
    )}
    ref={ref}
    rows={1}
    {...props}
  />
));
Textarea.displayName = "Textarea";

// ── Tooltip ──
const TooltipProvider = TooltipPrimitive.Provider;
const Tooltip = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;
const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "z-50 overflow-hidden rounded-md border border-hairline bg-white px-3 py-1.5 text-sm text-ink shadow-md",
      className
    )}
    {...props}
  />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

// ── 自定义渐变分隔条（保留参考组件的精致细节，改 accent 色）──
const CustomDivider: React.FC = () => (
  <div className="relative mx-1 h-6 w-[1.5px]">
    <div
      className="absolute inset-0 rounded-full bg-gradient-to-t from-transparent via-accent/50 to-transparent"
      style={{
        clipPath:
          "polygon(0% 0%, 100% 0%, 100% 40%, 140% 50%, 100% 60%, 100% 100%, 0% 100%, 0% 60%, -40% 50%, 0% 40%)",
      }}
    />
  </div>
);

interface PromptInputBoxProps {
  onSend?: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
  /** 深度调研开关回调（对应 model_choice pro / flash） */
  onModeChange?: (deep: boolean) => void;
  /** 是否显示输入框下方的参数快捷设置（市场/定位）。空态显示，会话态隐藏。 */
  showParams?: boolean;
  /** 流进行中点击停止按钮的回调（接 stopStream）。 */
  onStop?: () => void;
}

/** 输入框下方的参数快捷设置弹层（市场多选 + 定位单选）。 */
function ParamSettingsBar() {
  const [params, setParams] = useAtom(quickParamsAtom);
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const toggleMarket = (code: string) =>
    setParams((prev) => ({
      ...prev,
      markets: prev.markets.includes(code)
        ? prev.markets.filter((m) => m !== code)
        : [...prev.markets, code],
    }));

  return (
    <div ref={ref} className="relative mt-2 flex items-center gap-2 px-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-xs transition-colors",
          open
            ? "border-accent/40 bg-accent/10 text-accent"
            : "border-hairline bg-white text-ink-muted hover:border-hairline-strong hover:text-ink"
        )}
      >
        <SlidersHorizontal className="h-3.5 w-3.5" />
        {/* 已选市场国旗叠放 */}
        {params.markets.length > 0 ? (
          <span className="flex items-center -space-x-1">
            {params.markets.slice(0, 4).map((c) => (
              <Flag key={c} iso={marketIso(c)} size={15} className="ring-1 ring-white" />
            ))}
            {params.markets.length > 4 && (
              <span className="ml-1 text-[11px] text-ink-subtle">+{params.markets.length - 4}</span>
            )}
          </span>
        ) : (
          <span className="text-ink-subtle">选择市场</span>
        )}
        <span className="text-ink-subtle">·</span>
        <span>{params.positioning}</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-0 z-50 mb-2 max-h-[60vh] w-[380px] overflow-y-auto rounded-xl border border-hairline bg-white p-3 shadow-[0_8px_28px_rgba(26,29,33,0.12)]"
          >
            <div className="mb-1.5 text-[11px] font-medium text-ink-subtle">目标市场（可多选，默认美国）</div>
            <div className="space-y-2.5">
              {marketsByContinent().map((group) => (
                <div key={group.region}>
                  <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink-tertiary">
                    {group.region}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {group.markets.map((m) => {
                      const active = params.markets.includes(m.code);
                      return (
                        <button
                          key={m.code}
                          type="button"
                          onClick={() => toggleMarket(m.code)}
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-lg border px-2 py-1 text-xs transition-colors",
                            active
                              ? "border-accent bg-accent text-white"
                              : "border-hairline bg-white text-ink-muted hover:border-hairline-strong"
                          )}
                        >
                          <Flag iso={m.iso} size={15} />
                          {m.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <div className="mb-1.5 mt-3 text-[11px] font-medium text-ink-subtle">商家定位</div>
            <div className="flex flex-wrap gap-1.5">
              {POSITIONINGS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setParams((prev) => ({ ...prev, positioning: p }))}
                  className={cn(
                    "inline-flex items-center rounded-lg border px-2 py-1 text-xs transition-colors",
                    params.positioning === p
                      ? "border-accent bg-accent text-white"
                      : "border-hairline bg-white text-ink-muted hover:border-hairline-strong"
                  )}
                >
                  {p}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * 输入框（参考组件结构，改为白底黑字 + accent 主题）。
 * 结构：textarea 在上，底部一行 = 附件按钮 + 联网/深度调研开关 + 发送按钮。
 * 业务参数（市场/定位/预算）走流程中的 A2UI 表单，这里只收品类 + 调研深度。
 */
export const PromptInputBox = React.forwardRef<HTMLDivElement, PromptInputBoxProps>(
  (props, ref) => {
    const {
      onSend = () => {},
      isLoading = false,
      placeholder = "输入要调研的品类，如「瑜伽垫」「智能插座」…",
      className,
      onModeChange,
      showParams = false,
      onStop,
    } = props;
    const [input, setInput] = React.useState("");
    const [params, setParams] = useAtom(quickParamsAtom);
    const [mounted, setMounted] = React.useState(false);
    React.useEffect(() => setMounted(true), []);
    // 挂载前用服务端一致的默认值，避免 localStorage 导致的 hydration 不匹配
    const deep = mounted && params.modelChoice === "pro";
    const taRef = React.useRef<HTMLTextAreaElement>(null);

    React.useEffect(() => {
      if (!taRef.current) return;
      taRef.current.style.height = "auto";
      taRef.current.style.height = `${Math.min(taRef.current.scrollHeight, 200)}px`;
    }, [input]);

    const hasContent = input.trim() !== "";
    const submit = () => {
      if (!hasContent || isLoading) return;
      onSend(input.trim());
      setInput("");
    };

    const toggleDeep = () => {
      const next = !deep;
      setParams((prev) => ({ ...prev, modelChoice: next ? "pro" : "flash" }));
      onModeChange?.(next);
    };

    return (
      <TooltipProvider>
        <div
          ref={ref}
          className={cn(
            "rounded-3xl border border-hairline bg-white p-2 shadow-[0_2px_16px_rgba(26,29,33,0.06)] transition-all duration-300 focus-within:border-hairline-strong focus-within:shadow-[0_2px_20px_rgba(13,148,136,0.10)]",
            className
          )}
        >
          <Textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={placeholder}
            disabled={isLoading}
          />

          <div className="flex items-center justify-between gap-2 p-0 pt-2">
            <div className="flex items-center gap-1">
              {/* 附件（占位，后续接图片输入） */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink-muted"
                    disabled
                  >
                    <Paperclip className="h-5 w-5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>上传图片（即将支持）</TooltipContent>
              </Tooltip>

              {/* 联网（恒开，仅展示真实数据来源） */}
              <button
                type="button"
                className="flex h-8 items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2 py-1 text-accent"
              >
                <Globe className="h-4 w-4" />
                <span className="text-xs">实时联网</span>
              </button>

              <CustomDivider />

              {/* 深度调研开关（→ model_choice） */}
              <button
                type="button"
                onClick={toggleDeep}
                className={cn(
                  "flex h-8 items-center gap-1 rounded-full border px-2 py-1 transition-all",
                  deep
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-transparent bg-transparent text-ink-subtle hover:text-ink-muted"
                )}
              >
                <div className="flex h-5 w-5 items-center justify-center">
                  <motion.div
                    animate={{ scale: deep ? 1.1 : 1 }}
                    transition={{ type: "spring", stiffness: 260, damping: 25 }}
                  >
                    <Sparkles className="h-4 w-4" />
                  </motion.div>
                </div>
                <AnimatePresence>
                  {deep && (
                    <motion.span
                      initial={{ width: 0, opacity: 0 }}
                      animate={{ width: "auto", opacity: 1 }}
                      exit={{ width: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden whitespace-nowrap text-xs"
                    >
                      深度调研
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            </div>

            {/* 发送 / 停止按钮 */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => {
                    if (isLoading) {
                      onStop?.();
                    } else {
                      submit();
                    }
                  }}
                  disabled={!isLoading && !hasContent}
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200 active:scale-95",
                    isLoading
                      ? "bg-surface-2 text-ink-muted hover:bg-hairline-strong hover:text-ink"
                      : hasContent
                      ? "bg-accent text-white hover:bg-accent-hover"
                      : "bg-surface-2 text-ink-subtle"
                  )}
                >
                  {isLoading ? (
                    <Square className="h-3.5 w-3.5 fill-current" />
                  ) : (
                    <ArrowUp className="h-5 w-5" />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent>{isLoading ? "停止调研" : "开始调研"}</TooltipContent>
            </Tooltip>
          </div>
        </div>
        {showParams && mounted && <ParamSettingsBar />}
      </TooltipProvider>
    );
  }
);
PromptInputBox.displayName = "PromptInputBox";
