"use client";
import React, { useState } from "react";
import Link from "next/link";
import {
  Search, BarChart3, Globe2, Calculator, Shield, TrendingUp,
  ArrowRight, Check, ChevronDown, Menu, X, Zap, Bot, LineChart, ShoppingCart,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   SELECTPILOT — Premium Landing Page (taito.ai inspired)
   Clean, minimal, black+white with violet accent
   ═══════════════════════════════════════════════════════════════ */

/* ─── NAVBAR ─── */
function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="fixed top-0 inset-x-0 z-50 bg-white/80 backdrop-blur-xl border-b border-neutral-100">
      <nav className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <img src="/images/logo-icon.png" alt="SelectPilot" className="h-8 w-8 rounded-lg" />
          <span className="text-[17px] font-semibold tracking-tight text-neutral-900">SelectPilot</span>
        </Link>
        <ul className="hidden md:flex items-center gap-8 text-[14px] text-neutral-500">
          <li><a href="#features" className="hover:text-neutral-900 transition-colors">功能</a></li>
          <li><a href="#how" className="hover:text-neutral-900 transition-colors">工作流</a></li>
          <li><a href="#pricing" className="hover:text-neutral-900 transition-colors">定价</a></li>
          <li><a href="#faq" className="hover:text-neutral-900 transition-colors">FAQ</a></li>
        </ul>
        <div className="hidden md:flex items-center gap-3">
          <Link href="/login" className="px-4 py-2 text-[14px] text-neutral-600 hover:text-neutral-900 transition-colors">登录</Link>
          <Link href="/register" className="rounded-full bg-neutral-900 px-5 py-2.5 text-[14px] font-medium text-white hover:bg-neutral-800 transition-colors">免费开始</Link>
        </div>
        <button className="md:hidden" onClick={() => setOpen(!open)}>
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>
      {open && (
        <div className="md:hidden border-t border-neutral-100 bg-white px-6 py-4 space-y-3">
          <a href="#features" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">功能</a>
          <a href="#how" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">工作流</a>
          <a href="#pricing" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">定价</a>
          <a href="#faq" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">FAQ</a>
          <div className="flex gap-3 pt-2">
            <Link href="/login" className="flex-1 text-center rounded-full border border-neutral-200 px-4 py-2.5 text-sm font-medium">登录</Link>
            <Link href="/register" className="flex-1 text-center rounded-full bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white">注册</Link>
          </div>
        </div>
      )}
    </header>
  );
}

