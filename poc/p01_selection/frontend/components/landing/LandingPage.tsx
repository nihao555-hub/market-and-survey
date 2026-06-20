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
          {["Product", "Solutions", "Pricing", "Blog"].map((item) => (
            <li key={item}>
              <a href={`#${item.toLowerCase()}`} className="flex items-center h-[40px] px-[15px] rounded-[6px] text-[16px] text-[#0f0e0d] hover:bg-[#f5f5f4] transition-colors">
                {item}
              </a>
            </li>
          ))}
        </ul>
        <div className="hidden md:flex items-center gap-1">
          <Link href="/login" className="flex items-center h-[40px] px-[15px] rounded-[6px] text-[16px] text-[#0f0e0d] hover:bg-[#f5f5f4] transition-colors">
            Log in
          </Link>
          <Link href="/register" className="flex items-center h-[40px] px-[15px] rounded-[6px] bg-[#0f0e0d] text-[16px] font-medium text-[#fafaf9] hover:bg-[#262524] transition-colors">
            Get started
          </Link>
        </div>
        <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>
      {open && (
        <div className="md:hidden bg-[#fafaf9] border-t border-[#e7e5e4] px-[40px] py-6 space-y-4">
          {["Product", "Solutions", "Pricing", "Blog"].map((item) => (
            <a key={item} href={`#${item.toLowerCase()}`} onClick={() => setOpen(false)} className="block text-[16px] text-[#0f0e0d]">{item}</a>
          ))}
          <div className="flex gap-3 pt-3">
            <Link href="/login" className="flex-1 text-center h-[40px] leading-[40px] rounded-[6px] border border-[#e7e5e4] text-[16px] text-[#0f0e0d]">Log in</Link>
            <Link href="/register" className="flex-1 text-center h-[40px] leading-[40px] rounded-[6px] bg-[#0f0e0d] text-[16px] text-[#fafaf9]">Get started</Link>
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
              AI-powered product selection engine
              <ArrowRight className="h-4 w-4" />
            </a>

            {/* Headline - font-weight 400 like taito.ai */}
            <h1 className="text-[clamp(40px,5vw,61px)] font-normal leading-[1.2] tracking-[-0.025em] text-[#0f0e0d] max-w-[600px]">
              Run product research on autopilot
            </h1>

            {/* Description */}
            <p className="text-[16px] leading-[1.6] text-[#524f49] mt-6 max-w-[440px]">
              TikTok Shop rankings, social trends, Amazon BSR data, and profit modeling, automated. The product selection platform for cross-border sellers building exceptional businesses — without slowing down.
            </p>

            {/* CTA - matches taito hero CTA exactly */}
            <div className="mt-8">
              <Link href="/register" className="inline-flex items-center h-[50px] px-[20px] rounded-[8px] bg-[#0f0e0d] text-[20px] font-medium text-[#fafaf9] hover:bg-[#262524] transition-colors">
                Get started
              </Link>
            </div>
          </div>

          {/* Right: product screenshot - like taito.ai hero image */}
          <div className="mt-12 lg:mt-0 lg:flex-1 relative">
            <div className="rounded-[12px] border border-[#e7e5e4] shadow-2xl overflow-hidden bg-white">
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
            <p className="text-[16px] text-[#524f49] mb-4">Why SelectPilot?</p>
            <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
              Grow your sales,<br />not your research overhead
            </h2>
          </div>
          <p className="lg:flex-1 text-[16px] leading-[1.6] text-[#524f49] mt-6 lg:mt-2">
            Between finding products and validating margins, the research workload doubles before the revenue does. SelectPilot handles the operational research automatically, so you can focus on selling, not scraping data.
          </p>
        </header>

        {/* 3-column article cards - like taito.ai */}
        <div className="grid md:grid-cols-3 gap-4">
          <article className="rounded-[12px] border border-[#e7e5e4] bg-white overflow-hidden group">
            <div className="aspect-[4/3] bg-[#f5f5f4] overflow-hidden relative">
              <img src="/images/screenshot-research.png" alt="AI Research" className="w-full h-full object-cover object-top" />
              {/* Overlay icons like taito.ai */}
              <div className="absolute bottom-4 left-4 flex gap-2">
                <div className="w-10 h-10 rounded-[8px] bg-white/90 backdrop-blur flex items-center justify-center shadow-sm">
                  <Search className="w-5 h-5 text-[#524f49]" />
                </div>
                <div className="w-10 h-10 rounded-[8px] bg-white/90 backdrop-blur flex items-center justify-center shadow-sm">
                  <BarChart3 className="w-5 h-5 text-[#524f49]" />
                </div>
                <div className="w-10 h-10 rounded-[8px] bg-white/90 backdrop-blur flex items-center justify-center shadow-sm">
                  <TrendingUp className="w-5 h-5 text-[#524f49]" />
                </div>
              </div>
            </div>
            <div className="p-6">
              <h3 className="text-[16px] font-medium text-[#0f0e0d] mb-2">One platform for all product research</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">
                Market scanning, trend tracking, competitor analysis, and profit modeling run from one place, automatically. No more copying between spreadsheets.
              </p>
            </div>
          </article>

          <article className="rounded-[12px] border border-[#e7e5e4] bg-white overflow-hidden group">
            <div className="aspect-[4/3] bg-[#f5f5f4] overflow-hidden relative">
              <img src="/images/screenshot-categories.png" alt="Multi-platform" className="w-full h-full object-cover object-top" />
              {/* Chat mock overlay like taito.ai's Slack integration card */}
              <div className="absolute bottom-4 left-4 right-4 bg-white/95 backdrop-blur rounded-[8px] p-3 shadow-sm">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-5 h-5 rounded-full bg-[#0f0e0d] flex items-center justify-center">
                    <Bot className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-[12px] font-medium text-[#0f0e0d]">SelectPilot</span>
                  <span className="text-[11px] text-[#a8a29e]">just now</span>
                </div>
                <p className="text-[12px] text-[#524f49]">Found 24 trending products in Home & Garden across 3 markets...</p>
              </div>
            </div>
            <div className="p-6">
              <h3 className="text-[16px] font-medium text-[#0f0e0d] mb-2">Works where your data already lives</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">
                Access TikTok Shop, Amazon, 1688, and 8 social platforms from one interface. Your product data is always one conversation away.
              </p>
            </div>
          </article>

          <article className="rounded-[12px] border border-[#e7e5e4] bg-white overflow-hidden group">
            <div className="aspect-[4/3] bg-[#f5f5f4] overflow-hidden relative">
              <img src="/images/screenshot-hotselling.png" alt="Global Coverage" className="w-full h-full object-cover object-top" />
              {/* Country list overlay like taito.ai's policies card */}
              <div className="absolute top-4 right-4 bg-white/95 backdrop-blur rounded-[8px] p-3 shadow-sm">
                <p className="text-[12px] font-medium text-[#0f0e0d] mb-2">Market coverage</p>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px]">🇺🇸</span>
                    <span className="text-[12px] text-[#524f49]">United States</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[12px]">🇬🇧</span>
                    <span className="text-[12px] text-[#524f49]">United Kingdom</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[12px]">🇩🇪</span>
                    <span className="text-[12px] text-[#524f49]">Germany</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-6">
              <h3 className="text-[16px] font-medium text-[#0f0e0d] mb-2">26-country coverage, no workarounds</h3>
              <p className="text-[16px] leading-[1.6] text-[#524f49]">
                Local market data, category rankings, and pricing intelligence automated from day one. No manual fixes, no stale data. Just correct by default.
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
    { icon: Search, title: "Market scanning", desc: "AI Agent completes 8-stage structured research from category scan to competitor deep-dive." },
    { icon: TrendingUp, title: "Trend tracking", desc: "Real-time trends from TikTok, Douyin, Weibo, Xiaohongshu, Kuaishou, Bilibili, X, and Lemon8." },
    { icon: ShoppingCart, title: "Hot product rankings", desc: "28 categories across 26 countries, refreshed daily at midnight. Competition index quantified." },
    { icon: LineChart, title: "ECharts visualization", desc: "AI output automatically rendered as interactive bar, line, pie, and radar charts." },
    { icon: Calculator, title: "Profit modeling", desc: "14-item cost breakdown with Monte Carlo stress testing across 10,000 scenarios." },
    { icon: Shield, title: "9-level anti-detection", desc: "curl_cffi → Scrapling → Patchright fallback chain ensures zero data collection interruption." },
  ];

  return (
    <section id="features" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">Core capabilities</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d] max-w-[500px]">
            From zero to decision, no manual steps
          </h2>
          <p className="mt-4 text-[16px] leading-[1.6] text-[#524f49] max-w-[520px]">
            Market data, competitor analysis, profit calculations, and trend signals run automatically. Your team never has to chase it.
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
          <p className="text-[16px] text-[#524f49] mb-4">AI Agents</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            Set it up once. Research forever.
          </h2>
          <p className="mt-4 text-[16px] leading-[1.6] text-[#524f49] max-w-[520px]">
            Automate product research tasks like market scanning, trend analysis, and profit modeling as no-code autonomous agentic workflows.
          </p>
        </header>

        <div className="lg:flex lg:gap-[60px] lg:items-start">
          {/* Left: feature list */}
          <div className="lg:flex-1 space-y-[32px]">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Search className="w-5 h-5 text-[#78716c]" />
                <h3 className="text-[16px] font-medium text-[#0f0e0d]">Market intelligence</h3>
              </div>
              <p className="text-[16px] leading-[1.6] text-[#524f49] pl-8">
                Category scanning, competitor tracking, and hot product detection run end-to-end as no-code workflows. Every step of the research journey, handled.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Calculator className="w-5 h-5 text-[#78716c]" />
                <h3 className="text-[16px] font-medium text-[#0f0e0d]">Profit validation</h3>
              </div>
              <p className="text-[16px] leading-[1.6] text-[#524f49] pl-8">
                Cost structure, logistics fees, and margin calculations packaged for every product opportunity. No manual spreadsheet reconciliation.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Bot className="w-5 h-5 text-[#78716c]" />
                <h3 className="text-[16px] font-medium text-[#0f0e0d]">Research assistant</h3>
              </div>
              <p className="text-[16px] leading-[1.6] text-[#524f49] pl-8">
                Ask about categories, trends, and product viability — grounded in your real-time market data, not generic AI.
              </p>
            </div>
          </div>

          {/* Right: workflow visual */}
          <div className="mt-10 lg:mt-0 lg:flex-1">
            <div className="rounded-[12px] border border-[#e7e5e4] bg-white p-6 shadow-sm">
              <p className="text-[14px] text-[#524f49] mb-4 border-b border-[#e7e5e4] pb-4">Research trending products in Home & Garden for US market</p>
              <div className="space-y-3">
                {[
                  { title: "Scan categories", desc: "28 sub-categories analyzed" },
                  { title: "Identify hot products", desc: "Top 50 by sales velocity" },
                  { title: "Validate margins", desc: "14-item cost breakdown applied" },
                  { title: "Generate report", desc: "ECharts visualization + recommendations" },
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
      eyebrow: "Lean growth for",
      title: "Solo sellers",
      desc: "Scale product research without scaling headcount. Focus only when the opportunity needs a human.",
    },
    {
      eyebrow: "Strategic focus for",
      title: "Team leads",
      desc: "Hours of manual data collection handled automatically. The strategic decisions are yours.",
    },
    {
      eyebrow: "Best practices for",
      title: "Agencies",
      desc: "Build the research systems that scale your clients. Data collection and reporting, handled.",
    },
  ];

  return (
    <section className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">Built for</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            Different roles. Same product.
          </h2>
        </header>

        <div className="grid md:grid-cols-3 gap-4">
          {roles.map((role, i) => (
            <div key={i} className="rounded-[12px] border border-[#e7e5e4] bg-white p-8 flex flex-col">
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
    { value: "128K+", label: "Products tracked in real-time database" },
    { value: "26", label: "Countries with full TikTok Shop coverage" },
    { value: "8", label: "Social platforms monitored for trends" },
    { value: "$0", label: "Hidden fees — pricing includes all data costs" },
  ];

  return (
    <section className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">By the numbers</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            The math behind the product
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
            &ldquo;I used to spend 2-3 days per category researching products across TikTok and Amazon. SelectPilot&apos;s AI completes a full research report in 10 minutes with interactive charts. It completely changed how I do product selection.&rdquo;
          </blockquote>
          <figcaption className="mt-8 text-[16px] text-[#524f49]">
            <span className="font-medium text-[#0f0e0d]">Li Ming</span> &middot; TikTok Shop seller, $50K+ monthly GMV
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

function SecuritySection() {
  const badges = [
    { label: "Enterprise-grade", sub: "data security" },
    { label: "Multi-level", sub: "anti-detection" },
    { label: "Real-time", sub: "data freshness" },
    { label: "26-country", sub: "coverage" },
  ];

  return (
    <section className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="lg:flex lg:items-start lg:gap-[80px] mb-[60px]">
          <div className="lg:flex-1">
            <p className="text-[16px] text-[#524f49] mb-4">Security</p>
            <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
              Enterprise-grade reliability, by default
            </h2>
          </div>
          <p className="lg:flex-1 text-[16px] leading-[1.6] text-[#524f49] mt-6 lg:mt-2">
            As a seller, your product research data and strategies are your competitive edge. SelectPilot uses a 9-level anti-detection engine, encrypted data storage, and automated daily refreshes to ensure your intelligence is always accurate and secure.
          </p>
        </header>
        <ul className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {badges.map((b, i) => (
            <li key={i} className="rounded-[12px] border border-[#e7e5e4] bg-white p-6 flex items-center gap-4">
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
    name: "Free",
    price: "$0",
    period: "/month",
    desc: "Try AI product research",
    features: ["5 AI research sessions/month", "Category browsing & rankings", "1 target market", "Basic data snapshots"],
    cta: "Get started",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$15",
    period: "/month",
    desc: "For full-time cross-border sellers",
    features: ["100 AI research sessions/month", "ECharts interactive reports", "26 countries full coverage", "Category trend tracking", "Profit modeling engine", "Daily auto-refresh", "Priority data updates"],
    cta: "Subscribe",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$49",
    period: "/month",
    desc: "For teams and multi-store operations",
    features: ["Unlimited AI research", "All Pro features", "API access", "Team collaboration workspace", "Dedicated account manager", "Custom report templates", "SLA guarantee"],
    cta: "Contact us",
    highlighted: false,
  },
];

function PricingSection() {
  return (
    <section id="pricing" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[60px]">
          <p className="text-[16px] text-[#524f49] mb-4">Pricing</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">
            Simple, transparent pricing
          </h2>
          <p className="mt-4 text-[16px] leading-[1.6] text-[#524f49]">Choose the plan that fits. Upgrade or downgrade anytime.</p>
        </header>
        <div className="grid md:grid-cols-3 gap-4 max-w-[1000px]">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`rounded-[12px] border p-8 flex flex-col ${
                p.highlighted
                  ? "border-[#0f0e0d] bg-white shadow-lg ring-1 ring-[#0f0e0d]"
                  : "border-[#e7e5e4] bg-white"
              }`}
            >
              {p.highlighted && (
                <span className="self-start rounded-[6px] bg-[#0f0e0d] px-3 py-1 text-[12px] font-medium text-[#fafaf9] mb-4">Recommended</span>
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
    q: "What data sources does SelectPilot use?",
    a: "We pull real-time data from TikTok Shop (category rankings, hot products) via TikHub API, plus Amazon BSR, 8 social media platforms for trends, and 1688/Made-in-China for sourcing costs. All data is live and verified — never fabricated.",
  },
  {
    q: "What are the limitations of the Free plan?",
    a: "Free includes 5 AI research sessions per month, category browsing, and 1 target market. Upgrade to Pro for 100 sessions, 26-country coverage, ECharts reports, and profit modeling.",
  },
  {
    q: "How does the AI ensure research quality?",
    a: "Our AI Agent uses DeepSeek with an 8-stage structured research pipeline and real-time data tool chain. Every conclusion is grounded in live data. When a data channel isn't available, it's clearly labeled rather than fabricated.",
  },
  {
    q: "Which countries are supported?",
    a: "26 countries including US, UK, Germany, France, Japan, Korea, Singapore, Malaysia, Thailand, Vietnam, Indonesia, Philippines, Brazil, and more. Each market's TikTok Shop categories and hot products are independently tracked.",
  },
  {
    q: "Does pricing include API usage fees?",
    a: "Yes. Monthly fees cover all data collection and AI research costs with no hidden consumption charges. Enterprise plan additionally provides REST API access for internal system integration.",
  },
];

function FAQSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  return (
    <section id="blog" className="border-t border-[#e7e5e4]">
      <div className="mx-auto max-w-[1500px] px-[40px] py-[80px] lg:py-[120px]">
        <header className="mb-[48px]">
          <p className="text-[16px] text-[#524f49] mb-4">Learn more</p>
          <h2 className="text-[clamp(32px,3.5vw,39px)] font-normal leading-[1.2] tracking-[-0.015em] text-[#0f0e0d]">Frequently asked questions</h2>
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
          See what autopilot looks like.
        </h2>
        <p className="text-[16px] leading-[1.6] text-[#a8a29e] max-w-[500px] mb-8">
          The operational half of product research, handled. You focus on the half that needs you.
        </p>
        <Link href="/register" className="inline-flex items-center h-[50px] px-[20px] rounded-[8px] bg-[#fafaf9] text-[20px] font-medium text-[#0f0e0d] hover:bg-white transition-colors">
          Get started
        </Link>
      </div>

      {/* Footer nav */}
      <div className="border-t border-[#292524]">
        <div className="mx-auto max-w-[1500px] px-[40px] py-[48px]">
          <nav className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-[48px]">
            {[
              { title: "Product", links: ["Market scanning", "Trend tracking", "Profit modeling", "AI Agents", "Hot rankings"] },
              { title: "Solutions", links: ["For sellers", "For teams", "For agencies"] },
              { title: "Resources", links: ["Pricing", "Blog", "API docs"] },
              { title: "Legal", links: ["Privacy", "Terms", "DPA"] },
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
            <span className="text-[14px] text-[#a8a29e]">&copy; 2026 SelectPilot. Run product research on autopilot.</span>
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
