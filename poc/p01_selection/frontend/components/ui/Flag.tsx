"use client";
import React from "react";
import { cn } from "@/lib/utils";

/**
 * 圆形国旗（真实 SVG，非 emoji —— 符合设计规范"用图标库/真实资源，不用 emoji"）。
 * 资源：hatscripts/circle-flags（公开 CDN，单色描边友好，体积小）。
 * 加载失败时降级为国家码字母圆点，不破版。
 */
export function Flag({ iso, size = 16, className }: { iso: string; size?: number; className?: string }) {
  const [failed, setFailed] = React.useState(false);
  const code = (iso || "").toLowerCase();

  if (!code || failed) {
    return (
      <span
        className={cn(
          "inline-flex items-center justify-center rounded-full bg-surface-2 text-[8px] font-medium uppercase text-ink-subtle",
          className
        )}
        style={{ width: size, height: size }}
      >
        {code.slice(0, 2)}
      </span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`https://hatscripts.github.io/circle-flags/flags/${code}.svg`}
      alt=""
      width={size}
      height={size}
      onError={() => setFailed(true)}
      className={cn("inline-block rounded-full object-cover", className)}
      style={{ width: size, height: size }}
    />
  );
}
