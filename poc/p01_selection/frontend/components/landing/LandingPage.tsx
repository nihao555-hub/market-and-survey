"use client";
import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowRight, ChevronDown, Menu, X,
  Search, BarChart3, LineChart, Calculator, Shield, TrendingUp,
  Bot, Globe2, ShoppingCart, Zap,
} from "lucide-react";

// taito.ai-inspired enterprise B2B landing page
// Clean white, generous whitespace, restrained typography, black CTA

function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="fixed top-0 inset-x-0 z-50 bg-white/90 backdrop-blur-md border-b border-neutral-100">
      <nav className="mx-auto flex h-[60px] max-w-[1200px] items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2">
          <img src="/images/logo-icon.png" alt="SelectPilot" className="h-7 w-7 rounded-md" />
          <span className="text-[15px] font-semibold tracking-tight text-neutral-900">SelectPilot</span>
        </Link>
        <ul className="hidden md:flex items-center gap-7 text-[14px] text-neutral-500">
          <li><a href="#features" className="hover:text-neutral-900 transition-colors">Product</a></li>
          <li><a href="#workflow" className="hover:text-neutral-900 transition-colors">Solutions</a></li>
          <li><a href="#pricing" className="hover:text-neutral-900 transition-colors">Pricing</a></li>
          <li><a href="#faq" className="hover:text-neutral-900 transition-colors">FAQ</a></li>
        </ul>
        <div className="hidden md:flex items-center gap-3">
          <Link href="/login" className="px-4 py-2 text-[13px] text-neutral-500 hover:text-neutral-900 transition-colors">Log in</Link>
          <Link href="/register" className="rounded-full bg-neutral-900 px-5 py-2 text-[13px] font-medium text-white hover:bg-neutral-800 transition-colors">Get started</Link>
        </div>
        <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>
      {open && (
        <div className="md:hidden border-t border-neutral-100 bg-white px-6 py-4 space-y-3">
          <a href="#features" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">Product</a>
          <a href="#workflow" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">Solutions</a>
          <a href="#pricing" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">Pricing</a>
          <a href="#faq" onClick={() => setOpen(false)} className="block text-sm text-neutral-600">FAQ</a>
          <div className="flex gap-3 pt-2">
            <Link href="/login" className="flex-1 text-center rounded-full border border-neutral-200 px-4 py-2.5 text-sm">Log in</Link>
            <Link href="/register" className="flex-1 text-center rounded-full bg-neutral-900 px-4 py-2.5 text-sm text-white">Sign up</Link>
          </div>
        </div>
      )}
    </header>
  );
}

