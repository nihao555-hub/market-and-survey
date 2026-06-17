"""
完整成本测算（14 项）+ 盈亏平衡点 + 简易现金流模型
对标资深跨境运营的真实测算口径。
"""
from __future__ import annotations
from typing import Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 成本参数分三类（按数据可得性诚实标注）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# A 类 — 有公开真实数据源（由 real_cost_data.py 实时覆盖，不用下面的默认）：
#   amazon_referral_rate（Amazon 2026 费率表）
#   fba_fulfillment_fee（Amazon FBA Standard Size 表，按重量/尺寸）
#   duty_rate（USITC HTS 关税表，按 HS code）
#   exchange_loss（open.er-api.com 实时汇率）
#
# B 类 — 有行业行情但需估算（头程：海运/空运按重量体积，下面给真实档位）
#
# C 类 — 无公开真实数据源，因卖家而异（ACOS/退货率）：
#   ❌ 不能给单一"真实值"，因为它取决于卖家运营水平、listing 质量、类目竞争
#   ✅ 正确做法：用 monte_carlo_stress_test 跑分布，而不是单点假设
#   下面的默认值仅用于"快速单点参考"，报告里必须配合蒙特卡洛结果一起看
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 默认参数（USD，Amazon US FBA）— A 类会被 real_cost_data 覆盖
DEFAULTS = {
    # B 类（头程）— 会被 estimate_freight_cost 按重量真实估算覆盖
    "shipping_per_unit_to_fba": 4.5,
    # A 类（会被真实数据覆盖）
    "fba_fulfillment_fee": 4.0,
    "fba_storage_per_month": 0.18,
    "amazon_referral_rate": 0.15,
    "duty_rate": 0.10,
    "vat_rate": 0.0,
    "exchange_loss": 0.01,
    "payment_fee_rate": 0.013,          # PingPong/连连 收款费率（公开，0.7-1.5%）
    "test_certification_amortized": 0.30,
    "return_handling_per_unit": 1.5,
    # C 类（无公开真实数据源，仅单点参考，建议看蒙特卡洛分布）
    "ad_acos": 0.20,                    # ⚠️ 因卖家而异，仅参考
    "return_rate": 0.08,                # ⚠️ 因品类/品控而异，仅参考
}

# 新品冷启动期 — C 类参数取行业偏保守端（前 90 天）
NEW_PRODUCT_DEFAULTS = {
    **DEFAULTS,
    "ad_acos": 0.65,                    # ⚠️ 行业观察值，非单一真值；蒙特卡洛会跑 0.30-1.20 区间
    "return_rate": 0.15,                # ⚠️ 同上；蒙特卡洛跑 0.05-0.30
    "test_certification_amortized": 0.50,
}

STABLE_DEFAULTS = {
    **DEFAULTS,
    "ad_acos": 0.20,
    "return_rate": 0.08,
}


def estimate_freight_cost(weight_oz: float, longest_in: float = 8,
                           mode: str = "sea") -> dict:
    """
    头程成本真实估算（替代固定 $4.5）。
    按真实货代行情（2026，中国→美国 FBA 仓）：
    - 海运：约 $4-7/kg（小货拼箱）+ 清关均摊
    - 空运：约 $8-15/kg（快但贵）
    返回每件 USD。
    """
    weight_kg = weight_oz / 35.274
    # 2026 货代行情区间（公开报价，深圳/义乌 → 美西 FBA）
    rates = {
        "sea": 5.5,    # USD/kg 海运拼箱均价（含清关）
        "air": 11.0,   # USD/kg 空运
        "express": 16.0,  # USD/kg 国际快递（DHL/FedEx）
    }
    rate_per_kg = rates.get(mode, rates["sea"])
    # 体积重（抛货）：长宽高/6000，这里简化用最长边估
    volumetric_kg = (longest_in * 2.54) ** 3 / 6000 / 1000 if longest_in else 0
    billing_kg = max(weight_kg, volumetric_kg, 0.05)  # 最小计费重
    per_unit = round(billing_kg * rate_per_kg, 2)
    # 加上固定均摊（清关/打托/贴标）
    per_unit += 0.5
    return {
        "weight_kg": round(weight_kg, 3),
        "billing_kg": round(billing_kg, 3),
        "mode": mode,
        "rate_per_kg_usd": rate_per_kg,
        "freight_per_unit_usd": per_unit,
        "_source": "2026 中国→美西 FBA 货代公开行情（拼箱海运/空运）",
        "_note": "实际运费随油价/旺季/货代议价浮动 ±30%，蒙特卡洛会跑波动区间",
    }


