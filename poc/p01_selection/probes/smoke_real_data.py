"""验证 P0 + P3 修复：真采购成本 + 真关税 + ASIN 池机制"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.real_cost_data import build_real_cost_params, get_hts_duty, get_amazon_referral_rate, calc_fba_fulfillment_fee, get_usd_cny_rate
from modules.sourcing_1688 import estimate_procurement_cost
from modules.asin_pool import POOL
from modules.bestsellers import get_bestsellers

OUT = Path(__file__).resolve().parents[1] / "reports" / "smoke_real_data.md"
buf = []
buf.append("# 真实数据修复验证")

# 1. HTS 关税
buf.append("\n## 1. 真实关税（HTS）")
for cat in ["headphones", "wireless-earbuds", "smartwatch", "kitchen"]:
    r = get_hts_duty(cat)
    buf.append(f"- {cat}: HS={r['hs_code']}, duty_rate={r['duty_rate']*100:.2f}%")

# 2. Amazon Referral
buf.append("\n## 2. Amazon Referral 真实费率")
for cat in ["electronics", "headphones", "kitchen", "jewelry"]:
    buf.append(f"- {cat}: {get_amazon_referral_rate(cat)*100:.1f}%")

# 3. FBA Fee
buf.append("\n## 3. FBA Fulfillment Fee 真实计算")
for w, l in [(2, 5), (8, 10), (16, 14), (40, 20), (80, 30)]:
    f = calc_fba_fulfillment_fee(w, l)
    buf.append(f"- 重量 {w}oz / 最长边 {l}in → ${f}")

# 4. 实时汇率
buf.append("\n## 4. 实时汇率")
buf.append(f"- USD/CNY = {get_usd_cny_rate()}")

# 5. 综合
buf.append("\n## 5. 综合 build_real_cost_params (耳机, $70, 4oz, 5in)")
p = build_real_cost_params("headphones", 70, 4, 5)
buf.append(f"```json\n{json.dumps(p, ensure_ascii=False, indent=2)}\n```")

# 6. 1688 真实采购
buf.append("\n## 6. 1688 真实采购成本（蓝牙耳机）")
r1688 = estimate_procurement_cost("蓝牙耳机", target_sale_price_usd=70, use_proxy=False)
buf.append(f"```json\n{json.dumps(r1688, ensure_ascii=False, indent=2)[:1500]}\n```")

# 7. ASIN 池机制
buf.append("\n## 7. ASIN 池机制（先空，抓 BSR 后入池）")
buf.append(f"- 池初始 size: {POOL.size()}")
items = get_bestsellers("earbud-headphones", use_proxy=True, limit=10)
POOL.add_batch([it for it in items if isinstance(it, dict) and it.get("asin")])
buf.append(f"- 抓耳机子类目 BSR 后池 size: {POOL.size()}")
buf.append(f"- 池子摘要：")
buf.append("```")
buf.append(POOL.summary_for_llm()[:1500])
buf.append("```")

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"✅ 写入 {OUT} ({OUT.stat().st_size} bytes)")
print(f"\n--- 前 50 行 ---")
for line in OUT.read_text(encoding="utf-8").splitlines()[:50]:
    print(line)
