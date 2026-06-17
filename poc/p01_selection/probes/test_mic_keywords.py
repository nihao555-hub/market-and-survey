"""验证关键词映射 — 6 个品类都能拿到 MIC 真实采购成本"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.sourcing_1688 import get_real_procurement_cost

KWS = [
    "厨房收纳", "智能家居", "智能插座", "保鲜盒", 
    "宠物 自动喂食", "蓝牙耳机", "瑜伽垫", "户外 露营",
    "面部按摩", "美容仪",
]

for kw in KWS:
    r = get_real_procurement_cost(kw)
    if r.get("real_data"):
        print(f"✅ {kw:20} | source={r.get('source','?'):20} | "
               f"median=${r.get('median_usd', 'N/A'):>6} | n={r.get('samples', 0):>3}")
    else:
        print(f"❌ {kw:20} | error={r.get('error','?')}")
