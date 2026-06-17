import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch
from bs4 import BeautifulSoup

html = fetch("https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
             use_proxy=True, force_browser=True)
soup = BeautifulSoup(html, "lxml")

card = soup.select_one("div#gridItemRoot") or soup.select_one("div.zg-grid-general-faceout")
print(f"card found: {card is not None}")

if card:
    # 列子元素 class 与 text，用于定位标题
    print("\n--- 子元素含文字内容(>15字符) ---")
    for el in card.find_all(True):
        t = el.get_text(" ", strip=True)
        if 15 < len(t) < 200 and not el.find(True):  # 叶子节点
            cls = " ".join(el.get("class", []))
            print(f"  <{el.name} class='{cls[:50]}'>  {t[:80]}")
    print("\n--- 找含 dp/ 链接 + 周围结构 ---")
    a = card.find("a", href=lambda h: h and "/dp/" in h)
    if a:
        print(f"  href = {a.get('href')[:100]}")
        # 链接里所有 div 的 text
        for d in a.find_all("div"):
            cls = " ".join(d.get("class", []))
            txt = d.get_text(" ", strip=True)
            if txt and len(txt) > 5:
                print(f"    <div class='{cls[:50]}'>  {txt[:80]}")
