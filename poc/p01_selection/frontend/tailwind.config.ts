import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1440px" },
    },
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "var(--font-inter)",
          "-apple-system",
          "PingFang SC",
          "Microsoft YaHei",
          "system-ui",
          "sans-serif",
        ],
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        // ── shadcn / ai-elements 语义 token（CSS 变量驱动） ──
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        chart: {
          1: "hsl(var(--chart-1))",
          2: "hsl(var(--chart-2))",
          3: "hsl(var(--chart-3))",
          4: "hsl(var(--chart-4))",
          5: "hsl(var(--chart-5))",
        },
        // ── 品牌主色（橙色系，Primary #F97316 orange-500） ──
        brand: {
          DEFAULT: "#F97316",
          hover: "#EA580C",
          light: "#FB923C",
          fg: "#FFFFFF",
        },
        // ── 品牌辅助色（暖琥珀，用于渐变第二色） ──
        brand2: { DEFAULT: "#FBBF24" },
        // ── 语义色（设计稿② Semantic） ──
        success: { DEFAULT: "#10B981", bg: "#D1FAE5", border: "#A7F3D0" },
        warning: { DEFAULT: "#F59E0B", bg: "#FEF3C7", border: "#FDE68A" },
        danger: { DEFAULT: "#EF4444", bg: "#FEE2E2", border: "#FCA5A5" },
        info: { DEFAULT: "#3B82F6", bg: "#DBEAFE", border: "#93C5FD" },
        // ── 兼容旧 token（重映射到设计稿② slate 中性阶） ──
        canvas: "#FFFFFF",
        surface: { 1: "#F8FAFC", 2: "#F1F5F9", 3: "#E2E8F0", 4: "#CBD5E1" },
        hairline: { DEFAULT: "#E2E8F0", strong: "#CBD5E1", tertiary: "#94A3B8" },
        ink: { DEFAULT: "#0F172A", muted: "#475569", subtle: "#64748B", tertiary: "#94A3B8" },
      },
      borderRadius: {
        xl: "16px",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        xs: "0 1px 2px rgba(16,24,40,0.06)",
        sm: "0 2px 8px rgba(16,24,40,0.06)",
        md: "0 4px 16px rgba(16,24,40,0.08)",
        lg: "0 10px 24px rgba(16,24,40,0.10)",
        xl: "0 20px 48px rgba(16,24,40,0.12)",
      },
      transitionDuration: {
        fast: "200ms",
        std: "300ms",
        slow: "500ms",
      },
      keyframes: {
        "shimmer-wave": {
          "0%": { backgroundPosition: "200% top" },
          "100%": { backgroundPosition: "-200% top" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "shimmer-wave": "shimmer-wave 1.4s infinite linear",
        "fade-in-up": "fade-in-up 0.35s cubic-bezier(0.16,1,0.3,1)",
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
