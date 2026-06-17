import sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reviews import get_product_review_summary, reviews_to_text_list

asin = "B0DGHMNQ5Z"  # Apple AirPods 4
r = get_product_review_summary(asin)
print(f"\nASIN={asin}")
print(f"title: {r.get('title','')[:80]}")
print(f"rating: {r.get('rating')}")
print(f"total_reviews: {r.get('total_reviews')}")
print(f"ai_summary 长度: {len(r.get('ai_summary',''))}")
if r.get("ai_summary"):
    print(f"ai_summary 前300: {r['ai_summary'][:300]}")
print(f"sample_reviews 数: {len(r.get('sample_reviews', []))}")
for s in r.get("sample_reviews", [])[:5]:
    print(f"  - [{s.get('rating') or s.get('section','')}] {s.get('body','')[:100]}")

print("\n--- 喂 LLM 用的文本列表 ---")
for t in reviews_to_text_list(r):
    print(f" → {t[:160]}")
