"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Compass, BarChart3, TrendingUp, Search, Globe, Zap,
  Shield, Clock, ArrowRight, Check, ChevronDown, ChevronUp,
  Star, Users, FileText, Bot
} from "lucide-react";

const NAV_LINKS = [
  { label: "功能", href: "#features" },
  { label: "定价", href: "#pricing" },
  { label: "常见问题", href: "#faq" },
];

function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-200/60">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/25">
            <Compass className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold text-slate-900 tracking-tight">蓝海罗盘</span>
        </Link>
        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map(l => (
            <a key={l.href} href={l.href} className="text-sm text-slate-600 hover:text-slate-900 transition-colors">{l.label}</a>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm font-medium text-slate-700 hover:text-slate-900 px-4 py-2 rounded-lg transition-colors">
            登录
          </Link>
          <Link href="/register" className="text-sm font-semibold text-white bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 px-5 py-2.5 rounded-xl shadow-lg shadow-orange-500/25 transition-all hover:shadow-orange-500/40">
            免费试用
          </Link>
        </div>
      </div>
    </nav>
  );
}

function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-orange-50/80 via-white to-white" />
      <div className="absolute top-20 left-1/4 w-96 h-96 bg-orange-200/30 rounded-full blur-3xl" />
      <div className="absolute top-40 right-1/4 w-80 h-80 bg-amber-200/20 rounded-full blur-3xl" />

      <div className="relative max-w-5xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-orange-100/80 border border-orange-200/60 text-orange-700 text-sm font-medium mb-8">
            <Zap className="w-3.5 h-3.5" />
            AI 驱动的跨境电商选品决策引擎
          </div>

          <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-900 leading-[1.1]">
            用 AI 发现
            <span className="bg-gradient-to-r from-orange-500 via-amber-500 to-orange-600 bg-clip-text text-transparent"> 蓝海商机</span>
          </h1>

          <p className="mt-6 text-lg md:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            对话式 AI 选品助手，8 阶段自动化市场调研，真实数据驱动的选品决策报告。
            <br className="hidden md:block" />
            从 Amazon BSR 到 1688 采购成本，一站式完成。
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="group flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-semibold rounded-2xl shadow-xl shadow-orange-500/30 transition-all hover:shadow-orange-500/50 text-lg">
              免费开始使用
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <a href="#features" className="flex items-center gap-2 px-8 py-4 bg-white hover:bg-slate-50 text-slate-700 font-medium rounded-2xl border border-slate-200 shadow-sm transition-colors text-lg">
              了解更多
            </a>
          </div>
        </motion.div>

        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-8"
        >
          {[
            { value: "56+", label: "AI 工具", icon: Bot },
            { value: "26", label: "目标国家", icon: Globe },
            { value: "9 级", label: "反爬引擎", icon: Shield },
            { value: "实时", label: "数据更新", icon: Clock },
          ].map((s, i) => (
            <div key={i} className="text-center">
              <s.icon className="w-6 h-6 text-orange-500 mx-auto mb-2" />
              <div className="text-3xl font-bold text-slate-900">{s.value}</div>
              <div className="text-sm text-slate-500 mt-1">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

const FEATURES = [
  {
    icon: Search, title: "智能市场调研",
    desc: "AI Agent 自动完成 8 阶段选品调研，从品类扫描到竞品深挖，真实数据驱动决策。",
  },
  {
    icon: BarChart3, title: "实时数据仪表盘",
    desc: "Amazon BSR 热销榜、TikTok 社媒趋势、品类价格/销量趋势图表，一目了然。",
  },
  {
    icon: Globe, title: "26 国多市场覆盖",
    desc: "支持美国、英国、德国、日本等 26 个国家/地区，一键切换目标市场。",
  },
  {
    icon: TrendingUp, title: "利润测算引擎",
    desc: "14 项成本拆解 + 蒙特卡洛压力测试，精确计算利润率和亏损风险。",
  },
  {
    icon: Shield, title: "9 级反爬引擎",
    desc: "curl_cffi → Scrapling → patchright → botasaurus 等 9 级降级链，确保数据采集稳定。",
  },
  {
    icon: FileText, title: "自动报告生成",
    desc: "AI 自动产出带图表的选品决策报告，含 ECharts 交互式可视化。",
  },
];

function FeaturesSection() {
  return (
    <section id="features" className="py-24 bg-slate-50/50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="eyebrow text-orange-600 mb-3">核心功能</div>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 tracking-tight">
            一站式选品决策平台
          </h2>
          <p className="mt-4 text-lg text-slate-500 max-w-2xl mx-auto">
            从市场调研到采购成本，从竞品分析到利润测算，全流程 AI 自动化
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="group bg-white rounded-2xl p-7 border border-slate-200/60 shadow-sm hover:shadow-lg hover:border-orange-200/60 transition-all duration-300"
            >
              <div className="w-12 h-12 rounded-xl bg-orange-100 flex items-center justify-center mb-5 group-hover:bg-orange-500 transition-colors">
                <f.icon className="w-6 h-6 text-orange-600 group-hover:text-white transition-colors" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">{f.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

const PLANS = [
  {
    name: "免费版",
    price: "0",
    period: "永久免费",
    desc: "适合个人卖家试用",
    highlight: false,
    features: [
      "5 次 AI 调研/月",
      "1 个品类追踪",
      "基础数据仪表盘",
      "社区支持",
    ],
    cta: "免费开始",
  },
  {
    name: "专业版",
    price: "99",
    period: "/月",
    desc: "适合成长期卖家",
    highlight: true,
    features: [
      "100 次 AI 调研/月",
      "10 个品类追踪",
      "ECharts 交互式报告",
      "26 国市场数据",
      "利润测算引擎",
      "实时数据刷新",
      "邮件提醒",
      "优先技术支持",
    ],
    cta: "立即升级",
  },
  {
    name: "企业版",
    price: "299",
    period: "/月",
    desc: "适合团队和大卖",
    highlight: false,
    features: [
      "无限 AI 调研",
      "无限品类追踪",
      "API 接口访问",
      "多人协作",
      "自定义报告模板",
      "专属客户经理",
      "SLA 服务保障",
      "数据导出 Excel/PDF",
    ],
    cta: "联系我们",
  },
];

function PricingSection() {
  return (
    <section id="pricing" className="py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="eyebrow text-orange-600 mb-3">灵活定价</div>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 tracking-tight">
            选择适合你的方案
          </h2>
          <p className="mt-4 text-lg text-slate-500">
            从免费试用到企业定制，满足不同阶段需求
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {PLANS.map((plan, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15 }}
              className={`relative rounded-2xl p-8 flex flex-col ${
                plan.highlight
                  ? "bg-gradient-to-b from-orange-500 to-amber-500 text-white shadow-2xl shadow-orange-500/30 scale-105 border-0"
                  : "bg-white border border-slate-200 shadow-sm"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-slate-900 text-white text-xs font-semibold rounded-full">
                  最受欢迎
                </div>
              )}
              <div className="mb-6">
                <h3 className={`text-lg font-semibold ${plan.highlight ? "text-white" : "text-slate-900"}`}>{plan.name}</h3>
                <p className={`text-sm mt-1 ${plan.highlight ? "text-orange-100" : "text-slate-500"}`}>{plan.desc}</p>
              </div>
              <div className="mb-8">
                <span className={`text-5xl font-extrabold ${plan.highlight ? "text-white" : "text-slate-900"}`}>
                  ¥{plan.price}
                </span>
                <span className={`text-sm ml-1 ${plan.highlight ? "text-orange-100" : "text-slate-500"}`}>
                  {plan.period}
                </span>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f, j) => (
                  <li key={j} className="flex items-start gap-2.5 text-sm">
                    <Check className={`w-4 h-4 mt-0.5 flex-shrink-0 ${plan.highlight ? "text-orange-200" : "text-orange-500"}`} />
                    <span className={plan.highlight ? "text-white/90" : "text-slate-600"}>{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className={`block text-center py-3 rounded-xl font-semibold transition-all ${
                  plan.highlight
                    ? "bg-white text-orange-600 hover:bg-orange-50 shadow-lg"
                    : "bg-slate-900 text-white hover:bg-slate-800"
                }`}
              >
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

const FAQ_ITEMS = [
  { q: "蓝海罗盘和其他选品工具有什么区别？", a: "蓝海罗盘是国内首个 AI Agent 驱动的选品工具，不同于传统工具的手动数据查询，我们的 AI 智能体自动完成 8 阶段调研流程，真实抓取 Amazon、1688 等平台数据，并产出带图表的决策报告。" },
  { q: "数据来源是真实的吗？", a: "是的。所有数据均来自真实爬取（Amazon BSR、TikTok 热销、1688/Made-in-China 采购价等），不使用模拟数据。我们的 9 级反爬引擎确保数据采集的稳定性。" },
  { q: "免费版有什么限制？", a: "免费版每月可进行 5 次 AI 调研，追踪 1 个品类，包含基础数据仪表盘。适合个人卖家体验产品。升级到专业版可解锁更多功能。" },
  { q: "支持哪些电商平台？", a: "目前支持 Amazon（US/UK/DE/JP 等 15 站）、1688、Made-in-China、DHgate、GlobalSources 等主流 B2B/B2C 平台，以及 TikTok、Reddit 等社媒趋势数据。" },
];

function FAQSection() {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <section id="faq" className="py-24 bg-slate-50/50">
      <div className="max-w-3xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="eyebrow text-orange-600 mb-3">常见问题</div>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 tracking-tight">
            有疑问？看这里
          </h2>
        </div>
        <div className="space-y-3">
          {FAQ_ITEMS.map((item, i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-slate-200/60 overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between p-5 text-left hover:bg-slate-50/50 transition-colors"
              >
                <span className="font-medium text-slate-900">{item.q}</span>
                {open === i
                  ? <ChevronUp className="w-5 h-5 text-slate-400 flex-shrink-0" />
                  : <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />}
              </button>
              {open === i && (
                <div className="px-5 pb-5 text-slate-600 text-sm leading-relaxed border-t border-slate-100 pt-4">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FooterSection() {
  return (
    <footer className="bg-slate-900 text-slate-400 py-16">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col md:flex-row items-start justify-between gap-10">
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center">
                <Compass className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-white">蓝海罗盘</span>
            </div>
            <p className="text-sm max-w-xs">AI 驱动的跨境电商选品决策引擎，让数据说话，用智能发现蓝海商机。</p>
          </div>
          <div className="flex gap-16">
            <div>
              <h4 className="text-white font-semibold text-sm mb-4">产品</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition-colors">功能介绍</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">定价</a></li>
                <li><a href="#faq" className="hover:text-white transition-colors">常见问题</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm mb-4">联系</h4>
              <ul className="space-y-2 text-sm">
                <li>support@blueocean.ai</li>
              </ul>
            </div>
          </div>
        </div>
        <div className="mt-12 pt-8 border-t border-slate-800 text-sm text-center">
          &copy; {new Date().getFullYear()} 蓝海罗盘. All rights reserved.
        </div>
      </div>
    </footer>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <PricingSection />
      <FAQSection />
      <FooterSection />
    </div>
  );
}