function Hero() {
  return (
    <section className="pt-[100px] pb-16 md:pt-[140px] md:pb-24">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Announcement pill */}
        <div className="flex justify-center mb-8">
          <Link href="/register" className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-neutral-50 px-4 py-1.5 text-[12px] text-neutral-600 hover:bg-neutral-100 transition-colors">
            AI-powered product selection engine is live
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {/* Headline */}
        <h1 className="text-center text-[44px] md:text-[64px] font-semibold leading-[1.05] tracking-tight text-neutral-900 max-w-[800px] mx-auto">
          Run product research<br/>on autopilot
        </h1>

        {/* Description */}
        <p className="text-center text-[16px] md:text-[18px] text-neutral-500 leading-relaxed mt-6 max-w-[600px] mx-auto">
          TikTok Shop rankings, social trends, Amazon BSR data, and profit
          modeling, automated. The product selection platform for cross-border
          sellers building exceptional businesses — without slowing down.
        </p>

        {/* CTA */}
        <div className="flex justify-center mt-8">
          <Link href="/register" className="rounded-full bg-neutral-900 px-7 py-3.5 text-[14px] font-medium text-white hover:bg-neutral-800 transition-all hover:shadow-lg">
            Get started free
          </Link>
        </div>

        {/* Hero product shot */}
        <div className="mt-16 relative max-w-[1000px] mx-auto">
          <div className="rounded-2xl border border-neutral-200 shadow-2xl shadow-neutral-200/40 overflow-hidden bg-white">
            <img src="/images/screenshot-workspace.png" alt="SelectPilot workspace" className="w-full" />
          </div>
        </div>

        {/* Logo marquee */}
        <div className="mt-20 border-t border-neutral-100 pt-10">
          <div className="flex flex-wrap items-center justify-center gap-10 md:gap-14 opacity-60">
            {["TikTok Shop", "Amazon", "1688", "Douyin", "Xiaohongshu", "Weibo", "Bilibili", "Lemon8"].map((name) => (
              <span key={name} className="text-[13px] font-medium text-neutral-400 tracking-wide">{name}</span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function WhySection() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <header className="grid md:grid-cols-2 gap-8 mb-14">
          <div>
            <p className="text-[13px] text-neutral-400 mb-3">Why SelectPilot?</p>
            <h2 className="text-[32px] md:text-[40px] font-semibold leading-[1.1] tracking-tight text-neutral-900">
              Grow your sales,<br/>not your research overhead
            </h2>
          </div>
          <p className="text-[15px] text-neutral-500 leading-relaxed md:pt-8">
            Between finding products and validating margins, the research workload
            doubles before the revenue does. SelectPilot handles the operational
            research automatically, so you can focus on selling, not scraping data.
          </p>
        </header>

        {/* 3-column cards */}
        <div className="grid md:grid-cols-3 gap-5">
          <article className="rounded-2xl border border-neutral-100 bg-white overflow-hidden">
            <div className="aspect-[4/3] bg-neutral-50 overflow-hidden">
              <img src="/images/screenshot-research.png" alt="AI Research" className="w-full h-full object-cover object-top" />
            </div>
            <div className="p-6">
              <h3 className="text-[15px] font-semibold text-neutral-900 mb-2">One platform for all product research</h3>
              <p className="text-[13px] text-neutral-500 leading-relaxed">
                Market scanning, trend tracking, competitor analysis, and profit modeling run from one place, automatically. No more copying between spreadsheets.
              </p>
            </div>
          </article>

          <article className="rounded-2xl border border-neutral-100 bg-white overflow-hidden">
            <div className="aspect-[4/3] bg-neutral-50 overflow-hidden">
              <img src="/images/screenshot-categories.png" alt="Category Rankings" className="w-full h-full object-cover object-top" />
            </div>
            <div className="p-6">
              <h3 className="text-[15px] font-semibold text-neutral-900 mb-2">Works where your data already lives</h3>
              <p className="text-[13px] text-neutral-500 leading-relaxed">
                Access TikTok Shop, Amazon, 1688, and 8 social platforms from one interface. Your product data is always one conversation away.
              </p>
            </div>
          </article>

          <article className="rounded-2xl border border-neutral-100 bg-white overflow-hidden">
            <div className="aspect-[4/3] bg-neutral-50 overflow-hidden">
              <img src="/images/screenshot-hotselling.png" alt="Market Data" className="w-full h-full object-cover object-top" />
            </div>
            <div className="p-6">
              <h3 className="text-[15px] font-semibold text-neutral-900 mb-2">26-country coverage, no workarounds</h3>
              <p className="text-[13px] text-neutral-500 leading-relaxed">
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
    <section id="features" className="py-20 md:py-28 bg-neutral-50/50">
      <div className="mx-auto max-w-[1200px] px-6">
        <header className="mb-14">
          <p className="text-[13px] text-neutral-400 mb-3">Core capabilities</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold leading-[1.1] tracking-tight text-neutral-900">
            From zero to decision,<br/>no manual steps
          </h2>
          <p className="mt-4 text-[15px] text-neutral-500 max-w-[520px]">
            Market data, competitor analysis, profit calculations, and trend signals run automatically. Your team never has to chase it.
          </p>
        </header>

        <ul className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-neutral-100 rounded-2xl overflow-hidden border border-neutral-100">
          {features.map((f, i) => (
            <li key={i} className="bg-white p-7">
              <f.icon className="h-5 w-5 text-neutral-400 mb-4" />
              <h3 className="text-[14px] font-semibold text-neutral-900 mb-1.5">{f.title}</h3>
              <p className="text-[13px] text-neutral-500 leading-relaxed">{f.desc}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function WorkflowSection() {
  const steps = [
    { title: "Define direction", desc: "Tell AI your target category, market, and budget range." },
    { title: "AI auto-research", desc: "Agent collects TikTok hot items, Amazon rankings, social trends, 1688 costs in parallel." },
    { title: "Interactive visualization", desc: "ECharts renders price distribution, sales trends, and competitor comparisons." },
    { title: "Decision report", desc: "Profit calculation + risk assessment + recommended SKUs, export-ready." },
  ];

  return (
    <section id="workflow" className="py-20 md:py-28">
      <div className="mx-auto max-w-[1200px] px-6">
        <header className="mb-14">
          <p className="text-[13px] text-neutral-400 mb-3">AI Agents</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold leading-[1.1] tracking-tight text-neutral-900">
            Set it up once. Research forever.
          </h2>
          <p className="mt-4 text-[15px] text-neutral-500 max-w-[520px]">
            Automate product research tasks like market scanning, trend analysis, and profit modeling as no-code autonomous agentic workflows.
          </p>
        </header>

        <div className="grid md:grid-cols-2 gap-12 items-start">
          {/* Steps */}
          <div className="space-y-6">
            {steps.map((s, i) => (
              <div key={i} className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-neutral-900 text-white text-[12px] font-medium flex items-center justify-center">
                  {i + 1}
                </div>
                <div>
                  <h3 className="text-[14px] font-semibold text-neutral-900">{s.title}</h3>
                  <p className="text-[13px] text-neutral-500 mt-1 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Screenshot */}
          <div className="rounded-2xl border border-neutral-200 shadow-lg overflow-hidden bg-white">
            <img src="/images/screenshot-research.png" alt="AI workflow" className="w-full" />
          </div>
        </div>
      </div>
    </section>
  );
}

function StatsSection() {
  const stats = [
    { value: "128,540+", label: "Products in database", source: "Live data" },
    { value: "26", label: "Countries covered", source: "Global markets" },
    { value: "8", label: "Social platforms tracked", source: "Real-time trends" },
    { value: "14", label: "Cost items modeled", source: "Monte Carlo engine" },
  ];

  return (
    <section className="py-20 md:py-28 border-y border-neutral-100">
      <div className="mx-auto max-w-[1200px] px-6">
        <header className="mb-14">
          <p className="text-[13px] text-neutral-400 mb-3">By the numbers</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold tracking-tight text-neutral-900">
            The math behind the product
          </h2>
        </header>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((s, i) => (
            <div key={i}>
              <dd className="text-[36px] md:text-[48px] font-bold tracking-tight text-neutral-900">{s.value}</dd>
              <dt className="mt-2 text-[13px] text-neutral-500">{s.label}</dt>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function TestimonialSection() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-[800px] px-6">
        <figure className="text-center">
          <blockquote className="text-[18px] md:text-[22px] leading-relaxed text-neutral-700 font-normal">
            &ldquo;I used to spend 2-3 days per category researching products across TikTok and Amazon reviews. With SelectPilot, the AI completes a full research report in 10 minutes with interactive charts. It completely changed how I do product selection.&rdquo;
          </blockquote>
          <figcaption className="mt-8 text-[14px] text-neutral-500">
            <span className="font-medium text-neutral-900">Li Ming</span> &middot; TikTok Shop seller, $50K+ monthly GMV
          </figcaption>
        </figure>
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
    <section id="pricing" className="py-20 md:py-28 bg-neutral-50/50">
      <div className="mx-auto max-w-[1200px] px-6">
        <header className="text-center mb-14">
          <p className="text-[13px] text-neutral-400 mb-3">Pricing</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold tracking-tight text-neutral-900">
            Simple, transparent pricing
          </h2>
          <p className="mt-4 text-[15px] text-neutral-500">Choose the plan that fits. Upgrade or downgrade anytime.</p>
        </header>
        <div className="grid md:grid-cols-3 gap-5 max-w-[900px] mx-auto">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`rounded-2xl border p-7 flex flex-col ${
                p.highlighted
                  ? "border-neutral-900 bg-white shadow-xl ring-1 ring-neutral-900"
                  : "border-neutral-200 bg-white"
              }`}
            >
              {p.highlighted && (
                <span className="self-start rounded-full bg-neutral-900 px-3 py-1 text-[11px] font-medium text-white mb-4">Recommended</span>
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
                    <svg className="h-4 w-4 mt-0.5 flex-shrink-0 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className={`mt-6 flex items-center justify-center rounded-full py-3 text-[13px] font-medium transition-colors ${
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

function SecuritySection() {
  const badges = [
    { label: "Enterprise-grade", sub: "data security" },
    { label: "Multi-level", sub: "anti-detection" },
    { label: "Real-time", sub: "data freshness" },
    { label: "26-country", sub: "coverage" },
  ];

  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-[1200px] px-6">
        <header className="grid md:grid-cols-2 gap-8 mb-12">
          <div>
            <p className="text-[13px] text-neutral-400 mb-3">Security</p>
            <h2 className="text-[32px] md:text-[40px] font-semibold leading-[1.1] tracking-tight text-neutral-900">
              Enterprise-grade reliability,<br/>by default
            </h2>
          </div>
          <p className="text-[15px] text-neutral-500 leading-relaxed md:pt-8">
            As a seller, your product research data and strategies are your competitive edge. SelectPilot uses a 9-level anti-detection engine, encrypted data storage, and automated daily refreshes to ensure your intelligence is always accurate and secure.
          </p>
        </header>
        <ul className="grid grid-cols-2 md:grid-cols-4 gap-5">
          {badges.map((b, i) => (
            <li key={i} className="rounded-2xl border border-neutral-100 bg-white p-6 text-center">
              <Shield className="h-6 w-6 text-neutral-400 mx-auto mb-3" />
              <div className="text-[14px] font-semibold text-neutral-900">{b.label}</div>
              <div className="text-[12px] text-neutral-400 mt-0.5">{b.sub}</div>
            </li>
          ))}
        </ul>
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
    <section id="faq" className="py-20 md:py-28 bg-neutral-50/50">
      <div className="mx-auto max-w-[720px] px-6">
        <header className="mb-12">
          <p className="text-[13px] text-neutral-400 mb-3">Learn more</p>
          <h2 className="text-[32px] md:text-[40px] font-semibold tracking-tight text-neutral-900">Frequently asked questions</h2>
        </header>
        <div className="space-y-2">
          {faqs.map((f, i) => (
            <div key={i} className="border-b border-neutral-100">
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 py-5 text-left"
              >
                <span className="text-[14px] font-medium text-neutral-900">{f.q}</span>
                <ChevronDown className={`h-4 w-4 flex-shrink-0 text-neutral-400 transition-transform duration-200 ${openIdx === i ? "rotate-180" : ""}`} />
              </button>
              {openIdx === i && (
                <div className="pb-5 text-[13px] text-neutral-500 leading-relaxed">{f.a}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FooterCTA() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-[1200px] px-6 text-center">
        <h2 className="text-[32px] md:text-[44px] font-semibold tracking-tight text-neutral-900 mb-4">
          See what autopilot looks like.
        </h2>
        <p className="text-[16px] text-neutral-500 max-w-[500px] mx-auto mb-8">
          The operational half of product research, handled. You focus on the half that needs you.
        </p>
        <Link href="/register" className="inline-flex items-center gap-2 rounded-full bg-neutral-900 px-8 py-4 text-[14px] font-medium text-white hover:bg-neutral-800 transition-all hover:shadow-lg">
          Get started free
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-neutral-100 bg-white py-12">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-10">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-3">
              <img src="/images/logo-icon.png" alt="SelectPilot" className="h-6 w-6 rounded-md" />
              <span className="text-[14px] font-semibold text-neutral-900">SelectPilot</span>
            </Link>
            <p className="text-[12px] text-neutral-400 leading-relaxed">AI-powered product selection for cross-border commerce.</p>
          </div>
          {[
            { title: "Product", links: [["Market scanning", "#features"], ["Trend tracking", "#features"], ["Profit modeling", "#features"], ["AI Agents", "#workflow"]] },
            { title: "Solutions", links: [["For sellers", "#"], ["For teams", "#"], ["For agencies", "#"]] },
            { title: "Resources", links: [["Pricing", "#pricing"], ["FAQ", "#faq"], ["Blog", "#"], ["API docs", "#"]] },
            { title: "Legal", links: [["Privacy", "#"], ["Terms", "#"], ["DPA", "#"]] },
          ].map((col) => (
            <div key={col.title}>
              <h4 className="text-[12px] font-semibold text-neutral-900 mb-3">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map(([label, href]) => (
                  <li key={label}><a href={href} className="text-[13px] text-neutral-500 hover:text-neutral-900 transition-colors">{label}</a></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-neutral-100 pt-6 flex items-center justify-between">
          <span className="text-[12px] text-neutral-400">&copy; 2026 SelectPilot. Run product research on autopilot.</span>
        </div>
      </div>
    </footer>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-neutral-900 antialiased">
      <Navbar />
      <main>
        <Hero />
        <WhySection />
        <FeaturesSection />
        <WorkflowSection />
        <StatsSection />
        <TestimonialSection />
        <PricingSection />
        <SecuritySection />
        <FAQSection />
        <FooterCTA />
      </main>
      <Footer />
    </div>
  );
}
