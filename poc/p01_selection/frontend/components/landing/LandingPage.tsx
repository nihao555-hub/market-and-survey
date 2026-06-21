"use client";
import React, { useState } from "react";
import Link from "next/link";
import { ArrowRight, ChevronDown, Menu, X, Search, BarChart3, LineChart, Calculator, Shield, TrendingUp, Bot, Globe2, ShoppingCart, Zap } from "lucide-react";

function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="fixed top-0 inset-x-0 z-50">
      <nav className="mx-auto flex h-[80px] max-w-[1500px] items-center justify-between px-[40px]">
        <Link href="/" className="flex items-center gap-2">
          <img src="/images/logo-icon.png" alt="SelectPilot" className="h-7 w-7 rounded-md" />
          <span className="text-[20px] font-medium tracking-[-0.2px] text-[#0f0e0d]">SelectPilot</span>
        </Link>
        <ul className="hidden md:flex items-center gap-1">
          {[{label: "产品", href: "product"}, {label: "解决方案", href: "solutions"}, {label: "定价", href: "pricing"}, {label: "博客", href: "blog"}].map((item) => (
            <li key={item.href}>
              <a href={`#${item.href}`} className="flex items-center h-[40px] px-[15px] rounded-[6px] text-[16px] text-[#0f0e0d] hover:bg-[#f5f5f4] transition-colors">
                {item.label}
              </a>
            </li>
          ))}
        </ul>
        <div className="hidden md:flex items-center gap-1">
          <Link href="/login" className="flex items-center h-[40px] px-[15px] rounded-[6px] text-[16px] text-[#0f0e0d] hover:bg-[#f5f5f4] transition-colors">
            登录
          </Link>
          <Link href="/register" className="flex items-center h-[40px] px-[15px] rounded-[6px] bg-[#0f0e0d] text-[16px] font-medium text-[#fafaf9] hover:bg-[#262524] transition-colors">
            免费开始
          </Link>
        </div>
        <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>
      {open && (
        <div className="md:hidden bg-[#fafaf9] border-t border-[#e7e5e4] px-[40px] py-6 space-y-4">
          {[{label: "产品", href: "product"}, {label: "解决方案", href: "solutions"}, {label: "定价", href: "pricing"}, {label: "博客", href: "blog"}].map((item) => (
            <a key={item.href} href={`#${item.href}`} onClick={() => setOpen(false)} className="block text-[16px] text-[#0f0e0d]">{item.label}</a>
          ))}
          <div className="flex gap-3 pt-3">
            <Link href="/login" className="flex-1 text-center h-[40px] leading-[40px] rounded-[6px] border border-[#e7e5e4] text-[16px] text-[#0f0e0d]">登录</Link>
            <Link href="/register" className="flex-1 text-center h-[40px] leading-[40px] rounded-[6px] bg-[#0f0e0d] text-[16px] text-[#fafaf9]">免费开始</Link>
          </div>
        </div>
      )}
    </header>
  );
}

