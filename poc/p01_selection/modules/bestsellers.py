"""
Amazon Best Sellers / Movers & Shakers / 子类目 BSR 抓取
不硬编码类目 URL，让 LLM 给关键词，工具自动从 Amazon 站内搜索/导航发现真实 URL。
所有数据带 source_url，方便报告引用。
"""
from __future__ import annotations
from typing import Optional
from loguru import logger
from bs4 import BeautifulSoup
import urllib.parse, re

from modules.scraper import fetch


# 极少数顶层入口（Amazon 自己保证不会变的）
ROOT_BSR = "https://www.amazon.com/Best-Sellers/zgbs/"
ROOT_MOVERS = "https://www.amazon.com/gp/movers-and-shakers/"

# market/geo → Amazon 站点域名后缀。没有 Amazon 业务的市场不在表内。
AMAZON_TLD = {
    "US": "com", "UK": "co.uk", "GB": "co.uk", "DE": "de", "FR": "fr",
    "JP": "co.jp", "IN": "in", "AU": "com.au", "CA": "ca", "IT": "it",
    "ES": "es", "MX": "com.mx", "BR": "com.br", "SG": "sg", "AE": "ae",
    "SA": "sa", "NL": "nl", "SE": "se", "PL": "pl", "TR": "com.tr",
}
# 这些市场 Amazon 不运营（或基本无份额）→ BSR 不可用，应改用 search_multi_platform
NO_AMAZON_MARKETS = {"RU", "ID", "TH", "MY", "PH", "VN", "EG", "KR", "CN"}


# ━━━━━━━━━━ BSR → 月销估算的可校准曲线（无真实销量时的经验回退）━━━━━━━━━━
# 抽成模块级配置，便于按真实数据（如抓到的『bought in past month』样本）回归校准，
# 而不必改函数体。值越接近真实越好；这是「估算」非「真值」，故 real_data=False。
#
# 每档 (bsr 上限, 月销下限, 月销上限)，按 BSR 升序；最后一档用 None 表示无上限。
BSR_SALES_BRACKETS: list[tuple[int | None, int, int]] = [
    (100,     8000, 30000),
    (1000,    2000, 10000),
    (10000,   500,  3000),
    (100000,  100,  800),
    (None,    20,   200),
]
# 类目销量系数（相对 electronics=1.0）；未列出的类目用 DEFAULT。
BSR_CATEGORY_FACTORS: dict[str, float] = {
    "electronics": 1.0, "home-kitchen": 0.9, "beauty": 0.8,
    "toys": 0.6, "sports": 0.5,
}
BSR_CATEGORY_FACTOR_DEFAULT = 0.7


def bsr_sales_bracket(bsr: int) -> tuple[int, int]:
    """按 BSR 返回 (月销下限, 月销上限)，取自可校准的 BSR_SALES_BRACKETS。"""
    for upper, low, high in BSR_SALES_BRACKETS:
        if upper is None or bsr <= upper:
            return low, high
    last = BSR_SALES_BRACKETS[-1]
    return last[1], last[2]


def amazon_domain_for(geo: str | None) -> str:
    """返回该市场对应的 amazon 域名（含协议），无 Amazon 业务则回退 .com。"""
    tld = AMAZON_TLD.get((geo or "US").upper(), "com")
    return f"https://www.amazon.{tld}"