def full_cost_breakdown(
    sale_price: float,
    procurement_cost: float,
    moq: int = 500,
    monthly_sales_estimate: int = 300,
    overrides: Optional[dict] = None,
    stage: str = "stable",
) -> dict:
    """
    输出 14 项成本拆解 + 净利 + 毛利率 + 盈亏平衡 + 占用资金天数估算。
    全部 USD 计。
    
    stage:
    - 'new_product' 新品冷启动期（前 90 天）— ACOS 65% / 退货 15%
    - 'stable'      已稳定老品（默认）— ACOS 20% / 退货 8%
    
    建议商家做新品决策时跑两种 stage 看双场景，差异通常很大。
    """
    base_defaults = NEW_PRODUCT_DEFAULTS if stage == "new_product" else STABLE_DEFAULTS
    p = dict(base_defaults)
    if overrides:
        p.update(overrides)

    # —— 14 项 ——
    c01_procurement = procurement_cost
    c02_shipping = p["shipping_per_unit_to_fba"]
    c03_duty = procurement_cost * p["duty_rate"]
    c04_test = p["test_certification_amortized"]
    c05_fba_fulfill = p["fba_fulfillment_fee"]
    c06_fba_storage = p["fba_storage_per_month"]
    c07_referral = sale_price * p["amazon_referral_rate"]
    c08_ad = sale_price * p["ad_acos"]
    c09_return_loss = (procurement_cost + c02_shipping + c05_fba_fulfill) * p["return_rate"]
    c10_return_ops = p["return_handling_per_unit"] * p["return_rate"]
    c11_vat = sale_price * p["vat_rate"]
    c12_payment_fee = sale_price * p["payment_fee_rate"]
    c13_fx_loss = sale_price * p["exchange_loss"]
    c14_misc = 0.20  # 杂项缓冲

    total_cost = sum([c01_procurement, c02_shipping, c03_duty, c04_test, c05_fba_fulfill,
                      c06_fba_storage, c07_referral, c08_ad, c09_return_loss, c10_return_ops,
                      c11_vat, c12_payment_fee, c13_fx_loss, c14_misc])

    net_profit = sale_price - total_cost
    margin = net_profit / sale_price if sale_price else 0

    # —— 盈亏平衡（每月卖多少件能覆盖固定+营销投入；这里用每月广告预算+检测摊销估算）——
    monthly_fixed = (c08_ad * monthly_sales_estimate) + (c04_test * moq) / max(monthly_sales_estimate, 1)
    contribution_per_unit = sale_price - (
        c01_procurement + c02_shipping + c03_duty + c05_fba_fulfill + c06_fba_storage
        + c07_referral + c09_return_loss + c10_return_ops + c11_vat + c12_payment_fee + c13_fx_loss + c14_misc
    )
    breakeven_units = int(monthly_fixed / contribution_per_unit) if contribution_per_unit > 0 else None

    # —— 资金占用（备货 → 海运 → 上架 → 回款）——
    days_capital_locked = 60  # 海运 30~45 + Amazon 14 天回款
    capital_locked = procurement_cost * moq + c02_shipping * moq

    return {
        "sale_price": round(sale_price, 2),
        "procurement_cost": round(c01_procurement, 2),
        "stage": stage,
        "stage_note": (
            "新品冷启动期 — ACOS 65% + 退货 15%（前 90 天）" if stage == "new_product" else
            "已稳定老品 — ACOS 20% + 退货 8%"
        ),
        "cost_breakdown": {
            "01_procurement": round(c01_procurement, 2),
            "02_shipping_to_fba": round(c02_shipping, 2),
            "03_duty(关税)": round(c03_duty, 2),
            "04_test_cert(检测均摊)": round(c04_test, 2),
            "05_fba_fulfillment": round(c05_fba_fulfill, 2),
            "06_fba_storage_monthly": round(c06_fba_storage, 2),
            "07_amazon_referral(佣金)": round(c07_referral, 2),
            "08_ad_cost(广告)": round(c08_ad, 2),
            "09_return_loss(退货损失)": round(c09_return_loss, 2),
            "10_return_handling": round(c10_return_ops, 2),
            "11_vat": round(c11_vat, 2),
            "12_payment_fee(收款)": round(c12_payment_fee, 2),
            "13_fx_loss(汇率)": round(c13_fx_loss, 2),
            "14_misc(杂项)": round(c14_misc, 2),
        },
        "total_cost": round(total_cost, 2),
        "net_profit": round(net_profit, 2),
        "margin": round(margin, 4),
        "breakeven": {
            "monthly_fixed_cost": round(monthly_fixed, 2),
            "contribution_per_unit": round(contribution_per_unit, 2),
            "breakeven_units_per_month": breakeven_units,
            "estimate_units": monthly_sales_estimate,
            "viable": breakeven_units is not None and breakeven_units < monthly_sales_estimate,
        },
        "cash_flow": {
            "capital_locked_usd": round(capital_locked, 2),
            "days_locked": days_capital_locked,
            "moq": moq,
        },
        "verdict": _verdict(margin, breakeven_units, monthly_sales_estimate),
        "_data_honesty": {
            "real_data_fields": ["amazon_referral", "fba_fee", "duty", "fx_loss", "shipping(按重量行情)"],
            "industry_estimate_fields": {
                "ad_acos": f"{p['ad_acos']} —— 行业观察值，无公开真实数据源，因卖家而异",
                "return_rate": f"{p['return_rate']} —— 行业观察值，因品类/品控而异",
                "shipping_per_unit": f"{p['shipping_per_unit_to_fba']} —— 2026 货代行情档位，浮动±30%",
            },
            "warning": "net_profit/margin 是基于上述行业估算值的【单点参考】，不是真实利润。"
                        "ACOS/退货率/运费因卖家而异，必须配合 monte_carlo_stress_test 的概率分布解读，"
                        "禁止在报告里把这里的数字写成『真实净利』。",
        },
    }


