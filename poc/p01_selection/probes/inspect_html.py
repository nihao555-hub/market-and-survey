"""
对未通过的站点保存实际 HTML 到磁盘，方便人工/脚本分析真实结构，找到正确选择器。
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from patchright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "captured"
OUT.mkdir(exist_ok=True)

TARGETS = [
    ("temu", "https://www.temu.com/search_result.html?search_key=wireless+earbuds"),
    ("aliexpress", "https://www.aliexpress.com/w/wholesale-wireless-earbuds.html"),
]


def grab(name: str, url: str):
    print(f"[{name}] → {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 800}, locale="en-US",
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # 滚动几次帮助 SPA 加载
        for _ in range(3):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(800)
        page.wait_for_timeout(2000)
        html = page.content()
        path = OUT / f"{name}.html"
        path.write_text(html, encoding="utf-8")
        print(f"[{name}] saved {len(html):,} bytes → {path}")
        browser.close()


if __name__ == "__main__":
    for n, u in TARGETS:
        try:
            grab(n, u)
        except Exception as e:
            print(f"[{n}] FAIL: {e}")
        time.sleep(1)
