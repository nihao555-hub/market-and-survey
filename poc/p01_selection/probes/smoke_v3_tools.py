"""验证 A 路径所有新工具能真实工作"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.agent_tools import TOOL_IMPL

print("="*60)
print("1) compare_seasonality（5年历史季节性）")
try:
    r = TOOL_IMPL["compare_seasonality"](keyword="yoga mat", geo="US")
    if r.get("error"):
        print(f"  ❌ {r['error']}")
    else:
        print(f"  ✅ 峰值月 {r['peak_month']}月({r['peak_value']}) 谷值月 {r['valley_month']}月({r['valley_value']})")
        print(f"     季节性强度 {r['seasonality_strength']} | 当前 {r['current_month']}月 {r['current_position']}")
        print(f"     {r['verdict'][:100]}")
except Exception as e:
    print(f"  ❌ 异常: {e}")

print("\n" + "="*60)
print("2) monte_carlo_stress_test（5000次模拟）")
try:
    r = TOOL_IMPL["monte_carlo_stress_test"](
        sale_price=39.99, procurement_cost=4.6,
        monthly_sales_estimate=500, is_new_product=True, n_simulations=3000
    )
    pd = r["profit_distribution"]
    print(f"  ✅ 净利 mean=${pd['mean']} median=${pd['median']}")
    print(f"     亏损概率 {r['loss_probability']*100:.1f}% | VaR95 ${r['var_95']} | CVaR95 ${r['cvar_95']}")
    print(f"     {r['verdict']}")
except Exception as e:
    print(f"  ❌ 异常: {e}")

print("\n" + "="*60)
print("3) full_cost_breakdown 双 stage（new_product vs stable）")
try:
    from modules.full_cost import full_cost_breakdown
    for stg in ["new_product", "stable"]:
        r = full_cost_breakdown(39.99, 4.6, moq=500, monthly_sales_estimate=500, stage=stg)
        print(f"  {stg:12} → 净利 ${r['net_profit']} 毛利率 {r['margin']*100:.1f}% {r['verdict']}")
except Exception as e:
    print(f"  ❌ 异常: {e}")

print("\n" + "="*60)
print("4) extract_pain_points_precise（Python 精确统计）")
try:
    sample_reviews = [
        "The mat slides on hardwood floor, very slippery",
        "It slides around during practice, not stable at all",
        "Battery dies after 6 months, charge doesn't hold",
        "Great grip, love it",
        "The surface started peeling after 3 weeks",
        "slips when I sweat, dangerous for hot yoga",
        "peeling and flaking everywhere",
    ]
    r = TOOL_IMPL["extract_pain_points_precise"](reviews=sample_reviews)
    if r.get("error"):
        print(f"  ❌ {r['error']}")
    else:
        for p in r.get("pain_points", [])[:5]:
            print(f"  ✅ {p['pain_name']}: 精确命中 {p['exact_count']} 次 (hit_rate {p['hit_rate']})")
except Exception as e:
    print(f"  ❌ 异常: {e}")

print("\n" + "="*60)
print("5) get_keyword_metrics（DDGS 长尾词）")
try:
    r = TOOL_IMPL["get_keyword_metrics"](seed_keyword="yoga mat", max_suggestions=8)
    if r.get("error"):
        print(f"  ❌ {r['error']}")
    else:
        print(f"  ✅ {r['suggestion_count']} 个长尾词:")
        for s in r.get("suggestions", [])[:8]:
            print(f"     - {s['keyword']} (内容量 {s['content_volume']})")
except Exception as e:
    print(f"  ❌ 异常: {e}")

print("\n所有 v3 工具冒烟测试完成")