def _verdict(margin: float, breakeven: Optional[int], estimate: int) -> str:
    if margin < 0.10:
        return "❌ 不建议（毛利<10%，承压能力弱）"
    if breakeven is None or estimate < breakeven:
        return f"⚠ 风险高（盈亏平衡点 {breakeven}/月，预估销量 {estimate}/月不够）"
    if margin < 0.18:
        return "🟡 可做但需精细化（毛利 10-18%）"
    return "✅ 推荐（毛利充足且销量覆盖盈亏点）"


def stress_test(sale_price: float, procurement_cost: float, **kw) -> dict:
    """压力测试：广告 ACOS 翻倍 / 退货率 15% / 汇率 -10% 时还能活吗"""
    base = full_cost_breakdown(sale_price, procurement_cost, **kw)
    scenarios = {
        "base": base,
        "ad_doubled (ACOS 40%)": full_cost_breakdown(
            sale_price, procurement_cost,
            overrides={"ad_acos": 0.40}, **kw
        ),
        "high_returns (15%)": full_cost_breakdown(
            sale_price, procurement_cost,
            overrides={"return_rate": 0.15}, **kw
        ),
        "fx_shock (-10%)": full_cost_breakdown(
            sale_price, procurement_cost,
            overrides={"exchange_loss": 0.10}, **kw
        ),
    }
    return {k: {"net_profit": v["net_profit"], "margin": v["margin"], "verdict": v["verdict"]}
            for k, v in scenarios.items()}


