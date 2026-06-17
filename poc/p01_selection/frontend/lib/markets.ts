/** 目标市场 / 商家定位 / 模型档位 —— ClarifyForm 与输入框快捷设置共享，单一数据源。 */

/**
 * 数据可得性分级：
 * - strong：有专属出口代理节点 + 平台实测稳定（数据最扎实）
 * - ok    ：该市场平台可抓（本地平台 verified 或 Amazon 站点能出数据）
 *
 * 只列【确实能出数据】的市场。无代理节点且平台被地理封锁的（韩国/中东/澳洲/土耳其等）
 * 不放进来——避免让用户选了却抓不到、被迫用别国数据顶替。
 * 订阅真实节点（2026-06）：US/CA/UK/DE/JP/IN/SG/HK/TW。
 */
export type MarketTier = "strong" | "ok";

export const MARKETS: { code: string; label: string; iso: string; tier: MarketTier; region: string }[] = [
  // 北美洲
  { code: "US", label: "美国", iso: "us", tier: "strong", region: "北美洲" },
  { code: "CA", label: "加拿大", iso: "ca", tier: "strong", region: "北美洲" },
  // 南美洲（MercadoLibre 不强地理封锁，普通出口可抓）
  { code: "BR", label: "巴西", iso: "br", tier: "ok", region: "南美洲" },
  { code: "MX", label: "墨西哥", iso: "mx", tier: "ok", region: "南美洲" },
  // 欧洲
  { code: "UK", label: "英国", iso: "gb", tier: "strong", region: "欧洲" },
  { code: "DE", label: "德国", iso: "de", tier: "strong", region: "欧洲" },
  { code: "FR", label: "法国", iso: "fr", tier: "ok", region: "欧洲" }, // 借德国邻近节点
  { code: "RU", label: "俄罗斯", iso: "ru", tier: "ok", region: "欧洲" }, // Yandex Market 可抓
  // 亚洲
  { code: "CN", label: "中国", iso: "cn", tier: "ok", region: "亚洲" }, // 京东可抓
  { code: "JP", label: "日本", iso: "jp", tier: "strong", region: "亚洲" },
  { code: "IN", label: "印度", iso: "in", tier: "strong", region: "亚洲" },
  { code: "SG", label: "新加坡", iso: "sg", tier: "strong", region: "亚洲" },
];

/** 大洲分组顺序（用于 UI 分区展示） */
export const CONTINENT_ORDER = ["北美洲", "南美洲", "欧洲", "亚洲"];

export const POSITIONINGS = ["中端", "高端", "低价走量", "差异化细分"];

export function marketLabel(code: string): string {
  return MARKETS.find((m) => m.code === code)?.label || code;
}

export function marketIso(code: string): string {
  return MARKETS.find((m) => m.code === code)?.iso || "";
}

export function marketTier(code: string): MarketTier {
  return MARKETS.find((m) => m.code === code)?.tier || "ok";
}

/** 按大洲分组（UI 用） */
export function marketsByContinent(): { region: string; markets: typeof MARKETS }[] {
  return CONTINENT_ORDER.map((region) => ({
    region,
    markets: MARKETS.filter((m) => m.region === region),
  })).filter((g) => g.markets.length > 0);
}
