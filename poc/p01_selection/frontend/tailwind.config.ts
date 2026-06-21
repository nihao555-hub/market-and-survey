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
        // ── 品牌主色（Twenty CRM 中性灰，克制 B2B） ──
        // rgb() format to support Tailwind opacity modifiers (bg-brand/10, etc.)
        brand: {
          DEFAULT: "rgb(51 51 51 / <alpha-value>)",
          hover: "rgb(102 102 102 / <alpha-value>)",
          light: "rgb(153 153 153 / <alpha-value>)",
          fg: "#ffffff",
        },
        brand2: { DEFAULT: "rgb(131 131 131 / <alpha-value>)" },
        // ── 语义色（rgb format for opacity support） ──
        success: { DEFAULT: "rgb(22 163 74 / <alpha-value>)", bg: "#dcfce7", border: "#bbf7d0" },
        warning: { DEFAULT: "rgb(217 119 6 / <alpha-value>)", bg: "#fef9c3", border: "#fde68a" },
        danger: { DEFAULT: "rgb(220 38 38 / <alpha-value>)", bg: "#fee2e2", border: "#fca5a5" },
        info: { DEFAULT: "rgb(59 130 246 / <alpha-value>)", bg: "#dbeafe", border: "#93c5fd" },
        // ── 兼容旧 token → Twenty CRM gray CSS 变量 ──
        canvas: "var(--gray-1)",
        surface: { 1: "var(--gray-2)", 2: "var(--gray-3)", 3: "var(--gray-4)", 4: "var(--gray-5)" },
        hairline: { DEFAULT: "var(--gray-5)", strong: "var(--gray-6)", tertiary: "var(--gray-8)" },
        ink: { DEFAULT: "var(--gray-12)", muted: "var(--gray-11)", subtle: "var(--gray-9)", tertiary: "var(--gray-8)" },
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
