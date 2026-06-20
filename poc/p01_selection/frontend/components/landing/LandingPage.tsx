"use client";
import React, { useState } from "react";
import Link from "next/link";
import {
  Search, BarChart3, Globe2, Calculator, Shield, FileText,
  ArrowRight, Check, ChevronDown, Zap, TrendingUp, Star,
  Menu, X,
} from "lucide-react";

/* ────────────────────────── NAVBAR ────────────────────────── */
function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <nav className="fixed top-0 inset-x-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <img src="/images/logo-icon.png" alt="SelectPilot" className="h-8 w-8 rounded-lg" />
          <span className="text-lg font-semibold tracking-tight">SelectPilot</span>
        </Link>
        <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition-colors">功能</a>
          <a href="#pricing" className="hover:text-foreground transition-colors">定价</a>
          <a href="#faq" className="hover:text-foreground transition-colors">FAQ</a>
        </div>
        <div className="hidden md:flex items-center gap-3">
          <Link href="/login" className="rounded-xl px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">登录</Link>
          <Link href="/register" className="rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors">免费开始</Link>
        </div>
        <button className="md:hidden" onClick={() => setOpen(!open)}>
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <div className="md:hidden border-t border-border bg-background px-6 py-4 space-y-3">
          <a href="#features" onClick={() => setOpen(false)} className="block text-sm text-muted-foreground">功能</a>
          <a href="#pricing" onClick={() => setOpen(false)} className="block text-sm text-muted-foreground">定价</a>
          <a href="#faq" onClick={() => setOpen(false)} className="block text-sm text-muted-foreground">FAQ</a>
          <div className="flex gap-3 pt-2">
            <Link href="/login" className="flex-1 text-center rounded-xl border border-border px-4 py-2.5 text-sm font-medium">登录</Link>
            <Link href="/register" className="flex-1 text-center rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-medium text-white">注册</Link>
          </div>
        </div>
      )}
    </nav>
  );
}

