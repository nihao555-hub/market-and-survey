"use client";
import React from "react";
import {
  Search,
  TrendingUp,
  Swords,
  Users,
  Lightbulb,
  Activity,
  LineChart,
  Tag,
  PieChart,
  MessageSquare,
  Target,
  Compass,
  Heart,
  Layers,
  Sparkles,
} from "lucide-react";
import type { PageKey } from "@/lib/atoms";
import { ResearchLauncher, type ResearchConfig } from "./ResearchLauncher";
import { TasksPage } from "./TasksPage";
import { ReportsPage } from "./ReportsPage";
import { MonitorPage } from "./MonitorPage";
import { SettingsPage } from "./SettingsPage";
import { FavoritesPage, TrashPage } from "./SimplePages";

const RESEARCH: Record<string, ResearchConfig> = {
  market: {
    key: "market",
    title: "市场调研",
    subtitle: "围绕一个品类完成规模、趋势、需求与竞争的全景调研。",
    icon: <Search className="h-5 w-5" />,
    placeholder: "你想调研哪个市场？",
    examples: ["智能插座 北美市场", "宠物饮水机", "便携榨汁杯 欧洲", "露营折叠椅"],
    dimensions: [
      { title: "市场规模", desc: "TAM / SAM 估算与增长空间", icon: <PieChart className="h-4 w-4" /> },
      { title: "需求趋势", desc: "搜索热度与季节性走势", icon: <TrendingUp className="h-4 w-4" /> },
      { title: "竞争格局", desc: "头部玩家与集中度", icon: <Swords className="h-4 w-4" /> },
      { title: "利润空间", desc: "成本拆解与利润测算", icon: <Tag className="h-4 w-4" /> },
    ],
  },
  trend: {
    key: "trend",
    title: "趋势探索",
    subtitle: "发现正在上升的品类与关键词，捕捉早期机会。",
    icon: <TrendingUp className="h-5 w-5" />,
    placeholder: "想探索什么趋势？",
    examples: ["2024 上升品类", "TikTok 爆款趋势", "夏季户外", "智能家居新趋势"],
    dimensions: [
      { title: "热度走势", desc: "Google Trends 时间序列", icon: <LineChart className="h-4 w-4" /> },
      { title: "上升速度", desc: "周/月环比增长", icon: <Activity className="h-4 w-4" /> },
      { title: "社媒声量", desc: "TikTok / Reddit 讨论", icon: <MessageSquare className="h-4 w-4" /> },
      { title: "相关词扩展", desc: "长尾与关联品类", icon: <Sparkles className="h-4 w-4" /> },
    ],
  },
  competitor: {
    key: "competitor",
    title: "竞品分析",
    subtitle: "拆解对手的 listing、定价、评论与差评痛点。",
    icon: <Swords className="h-5 w-5" />,
    placeholder: "想分析哪些竞品？",
    examples: ["Anker 充电宝", "某款蓝牙耳机", "Top 3 宠物饮水机", "竞品定价对比"],
    dimensions: [
      { title: "Listing 对比", desc: "标题 / 卖点 / 主图", icon: <Layers className="h-4 w-4" /> },
      { title: "定价策略", desc: "价格带与促销", icon: <Tag className="h-4 w-4" /> },
      { title: "评论洞察", desc: "好评亮点与差评痛点", icon: <MessageSquare className="h-4 w-4" /> },
      { title: "销量估算", desc: "BSR → 月销区间", icon: <TrendingUp className="h-4 w-4" /> },
    ],
  },
  audience: {
    key: "audience",
    title: "受众洞察",
    subtitle: "刻画目标人群画像、使用场景与购买动机。",
    icon: <Users className="h-5 w-5" />,
    placeholder: "想洞察哪类人群？",
    examples: ["露营人群画像", "母婴消费者", "宠物主人", "健身爱好者"],
    dimensions: [
      { title: "人群画像", desc: "年龄 / 地域 / 偏好", icon: <Users className="h-4 w-4" /> },
      { title: "使用场景", desc: "高频场景与需求", icon: <Compass className="h-4 w-4" /> },
      { title: "购买动机", desc: "决策因素与顾虑", icon: <Heart className="h-4 w-4" /> },
      { title: "声音来源", desc: "评论 / 社媒 / 问答", icon: <MessageSquare className="h-4 w-4" /> },
    ],
  },
  opportunity: {
    key: "opportunity",
    title: "机会挖掘",
    subtitle: "结合需求缺口与差异化空间，找出可切入的产品机会。",
    icon: <Lightbulb className="h-5 w-5" />,
    placeholder: "想在哪里挖掘机会？",
    examples: ["蓝海细分品类", "差评里的需求缺口", "差异化卖点", "低竞争高需求"],
    dimensions: [
      { title: "需求缺口", desc: "未被满足的痛点", icon: <Target className="h-4 w-4" /> },
      { title: "差异化空间", desc: "可改进的产品方向", icon: <Sparkles className="h-4 w-4" /> },
      { title: "竞争强度", desc: "蓝海 / 红海判定", icon: <Swords className="h-4 w-4" /> },
      { title: "机会评分", desc: "综合可行性打分", icon: <Lightbulb className="h-4 w-4" /> },
    ],
  },
};

export function renderPage(page: PageKey): React.ReactNode {
  if (page in RESEARCH) {
    return <ResearchLauncher config={RESEARCH[page]} />;
  }
  switch (page) {
    case "tasks":
      return <TasksPage />;
    case "reports":
      return <ReportsPage />;
    case "favorites":
      return <FavoritesPage />;
    case "trash":
      return <TrashPage />;
    case "monitor":
      return <MonitorPage />;
    case "settings":
      return <SettingsPage />;
    default:
      return null;
  }
}
