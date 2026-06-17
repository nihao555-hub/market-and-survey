"""诊断 Amazon UK 商品卡片价格 selector"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.scraper import fetch_with_patchright
from scrapling.parser import Adaptor

html = fetch_with_patchright("https://www.amazon.co.uk/s?k=kitchen+storage",
                              proxy="http://127.0.0.1:10808", wait_ms=6000)
print(f"len: {len(html) if html else 0}")

if html:
    Path("amazon_uk_dump.html").write_text(html[:800000], encoding="utf-8")
    adp = Adaptor(html, url="x", auto_match=False)
    cards = adp.css("div[data-component-type='s-search-result']")
    print(f"cards: {len(cards)}")
    if cards:
        c = cards[0]
        # 看价格相关元素
        for sel in [
            "span.a-price span.a-offscreen",
            "span.a-price-whole",
            "span.a-color-base.a-text-bold",
            "span[data-a-color='price']",
            "div[data-cy='price-recipe']",
            ".a-price",
            "span.a-color-price",
        ]:
            n = c.css(sel)
            if n:
                txts = [(x.text or "").strip()[:30] for x in n[:3]]
                print(f"  {sel}: {len(n)} 个, 文本: {txts}")
        # 看 raw HTML 第一卡片
        raw = c.html_content[:3000] if hasattr(c, 'html_content') else str(c)[:3000]
        # 找 £ 符号附近
        for m in re.finditer(r'£[\d,]+\.?\d*', raw):
            pos = m.start()
            print(f"  £ 位置: {raw[max(0,pos-100):pos+50]}")
            break
