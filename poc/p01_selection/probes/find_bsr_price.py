import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch
from bs4 import BeautifulSoup

html = fetch("https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
             use_proxy=True, force_browser=True)
soup = BeautifulSoup(html, "lxml")
cards = soup.select("div#gridItemRoot")
print(f"卡总数: {len(cards)}\n")
# 看前5张卡，每张的 $ 元素
for i, card in enumerate(cards[:5]):
    print(f"=== 卡 #{i+1} ===")
    found_any = False
    for el in card.find_all(True):
        t = el.get_text(strip=True)
        if "$" in t and 1 < len(t) < 30 and not el.find(True):
            cls = " ".join(el.get("class", []))
            print(f"  <{el.name} class='{cls[:70]}'>  {t}")
            found_any = True
    if not found_any:
        print("  (无价格)")
    print()
