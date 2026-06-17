from pathlib import Path
import re

html = Path("poc/01-选品/probes/captured/aliexpress.html").read_text(encoding="utf-8")
print("Total length:", len(html))
print("Contains 'captcha':", "captcha" in html.lower())
print("Contains 'verify':", "verify" in html.lower())
print("Contains 'punish':", "punish" in html.lower())
print("Contains 'item' anchors:", len(re.findall(r'href="/item/', html)))
print("Contains '_full.html':", html.count("_full.html"))
print("script tags:", html.count("<script"))

# 提取 title
m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
print("Title:", m.group(1).strip()[:200] if m else "?")

# 看页面顶部内容
print("\n--- first 2000 chars (text only) ---")
text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
text = re.sub(r"<[^>]+>", " ", text)
text = re.sub(r"\s+", " ", text).strip()
print(text[:2000])