function Hero() {
  return (
    <section className="pt-[80px]">
      <div className="mx-auto max-w-[1500px] px-[40px] pt-[80px] pb-0 lg:pb-0">
        <div className="lg:flex lg:items-start lg:gap-12">
          {/* Left: text content */}
          <div className="lg:flex-1 lg:pt-[40px] lg:pb-[80px]">
            {/* Announcement link */}
            <a href="#product" className="inline-flex items-center gap-2 text-[16px] text-[#524f49] hover:text-[#0f0e0d] transition-colors mb-8">
              AI 驱动的智能选品引擎
              <ArrowRight className="h-4 w-4" />
            </a>

            {/* Headline - font-weight 400 like taito.ai */}
            <h1 className="text-[clamp(40px,5vw,61px)] font-normal leading-[1.2] tracking-[-0.025em] text-[#0f0e0d] max-w-[600px]">
              让选品调研全自动运行
            </h1>

            {/* Description */}
            <p className="text-[16px] leading-[1.6] text-[#524f49] mt-6 max-w-[440px]">
              TikTok Shop 排名、社交趋势、Amazon BSR 数据、利润建模，全部自动化。为跨境卖家打造的智能选品平台——让你专注增长，而非手动搜集数据。
            </p>

            {/* CTA - matches taito hero CTA exactly */}
            <div className="mt-8">
              <Link href="/register" className="inline-flex items-center h-[50px] px-[20px] rounded-[8px] bg-[#0f0e0d] text-[20px] font-medium text-[#fafaf9] hover:bg-[#262524] transition-colors">
                免费开始
              </Link>
            </div>
          </div>

          {/* Right: product screenshot - like taito.ai hero image */}
          <div className="mt-12 lg:mt-0 lg:flex-1 relative">
            <div className="rounded-[12px] border border-[#e7e5e4] shadow-2xl overflow-hidden bg-[var(--gray-1)]">
              <img src="/images/screenshot-workspace.png" alt="SelectPilot workspace" className="w-full" />
            </div>
          </div>
        </div>
      </div>

      {/* Logo marquee - with border-top like taito.ai */}
      <div className="border-t border-[#e7e5e4] mt-16 lg:mt-0">
        <div className="mx-auto max-w-[1500px] px-[40px] py-[24px]">
          <div className="flex items-center gap-[48px] overflow-hidden">
            <div className="flex items-center gap-[48px] animate-marquee whitespace-nowrap">
              {["TikTok Shop", "Amazon", "1688", "Douyin", "Xiaohongshu", "Weibo", "Bilibili", "Lemon8", "TikTok Shop", "Amazon", "1688", "Douyin"].map((name, i) => (
                <span key={i} className="text-[14px] font-medium text-[#a8a29e] tracking-wide flex-shrink-0">{name}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function WhySection() {
  return (
    <section id="product" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        {/* Header: 2-column like taito.ai */}
        <header className="lg:flex lg:items-start lg:gap-[80px] mb-[60px]">
          <div className="lg:flex-1">
            <p className="text-[16px] text-[#524f49] mb-4">为什么选择 SelectPilot？</p>
            <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
              提升销售额，<br />而非增加调研负担
            </h2>
          </div>
          <p className="lg:flex-1 text-[16px] leading-[1.6] text-[#524f49] mt-6 lg:mt-2">
            从发现产品到验证利润，调研工作量往往在收入增长之前就已经翻倍。SelectPilot 自动完成操作性调研，让你专注卖货，而非爬取数据。
          </p>
        </header>

        {/* 3-column article cards - like taito.ai */}
        <div className="grid md:grid-cols-3 gap-4">
          <article className="rounded-[12px] border border-[#e7e5e4] bg-[var(--gray-1)] overflow-hidden group">
            <div className="aspect-[4/3] bg-[#f5f5f4] overflow-hidden relative">
              <img src="/images/screenshot-research.png" alt="AI Research" className="w-full h-full object-cover object-top" />
              {/* Overlay icons like taito.ai */}
              <div className="absolute bottom-4 left-4 flex gap-2">
                <div className="w-10 h-10 rounded-[8px] bg-[var(--gray-1)]/90 backdrop-blur flex items-center justify-center shadow-sm">
                  <Search className="w-5 h-5 text-[#524f49]" />
                </div>
                <div className="w-10 h-10 rounded-[8px] bg-[var(--gray-1)]/90 backdrop-blur flex items-center justify-center shadow-sm">
                  <BarChart3 className="w-5 h-5 text-[#524f49]" />
                </div>
                <div className="w-10 h-10 rounded-[8px] bg-[var(--gray-1)]/90 backdrop-blur flex items-center justify-center shadow-sm">
                  <TrendingUp className="w-5 h-5 text-[#524f49]" />
                </div>
              </div>
            </div>
            <div className="p-6">
              <h3 className="text-[16px] font-medium text-[#0f0e0d] mb-2">一个平台完成所有选品调研</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">
                市场扫描、趋势跟踪、竞品分析、利润建模，全部在一个地方自动运行。不再在多个表格间复制粘贴。
              </p>
            </div>
          </article>

          <article className="rounded-[12px] border border-[#e7e5e4] bg-[var(--gray-1)] overflow-hidden group">
            <div className="aspect-[4/3] bg-[#f5f5f4] overflow-hidden relative">
              <img src="/images/screenshot-categories.png" alt="Multi-platform" className="w-full h-full object-cover object-top" />
              {/* Chat mock overlay like taito.ai's Slack integration card */}
              <div className="absolute bottom-4 left-4 right-4 bg-[var(--gray-1)]/95 backdrop-blur rounded-[8px] p-3 shadow-sm">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-5 h-5 rounded-full bg-[#0f0e0d] flex items-center justify-center">
                    <Bot className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-[12px] font-medium text-[#0f0e0d]">SelectPilot</span>
                  <span className="text-[11px] text-[#a8a29e]">刚刚</span>
                </div>
                <p className="text-[12px] text-[#524f49]">在家居园艺品类发现 24 个趋势产品，覆盖 3 个市场...</p>
              </div>
            </div>
            <div className="p-6">
              <h3 className="text-[16px] font-medium text-[#0f0e0d] mb-2">数据在哪里，就在哪里用</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">
                一个界面访问 TikTok Shop、Amazon、1688 和 8 个社交平台。产品数据只需一次对话即可获取。
              </p>
            </div>
          </article>

          <article className="rounded-[12px] border border-[#e7e5e4] bg-[var(--gray-1)] overflow-hidden group">
            <div className="aspect-[4/3] bg-[#f5f5f4] overflow-hidden relative">
              <img src="/images/screenshot-hotselling.png" alt="Global Coverage" className="w-full h-full object-cover object-top" />
              {/* Country list overlay like taito.ai's policies card */}
              <div className="absolute top-4 right-4 bg-[var(--gray-1)]/95 backdrop-blur rounded-[8px] p-3 shadow-sm">
                <p className="text-[12px] font-medium text-[#0f0e0d] mb-2">市场覆盖</p>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px]">🇺🇸</span>
                    <span className="text-[12px] text-[#524f49]">美国</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[12px]">🇬🇧</span>
                    <span className="text-[12px] text-[#524f49]">英国</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[12px]">🇩🇪</span>
                    <span className="text-[12px] text-[#524f49]">德国</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-6">
              <h3 className="text-[16px] font-medium text-[#0f0e0d] mb-2">26 国家覆盖，无需工人</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">
                本地市场数据、品类排名、价格情报从第一天就自动运行。无需手动修复，没有过期数据。默认就是正确的。
              </p>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    { icon: Search, title: "市场扫描", desc: "AI Agent 完成 8 阶段结构化调研，从品类扫描到竞品深度分析。" },
    { icon: TrendingUp, title: "趋势跟踪", desc: "来自 TikTok、抖音、微博、小红书、快手、B站、X 和 Lemon8 的实时趋势。" },
    { icon: ShoppingCart, title: "爆品排行榜", desc: "28 个品类覆盖 26 个国家，每日午夜自动刷新。竞争指数量化。" },
    { icon: LineChart, title: "ECharts 可视化", desc: "AI 输出自动渲染为交互式柱状图、折线图、饼图和雷达图。" },
    { icon: Calculator, title: "利润建模", desc: "14 项成本拆解，配合蒙特卡洛 10,000 场景压力测试。" },
    { icon: Shield, title: "9 级反检测", desc: "curl_cffi → Scrapling → Patchright 降级链，确保数据采集零中断。" },
  ];

  return (
    <section id="features" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">核心能力</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d] max-w-[500px]">
            从零到决策，无需手动操作
          </h2>
          <p className="mt-4 text-[16px] leading-[1.6] text-[#524f49] max-w-[520px]">
            市场数据、竞品分析、利润计算、趋势信号自动运行。你的团队永远不需要手动追踪。
          </p>
        </header>

        <ul className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-[#e7e5e4] rounded-[12px] overflow-hidden border border-[#e7e5e4]">
          {features.map((f, i) => (
            <li key={i} className="bg-[#fafaf9] p-[32px]">
              <f.icon className="h-5 w-5 text-[#78716c] mb-5" />
              <h3 className="text-[16px] font-medium text-[#0f0e0d] mb-2">{f.title}</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">{f.desc}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function WorkflowSection() {
  return (
    <section id="solutions" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">AI 智能体</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            设置一次，永久调研。
          </h2>
          <p className="mt-4 text-[16px] leading-[1.6] text-[#524f49] max-w-[520px]">
            将市场扫描、趋势分析、利润建模等选品调研任务自动化为无代码自主 Agent 工作流。
          </p>
        </header>

        <div className="lg:flex lg:gap-[60px] lg:items-start">
          {/* Left: feature list */}
          <div className="lg:flex-1 space-y-[32px]">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Search className="w-5 h-5 text-[#78716c]" />
                <h3 className="text-[16px] font-medium text-[#0f0e0d]">市场情报</h3>
              </div>
              <p className="text-[16px] leading-[1.6] text-[#524f49] pl-8">
                品类扫描、竞品跟踪、爆品检测端到端运行为无代码工作流。调研旅程的每一步，都已处理。
              </p>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Calculator className="w-5 h-5 text-[#78716c]" />
                <h3 className="text-[16px] font-medium text-[#0f0e0d]">利润验证</h3>
              </div>
              <p className="text-[16px] leading-[1.6] text-[#524f49] pl-8">
                成本结构、物流费用、利润计算为每个产品机会打包完成。无需手动表格核对。
              </p>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Bot className="w-5 h-5 text-[#78716c]" />
                <h3 className="text-[16px] font-medium text-[#0f0e0d]">调研助手</h3>
              </div>
              <p className="text-[16px] leading-[1.6] text-[#524f49] pl-8">
                询问品类、趋势、产品可行性——基于你的实时市场数据，而非通用 AI。
              </p>
            </div>
          </div>

          {/* Right: workflow visual */}
          <div className="mt-10 lg:mt-0 lg:flex-1">
            <div className="rounded-[12px] border border-[#e7e5e4] bg-[var(--gray-1)] p-6 shadow-sm">
              <p className="text-[14px] text-[#524f49] mb-4 border-b border-[#e7e5e4] pb-4">调研美国市场家居园艺品类趋势产品</p>
              <div className="space-y-3">
                {[
                  { title: "扫描品类", desc: "28 个子品类已分析" },
                  { title: "识别爆品", desc: "按销售速度排名前 50" },
                  { title: "验证利润", desc: "14 项成本拆解已应用" },
                  { title: "生成报告", desc: "ECharts 可视化 + 推荐建议" },
                ].map((step, i) => (
                  <div key={i} className="flex items-start gap-3 py-2">
                    <div className="w-6 h-6 rounded-full bg-[#0f0e0d] text-[#fafaf9] text-[11px] font-medium flex items-center justify-center flex-shrink-0 mt-0.5">
                      ✓
                    </div>
                    <div>
                      <h4 className="text-[14px] font-medium text-[#0f0e0d]">{step.title}</h4>
                      <p className="text-[13px] text-[#a8a29e]">{step.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function BuiltForSection() {
  const roles = [
    {
      eyebrow: "精益增长",
      title: "个人卖家",
      desc: "不增加人员就能规模化选品调研。只在机会需要人工判断时才介入。",
    },
    {
      eyebrow: "战略聚焦",
      title: "团队负责人",
      desc: "数小时的手动数据采集自动完成。战略决策留给你。",
    },
    {
      eyebrow: "最佳实践",
      title: "代运机构",
      desc: "构建可规模化的客户调研系统。数据采集和报告，已处理。",
    },
  ];

  return (
    <section className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">为谁而建</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            不同角色，同一产品。
          </h2>
        </header>

        <div className="grid md:grid-cols-3 gap-4">
          {roles.map((role, i) => (
            <div key={i} className="rounded-[12px] border border-[#e7e5e4] bg-[var(--gray-1)] p-8 flex flex-col">
              <p className="text-[14px] text-[#a8a29e] mb-2">{role.eyebrow}</p>
              <h3 className="text-[20px] font-medium text-[#0f0e0d] mb-3">{role.title}</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">{role.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatsSection() {
  const stats = [
    { value: "128K+", label: "实时数据库跟踪产品数" },
    { value: "26", label: "TikTok Shop 全覆盖国家数" },
    { value: "8", label: "监控趋势的社交平台数" },
    { value: "￥0", label: "隐藏费用——定价包含所有数据成本" },
  ];

  return (
    <section className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">用数字说话</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            产品背后的数据
          </h2>
        </header>
        <dl className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((s, i) => (
            <div key={i}>
              <dd className="text-[clamp(36px,4vw,48px)] font-normal tracking-[-0.02em] text-[#0f0e0d]">{s.value}</dd>
              <dt className="mt-3 text-[16px] leading-[1.5] text-[#524f49]">{s.label}</dt>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function TestimonialSection() {
  return (
    <section className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <figure className="max-w-[800px]">
          <blockquote className="text-[clamp(18px,2vw,22px)] leading-[1.6] text-[#44403c] font-normal">
            &ldquo;以前每个品类调研要花 2-3 天，在 TikTok 和 Amazon 之间反复对比。现在 SelectPilot 的 AI 10 分钟就能出一份完整的调研报告，还带交互式图表。完全改变了我的选品方式。&rdquo;
          </blockquote>
          <figcaption className="mt-8 text-[16px] text-[#524f49]">
            <span className="font-medium text-[#0f0e0d]">李明</span> &middot; TikTok Shop 卖家，月 GMV $50K+
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

function SecuritySection() {
  const badges = [
    { label: "企业级", sub: "数据安全" },
    { label: "多层级", sub: "反检测" },
    { label: "实时", sub: "数据新鲜度" },
    { label: "26 国家", sub: "市场覆盖" },
  ];

  return (
    <section className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="lg:flex lg:items-start lg:gap-[80px] mb-[60px]">
          <div className="lg:flex-1">
            <p className="text-[16px] text-[#524f49] mb-4">安全</p>
            <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
              企业级可靠性，默认内置
            </h2>
          </div>
          <p className="lg:flex-1 text-[16px] leading-[1.6] text-[#524f49] mt-6 lg:mt-2">
            作为卖家，你的选品数据和策略是核心竞争力。SelectPilot 使用 9 级反检测引擎、加密数据存储和自动每日刷新，确保你的情报始终准确且安全。
          </p>
        </header>
        <ul className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {badges.map((b, i) => (
            <li key={i} className="rounded-[12px] border border-[#e7e5e4] bg-[var(--gray-1)] p-6 flex items-center gap-4">
              <Shield className="h-5 w-5 text-[#78716c] flex-shrink-0" />
              <div>
                <div className="text-[16px] font-medium text-[#0f0e0d]">{b.label}</div>
                <div className="text-[14px] text-[#a8a29e]">{b.sub}</div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

const plans = [
  {
    name: "免费版",
    price: "￥0",
    period: "/月",
    desc: "体验 AI 选品调研",
    features: ["5 次 AI 调研/月", "品类浏览与排名", "1 个目标市场", "基础数据快照"],
    cta: "免费开始",
    highlighted: false,
  },
  {
    name: "专业版",
    price: "￥15",
    period: "/月",
    desc: "为全职跨境卖家打造",
    features: ["100 次 AI 调研/月", "ECharts 交互式报告", "26 国家全覆盖", "品类趋势跟踪", "利润建模引擎", "每日自动刷新", "优先数据更新"],
    cta: "立即订阅",
    highlighted: true,
  },
  {
    name: "企业版",
    price: "￥49",
    period: "/月",
    desc: "为团队和多店铺运营打造",
    features: ["无限 AI 调研", "包含专业版所有功能", "API 接入", "团队协作工作区", "专属客户经理", "自定义报告模板", "SLA 保障"],
    cta: "联系我们",
    highlighted: false,
  },
];

function PricingSection() {
  return (
    <section id="pricing" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">定价</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            简单透明的定价
          </h2>
          <p className="mt-4 text-[16px] leading-[1.6] text-[#524f49]">选择适合你的方案。随时升降级。</p>
        </header>
        <div className="grid md:grid-cols-3 gap-4 max-w-[1000px]">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`rounded-[12px] border p-8 flex flex-col ${
                p.highlighted
                  ? "border-[#0f0e0d] bg-[var(--gray-1)] shadow-lg ring-1 ring-[#0f0e0d]"
                  : "border-[#e7e5e4] bg-[var(--gray-1)]"
              }`}
            >
              {p.highlighted && (
                <span className="self-start rounded-[6px] bg-[#0f0e0d] px-3 py-1 text-[12px] font-medium text-[#fafaf9] mb-4">推荐</span>
              )}
              <h3 className="text-[16px] font-medium text-[#0f0e0d]">{p.name}</h3>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-[36px] font-normal tracking-[-0.02em] text-[#0f0e0d]">{p.price}</span>
                <span className="text-[16px] text-[#a8a29e]">{p.period}</span>
              </div>
              <p className="mt-2 text-[14px] text-[#524f49]">{p.desc}</p>
              <ul className="mt-6 space-y-3 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-[14px] text-[#524f49]">
                    <svg className="h-4 w-4 mt-0.5 flex-shrink-0 text-[#78716c]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className={`mt-8 flex items-center justify-center h-[44px] rounded-[8px] text-[16px] font-medium transition-colors ${
                  p.highlighted
                    ? "bg-[#0f0e0d] text-[#fafaf9] hover:bg-[#262524]"
                    : "border border-[#e7e5e4] text-[#0f0e0d] hover:bg-[#f5f5f4]"
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

const faqs = [
  {
    q: "SelectPilot 使用哪些数据源？",
    a: "我们通过 TikHub API 拉取 TikTok Shop 实时数据（品类排名、爆品），加上 Amazon BSR、8 个社交平台趋势、以及 1688/中国制造网的采购成本。所有数据实时验证——绝不编造。",
  },
  {
    q: "免费版有什么限制？",
    a: "免费版包含每月 5 次 AI 调研、品类浏览和 1 个目标市场。升级专业版可获得 100 次调研、26 国家覆盖、ECharts 报告和利润建模。",
  },
  {
    q: "AI 如何确保调研质量？",
    a: "我们的 AI Agent 使用 DeepSeek，配合 8 阶段结构化调研流水线和实时数据工具链。每个结论都基于实时数据。当数据通道不可用时，会明确标注而非编造。",
  },
  {
    q: "支持哪些国家？",
    a: "26 个国家，包括美国、英国、德国、法国、日本、韩国、新加坡、马来西亚、泰国、越南、印度尼西亚、菲律宾、巴西等。每个市场的 TikTok Shop 品类和爆品独立跟踪。",
  },
  {
    q: "定价是否包含 API 使用费？",
    a: "是的。月费覆盖所有数据采集和 AI 调研成本，无隐藏消费。企业版额外提供 REST API 接入，用于内部系统集成。",
  },
];

function FAQSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  return (
    <section id="blog" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[48px]">
          <p className="text-[16px] text-[#524f49] mb-4">了解更多</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">常见问题</h2>
        </header>
        <div className="max-w-[800px]">
          {faqs.map((f, i) => (
            <div key={i} className="border-b border-[#e7e5e4]">
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 py-[20px] text-left"
              >
                <span className="text-[16px] font-medium text-[#0f0e0d]">{f.q}</span>
                <ChevronDown className={`h-5 w-5 flex-shrink-0 text-[#a8a29e] transition-transform duration-200 ${openIdx === i ? "rotate-180" : ""}`} />
              </button>
              {openIdx === i && (
                <div className="pb-[20px] text-[16px] leading-[1.6] text-[#524f49]">{f.a}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-[#e7e5e4] bg-[#0f0e0d] text-[#fafaf9]">
      {/* Footer CTA */}
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#fafaf9] mb-4">
          看看自动化是什么样的。
        </h2>
        <p className="text-[16px] leading-[1.6] text-[#a8a29e] max-w-[500px] mb-8">
          选品调研的操作性工作，已处理。你只需专注需要你的那一半。
        </p>
        <Link href="/register" className="inline-flex items-center h-[50px] px-[20px] rounded-[8px] bg-[#fafaf9] text-[20px] font-medium text-[#0f0e0d] hover:bg-[var(--gray-1)] transition-colors">
          免费开始
        </Link>
      </div>

      {/* Footer nav */}
      <div className="border-t border-[#292524]">
        <div className="mx-auto max-w-[1500px] px-[40px] py-[48px]">
          <nav className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-[48px]">
            {[
              { title: "产品", links: ["市场扫描", "趋势跟踪", "利润建模", "AI 智能体", "爆品排行"] },
              { title: "解决方案", links: ["个人卖家", "团队版", "代运机构"] },
              { title: "资源", links: ["定价", "博客", "API 文档"] },
              { title: "法律", links: ["隐私政策", "服务条款", "DPA"] },
            ].map((col) => (
              <div key={col.title}>
                <h4 className="text-[16px] font-medium text-[#fafaf9] mb-4">{col.title}</h4>
                <ul className="space-y-2">
                  {col.links.map((link) => (
                    <li key={link}>
                      <a href="#" className="text-[16px] text-[#a8a29e] hover:text-[#fafaf9] transition-colors py-[5px] block">{link}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
          <div className="border-t border-[#292524] pt-6 flex items-center justify-between">
            <span className="text-[14px] text-[#a8a29e]">&copy; 2026 SelectPilot. 让选品调研全自动运行。</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#fafaf9] text-[#0f0e0d] antialiased">
      <Navbar />
      <main>
        <Hero />
        <WhySection />
        <FeaturesSection />
        <WorkflowSection />
        <BuiltForSection />
        <StatsSection />
        <TestimonialSection />
        <SecuritySection />
        <PricingSection />
        <FAQSection />
      </main>
      <Footer />
    </div>
  );
}
