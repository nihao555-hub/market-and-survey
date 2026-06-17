"""验证修复后的 fetch：① 代理可用时正常抓 ② 拿到反爬页面会被识别丢弃"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.scraper import fetch, FetchFailed

print("\n--- T1: Amazon US (verified, 应该成功) ---")
try:
    html = fetch("https://www.amazon.com/s?k=yoga+mat", use_proxy=True)
    print(f"✅ Amazon US: {len(html)} chars")
    print(f"   含 'data-component-type': {'data-component-type' in html}")
except FetchFailed as e:
    print(f"❌ Amazon US 失败: {e}")

print("\n--- T2: Walmart (blocked, 应该报错或返回空) ---")
try:
    html = fetch("https://www.walmart.com/search?q=yoga+mat", use_proxy=True, force_browser=True)
    print(f"⚠ Walmart 拿到 {len(html)} chars（不应该）")
    # 看是否真有商品
    print(f"   含 'data-item-id': {'data-item-id' in html}")
    print(f"   含 'press & hold': {'press & hold' in html.lower()}")
except FetchFailed as e:
    print(f"✅ Walmart 正确报错: {str(e)[:150]}")

print("\n--- T3: Amazon UK (untested, 用 US 代理) ---")
try:
    html = fetch("https://www.amazon.co.uk/s?k=kitchen+gadgets", use_proxy=True)
    print(f"⚠ Amazon UK 拿到 {len(html)} chars")
    print(f"   含 'data-component-type': {'data-component-type' in html}")
except FetchFailed as e:
    print(f"❌ Amazon UK 失败: {str(e)[:150]}")
