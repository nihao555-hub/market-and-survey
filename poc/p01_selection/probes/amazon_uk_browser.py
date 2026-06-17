"""用 patchright 浏览器走完 Akamai 挑战拿真实数据"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch_with_patchright, fetch_with_botasaurus, is_blocked_page

print("--- patchright (with proxy + 6s wait) ---")
html = fetch_with_patchright("https://www.amazon.co.uk/s?k=kitchen+gadgets",
                               proxy="http://127.0.0.1:10808", wait_ms=6000)
if html:
    print(f"OK {len(html)} chars")
    blocked, sign = is_blocked_page(html)
    print(f"  blocked={blocked} sign={sign}")
    print(f"  has data-component-type: {'data-component-type' in html}")
else:
    print("None")

print("\n--- botasaurus (with proxy) ---")
html = fetch_with_botasaurus("https://www.amazon.co.uk/s?k=kitchen+gadgets",
                               proxy="http://127.0.0.1:10808")
if html:
    print(f"OK {len(html)} chars")
    blocked, sign = is_blocked_page(html)
    print(f"  blocked={blocked} sign={sign}")
    print(f"  has data-component-type: {'data-component-type' in html}")
else:
    print("None")
