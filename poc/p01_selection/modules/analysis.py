"""
分析层：自研的"小脑子"——
1) 利润测算（公式）
2) 简易蓝海/红海评分（基于价格分布、库存、评分）
3) 选品建议（规则；后续可换 LLM）
LLM 接入预留接口，但 PoC 不强依赖外部 API，确保跑通。

⚠️⚠️ 弃用警告（2026-06）⚠️⚠️
本模块的 calc_profit / score_opportunity / suggest_decisions 含**编造假设**
（如 suggest_decisions 用"成本=40%售价"、"广告=10%售价"等拍脑袋数字）。
这些**绝对不可用于 agent 的真实选品报告**。
- agent 工具链已完全不调用本模块（见 agent_tools.py 顶部说明）；
- 利润测算统一走 modules.full_cost.full_cost_breakdown 的真实数据路径。
本模块仅保留给老的 modules.pipeline（离线 demo 脚本）兼容，勿在新代码里 import。
"""

from __future__ import annotations
import pandas as pd
from loguru import logger

_DEPRECATION = ("modules.analysis 含编造假设（成本=40%售价等），禁止用于真实选品报告；"
                "请改用 modules.full_cost.full_cost_breakdown（真实数据路径）。")


# ---------- 利润测算 ----------
def calc_profit(
    sale_price: float,
    cost: float,
    shipping: float = 0.0,
    platform_fee_rate: float = 0.15,
    fba_fee: float = 0.0,
    ad_cost: float = 0.0,
    return_rate: float = 0.05,
    tax_rate: float = 0.0,
) -> dict:
    """单品利润测算（美元/英镑通用，按相同币种计算）"""
    gross = sale_price
    fees = sale_price * platform_fee_rate + fba_fee + ad_cost
    cogs = cost + shipping
    revenue_after_returns = gross * (1 - return_rate)
    tax = revenue_after_returns * tax_rate
    net = revenue_after_returns - cogs - fees - tax
    margin = net / sale_price if sale_price else 0
    return {
        "sale_price": round(sale_price, 2),
        "cogs": round(cogs, 2),
        "fees": round(fees, 2),
        "tax": round(tax, 2),
        "net_profit": round(net, 2),
        "margin": round(margin, 4),
    }


# ---------- 蓝海/红海打分 ----------
def score_opportunity(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入：商品最新快照 DataFrame（含 price/rating/in_stock）
    输出：附加 opportunity_score（0-100，越高越蓝海）
    简易规则：
      - 价格分散度高(细分多/竞争弱) → 加分
      - 平均评分低（用户不满意，有改进空间）→ 加分
      - 缺货比例高 → 加分（供给紧）
    """
    if df.empty:
        return df
    out = df.copy()
    price_std = out["price"].std()
    avg_rating = out["rating"].mean() if out["rating"].notna().any() else 3.5
    out_of_stock_ratio = 1 - out["in_stock"].mean()

    # 各维度归一到 0-1
    s1 = min(price_std / 30.0, 1.0)
    s2 = (5.0 - avg_rating) / 5.0
    s3 = out_of_stock_ratio

    score = round((0.4 * s1 + 0.4 * s2 + 0.2 * s3) * 100, 1)
    out["opportunity_score"] = score
    logger.info(f"机会评分：{score}（价格分散={s1:.2f}, 评分缺口={s2:.2f}, 缺货={s3:.2f}）")
    return out


# ---------- 选品建议（规则+预留 LLM 接口） ----------
def suggest_decisions(scored: pd.DataFrame, top_n: int = 10) -> list[dict]:
    """从打分结果中挑出候选品，给出建议"""
    if scored.empty:
        return []
    # 候选标准：评分中等偏低（有改进空间）+ 价格在中位数附近 + 仍在售
    median_price = scored["price"].median()
    candidates = scored[
        (scored["price"].between(median_price * 0.7, median_price * 1.3))
        & (scored["in_stock"])
    ].sort_values("price", ascending=False).head(top_n)

    suggestions = []
    for _, r in candidates.iterrows():
        prof = calc_profit(
            sale_price=r["price"],
            cost=r["price"] * 0.4,           # 假设成本 = 40% 售价
            shipping=2.0,
            platform_fee_rate=0.15,
            ad_cost=r["price"] * 0.10,
        )
        suggestions.append({
            "title": r["title"],
            "price": r["price"],
            "rating": r["rating"],
            "url": r["url"],
            "estimated_profit": prof["net_profit"],
            "estimated_margin": prof["margin"],
            "decision": "上架" if prof["margin"] > 0.20 else "观察",
            "reason": f"机会分 {r['opportunity_score']}，毛利 {prof['margin']*100:.1f}%",
        })
    return suggestions


if __name__ == "__main__":
    print(calc_profit(20, 8, 2, 0.15, 0, 2, 0.05))
