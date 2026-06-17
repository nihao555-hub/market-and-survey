import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.bestsellers import get_bestsellers, estimate_monthly_sales_from_bsr

items = get_bestsellers("electronics", use_proxy=True, limit=8)
print(f"\n抓到 {len(items)} 个 BSR 商品\n")
for it in items[:8]:
    rank = it.get("rank")
    sales = estimate_monthly_sales_from_bsr(rank, "electronics") if rank else None
    line = f"  #{rank}  ${it.get('price')}  ★{it.get('rating')}  ~{sales}/mo  ASIN={it.get('asin')[:10]}  {(it.get('title','') or '')[:55]}"
    print(line)
