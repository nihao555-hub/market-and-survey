"""端到端冒烟测试 — 完整链路：discover → BSR → reviews → 1688 → 成本 → 截图"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.bestsellers import discover_bestsellers_url, get_bestsellers_by_url
from modules.reviews import get_product_review_summary
from modules.sourcing_1688 import get_real_procurement_cost
from modules.full_cost import full_cost_breakdown
from modules.real_cost_data import build_real_cost_params
from modules.evidence import screenshot_url

OUT = Path(__file__).resolve().parents[1] / "reports" / "smoke_chain.md"
buf = []

# 1. LLM 给关键词，自动发现 BSR 子类目
buf.append("## 1. discover_bsr_url (LLM 给关键词，工具自动发现真实子类目)")
d = discover_bestsellers_url("wireless earbuds", use_proxy=True)
buf.append(f"- search_url: {d.get('search_url')}")
buf.append(f"- 候选数: {len(d.get('candidates', []))}")
for c in d.get("candidates", [])[:5]:
    buf.append(f"  - {c['department_text']} → {c['url']}")

# 2. 抓第一个 BSR URL
buf.append("\n## 2. get_bestsellers_by_url 抓真品")
r = {"items": []}
if d.get("candidates"):
    bsr_url = d["candidates"][0]["url"]
    r = get_bestsellers_by_url(bsr_url, use_proxy=True, limit=10)
    buf.append(f"- URL: {bsr_url}")
    buf.append(f"- 抓到: {r.get('count', 0)} 件")
    for it in r.get("items", [])[:5]:
        buf.append(f"  - #{it.get('rank')} ${it.get('price')} ★{it.get('rating')} "
                    f"reviews={it.get('review_count')} ASIN={it.get('asin')} "
                    f"{(it.get('title') or '')[:50]}")
else:
    buf.append("- ⚠ 没发现 BSR 候选 URL")

# 3. 真实评论
buf.append("\n## 3. 真实评论 + 关键词云")
items = r.get("items", [])
test_asins = [it["asin"] for it in items if it.get("asin")][:2]
for asin in test_asins:
    rev = get_product_review_summary(asin, use_proxy=True)
    buf.append(f"\n### ASIN={asin}")
    buf.append(f"- 评论数: {rev.get('total_reviews')}, 抓到样本: {rev.get('sample_count')}")
    buf.append(f"- AI summary: {rev.get('ai_summary','无')[:200]}")
    buf.append(f"- 关键词云数: {len(rev.get('keywords', []))}")
    for kw in rev.get("keywords", [])[:8]:
        buf.append(f"  - {kw}")
    if rev.get("error"):
        buf.append(f"- ⚠ error: {rev['error']}")

# 4. 1688 真实采购成本
buf.append("\n## 4. 1688 采购成本（真实获取，失败时返回 error）")
sp = get_real_procurement_cost("蓝牙耳机", use_proxy=False)
buf.append(f"```json\n{json.dumps(sp, ensure_ascii=False, indent=2)[:1000]}\n```")

# 5. 真实成本参数
buf.append("\n## 5. 真实成本参数（关税+佣金+FBA+汇率）")
real = build_real_cost_params("headphones", 70, 4, 5)
buf.append(f"```json\n{json.dumps(real, ensure_ascii=False, indent=2)}\n```")

# 6. 完整 14 项成本测算
buf.append("\n## 6. 完整 14 项成本测算（真实参数）")
fb = full_cost_breakdown(69.99, 18.0, moq=500, monthly_sales_estimate=600,
                          overrides={k: v for k, v in real.items() if not k.startswith("_")})
buf.append(f"- 净利: ${fb['net_profit']} 毛利率: {fb['margin']*100:.2f}%")
buf.append(f"- 决策: {fb['verdict']}")
buf.append(f"- 14 项成本：")
for k, v in fb["cost_breakdown"].items():
    buf.append(f"  - {k}: ${v}")

# 7. 截图证据（取 ASIN 池中一件做截图）
buf.append("\n## 7. 证据截图")
if test_asins:
    sc = screenshot_url(f"https://www.amazon.com/dp/{test_asins[0]}",
                        f"smoke_{test_asins[0]}", use_proxy=True)
    buf.append(f"```json\n{json.dumps(sc, ensure_ascii=False, indent=2)}\n```")

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"\n✅ 写入 {OUT} ({OUT.stat().st_size} bytes)")
print(f"\n--- 前 80 行 ---")
for line in OUT.read_text(encoding="utf-8").splitlines()[:80]:
    print(line)