def discover_bestsellers_url(category_keyword: str, use_proxy: bool = True,
                              geo: str = "US") -> dict:
    """
    LLM 给类目关键词，工具尝试自动发现真实 BSR 子类目 URL（按目标市场选 Amazon 站点）。
    Amazon 搜索页 UI 是 SPA，UI 上的 zgbs 链接可能为空。
    本函数返回：① 直接搜索 URL（必有）② 已知映射（少数高频品类）③ Best Sellers 顶部入口
    LLM 应理解：发现失败时应该用 search_products 直接抓搜索结果，再从中提 ASIN 入池。

    market 无 Amazon 业务（RU/东南亚等）时，返回 amazon_available=False，
    提示 LLM 改用 search_multi_platform 抓本地平台（lazada/ozon/...）。
    """
    geo_u = (geo or "US").upper()
    base = amazon_domain_for(geo_u)
    q = urllib.parse.quote(category_keyword)
    search_url = f"{base}/s?k={q}"
    logger.info(f"🔍 发现子类目（{geo_u} → {base}） → {search_url}")

    if geo_u in NO_AMAZON_MARKETS:
        return {
            "keyword": category_keyword, "geo": geo_u,
            "amazon_available": False,
            "search_url": None, "candidates": [],
            "note": (f"目标市场 {geo_u} 没有 Amazon 业务，BSR 不适用。"
                     f"请改用 search_multi_platform 抓该市场的本地平台"
                     f"（如 lazada_sg / ozon / mercadolibre 等）获取畅销品。"),
        }

    candidates = [
        {"department_text": "通用搜索结果（兜底）", "url": search_url, "type": "search"},
        {"department_text": "Best Sellers 顶页", "url": f"{base}/Best-Sellers/zgbs/",
         "type": "root_bs"},
    ]

    # 高频跨境品类的已知 BSR 子类目（社区维护，公开 node-id）。
    # node-id 在各 Amazon 站点通用性不保证，仅 US 站点确定有效；非 US 站点只给搜索兜底。
    known_subcategories = {
        "wireless earbuds": "/Best-Sellers-Electronics-Earbud-In-Ear-Headphones/zgbs/electronics/12097479011/",
        "earbud": "/Best-Sellers-Electronics-Earbud-In-Ear-Headphones/zgbs/electronics/12097479011/",
        "bluetooth headphones": "/Best-Sellers-Electronics-Over-Ear-Headphones/zgbs/electronics/172541/",
        "over ear headphones": "/Best-Sellers-Electronics-Over-Ear-Headphones/zgbs/electronics/172541/",
        "on ear headphones": "/Best-Sellers-Electronics-On-Ear-Headphones/zgbs/electronics/172543/",
        "bluetooth speaker": "/Best-Sellers-Electronics-Portable-Bluetooth-Speakers/zgbs/electronics/7073956011/",
        "smart watch": "/Best-Sellers-Electronics-Smartwatches/zgbs/electronics/7939901011/",
        "smartwatch": "/Best-Sellers-Electronics-Smartwatches/zgbs/electronics/7939901011/",
        "phone case": "/Best-Sellers-Cell-Phones-Accessories-Cell-Phone-Basic-Cases/zgbs/wireless/2407749011/",
        "kitchen": "/Best-Sellers-Kitchen-Dining-Kitchen-Utensils-Gadgets/zgbs/home-garden/289814/",
    }
    if geo_u == "US":
        low = category_keyword.lower()
        for k, v in known_subcategories.items():
            if k in low:
                candidates.insert(0, {"department_text": f"匹配 known: {k}",
                                      "url": base + v, "type": "bsr"})
                break

    return {"keyword": category_keyword, "geo": geo_u, "amazon_available": True,
            "search_url": search_url, "candidates": candidates,
            "note": ("如果你想要的具体子类目不在 known list，请直接用 search_products(amazon, keyword) "
                     "抓搜索结果（已自动入池），效果一样")}