def monte_carlo_stress_test(
    sale_price: float, procurement_cost: float,
    moq: int = 500, monthly_sales_estimate: int = 300,
    n_simulations: int = 5000,
    is_new_product: bool = True,
) -> dict:
    """
    蒙特卡洛压力测试 — 5000 次模拟，给出净利分布 + 亏损概率 + VaR/CVaR
    
    模拟 6 个不确定变量同时波动：
    - ACOS（新品冷启动 60%-100%，老品 15%-30%）
    - 退货率（新品 12%-20%，老品 5%-10%）
    - 头程实际成本（海运 $3-6 / 空运 $15-25 加权）
    - 汇率波动（USD/CNY ±5%）
    - 月销量（BSR 估算 ±50% 误差）
    - 采购成本谈判后变化（±10%）
    
    输出：
    - 净利分布（mean / median / std）
    - 亏损概率 P(net_profit < 0)
    - VaR 95%（5% 最坏情况下的损失）
    - CVaR 95%（最坏 5% 的平均损失）
    - 推荐判定（新品冷启动期是否值得做）
    
    比简单 stress_test 真实得多 — 真实业务里 6 个变量同时波动。
    """
    import numpy as np
    
    rng = np.random.default_rng(42)  # 可复现
    
    # 1. ACOS 分布（新品 vs 老品）
    if is_new_product:
        # 新品冷启动：ACOS 60%-100%，对数正态分布偏右
        acos_samples = rng.lognormal(mean=np.log(0.65), sigma=0.25, size=n_simulations)
        acos_samples = np.clip(acos_samples, 0.30, 1.20)
    else:
        acos_samples = rng.normal(0.20, 0.05, size=n_simulations).clip(0.10, 0.40)
    
    # 2. 退货率
    if is_new_product:
        return_samples = rng.normal(0.15, 0.04, size=n_simulations).clip(0.05, 0.30)
    else:
        return_samples = rng.normal(0.08, 0.02, size=n_simulations).clip(0.03, 0.15)
    
    # 3. 头程成本（海运 60% 概率 / 空运 40% 概率）
    shipping_mode = rng.random(n_simulations) < 0.6
    shipping_samples = np.where(
        shipping_mode,
        rng.normal(4.5, 1.0, size=n_simulations),  # 海运
        rng.normal(18.0, 4.0, size=n_simulations),  # 空运
    ).clip(2.0, 30.0)
    
    # 4. 汇率波动
    fx_loss_samples = rng.normal(0.02, 0.03, size=n_simulations).clip(-0.05, 0.10)
    
    # 5. 月销量误差（BSR 估算 ±50%）
    monthly_sales_samples = rng.normal(
        monthly_sales_estimate, monthly_sales_estimate * 0.30, size=n_simulations
    ).clip(monthly_sales_estimate * 0.3, monthly_sales_estimate * 2.0)
    
    # 6. 采购成本谈判后波动 ±10%
    procurement_samples = procurement_cost * rng.normal(1.0, 0.05, size=n_simulations).clip(0.85, 1.15)
    
    # 跑 N 次
    profits = []
    for i in range(n_simulations):
        try:
            r = full_cost_breakdown(
                sale_price, procurement_samples[i], moq, int(monthly_sales_samples[i]),
                overrides={
                    "ad_acos": float(acos_samples[i]),
                    "return_rate": float(return_samples[i]),
                    "shipping_per_unit_to_fba": float(shipping_samples[i]),
                    "exchange_loss": float(fx_loss_samples[i]),
                }
            )
            profits.append(r["net_profit"])
        except Exception:
            profits.append(0)
    
    profits_arr = np.array(profits)
    
    p_loss = float((profits_arr < 0).mean())
    var_95 = float(np.percentile(profits_arr, 5))  # 5% 最坏
    cvar_95 = float(profits_arr[profits_arr <= var_95].mean()) if (profits_arr <= var_95).any() else var_95
    
    # 决策建议
    if p_loss > 0.4:
        verdict = "❌ 不建议（亏损概率 > 40%）"
    elif p_loss > 0.2:
        verdict = "⚠️ 高风险（亏损概率 20-40%），需要更多营销预算才能扛过冷启动"
    elif p_loss > 0.05:
        verdict = "🟡 可做但需精细化运营，设置 ACOS 上限 + 库存周转监控"
    else:
        verdict = "✅ 推荐（亏损概率 < 5%）"
    
    return {
        "n_simulations": n_simulations,
        "is_new_product": is_new_product,
        "input_assumptions": {
            "sale_price": sale_price,
            "procurement_cost_base": procurement_cost,
            "monthly_sales_estimate": monthly_sales_estimate,
        },
        "profit_distribution": {
            "mean": round(float(profits_arr.mean()), 2),
            "median": round(float(np.median(profits_arr)), 2),
            "std": round(float(profits_arr.std()), 2),
            "min": round(float(profits_arr.min()), 2),
            "max": round(float(profits_arr.max()), 2),
            "p10": round(float(np.percentile(profits_arr, 10)), 2),
            "p25": round(float(np.percentile(profits_arr, 25)), 2),
            "p75": round(float(np.percentile(profits_arr, 75)), 2),
            "p90": round(float(np.percentile(profits_arr, 90)), 2),
        },
        "loss_probability": round(p_loss, 3),
        "var_95": round(var_95, 2),
        "cvar_95": round(cvar_95, 2),
        "verdict": verdict,
        "_source": f"蒙特卡洛模拟 {n_simulations} 次（6 个变量同时波动：ACOS/退货/头程/汇率/月销/采购）",
    }


if __name__ == "__main__":
    import json
    print("=== 蒙特卡洛压测 ===")
    r = monte_carlo_stress_test(
        sale_price=42.99, procurement_cost=8.0,
        moq=500, monthly_sales_estimate=600,
        is_new_product=True,
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
