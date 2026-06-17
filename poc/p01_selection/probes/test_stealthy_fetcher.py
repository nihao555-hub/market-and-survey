"""测试 Scrapling StealthyFetcher 突破 Cloudflare"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapling.fetchers import StealthyFetcher

# 测美区主站点
for url in [
    "https://www.bestbuy.com/site/searchpage.jsp?st=earbuds",
    "https://www.target.com/s?searchTerm=yoga+mat",
    "https://www.aliexpress.com/w/wholesale-yoga-mat.html",
]:
    print(f"\n--- {url[:60]}... ---")
    try:
        page = StealthyFetcher.fetch(url, headless=True, network_idle=True,
                                       google_search=False,
                                       wait_selector_state="visible",
                                       proxy="http://127.0.0.1:10808",
                                       timeout=30000)
        if page:
            html = page.body if hasattr(page, 'body') else page.content
            print(f"  len: {len(html)}, status: {getattr(page, 'status', '?')}")
            print(f"  has 'data-item-id': {'data-item-id' in html}")
            print(f"  has 'add to cart': {'add to cart' in html.lower()}")
            print(f"  has robot: {'robot' in html.lower()[:5000]}")
        else:
            print("  None")
    except Exception as e:
        print(f"  ERROR: {str(e)[:200]}")