def _parse_bsr_grid(html: str, source: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    cards = soup.select("div#gridItemRoot") or soup.select("div.zg-grid-general-faceout")
    for c in cards:
        try:
            rank_node = c.select_one("span.zg-bdg-text") or c.select_one(".zg-badge-text")
            rank_txt = rank_node.get_text(strip=True).replace("#", "") if rank_node else ""
            rank = int(rank_txt) if rank_txt.isdigit() else None

            title_node = (c.select_one("[class*='p13n-sc-css-line-clamp']")
                          or c.select_one("div.p13n-sc-truncate"))
            title = title_node.get_text(" ", strip=True) if title_node else ""

            a = c.select_one("a.a-link-normal[href*='/dp/']")
            href = a.get("href", "") if a else ""
            asin = ""
            if "/dp/" in href:
                asin = href.split("/dp/")[1].split("/")[0].split("?")[0]
            full_url = ("https://www.amazon.com" + href) if href.startswith("/") else href

            price_node = c.select_one("[class*='p13n-sc-price']")
            price = None
            if price_node:
                t = price_node.get_text(strip=True).replace("$", "").replace(",", "")
                try:
                    price = float(t.split()[0])
                except Exception:
                    pass

            rating_node = c.select_one("span.a-icon-alt") or c.select_one("i.a-icon-star span")
            rating = None
            if rating_node:
                try:
                    rating = float(rating_node.get_text(strip=True).split()[0])
                except Exception:
                    pass

            review_node = c.select_one("span.a-size-small")
            review_count = None
            if review_node:
                t = review_node.get_text(strip=True).replace(",", "")
                if t.isdigit():
                    review_count = int(t)

            # 真实月销：BSR 卡片上的 "X+ bought in past month"
            bought_past_month = None
            try:
                ctext = c.get_text(" ", strip=True)
                bm = re.search(r'([\d,.]+[KkMm]?\+?)\s*bought in past month', ctext, re.IGNORECASE)
                if bm:
                    raw = bm.group(1).replace("+", "").replace(",", "")
                    mult = 1
                    if raw and raw[-1] in "Kk": mult = 1000; raw = raw[:-1]
                    elif raw and raw[-1] in "Mm": mult = 1_000_000; raw = raw[:-1]
                    bought_past_month = int(float(raw) * mult) if raw else None
            except Exception:
                pass

            if title or asin:
                item = {
                    "rank": rank, "asin": asin, "title": title[:120],
                    "price": price, "rating": rating, "review_count": review_count,
                    "url": full_url, "source": source, "source_url": source_url,
                }
                if bought_past_month is not None:
                    item["bought_past_month"] = bought_past_month
                items.append(item)
        except Exception as e:
            logger.debug(f"parse bsr item err: {e}")
            continue
    return items


def get_bestsellers_by_url(bsr_url: str, use_proxy: bool = True, limit: int = 50,
                            paginate: bool = True) -> dict:
    """
    抓 BSR URL。Amazon BSR 一页 50 条；paginate=True 时自动抓 page 2 拼到 100 条。
    """
    logger.info(f"📦 BSR by URL → {bsr_url} (limit={limit}, paginate={paginate})")
    all_items = []
    pages_to_fetch = 1
    if paginate and limit > 50:
        pages_to_fetch = min(4, (limit + 49) // 50)  # 最多 4 页 = 200 条
    
    for page_no in range(1, pages_to_fetch + 1):
        page_url = bsr_url if page_no == 1 else (
            bsr_url + ("&" if "?" in bsr_url else "?") + f"pg={page_no}"
        )
        try:
            html = fetch(page_url, use_proxy=use_proxy, force_browser=True)
        except Exception as e:
            logger.warning(f"BSR page {page_no} fail: {str(e)[:80]}")
            continue
        items = _parse_bsr_grid(html, source=bsr_url, source_url=page_url)
        if not items:
            break  # 没数据了，停翻页
        all_items.extend(items)
        if len(all_items) >= limit:
            break
    
    return {"url": bsr_url, "pages_fetched": pages_to_fetch,
            "count": len(all_items[:limit]),
            "total_raw": len(all_items),
            "items": all_items[:limit]}


def get_movers_shakers_by_url(url: str, use_proxy: bool = True, limit: int = 50) -> dict:
    logger.info(f"📈 Movers&Shakers by URL → {url}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return {"url": url, "error": str(e)[:120], "items": []}
    items = _parse_bsr_grid(html, source=url, source_url=url)
    return {"url": url, "count": len(items), "items": items[:limit]}


# 兼容旧函数名（被其他文件 import）
def estimate_monthly_sales_from_bsr(bsr: int, category: str = "electronics",
                                     bought_past_month: int = None) -> dict:
    """
    月销估算。优先用 Amazon 第一方真实数据『X+ bought in past month』，
    没有才退回 BSR 经验公式（明确标注 real_data=False）。
    """
    # 优先：Amazon 搜索页/详情页的真实月销标签
    if bought_past_month is not None and bought_past_month > 0:
        return {
            "bsr": bsr, "category": category, "real_data": True,
            "monthly_sales": bought_past_month,
            "monthly_sales_display": f"{bought_past_month}+",
            "source": "Amazon『X+ bought in past month』第一方真实销量数据",
            "note": "Amazon 官方展示的过去 30 天真实购买量（下限值，实际更高）",
        }
    if not bsr or bsr <= 0:
        return {"bsr": bsr, "real_data": False, "error": "no bsr & no bought-data"}
    factor = BSR_CATEGORY_FACTORS.get(category, BSR_CATEGORY_FACTOR_DEFAULT)
    base_low, base_high = bsr_sales_bracket(bsr)
    return {
        "bsr": bsr, "category": category, "real_data": False,
        "estimated_monthly_sales_low": int(base_low * factor),
        "estimated_monthly_sales_high": int(base_high * factor),
        "source": "公开行业经验区间（Amazon 不公开真实销量）",
        "warning": "区间估算，非真实销量。若要真实月销，请抓含『bought in past month』标签的搜索结果。",
    }


def get_bestsellers(category: str = "electronics", use_proxy: bool = True, limit: int = 30,
                     geo: str = "US") -> list[dict]:
    """兼容旧调用（agent_tools 老版会用到）"""
    discovered = discover_bestsellers_url(category, use_proxy=use_proxy, geo=geo)
    if discovered.get("candidates"):
        url = discovered["candidates"][0]["url"]
        r = get_bestsellers_by_url(url, use_proxy=use_proxy, limit=limit)
        return r.get("items", [])
    return [{"error": "no bsr url discovered for " + category}]


def get_movers_shakers(category: str = "electronics", use_proxy: bool = True, limit: int = 30) -> list[dict]:
    return []  # 弃用，改用 by_url
