/**
 * 工具名人类化（steering §4.1）：把 snake_case 工具名 + 参数转成可读文案。
 * 用映射表而非 if-else 链，便于扩展（steering 明确要求）。
 *
 * 措辞合规：前端一律用「获取 / 搜索 / 读取 / 分析」等中性词，不出现「抓取/爬取」。
 */
type ToolDisplayRule = {
  inProgress: (input: any) => string;
  finished: (input: any) => string;
};

const q = (input: any, key: string, fallback: any = "") =>
  (input && typeof input === "object" && input[key]) || fallback;

export const TOOL_DISPLAY_RULES: Record<string, ToolDisplayRule> = {
  search_products: {
    inProgress: (i) => `正在搜索 ${q(i, "platform", "平台")} 的「${q(i, "keyword", "")}」`,
    finished: (i) => `已获取 ${q(i, "platform", "平台")} 商品数据`,
  },
  search_multi_platform: {
    inProgress: (i) => `正在并发搜索多平台：${(q(i, "platforms", []) as string[]).join(", ")}`,
    finished: () => `多平台数据获取完成`,
  },
  get_bestsellers_by_url: {
    inProgress: () => `正在获取畅销榜数据`,
    finished: () => `已获取畅销榜数据`,
  },
  get_bestsellers: {
    inProgress: (i) => `正在获取「${q(i, "category", "品类")}」畅销榜`,
    finished: () => `已获取畅销榜数据`,
  },
  discover_bsr_url: {
    inProgress: () => `正在定位目标市场榜单`,
    finished: () => `榜单入口已定位`,
  },
  get_reviews_batch: {
    inProgress: (i) => `正在读取用户评论（${(q(i, "asins", []) as string[]).length} 个商品）`,
    finished: () => `用户评论读取完成`,
  },
  extract_pain_points_precise: {
    inProgress: () => `正在精确统计用户痛点`,
    finished: () => `痛点分析完成`,
  },
  analyze_review_temporal: {
    inProgress: () => `正在分析评论时间分布`,
    finished: () => `评论趋势分析完成`,
  },
  get_trend: {
    inProgress: (i) => `正在查询搜索趋势：${q(i, "keyword", "")}`,
    finished: () => `趋势数据已获取`,
  },
  get_keyword_metrics: {
    inProgress: (i) => `正在扩展关键词：${q(i, "seed_keyword", "")}`,
    finished: () => `关键词数据已获取`,
  },
  compare_seasonality: {
    inProgress: () => `正在分析 5 年季节性`,
    finished: () => `季节性分析完成`,
  },
  get_real_procurement_cost: {
    inProgress: () => `正在查询采购成本`,
    finished: () => `采购成本已获取`,
  },
  get_supplier_detail_price: {
    inProgress: () => `正在查询供应商阶梯报价`,
    finished: () => `阶梯报价已获取`,
  },
  full_cost_breakdown: {
    inProgress: () => `正在做 14 项成本拆解`,
    finished: () => `成本拆解完成`,
  },
  monte_carlo_stress_test: {
    inProgress: () => `正在跑蒙特卡洛压力测试（5000 次）`,
    finished: () => `压力测试完成`,
  },
  deep_ip_risk_assessment: {
    inProgress: () => `正在做 IP 风险深度评估`,
    finished: () => `IP 风险评估完成`,
  },
  capture_evidence_batch: {
    inProgress: () => `正在获取候选品图片与截图证据`,
    finished: () => `证据图片已获取`,
  },
  get_keepa_charts_batch: {
    inProgress: () => `正在获取价格历史曲线`,
    finished: () => `价格历史曲线已获取`,
  },
  pick_platforms_for_market: {
    inProgress: () => `正在选择目标市场平台`,
    finished: () => `平台已选定`,
  },
  generate_report: {
    inProgress: () => `正在生成最终决策报告`,
    finished: () => `报告生成完成`,
  },
};

export function getToolDisplayMessage(
  toolName: string,
  input: any,
  isFinished: boolean
): string {
  const rule = TOOL_DISPLAY_RULES[toolName];
  if (rule) return isFinished ? rule.finished(input) : rule.inProgress(input);
  // 默认：snake_case → 中性文案（统一用「获取/执行」，不用「抓取」）
  const human = toolName.replace(/_/g, " ");
  return isFinished ? `已完成 ${human}` : `正在执行 ${human}`;
}