/* ────────────────────────── HERO ────────────────────────── */
function Hero() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden">
      {/* Gradient bg */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-to-b from-violet-500/20 via-violet-400/5 to-transparent rounded-full blur-3xl" />
        <div className="absolute top-20 left-1/4 w-[400px] h-[400px] bg-gradient-to-br from-cyan-400/10 to-transparent rounded-full blur-3xl" />
      </div>

      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center max-w-3xl mx-auto">
          {/* Badge */}
          <div className="animate-element animate-delay-100 inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-4 py-1.5 text-sm text-violet-700 mb-8">
            <Zap className="h-3.5 w-3.5" />
            <span>AI 驱动的跨境电商选品决策引擎</span>
          </div>

          {/* Headline */}
          <h1 className="animate-element animate-delay-200 text-5xl md:text-7xl font-semibold tracking-tight leading-[1.1] mb-6">
            用 AI 发现
            <br />
            <span className="bg-gradient-to-r from-violet-600 via-purple-600 to-cyan-500 bg-clip-text text-transparent">
              下一个爆品
            </span>
          </h1>

          {/* Subheadline */}
          <p className="animate-element animate-delay-300 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            对话式 AI 选品助手，8 阶段自动化市场调研，从 Amazon BSR 到 1688 采购成本，真实数据驱动的选品决策报告。
          </p>

          {/* CTA */}
          <div className="animate-element animate-delay-400 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="group flex items-center gap-2 rounded-2xl bg-violet-600 px-8 py-4 text-base font-medium text-white hover:bg-violet-700 transition-all hover:shadow-lg hover:shadow-violet-500/25">
              免费开始使用
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <a href="#features" className="flex items-center gap-2 rounded-2xl border border-border px-8 py-4 text-base font-medium text-foreground hover:bg-muted transition-colors">
              了解更多
            </a>
          </div>
        </div>

        {/* Stats */}
        <div className="animate-element animate-delay-500 mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
          {[
            { value: "56+", label: "AI 工具链", icon: Zap },
            { value: "26", label: "目标国家", icon: Globe2 },
            { value: "9 级", label: "反爬引擎", icon: Shield },
            { value: "实时", label: "数据更新", icon: TrendingUp },
          ].map((s, i) => (
            <div key={i} className="text-center p-4 rounded-2xl border border-border/50 bg-card/50 backdrop-blur-sm">
              <s.icon className="h-5 w-5 text-violet-500 mx-auto mb-2" />
              <div className="text-2xl font-bold tracking-tight">{s.value}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Hero Image */}
        <div className="animate-element animate-delay-600 mt-16 relative">
          <div className="rounded-2xl border border-border/50 shadow-2xl shadow-violet-500/5 overflow-hidden bg-gradient-to-b from-card to-muted/50 p-1">
            <img
              src="/images/hero-dashboard.png"
              alt="SelectPilot Dashboard"
              className="w-full rounded-xl"
            />
          </div>
          {/* Glow effect */}
          <div className="absolute -inset-4 bg-gradient-to-r from-violet-500/10 via-purple-500/5 to-cyan-500/10 rounded-3xl blur-2xl -z-10" />
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────── FEATURES ────────────────────────── */
const features = [
  {
    icon: Search,
    title: "智能市场调研",
    desc: "AI Agent 自动完成 8 阶段选品调研，从品类扫描到竞品深挖，真实数据驱动决策。",
    color: "text-violet-500",
    bg: "bg-violet-50",
  },
  {
    icon: BarChart3,
    title: "实时数据仪表盘",
    desc: "Amazon BSR 热销榜、TikTok 社媒趋势、品类价格走势，ECharts 交互式图表一目了然。",
    color: "text-cyan-500",
    bg: "bg-cyan-50",
  },
  {
    icon: Globe2,
    title: "26 国多市场覆盖",
    desc: "支持美国、英国、德国、日本等 26 个国家/地区，一键切换目标市场。",
    color: "text-emerald-500",
    bg: "bg-emerald-50",
  },
  {
    icon: Calculator,
    title: "利润测算引擎",
    desc: "14 项成本拆解 + 蒙特卡洛压力测试，精确计算利润率和亏损风险。",
    color: "text-amber-500",
    bg: "bg-amber-50",
  },
  {
    icon: Shield,
    title: "9 级反爬引擎",
    desc: "curl_cffi → Scrapling → patchright → botasaurus 等 9 级降级链，确保数据采集稳定。",
    color: "text-rose-500",
    bg: "bg-rose-50",
  },
  {
    icon: FileText,
    title: "自动报告生成",
    desc: "AI 自动产出带图表的选品决策报告，含 ECharts 交互式可视化，可导出 PDF。",
    color: "text-indigo-500",
    bg: "bg-indigo-50",
  },
];

function Features() {
  return (
    <section id="features" className="py-24 bg-muted/30">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-4 py-1.5 text-sm text-violet-700 mb-4">
            <Star className="h-3.5 w-3.5" />
            核心功能
          </div>
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-4">一站式选品决策平台</h2>
          <p className="text-muted-foreground">从市场调研到采购成本，从竞品分析到利润测算，全流程 AI 自动化</p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="group rounded-2xl border border-border/50 bg-card p-6 hover:shadow-lg hover:border-violet-200/50 transition-all duration-300">
              <div className={`w-11 h-11 rounded-xl ${f.bg} flex items-center justify-center mb-4`}>
                <f.icon className={`h-5 w-5 ${f.color}`} />
              </div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────── PRICING ────────────────────────── */
const plans = [
  {
    name: "免费版",
    desc: "适合个人卖家试用",
    price: "0",
    features: ["5 次 AI 调研/月", "1 个品类追踪", "基础数据仪表盘", "社区支持"],
    cta: "免费开始",
    popular: false,
  },
  {
    name: "专业版",
    desc: "适合成长期卖家",
    price: "99",
    features: [
      "100 次 AI 调研/月", "10 个品类追踪", "ECharts 交互式报告",
      "26 国市场数据", "利润测算引擎", "实时数据刷新", "邮件提醒", "优先技术支持",
    ],
    cta: "立即升级",
    popular: true,
  },
  {
    name: "企业版",
    desc: "适合团队和大卖",
    price: "299",
    features: [
      "无限 AI 调研", "无限品类追踪", "API 接口访问", "多人协作",
      "自定义报告模板", "专属客户经理", "SLA 服务保障", "数据导出 Excel/PDF",
    ],
    cta: "联系我们",
    popular: false,
  },
];

function Pricing() {
  return (
    <section id="pricing" className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-4 py-1.5 text-sm text-violet-700 mb-4">
            灵活定价
          </div>
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-4">选择适合你的方案</h2>
          <p className="text-muted-foreground">从免费试用到企业定制，满足不同阶段需求</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <div key={i} className={`relative rounded-2xl border p-8 flex flex-col ${
              plan.popular
                ? "border-violet-300 bg-gradient-to-b from-violet-50 to-card shadow-lg shadow-violet-500/10 scale-[1.02]"
                : "border-border/50 bg-card"
            }`}>
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-violet-600 px-4 py-1 text-xs font-medium text-white">
                  最受欢迎
                </div>
              )}
              <div className="mb-6">
                <h3 className={`text-xl font-semibold ${plan.popular ? "text-violet-700" : ""}`}>{plan.name}</h3>
                <p className="text-sm text-muted-foreground mt-1">{plan.desc}</p>
              </div>
              <div className="mb-6">
                <span className="text-4xl font-bold tracking-tight">¥{plan.price}</span>
                {plan.price !== "0" && <span className="text-muted-foreground ml-1">/月</span>}
                {plan.price === "0" && <span className="text-muted-foreground ml-2">永久免费</span>}
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f, j) => (
                  <li key={j} className="flex items-start gap-2.5 text-sm">
                    <Check className={`h-4 w-4 mt-0.5 flex-shrink-0 ${plan.popular ? "text-violet-500" : "text-emerald-500"}`} />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link href="/register" className={`rounded-xl py-3 text-center text-sm font-medium transition-colors ${
                plan.popular
                  ? "bg-violet-600 text-white hover:bg-violet-700"
                  : "border border-border text-foreground hover:bg-muted"
              }`}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────── FAQ ────────────────────────── */
const faqs = [
  {
    q: "SelectPilot 和其他选品工具有什么区别？",
    a: "SelectPilot 是唯一一个结合了对话式 AI Agent + 56 种工具链 + 9 级反爬引擎的全自动选品平台。不只是看数据，而是像雇了一位资深选品专家帮你分析。",
  },
  {
    q: "数据来源是真实的吗？",
    a: "所有数据都来自实时抓取——Amazon BSR 排名、商品详情、评论数据、1688 供应商报价、TikTok 社媒趋势等。每个数据点都有来源追溯，绝不虚构。",
  },
  {
    q: "免费版有什么限制？",
    a: "免费版每月可进行 5 次 AI 调研和追踪 1 个品类。升级到专业版可获得 100 次调研额度、ECharts 交互式图表、26 国市场数据等完整功能。",
  },
  {
    q: "支持哪些电商平台？",
    a: "目前支持 Amazon（26 个站点）、1688、Made-in-China、DHgate 的数据采集，以及 TikTok、Reddit 等社媒趋势分析。我们在持续接入更多平台。",
  },
];

function FAQ() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  return (
    <section id="faq" className="py-24 bg-muted/30">
      <div className="mx-auto max-w-3xl px-6">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-4 py-1.5 text-sm text-violet-700 mb-4">
            常见问题
          </div>
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">有疑问？看这里</h2>
        </div>
        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <div key={i} className="rounded-2xl border border-border/50 bg-card overflow-hidden">
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="w-full flex items-center justify-between p-5 text-left text-sm font-medium hover:bg-muted/50 transition-colors"
              >
                {faq.q}
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${openIdx === i ? "rotate-180" : ""}`} />
              </button>
              {openIdx === i && (
                <div className="px-5 pb-5 text-sm text-muted-foreground leading-relaxed">{faq.a}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────── CTA ────────────────────────── */
function CTA() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="relative rounded-3xl bg-gradient-to-br from-violet-600 to-purple-700 p-12 md:p-16 text-center overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImEiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMSIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjA4KSIvPjwvcGF0dGVybj48L2RlZnM+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNhKSIvPjwvc3ZnPg==')] opacity-50" />
          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-semibold text-white tracking-tight mb-4">
              准备好发现下一个爆品了吗？
            </h2>
            <p className="text-violet-200 text-lg mb-8 max-w-xl mx-auto">
              加入数千名跨境卖家，用 AI 驱动你的选品决策
            </p>
            <Link href="/register" className="inline-flex items-center gap-2 rounded-2xl bg-white px-8 py-4 text-base font-medium text-violet-700 hover:bg-violet-50 transition-colors">
              免费开始使用 <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────── FOOTER ────────────────────────── */
function Footer() {
  return (
    <footer className="border-t border-border py-12">
      <div className="mx-auto max-w-6xl px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <img src="/images/logo-icon.png" alt="SelectPilot" className="h-7 w-7 rounded-lg" />
            <span className="text-sm font-semibold">SelectPilot</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">功能介绍</a>
            <a href="#pricing" className="hover:text-foreground transition-colors">定价</a>
            <a href="#faq" className="hover:text-foreground transition-colors">常见问题</a>
            <span>support@selectpilot.ai</span>
          </div>
        </div>
        <div className="mt-8 pt-6 border-t border-border text-center text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} SelectPilot. All rights reserved.
        </div>
      </div>
    </footer>
  );
}

/* ────────────────────────── MAIN ────────────────────────── */
export function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <Hero />
      <Features />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
    </div>
  );
}
