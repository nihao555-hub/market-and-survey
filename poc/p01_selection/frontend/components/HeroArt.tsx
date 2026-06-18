import React from "react";
import { cn } from "@/lib/utils";

/**
 * HeroArt —— 首页 Hero 的「数据调研」插画。
 * 全部用半透明白色（毛玻璃）绘制，天然融入橙色渐变背景，无硬边、无栅格底。
 * 纯内联 SVG：矢量清晰、可主题化、零额外资源。
 */
export function HeroArt({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 560 400"
      fill="none"
      role="presentation"
      aria-hidden
      className={cn("pointer-events-none select-none", className)}
    >
      <defs>
        {/* 卡片表面渐变（顶部更亮，制造毛玻璃高光） */}
        <linearGradient id="ha-glass" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.34" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0.10" />
        </linearGradient>
        {/* 折线图区域填充 */}
        <linearGradient id="ha-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.55" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
        {/* 柱状渐变 */}
        <linearGradient id="ha-bar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0.45" />
        </linearGradient>
        {/* 柔光（让插画与背景边缘渐隐融合） */}
        <radialGradient id="ha-glow" cx="0.55" cy="0.42" r="0.62">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.30" />
          <stop offset="0.55" stopColor="#ffffff" stopOpacity="0.06" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
        <filter id="ha-soft" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="9" />
        </filter>
      </defs>

      {/* 背景柔光：让整组图形从渐变里「浮」出来，边缘自然融合 */}
      <ellipse cx="300" cy="180" rx="250" ry="170" fill="url(#ha-glow)" />

      {/* —— 折线 / 面积图大面板（右上） —— */}
      <g filter="url(#ha-soft)" opacity="0.4">
        <rect x="296" y="44" width="236" height="158" rx="20" fill="#ffffff" />
      </g>
      <rect
        x="296"
        y="44"
        width="236"
        height="158"
        rx="20"
        fill="url(#ha-glass)"
        stroke="#ffffff"
        strokeOpacity="0.55"
        strokeWidth="1.25"
      />
      {/* 网格 */}
      <g stroke="#ffffff" strokeOpacity="0.22" strokeWidth="1">
        <line x1="320" y1="86" x2="510" y2="86" />
        <line x1="320" y1="118" x2="510" y2="118" />
        <line x1="320" y1="150" x2="510" y2="150" />
      </g>
      {/* 面积填充 + 上升折线 */}
      <path
        d="M320 168 L356 150 L392 158 L428 120 L464 132 L500 78 L500 178 L320 178 Z"
        fill="url(#ha-area)"
      />
      <polyline
        points="320,168 356,150 392,158 428,120 464,132 500,78"
        stroke="#ffffff"
        strokeOpacity="0.95"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* 末端发光点 */}
      <circle cx="500" cy="78" r="9" fill="#ffffff" opacity="0.35" />
      <circle cx="500" cy="78" r="4.5" fill="#ffffff" />

      {/* —— 柱状图面板（中部，与折线面板叠压） —— */}
      <g filter="url(#ha-soft)" opacity="0.4">
        <rect x="150" y="118" width="208" height="150" rx="20" fill="#ffffff" />
      </g>
      <rect
        x="150"
        y="118"
        width="208"
        height="150"
        rx="20"
        fill="url(#ha-glass)"
        stroke="#ffffff"
        strokeOpacity="0.55"
        strokeWidth="1.25"
      />
      <g>
        <rect x="178" y="206" width="20" height="40" rx="6" fill="url(#ha-bar)" />
        <rect x="212" y="186" width="20" height="60" rx="6" fill="url(#ha-bar)" />
        <rect x="246" y="166" width="20" height="80" rx="6" fill="url(#ha-bar)" />
        <rect x="280" y="190" width="20" height="56" rx="6" fill="url(#ha-bar)" />
        <rect x="314" y="148" width="20" height="98" rx="6" fill="#ffffff" opacity="0.98" />
      </g>
      <line
        x1="170"
        y1="246"
        x2="342"
        y2="246"
        stroke="#ffffff"
        strokeOpacity="0.4"
        strokeWidth="1.25"
      />

      {/* —— 环形图面板（右下） —— */}
      <g filter="url(#ha-soft)" opacity="0.4">
        <rect x="372" y="232" width="138" height="138" rx="20" fill="#ffffff" />
      </g>
      <rect
        x="372"
        y="232"
        width="138"
        height="138"
        rx="20"
        fill="url(#ha-glass)"
        stroke="#ffffff"
        strokeOpacity="0.55"
        strokeWidth="1.25"
      />
      <g transform="translate(441 301)">
        {/* 环形三段 */}
        <circle r="34" fill="none" stroke="#ffffff" strokeOpacity="0.28" strokeWidth="16" />
        <circle
          r="34"
          fill="none"
          stroke="#ffffff"
          strokeOpacity="0.95"
          strokeWidth="16"
          strokeDasharray="86 128"
          strokeDashoffset="0"
          strokeLinecap="round"
          transform="rotate(-90)"
        />
        <circle
          r="34"
          fill="none"
          stroke="#ffffff"
          strokeOpacity="0.6"
          strokeWidth="16"
          strokeDasharray="46 168"
          strokeDashoffset="-92"
          strokeLinecap="round"
          transform="rotate(-90)"
        />
      </g>

      {/* —— 浮动小卡：左上（迷你饼 + 文本行） —— */}
      <g>
        <rect
          x="92"
          y="62"
          width="120"
          height="62"
          rx="14"
          fill="url(#ha-glass)"
          stroke="#ffffff"
          strokeOpacity="0.5"
          strokeWidth="1.25"
        />
        <circle cx="120" cy="93" r="15" fill="none" stroke="#ffffff" strokeOpacity="0.45" strokeWidth="7" />
        <circle
          cx="120"
          cy="93"
          r="15"
          fill="none"
          stroke="#ffffff"
          strokeWidth="7"
          strokeDasharray="46 48"
          transform="rotate(-90 120 93)"
          strokeLinecap="round"
        />
        <rect x="146" y="84" width="46" height="6" rx="3" fill="#ffffff" fillOpacity="0.85" />
        <rect x="146" y="98" width="34" height="6" rx="3" fill="#ffffff" fillOpacity="0.5" />
      </g>

      {/* —— 浮动小卡：右侧（文本行） —— */}
      <g>
        <rect
          x="478"
          y="208"
          width="74"
          height="58"
          rx="14"
          fill="url(#ha-glass)"
          stroke="#ffffff"
          strokeOpacity="0.5"
          strokeWidth="1.25"
        />
        <rect x="492" y="224" width="46" height="6" rx="3" fill="#ffffff" fillOpacity="0.85" />
        <rect x="492" y="237" width="36" height="6" rx="3" fill="#ffffff" fillOpacity="0.55" />
        <rect x="492" y="250" width="42" height="6" rx="3" fill="#ffffff" fillOpacity="0.4" />
      </g>

      {/* —— 装饰：浮动光点 / 立方 / 火花 —— */}
      <circle cx="262" cy="86" r="7" fill="#ffffff" opacity="0.9" />
      <circle cx="118" cy="170" r="5" fill="#ffffff" opacity="0.7" />
      <circle cx="356" cy="300" r="5" fill="#ffffff" opacity="0.6" />
      <circle cx="226" cy="300" r="8" fill="#ffffff" opacity="0.5" />
      <circle cx="534" cy="150" r="5" fill="#ffffff" opacity="0.55" />
      {/* 小立方 */}
      <g opacity="0.7" transform="translate(120 232)">
        <path d="M0 6 L12 0 L24 6 L12 12 Z" fill="#ffffff" fillOpacity="0.9" />
        <path d="M0 6 L12 12 L12 26 L0 20 Z" fill="#ffffff" fillOpacity="0.55" />
        <path d="M24 6 L12 12 L12 26 L24 20 Z" fill="#ffffff" fillOpacity="0.7" />
      </g>
      {/* 火花 */}
      <path
        d="M300 130 l0 -14 M300 130 l0 14 M300 130 l-14 0 M300 130 l14 0"
        stroke="#ffffff"
        strokeOpacity="0.7"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
