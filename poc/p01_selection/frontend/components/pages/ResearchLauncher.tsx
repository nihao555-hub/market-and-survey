"use client";
import React from "react";
import { useSetAtom } from "jotai";
import { ArrowUp, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { draftCategoryAtom } from "@/lib/atoms";
import { PageContainer, PageHeader, Panel } from "./primitives";

export interface ResearchConfig {
  key: string;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  placeholder: string;
  examples: string[];
  dimensions: { title: string; desc: string; icon: React.ReactNode }[];
}

export function ResearchLauncher({ config }: { config: ResearchConfig }) {
  const setDraft = useSetAtom(draftCategoryAtom);
  const [input, setInput] = React.useState("");

  const start = (text: string) => {
    const c = text.trim();
    if (!c) return;
    setDraft(c);
  };

  return (
    <PageContainer>
      <PageHeader icon={config.icon} title={config.title} subtitle={config.subtitle} />

      {/* 调研入口 */}
      <section className="relative overflow-hidden rounded-2xl border border-brand/20 bg-gradient-to-br from-brand via-brand-light to-brand2 p-6 text-white shadow-md">
        <div className="pointer-events-none absolute -right-10 -top-12 h-44 w-44 rounded-full bg-white/10 blur-2xl" />
        <div className="relative max-w-2xl">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-xs font-medium">
            <Sparkles className="h-3.5 w-3.5" />
            AI 驱动 · {config.title}
          </div>
          <h2 className="mt-3 text-xl font-semibold">{config.placeholder}</h2>

          <div className="mt-4 flex items-center gap-2 rounded-xl border border-white/20 bg-white/95 p-1.5 shadow-lg backdrop-blur">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && start(input)}
              placeholder="输入一个品类、品牌或市场关键词…"
              className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none"
            />
            <button
              onClick={() => start(input)}
              disabled={!input.trim()}
              className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand text-white transition-colors hover:bg-brand-hover disabled:opacity-40"
            >
              <ArrowUp className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {config.examples.map((ex) => (
              <button
                key={ex}
                onClick={() => start(ex)}
                className="rounded-full bg-white/15 px-2.5 py-1 text-xs text-white transition-colors hover:bg-white/25"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 分析维度 */}
      <h3 className="mb-3 mt-7 text-sm font-semibold text-ink">分析维度</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {config.dimensions.map((d) => (
          <Panel key={d.title} className="transition-shadow hover:shadow-sm" bodyClassName="p-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand/10 text-brand">
              {d.icon}
            </span>
            <div className="mt-3 text-sm font-medium text-ink">{d.title}</div>
            <div className="mt-1 text-xs leading-relaxed text-ink-subtle">{d.desc}</div>
          </Panel>
        ))}
      </div>
    </PageContainer>
  );
}

export function CenteredHint({ children }: { children: React.ReactNode }) {
  return <div className={cn("text-center text-sm text-ink-subtle")}>{children}</div>;
}