/* ─── HERO ─── */
function Hero() {
  return (
    <section className="pt-28 pb-16 md:pt-36 md:pb-24">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid md:grid-cols-2 items-center gap-12 md:gap-16">
          {/* Left */}
          <div>
            <Link href="/register" className="inline-flex items-center gap-2 rounded-full bg-violet-50 border border-violet-100 px-4 py-1.5 text-[13px] text-violet-700 mb-6 hover:bg-violet-100 transition-colors">
              AI 选品引擎正式上线 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <h1 className="text-[42px] md:text-[56px] font-semibold leading-[1.1] tracking-tight text-neutral-900 mb-6">
              用 AI 发现<br/>蓝海爆品机会
            </h1>
            <p className="text-lg text-neutral-500 leading-relaxed mb-8 max-w-[480px]">
              实时采集 TikTok Shop + 社媒趋势 + Amazon BSR 数据，AI Agent 自动完成市场调研、竞品分析、利润测算。对话即研究，数据即决策。
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <Link href="/register" className="inline-flex items-center justify-center gap-2 rounded-full bg-neutral-900 px-7 py-3.5 text-[15px] font-medium text-white hover:bg-neutral-800 transition-all hover:shadow-lg">
                免费开始使用
              </Link>
              <a href="#features" className="inline-flex items-center justify-center gap-2 rounded-full border border-neutral-200 px-7 py-3.5 text-[15px] font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
                了解更多
              </a>
            </div>
          </div>
          {/* Right — App screenshot */}
          <div className="relative">
            <div className="rounded-2xl border border-neutral-200 shadow-2xl shadow-neutral-200/50 overflow-hidden bg-white">
              <img src="/images/hero-app.png" alt="SelectPilot 产品界面" className="w-full" />
            </div>
            <div className="absolute -inset-4 bg-gradient-to-tr from-violet-100/40 via-transparent to-violet-100/20 rounded-3xl -z-10 blur-2xl" />
          </div>
        </div>

        {/* Logo bar */}
        <div className="mt-20 border-t border-neutral-100 pt-10">
          <p className="text-center text-[12px] uppercase tracking-widest text-neutral-400 mb-6">数据覆盖平台</p>
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12 text-neutral-400">
            {["TikTok Shop", "Amazon", "Douyin", "Xiaohongshu", "1688", "Weibo", "Bilibili", "Lemon8"].map((name) => (
              <span key={name} className="text-[14px] font-medium text-neutral-400 hover:text-neutral-600 transition-colors">{name}</span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── WHY SECTION (3 feature cards) ─── */
function WhySection() {
  return (
    <section id="features" className="py-20 md:py-28">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid md:grid-cols-[1fr_1.2fr] gap-8 md:gap-12 items-start mb-16">
          <div>
            <p className="text-[13px] font-medium uppercase tracking-widest text-violet-600 mb-3">为什么选择 SelectPilot？</p>
            <h2 className="text-[32px] md:text-[40px] font-semibold leading-[1.15] tracking-tight text-neutral-900">
              真实数据驱动选品，<br/>不靠猜测和经验
            </h2>
          </div>
          <p className="text-[16px] text-neutral-500 leading-relaxed md:pt-10">
            跨境电商卖家面临信息过载、数据零散的困境。SelectPilot 将 TikTok Shop 实时数据、Amazon BSR 排名、社媒趋势、采购成本全部整合到一个 AI 对话界面中，让你用自然语言完成原本需要数小时的市场调研。
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {[
            {
              title: "一个平台，全链路数据",
              desc: "品类排名、实时热销、社媒趋势、采购成本、利润测算，从发现到决策一站完成。",
              icon: BarChart3,
            },
            {
              title: "AI Agent 即时调研",
              desc: "对话式交互，输入一个品类或产品名称，AI 自动完成 8 阶段深度调研，产出 ECharts 图表报告。",
              icon: Bot,
            },
            {
              title: "26 国实时数据覆盖",
              desc: "支持全球 26 个国家/地区的 TikTok Shop、Amazon、社媒趋势数据，每日自动更新。",
              icon: Globe2,
            },
          ].map((f, i) => (
            <article key={i} className="group rounded-2xl border border-neutral-100 bg-neutral-50/50 p-7 hover:border-neutral-200 hover:bg-white hover:shadow-lg hover:shadow-neutral-100/50 transition-all">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white border border-neutral-100 shadow-sm">
                <f.icon className="h-5 w-5 text-violet-600" />
              </div>
              <h3 className="text-[15px] font-semibold text-neutral-900 mb-2">{f.title}</h3>
              <p className="text-[14px] text-neutral-500 leading-relaxed">{f.desc}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── HOW IT WORKS (workflow visualization) ─── */
function HowSection() {
  const steps = [
    { num: "01", title: "输入选品方向", desc: "告诉 AI 你想探索的品类、目标市场、预算范围。" },
    { num: "02", title: "AI 自动调研", desc: "Agent 并行采集 TikTok 热销、Amazon 排名、社媒趋势、1688 成本。" },
    { num: "03", title: "数据可视化", desc: "ECharts 交互图表呈现价格分布、销量趋势、竞品对比。" },
    { num: "04", title: "决策报告", desc: "综合利润测算 + 风险评估 + 推荐 SKU，一键导出。" },
  ];
  return (
    <section id="how" className="py-20 md:py-28 bg-neutral-50/70">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="text-center mb-16">
          <p className="text-[13px] font-medium uppercase tracking-widest text-violet-600 mb-3">工作流程</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold tracking-tight text-neutral-900">
            从灵感到决策，四步完成
          </h2>
        </div>
        <div className="grid md:grid-cols-4 gap-6">
          {steps.map((s) => (
            <div key={s.num} className="relative rounded-2xl border border-neutral-100 bg-white p-6">
              <span className="text-[40px] font-bold text-neutral-100 leading-none">{s.num}</span>
              <h3 className="mt-3 text-[15px] font-semibold text-neutral-900">{s.title}</h3>
              <p className="mt-2 text-[13px] text-neutral-500 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── FEATURES GRID (6 items) ─── */
function FeaturesGrid() {
  const items = [
    { icon: Search, title: "智能市场调研", desc: "AI Agent 8 阶段自动化调研，从品类扫描到竞品深挖。" },
    { icon: LineChart, title: "ECharts 图表报告", desc: "柱状图、折线图、饼图、雷达图，AI 产出自动渲染为交互式图表。" },
    { icon: ShoppingCart, title: "TikTok Shop 实时数据", desc: "28 个品类、95 款热销商品实时追踪，每日 0 点自动更新。" },
    { icon: Calculator, title: "利润测算引擎", desc: "14 项成本拆解 + 蒙特卡洛压力测试，精确计算利润率和亏损风险。" },
    { icon: Shield, title: "9 级反爬引擎", desc: "curl_cffi → Scrapling → patchright 等 9 级降级链，数据采集零中断。" },
    { icon: TrendingUp, title: "社媒趋势 × 8 平台", desc: "TikTok、抖音、微博、小红书、快手、B站、X、Lemon8 热榜聚合。" },
  ];
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="text-center mb-14">
          <p className="text-[13px] font-medium uppercase tracking-widest text-violet-600 mb-3">核心能力</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold tracking-tight text-neutral-900">
            完整的选品数据基础设施
          </h2>
          <p className="mt-4 text-[16px] text-neutral-500 max-w-2xl mx-auto">
            从数据采集到 AI 分析到可视化报告，每一步都为跨境电商卖家优化。
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((f, i) => (
            <div key={i} className="rounded-2xl border border-neutral-100 p-6 hover:border-neutral-200 hover:shadow-md transition-all">
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50">
                <f.icon className="h-[18px] w-[18px] text-violet-600" />
              </div>
              <h3 className="text-[15px] font-semibold text-neutral-900 mb-1.5">{f.title}</h3>
              <p className="text-[13px] text-neutral-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── STATS ─── */
function Stats() {
  const stats = [
    { value: "128,540+", label: "商品数据库规模" },
    { value: "26", label: "覆盖国家/地区" },
    { value: "8", label: "社媒平台趋势" },
    { value: "2000%+", label: "用户利润率目标" },
  ];
  return (
    <section className="py-16 bg-neutral-900 text-white">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((s, i) => (
            <div key={i} className="text-center">
              <div className="text-[32px] md:text-[40px] font-bold tracking-tight">{s.value}</div>
              <div className="mt-1 text-[13px] text-neutral-400">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── PRICING ─── */
const plans = [
  {
    name: "免费版",
    price: "¥0",
    period: "/月",
    desc: "适合初步体验 AI 选品能力",
    features: ["5 次 AI 调研/月", "品类浏览 & 热销榜", "1 个目标市场", "基础数据快照"],
    cta: "免费开始",
    highlighted: false,
  },
  {
    name: "专业版",
    price: "¥99",
    period: "/月",
    desc: "适合全职跨境电商卖家",
    features: ["100 次 AI 调研/月", "ECharts 交互式图表", "26 国全市场覆盖", "品类趋势追踪", "利润测算引擎", "每日定时刷新", "优先数据更新"],
    cta: "立即订阅",
    highlighted: true,
  },
  {
    name: "企业版",
    price: "¥299",
    period: "/月",
    desc: "适合团队和多店铺运营",
    features: ["无限 AI 调研", "所有专业版功能", "API 接口访问", "多人协作空间", "专属客户经理", "自定义报告模板", "SLA 保障"],
    cta: "联系我们",
    highlighted: false,
  },
];

function Pricing() {
  return (
    <section id="pricing" className="py-20 md:py-28 bg-neutral-50/70">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="text-center mb-14">
          <p className="text-[13px] font-medium uppercase tracking-widest text-violet-600 mb-3">定价方案</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold tracking-tight text-neutral-900">
            简单透明的定价
          </h2>
          <p className="mt-4 text-[16px] text-neutral-500">选择最适合你的方案，随时升级或降级。</p>
        </div>
        <div className="grid md:grid-cols-3 gap-5 max-w-4xl mx-auto">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`rounded-2xl border p-7 flex flex-col ${
                p.highlighted
                  ? "border-neutral-900 bg-white shadow-xl shadow-neutral-200/50 ring-1 ring-neutral-900"
                  : "border-neutral-200 bg-white"
              }`}
            >
              {p.highlighted && (
                <span className="self-start rounded-full bg-neutral-900 px-3 py-1 text-[11px] font-medium text-white mb-4">推荐</span>
              )}
              <h3 className="text-[15px] font-semibold text-neutral-900">{p.name}</h3>
              <div className="mt-3 flex items-baseline gap-0.5">
                <span className="text-[36px] font-bold text-neutral-900">{p.price}</span>
                <span className="text-[14px] text-neutral-400">{p.period}</span>
              </div>
              <p className="mt-2 text-[13px] text-neutral-500">{p.desc}</p>
              <ul className="mt-6 space-y-2.5 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-[13px] text-neutral-600">
                    <Check className="h-4 w-4 mt-0.5 flex-shrink-0 text-violet-600" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className={`mt-6 flex items-center justify-center rounded-full py-3 text-[14px] font-medium transition-colors ${
                  p.highlighted
                    ? "bg-neutral-900 text-white hover:bg-neutral-800"
                    : "border border-neutral-200 text-neutral-700 hover:bg-neutral-50"
                }`}
              >
                {p.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── TESTIMONIAL ─── */
function Testimonial() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-[800px] px-6 text-center">
        <blockquote className="text-[20px] md:text-[24px] font-medium leading-relaxed text-neutral-800 mb-6">
          "以前选品靠刷 TikTok + 翻 Amazon 评论，一个品类要花两三天。用了 SelectPilot 之后，输入品类名称 AI 就自动调研完了，图表报告一目了然，选品决策时间从天缩短到分钟。"
        </blockquote>
        <div className="text-[14px] text-neutral-500">
          <span className="font-medium text-neutral-700">李明</span> · TikTok Shop 卖家，月 GMV $50K+
        </div>
      </div>
    </section>
  );
}

/* ─── FAQ ─── */
const faqs = [
  {
    q: "SelectPilot 的数据来源是什么？",
    a: "我们通过 TikHub API 获取 TikTok Shop 实时数据（品类排名、热销商品），同时采集 Amazon BSR、8 个社媒平台趋势数据、1688/Made-in-China 采购成本。所有数据均为真实实时数据，不编造。",
  },
  {
    q: "免费版有什么限制？",
    a: "免费版每月可进行 5 次 AI 调研对话，可浏览品类榜单和热销榜，限 1 个目标市场。升级专业版后解锁 100 次调研、26 国覆盖和 ECharts 图表。",
  },
  {
    q: "AI Agent 的调研质量如何保证？",
    a: "AI Agent 基于 DeepSeek 大模型，配合 8 阶段结构化调研流程和实时数据工具链。每次调研都基于真实数据产出结论，如 TikTok Shop 无数据时会明确标注「通道未就绪」而非编造。",
  },
  {
    q: "支持哪些国家/地区？",
    a: "目前支持 26 个国家/地区：美国、英国、德国、法国、日本、韩国、新加坡、马来西亚、泰国、越南、印尼、菲律宾、巴西等。每个国家的 TikTok Shop 品类和热销数据独立采集。",
  },
  {
    q: "定价是否包含 API 调用费用？",
    a: "是的。月费已包含所有数据采集和 AI 调研费用，无隐藏消耗。企业版额外提供 REST API 接口，方便与内部系统对接。",
  },
];

function FAQ() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  return (
    <section id="faq" className="py-20 md:py-28 bg-neutral-50/70">
      <div className="mx-auto max-w-[720px] px-6">
        <div className="text-center mb-12">
          <p className="text-[13px] font-medium uppercase tracking-widest text-violet-600 mb-3">常见问题</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold tracking-tight text-neutral-900">FAQ</h2>
        </div>
        <div className="space-y-3">
          {faqs.map((f, i) => (
            <div key={i} className="rounded-xl border border-neutral-200 bg-white overflow-hidden">
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 px-6 py-4 text-left"
              >
                <span className="text-[14px] font-medium text-neutral-900">{f.q}</span>
                <ChevronDown className={`h-4 w-4 flex-shrink-0 text-neutral-400 transition-transform ${openIdx === i ? "rotate-180" : ""}`} />
              </button>
              {openIdx === i && (
                <div className="px-6 pb-4 text-[13px] text-neutral-500 leading-relaxed">{f.a}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── BOTTOM CTA ─── */
function BottomCTA() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-[1200px] px-6 text-center">
        <h2 className="text-[32px] md:text-[44px] font-semibold tracking-tight text-neutral-900 mb-4">
          开始用 AI 发现下一个爆品
        </h2>
        <p className="text-[16px] text-neutral-500 max-w-xl mx-auto mb-8">
          真实数据、智能分析、一键报告。加入已经在使用 SelectPilot 的跨境电商卖家。
        </p>
        <Link href="/register" className="inline-flex items-center gap-2 rounded-full bg-neutral-900 px-8 py-4 text-[15px] font-medium text-white hover:bg-neutral-800 transition-all hover:shadow-lg">
          免费注册 <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

/* ─── FOOTER ─── */
function Footer() {
  return (
    <footer className="border-t border-neutral-100 bg-white py-12">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-10">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-3">
              <img src="/images/logo-icon.png" alt="SelectPilot" className="h-7 w-7 rounded-md" />
              <span className="text-[15px] font-semibold text-neutral-900">SelectPilot</span>
            </Link>
            <p className="text-[12px] text-neutral-400 leading-relaxed">AI 驱动的跨境电商选品决策引擎</p>
          </div>
          {/* Links */}
          {[
            { title: "产品", links: [["功能", "#features"], ["工作流", "#how"], ["定价", "#pricing"]] },
            { title: "资源", links: [["FAQ", "#faq"], ["博客", "#"], ["API 文档", "#"]] },
            { title: "公司", links: [["关于我们", "#"], ["联系方式", "#"]] },
            { title: "法律", links: [["隐私政策", "#"], ["服务条款", "#"]] },
          ].map((col) => (
            <div key={col.title}>
              <h4 className="text-[12px] font-semibold uppercase tracking-wider text-neutral-900 mb-3">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map(([label, href]) => (
                  <li key={label}><a href={href} className="text-[13px] text-neutral-500 hover:text-neutral-900 transition-colors">{label}</a></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-neutral-100 pt-6 text-center text-[12px] text-neutral-400">
          © 2026 SelectPilot. All rights reserved.
        </div>
      </div>
    </footer>
  );
}

/* ═══ EXPORT ═══ */
export function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-neutral-900 antialiased">
      <Navbar />
      <main>
        <Hero />
        <WhySection />
        <HowSection />
        <FeaturesGrid />
        <Stats />
        <Pricing />
        <Testimonial />
        <FAQ />
        <BottomCTA />
      </main>
      <Footer />
    </div>
  );
}
