import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch

# Walmart - patchright 拿了 17K，看是啥
html = fetch("https://www.walmart.com/search?q=kitchen", use_proxy=True, force_browser=True)
print(f"Walmart {len(html)} chars")
Path("walmart_via_patchright.html").write_text(html[:50000], encoding="utf-8")
print(html[:1500])
