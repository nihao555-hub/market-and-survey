"""
直接看 "Customers say" 在 HTML 里的真实上下文 —— 找到注入点。
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.reviews import _fetch_dp_with_review_loaded

ASIN = "B0CRTR3PMF"  # Soundcore P30i, 评论 34112 条
html = _fetch_dp_with_review_loaded(ASIN, use_proxy=True)
print(f"size: {len(html or '')}")

# 找所有 "Customers say" 出现位置 + 周围 800 字符
for m in re.finditer(r"Customers say", html or ""):
    pos = m.start()
    ctx = html[max(0, pos - 300): pos + 1500]
    print(f"\n=== pos={pos} ===")
    print(ctx)
    print("=" * 80)
