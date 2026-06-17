"""扫描 captured HTML，找出最有可能的商品卡选择器（出现次数 >=10 的容器/链接）"""
import re
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup

CAP = Path(__file__).resolve().parent / "captured"

for f in CAP.glob("*.html"):
    print("\n" + "=" * 80)
    print(f"分析 {f.name} ({f.stat().st_size:,} bytes)")
    print("=" * 80)
    soup = BeautifulSoup(f.read_text(encoding="utf-8"), "lxml")

    # 1) class 出现频次 Top 30
    cls_counter = Counter()
    for tag in soup.find_all(class_=True):
        for c in tag.get("class", []):
            cls_counter[c] += 1
    print("\n[Top 30 class names by frequency]")
    for c, n in cls_counter.most_common(30):
        if n >= 10:
            print(f"  {n:>4}× .{c}")

    # 2) data-* 属性的频次
    attr_counter = Counter()
    for tag in soup.find_all():
        for k in tag.attrs:
            if k.startswith("data-"):
                attr_counter[k] += 1
    print("\n[Top 15 data-* attributes]")
    for a, n in attr_counter.most_common(15):
        if n >= 5:
            print(f"  {n:>4}× [{a}]")

    # 3) 商品链接特征：href 含 product/item/g- 等关键词
    links = soup.find_all("a", href=True)
    pat_count = Counter()
    for a in links:
        h = a["href"]
        for pat in ["/product/", "-g-", "/item/", "/itm/", "/dp/", "/products/"]:
            if pat in h:
                pat_count[pat] += 1
    print("\n[Product-like link patterns]")
    for p, n in pat_count.most_common():
        print(f"  {n:>4}× href contains {p!r}")
