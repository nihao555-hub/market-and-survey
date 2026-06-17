import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
h = Path("walmart_v2.html").read_text(encoding="utf-8")
print(f"len: {len(h)}")
# 关键标志
for kw in ["press & hold", "Verify", "Robot", "blocked", "Access Denied", "captcha", "px-captcha", "PerimeterX"]:
    if kw.lower() in h.lower():
        print(f"  ⚠️ contains: {kw}")
print("---first 2000---")
print(h[:2000])
