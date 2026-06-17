"""分析已抓 walmart_dump.html 找当前 selector"""
import sys, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path

html = Path("walmart_dump.html").read_text(encoding="utf-8")
print(f"len: {len(html)}")
print(f"data-item-id 出现次数: {html.count('data-item-id')}")
print(f"data-testid 出现次数: {html.count('data-testid')}")
print(f"$ 出现次数: {html.count('$')}")

# 找价格元素
prices = re.findall(r'\$[\d,]+\.?\d*', html)
print(f"价格匹配（前 10）: {prices[:10]}")

# 找 __NEXT_DATA__ - Walmart 用 Next.js
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
if m:
    print(f"\n✅ 找到 __NEXT_DATA__ ({len(m.group(1))} chars)")
    Path("walmart_next_data.json").write_text(m.group(1), encoding="utf-8")
    try:
        data = json.loads(m.group(1))
        # 找商品列表
        def find_keys(obj, key, depth=0):
            if depth > 8: return []
            results = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == key:
                        results.append(v)
                    results.extend(find_keys(v, key, depth+1))
            elif isinstance(obj, list):
                for it in obj:
                    results.extend(find_keys(it, key, depth+1))
            return results
        items = find_keys(data, "items")
        for it in items[:3]:
            if isinstance(it, list) and len(it) > 0:
                print(f"\n找到商品列表，{len(it)} 个，第一个键：{list(it[0].keys())[:15] if isinstance(it[0], dict) else type(it[0])}")
                if isinstance(it[0], dict):
                    print(f"  name: {it[0].get('name', '')[:80]}")
                    print(f"  price: {it[0].get('price') or it[0].get('priceInfo')}")
                    print(f"  has __typename: {'__typename' in it[0]}")
                break
    except Exception as e:
        print(f"JSON 解析失败: {e}")
else:
    print("\n❌ 没找到 __NEXT_DATA__")
    # 搜其他模式
    print(f"window.__INITIAL_STATE__ 出现: {html.count('__INITIAL_STATE__')}")
    print(f"window.__APOLLO_STATE__ 出现: {html.count('__APOLLO_STATE__')}")
