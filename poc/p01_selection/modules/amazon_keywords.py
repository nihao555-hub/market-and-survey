"""
Amazon 搜索自动补全（买家在 Amazon 真实搜索的词）— 免费、无 key、无反爬。

为什么比 Google 关键词更适合电商选品：
- Google 搜索量 = 全网信息查询意图（很多是查资料、看新闻）
- Amazon autocomplete = **买家在 Amazon 真实输入的购物词**，带强购买意图
- 补全顺序 = Amazon 按真实搜索热度排序（第 1 个比第 10 个热）

数据形式：
- 按热度排序的真实长尾词（含品牌词、功能词、场景词）
- 可做：标题/五点关键词、差异化卖点发现（"noise cancelling"/"long battery life" = 买家在意的功能）
"""
from __future__ import annotations
import requests
from loguru import logger

# 各站点 completion 域名 + marketplace id
_MARKETPLACE = {
    "US": ("completion.amazon.com", "ATVPDKIKX0DER"),
    "UK": ("completion.amazon.co.uk", "A1F83G8C2ARO7P"),
    "DE": ("completion.amazon.de", "A1PA6795UKMFR9"),
    "FR": ("completion.amazon.fr", "A13V1IB3VIYZZH"),
    "JP": ("completion.amazon.co.jp", "A1VC38T7YXB528"),
    "CA": ("completion.amazon.ca", "A2EUQ1WTGCTBG2"),
    "IT": ("completion.amazon.it", "APJ6JRA9NG5V4"),
    "ES": ("completion.amazon.es", "A1RKKUPIHCS9HS"),
    "IN": ("completion.amazon.in", "A21TJRUUN4KGV"),
    "AU": ("completion.amazon.com.au", "A39IBJ37TRP1C6"),
}


def get_amazon_keyword_suggestions(seed_keyword: str, geo: str = "US",
                                    deep: bool = False) -> dict:
    """
    拿 Amazon 真实买家搜索补全词（按热度排序）。
    deep=True 时对每个一级建议再扩展一层（a-z 后缀），拿更多长尾。
    """
    geo = geo.upper()
    domain, mid = _MARKETPLACE.get(geo, _MARKETPLACE["US"])
    logger.info(f"🔍 Amazon 自动补全 '{seed_keyword}' ({geo})")

    def _fetch(prefix: str) -> list[str]:
        url = f"https://{domain}/api/2017/suggestions"
        params = {"mid": mid, "alias": "aps", "prefix": prefix, "limit": 11}
        try:
            r = requests.get(url, params=params, timeout=12,
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            data = r.json()
            return [s.get("value") for s in data.get("suggestions", [])
                    if s.get("value") and s.get("value").lower() != prefix.lower()]
        except Exception as e:
            logger.debug(f"amazon suggest fail '{prefix}': {str(e)[:80]}")
            return []

    level1 = _fetch(seed_keyword)
    if not level1:
        return {"seed": seed_keyword, "geo": geo, "error": "no_suggestions",
                "suggestions": []}

    # 一级建议（带热度 rank）
    suggestions = [{"keyword": kw, "rank": i + 1, "level": 1}
                   for i, kw in enumerate(level1)]

    if deep:
        seen = {s["keyword"] for s in suggestions}
        # 对前 5 个一级词再扩展（加空格触发下一层）
        for base in level1[:5]:
            for kw in _fetch(base + " "):
                if kw not in seen:
                    seen.add(kw)
                    suggestions.append({"keyword": kw, "rank": None, "level": 2})

    # 提炼"功能/卖点词"（出现频率高的修饰词 = 买家在意的点）
    import re
    from collections import Counter
    seed_words = set(seed_keyword.lower().split())
    modifiers = Counter()
    for s in suggestions:
        for w in re.findall(r'[a-z]+', s["keyword"].lower()):
            if w not in seed_words and len(w) > 2:
                modifiers[w] += 1
    top_modifiers = [{"word": w, "count": c} for w, c in modifiers.most_common(12)]

    return {
        "seed": seed_keyword, "geo": geo,
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
        "top_modifiers": top_modifiers,  # 高频修饰词 = 买家在意的功能/卖点
        "_source": "Amazon 搜索自动补全（买家真实购物搜索词，按热度排序）",
        "_real_data": True,
        "_note": ("补全顺序即 Amazon 真实搜索热度（rank 1 最热）。"
                  "top_modifiers 是买家高频附加词，反映真实需求点（如 noise cancelling/thick/long battery）。"
                  "用于：Listing 标题关键词 + 差异化卖点发现。"),
    }


if __name__ == "__main__":
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    r = get_amazon_keyword_suggestions("wireless earbuds", "US", deep=True)
    print(json.dumps(r, ensure_ascii=False, indent=2)[:2000])
