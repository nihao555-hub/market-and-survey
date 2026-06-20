"""验证多 ASIN 批量评论获取，一次拿 16+ 条真评论"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reviews import get_reviews_batch

ASINS = ["B0DGHMNQ5Z", "B0FQFB8FMG", "B0DXXYS4BJ"]  # AirPods 4 / AirPods Pro 3 / Roku
r = get_reviews_batch(ASINS, use_proxy=True, max_total=30)

OUT = Path(__file__).resolve().parents[1] / "reports" / "reviews_batch_test.md"
buf = []
buf.append("# 多 ASIN 批量评论获取测试")
buf.append(f"\n**ASIN 数**: {r['asins_count']}  **评论总数**: {r['total_reviews']}\n")
buf.append("## 各 ASIN 概览\n")
for p in r['per_asin']:
    buf.append(f"- **{p['asin']}** ({p.get('rating','-')}★, {p.get('total_reviews','-')} 评)")
    buf.append(f"  - 标题: {p.get('title','')}")
    buf.append(f"  - 抓到样本数: {p.get('samples', 0)}")
buf.append("\n## 真实评论（前 15 条）\n")
for i, rev in enumerate(r['reviews'][:15], 1):
    rating = rev.get('rating', '?')
    title = rev.get('title', '').strip()
    body = rev.get('body', '').strip()
    asin = rev.get('from_asin', '?')
    date = rev.get('date', '')
    buf.append(f"### #{i}  [{rating}★] {title}")
    buf.append(f"- ASIN: {asin}  |  {date}")
    buf.append(f"- {body[:300]}{'...' if len(body) > 300 else ''}\n")

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"✅ 写入：{OUT}")
print(f"   文件大小：{OUT.stat().st_size} bytes")
print(f"   评论总数：{r['total_reviews']}")
print(f"\n--- 前 30 行预览 ---")
for line in OUT.read_text(encoding="utf-8").splitlines()[:30]:
    print(line)
