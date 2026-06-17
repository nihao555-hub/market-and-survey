"""验证 26 平台注册表"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.platforms import summary, list_all, list_tested_ok, build_search_url

s = summary()
print(f"总平台数: {s['total']}")
print(f"\n按地区分布:")
for r, ps in s["by_region"].items():
    print(f"  {r}: {len(ps)} 个 — {', '.join(ps)}")
print(f"\n按状态:")
for st, n in s["by_status"].items():
    print(f"  {st}: {n}")
print(f"\n实测可用 ({s['tested_ok_count']}):")
for p in list_tested_ok():
    print(f"  ✅ {p['id']:<14} {p['name']:<24} {p['region']:<16} URL: {p['evidence_url']}")

print(f"\n--- 测 build_search_url ---")
for pid in ["amazon", "shopee_sg", "rakuten", "mercadolibre"]:
    print(f"  {pid:<14} → {build_search_url(pid, 'wireless earbuds')}")
