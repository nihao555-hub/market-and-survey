"""测试俄罗斯平台 + 印度 + 中东能否抓"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.scraper import fetch, FetchFailed, is_blocked_page
from modules.platforms import PLATFORMS

tests = [
    ("ozon", "smart home"),
    ("wildberries", "умный дом"),  # 俄语"智能家居"
    ("yandex_market", "smart home"),
    ("amazon_in", "smart home"),
    ("flipkart", "smart home"),
    ("amazon_ae", "smart home"),
    ("noon", "smart home"),
    ("amazon_au", "smart home"),
    ("rakuten", "smart home"),
    ("coupang", "smart home"),
    ("trendyol", "akilli ev"),
    ("shopee_sg", "smart home"),
    ("lazada_sg", "smart home"),
    ("tokopedia", "smart home"),
    ("shein", "kitchen"),
]

for plat_id, kw in tests:
    p = PLATFORMS.get(plat_id)
    if not p:
        print(f"❌ {plat_id}: 不在注册表")
        continue
    url = p["search_url"].format(kw=kw.replace(" ", "+"))
    proxy_needed = bool(p.get("needs_proxy"))
    try:
        html = fetch(url, use_proxy=proxy_needed, force_browser=True)
        is_block, sign = is_blocked_page(html)
        # 看是否有商品卡片
        from scrapling.parser import Adaptor
        adp = Adaptor(html, url=url, auto_match=False)
        cards = adp.css(p["card_sel"])
        print(f"✅ {plat_id:20} ({kw[:20]:20}) | HTML={len(html):>7} | cards={len(cards):>3} | blocked={is_block}")
    except FetchFailed as e:
        print(f"❌ {plat_id:20} ({kw[:20]:20}) | {str(e)[:80]}")
    except Exception as e:
        print(f"⚠ {plat_id:20} ({kw[:20]:20}) | {str(e)[:80]}")
