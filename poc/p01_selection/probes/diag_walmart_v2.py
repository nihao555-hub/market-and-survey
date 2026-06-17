"""强制等待 Walmart React 渲染完，再抓 DOM"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 直接用 patchright 控制等待
from patchright.sync_api import sync_playwright

PROXY = {"server": "http://127.0.0.1:10808"}
URL = "https://www.walmart.com/search?q=wireless+earbuds"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, proxy=PROXY)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        locale="en-US",
        viewport={"width": 1920, "height": 1080},
    )
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    # 等真实商品出现
    try:
        page.wait_for_selector("[data-item-id], [data-testid='item-stack'] > div, section[data-testid] [class*='product']", timeout=20000)
    except Exception as e:
        print(f"等商品 selector 超时: {e}")
    page.wait_for_timeout(3000)  # 多等 3 秒让懒加载完成
    
    # 拉 HTML
    html = page.content()
    print(f"HTML 长度: {len(html)}")
    Path("walmart_v2.html").write_text(html[:600000], encoding="utf-8")
    
    # 直接在页面里查多种 selector
    for sel in [
        "[data-item-id]",
        "[data-testid='item-stack'] > div",
        "div[data-testid='list-view']",
        "div[role='group']",
        "section [class*='ProductCard']",
        "div[data-testid='item']",
        "div[data-automation-id='product']",
        "[data-test='product-card']",
        "[data-stack-index]",
    ]:
        cnt = page.locator(sel).count()
        if cnt > 0:
            print(f"  ✅ {sel}: {cnt} 个")
            # 取第一个的标题/价格
            first = page.locator(sel).first
            try:
                txt = first.inner_text()[:200]
                print(f"     样本文本: {txt}")
            except Exception:
                pass
    
    browser.close()
print("\n✅ 完成，已存 walmart_v2.html")
