"""
修 14 个 HTML 拿到了但 selector 过时的平台。
策略：抓 HTML → 用浏览器实际访问页面 → 找当前真正能用的卡片 selector → 写回 platforms.py
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.scraper import fetch
from modules.platforms import PLATFORMS

# 一次性抓所有 selector 待修平台并诊断
TO_FIX = [
    ("shopee_sg", "wireless earbuds"),
    ("shopee_my", "wireless earbuds"),
    ("lazada_sg", "earphones"),
    ("tokopedia", "earphones"),
    ("shein", "kitchen organizer"),
    ("alibaba", "earbuds"),
    ("tiktok_shop", "earbuds"),
    ("trendyol", "kulaklik"),
    ("cdiscount", "ecouteurs"),
    ("otto", "kopfhorer"),
    ("yandex_market", "earphones"),
    ("flipkart", "earphones"),
    ("amazon_ae", "earphones"),
    ("noon", "earphones"),
    ("wildberries", "earphones"),
]


def find_card_selector(html: str, plat_id: str) -> dict:
    """从 HTML 自动挖掘最可能的商品卡片 selector"""
    from scrapling.parser import Adaptor
    adp = Adaptor(html, url="", auto_match=False)
    
    # 候选 selector（按 e-commerce 通用模式排序）
    candidates = [
        # 通用 data-* 属性
        ("[data-item-id]", "data-item-id"),
        ("[data-test='product-card']", "data-test product-card"),
        ("[data-testid='product-card']", "data-testid product-card"),
        ("[data-component='product-card']", "data-component product-card"),
        ("[data-pid]", "data-pid"),
        ("[data-id^='product']", "data-id product"),
        ("[data-product-id]", "data-product-id"),
        ("[data-sku]", "data-sku"),
        ("[data-asin]", "data-asin"),
        ("[itemprop='itemListElement']", "schema.org itemList"),
        # class 模式
        ("[class*='product-card']", "class含 product-card"),
        ("[class*='ProductCard']", "class含 ProductCard"),
        ("[class*='product-item']", "class含 product-item"),
        ("[class*='ProductItem']", "class含 ProductItem"),
        ("[class*='item-card']", "class含 item-card"),
        ("[class*='goods-item']", "class含 goods-item"),
        ("[class*='goods-card']", "class含 goods-card"),
        ("[class*='listItem']", "class含 listItem"),
        ("[class*='SearchResultItem']", "class含 SearchResultItem"),
        # 特殊
        ("article[class*='product']", "article+product"),
        ("li[class*='product']", "li+product"),
        ("li[class*='item']", "li+item"),
        ("article", "article 任意"),
    ]
    
    found = []
    for sel, label in candidates:
        try:
            cnt = len(adp.css(sel))
            if cnt >= 5:  # 至少 5 个才算靠谱
                found.append({"selector": sel, "label": label, "count": cnt})
        except Exception:
            pass
    
    return {"plat_id": plat_id, "html_len": len(html), "candidates": found[:5]}


def main():
    print("修复 selector — 抓 HTML 并自动诊断\n" + "="*60)
    out_lines = ["# Selector 修复报告\n"]
    
    for plat_id, kw in TO_FIX:
        if plat_id not in PLATFORMS:
            continue
        p = PLATFORMS[plat_id]
        url = p["search_url"].format(kw=kw.replace(" ", "+"))
        use_proxy = bool(p.get("needs_proxy"))
        try:
            html = fetch(url, use_proxy=use_proxy, force_browser=True)
        except Exception as e:
            print(f"❌ {plat_id}: fetch 失败 {str(e)[:80]}")
            continue
        
        diag = find_card_selector(html, plat_id)
        print(f"\n--- {plat_id} ({len(html)} chars) ---")
        out_lines.append(f"\n## {plat_id} ({p.get('name')}) — HTML {len(html)} chars\n\n")
        out_lines.append(f"原 selector: `{p['card_sel']}`\n\n候选：\n\n")
        if diag["candidates"]:
            for c in diag["candidates"]:
                print(f"  ✅ {c['selector']:50} ({c['label']}) → {c['count']}")
                out_lines.append(f"- `{c['selector']}` — {c['count']} 个 ({c['label']})\n")
        else:
            print(f"  ⚠ 没找到候选 selector，HTML 可能是 SPA 未渲染")
            out_lines.append("- ⚠ 未找到候选\n")
    
    Path("reports/selector_fix.md").write_text("".join(out_lines), encoding="utf-8")
    print(f"\n📊 详情存：reports/selector_fix.md")


if __name__ == "__main__":
    main()
