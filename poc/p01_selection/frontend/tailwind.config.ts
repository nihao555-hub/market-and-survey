import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        accent: { DEFAULT: "#0d9488", hover: "#0b8076" },
        canvas: "#ffffff",
        surface: { 1: "#fafbfc", 2: "#f4f5f7", 3: "#eef0f3", 4: "#e8eaee" },
        hairline: { DEFAULT: "#e8eaed", strong: "#d8dbe0", tertiary: "#c8ccd2" },
        ink: { DEFAULT: "#1a1d21", muted: "#4b5563", subtle: "#8a8f98", tertiary: "#a8adb5" },
        success: "#27a644",
        danger: "#dc2626",
        warning: "#d4a017",
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
      },
      animation: {
        "shimmer-wave": "shimmer-wave 1.4s infinite linear",
        "fade-in-up": "fade-in-up 0.35s cubic-bezier(0.16,1,0.3,1)",
      },
    },
  },
  plugins: [],
};
export default config;
