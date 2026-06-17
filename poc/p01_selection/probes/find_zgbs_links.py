"""找 Amazon 搜索页里实际的 BSR 子类目入口"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch
from bs4 import BeautifulSoup

html = fetch("https://www.amazon.com/s?k=wireless+earbuds", use_proxy=True, force_browser=True)
print(f"size: {len(html)}")
soup = BeautifulSoup(html, "lxml")

# Amazon 现在把 BSR 链接放在哪？
# 1. Department 筛选区
print("\n=== Department / Category 筛选区 ===")
for sel in ["#departments", "[data-component-id*='department']",
             "div[id*='Department']", "ul[aria-labelledby*='department']"]:
    el = soup.select_one(sel)
    if el:
        for a in el.select("a[href]"):
            t = a.get_text(strip=True)
            h = a.get("href", "")
            if t and 2 < len(t) < 50:
                print(f"  {t:<40} {h[:80]}")
        break

# 2. 直接找 zgbs 链接
print("\n=== 含 'zgbs' 的链接 ===")
for a in soup.select("a[href*='zgbs']"):
    print(f"  {a.get_text(strip=True)[:50]:<40} {a.get('href','')[:100]}")

# 3. 找面包屑里的类目
print("\n=== 面包屑类目链接 ===")
for sel in ["#nav-subnav", ".s-breadcrumb"]:
    el = soup.select_one(sel)
    if el:
        for a in el.select("a"):
            t = a.get_text(strip=True)
            h = a.get("href", "")
            if t and h:
                print(f"  {t} → {h[:100]}")

# 4. 尝试从 i= 参数倒推 department
print("\n=== 含 'i=' department 参数的链接 ===")
deps = set()
for a in soup.select("a[href*='&i=']"):
    h = a.get("href", "")
    m = re.search(r"[&?]i=([\w-]+)", h)
    if m:
        deps.add(m.group(1))
print(f"  发现 departments: {deps}")
for dep in deps:
    print(f"  → 推测 BSR URL: https://www.amazon.com/Best-Sellers/zgbs/{dep}/")
