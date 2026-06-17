"""
1688 真实采购成本（仅返回真实抓取结果，不估算、不模拟）
若抓不到数据，返回 error 让 Agent 知道并采取真实替代方案。

供应链多级备用：
- L1 1688（中国 B2B 龙头，最低价但反爬严）
- L2 Made-in-China（英文界面，反爬轻）
- L3 AliExpress 跨境批发（含 Wholesale 标签的商品，但价格略高）
- L4 Alibaba.com B2B（全球 B2B）
"""
from __future__ import annotations
import re, urllib.parse
from loguru import logger
from bs4 import BeautifulSoup

from modules.scraper import fetch
from modules.real_cost_data import get_usd_cny_rate


def search_made_in_china(keyword_en: str, use_proxy: bool = False, limit: int = 20) -> dict:
    """搜 Made-in-China.com，英文界面反爬轻很多。"""
    q = urllib.parse.quote(keyword_en.replace(" ", "_"))
    url = f"https://www.made-in-china.com/products-search/hot-china-products/{q}.html"
    logger.info(f"🏭 搜 Made-in-China → {keyword_en}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return {"keyword": keyword_en, "url": url, "error": str(e)[:120], "items": []}
    
    soup = BeautifulSoup(html, "lxml")
    items = []
    # 优先 [class*='product-card'] 和 [class*='gallery-product']，其次 [class*='product']
    cards = (soup.select("[class*='product-card']")
              or soup.select("[class*='gallery-product']")
              or soup.select("[class*='ProductCard']")
              or soup.select("div.product-item"))
    if not cards:
        # 兜底：用 strong.price 反向定位卡片父级
        prices = soup.select("strong.price, [class*='price-new']")
        cards = []
        for p in prices[:limit * 2]:
            # 向上 4 层找含 h2 的卡片父级
            cur = p
            for _ in range(5):
                cur = cur.parent
                if cur and cur.find("h2"):
                    cards.append(cur)
                    break
        cards = list({id(c): c for c in cards}.values())
    
    for c in cards[:limit]:
        try:
            title_node = c.select_one("h2 a") or c.select_one("h2") or c.select_one("a[title]")
            price_node = c.select_one("strong.price") or c.select_one("[class*='price']")
            if not title_node:
                continue
            title = title_node.get_text(strip=True)[:140]
            href = title_node.get("href", "") if hasattr(title_node, "get") else ""
            if href and not href.startswith("http"):
                href = "https:" + href if href.startswith("//") else "https://www.made-in-china.com" + href
            
            price_usd = None
            moq = None
            if price_node:
                ptxt = price_node.get_text(" ", strip=True)
                # "US$7.45-9.20" 或 "$5.00 / Piece"
                m = re.search(r'US?\$?\s?([\d.]+)', ptxt)
                if m:
                    try:
                        price_usd = float(m.group(1))
                    except Exception:
                        pass
            # MOQ
            for kw_node in c.select("[class*='moq'], [class*='MinOrder'], [class*='order']"):
                txt = kw_node.get_text(" ", strip=True)
                if "piece" in txt.lower() or "ピース" in txt:
                    mm = re.search(r'(\d+)', txt)
                    if mm:
                        moq = int(mm.group(1))
                        break
            
            if title and price_usd and 0.1 < price_usd < 1000:  # 合理价格区间
                items.append({"title": title, "price_usd": price_usd,
                               "moq": moq, "source_url": href})
        except Exception:
            continue
    return {"keyword": keyword_en, "url": url, "count": len(items), "items": items}


def _extract_moq_ladder(text: str) -> list[dict]:
    """
    从商品详情页文本提取 MOQ 价格阶梯（精准单价突破口）。
    匹配多种格式：
    - "100-499 Pieces US$8.50" / "1000+ Pieces $6.20"
    - "≥500 Pieces $7.00"
    - "1 - 99 pieces $9.99 / 100 - 999 pieces $8.50"
    返回 [{min_qty, max_qty, price_usd}]，按 min_qty 升序。
    """
    ladders = []
    # 格式1: 数字-数字 单位 ... 价格
    for m in re.finditer(
        r'(\d[\d,]*)\s*[-–~]\s*(\d[\d,]*)\s*(?:Pieces?|Sets?|Bags?|Units?|pcs?|PCS?)'
        r'[^$€£]{0,40}(?:US\s*)?[\$€£]\s*([\d]+\.?\d*)', text, re.I):
        try:
            ladders.append({
                "min_qty": int(m.group(1).replace(",", "")),
                "max_qty": int(m.group(2).replace(",", "")),
                "price_usd": float(m.group(3)),
            })
        except Exception:
            continue
    # 格式2: >=N 单位 ... 价格
    for m in re.finditer(
        r'[≥>]=?\s*(\d[\d,]*)\s*(?:Pieces?|Sets?|Units?|pcs?|PCS?)'
        r'[^$€£]{0,30}(?:US\s*)?[\$€£]\s*([\d]+\.?\d*)', text, re.I):
        try:
            ladders.append({
                "min_qty": int(m.group(1).replace(",", "")),
                "max_qty": None,
                "price_usd": float(m.group(2)),
            })
        except Exception:
            continue
    # 去重 + 排序
    seen = set()
    uniq = []
    for l in sorted(ladders, key=lambda x: x["min_qty"]):
        key = (l["min_qty"], l["price_usd"])
        if key not in seen and 0.1 < l["price_usd"] < 2000:
            seen.add(key)
            uniq.append(l)
    return uniq


def get_supplier_detail_price(detail_url: str, target_qty: int = 500,
                               use_proxy: bool = True, max_retries: int = 3) -> dict:
    """
    抓供应商商品详情页的 **精准 MOQ 阶梯价**（突破搜索页只有区间的限制）。
    带重试扛 MIC/DHgate 间歇反爬。
    
    target_qty: 商家计划下单量 → 返回对应档位的精准单价。
    """
    if not detail_url or not detail_url.startswith("http"):
        return {"ok": False, "error": "invalid_url"}
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            html = fetch(detail_url, use_proxy=use_proxy, force_browser=True)
        except Exception as e:
            last_err = str(e)[:120]
            logger.warning(f"[detail_price] 第{attempt}次抓取失败: {last_err}")
            continue
        if not html or len(html) < 8000:
            last_err = f"page_too_small_{len(html or '')}"
            logger.warning(f"[detail_price] 第{attempt}次页面过小（{len(html or '')}），重试")
            continue
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        ladder = _extract_moq_ladder(text)
        # MOQ
        moq = None
        moq_m = re.search(r'(?:Min\.?\s*Order|MOQ|Minimum Order(?:\s*Quantity)?)[:\s]*(\d[\d,]*)', text, re.I)
        if moq_m:
            moq = int(moq_m.group(1).replace(",", ""))
        if not ladder:
            # 没阶梯，至少抓单一价格
            single = re.findall(r'(?:US\s*)?[\$€£]\s*([\d]+\.?\d*)', text)
            single_prices = sorted([float(x) for x in single if 0.1 < float(x) < 2000])[:5]
            if not single_prices:
                last_err = "no_price_in_detail"
                continue
            return {
                "ok": True, "url": detail_url, "moq": moq,
                "has_ladder": False,
                "single_prices_usd": single_prices,
                "price_at_target_qty": single_prices[len(single_prices)//2],  # 取中位
                "target_qty": target_qty,
                "_attempts": attempt,
                "_source": "供应商详情页（无阶梯，取页面价格中位）",
                "_note": "未找到 MOQ 阶梯表，返回详情页价格中位数作参考",
            }
        # 找 target_qty 对应的档位
        chosen = ladder[0]
        for l in ladder:
            if l["min_qty"] <= target_qty and (l["max_qty"] is None or target_qty <= l["max_qty"]):
                chosen = l
                break
            if l["min_qty"] <= target_qty:
                chosen = l  # 取不超过 target 的最大档
        return {
            "ok": True, "url": detail_url, "moq": moq,
            "has_ladder": True,
            "price_ladder": ladder,
            "target_qty": target_qty,
            "price_at_target_qty": chosen["price_usd"],
            "chosen_tier": chosen,
            "_attempts": attempt,
            "_source": "供应商详情页 MOQ 阶梯价（精准单价）",
            "_real_data": True,
            "_note": f"按下单量 {target_qty} 件取对应档位单价 ${chosen['price_usd']}，比搜索页区间精准",
        }
    return {"ok": False, "url": detail_url, "error": last_err or "all_retries_failed"}


def search_globalsources(keyword_en: str, use_proxy: bool = True, limit: int = 20) -> dict:
    """搜 GlobalSources.com（老牌国际 B2B，英文，反爬中等）。"""
    q = urllib.parse.quote(keyword_en)
    url = f"https://www.globalsources.com/searchList/products?query={q}"
    logger.info(f"🏭 搜 GlobalSources → {keyword_en}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return {"keyword": keyword_en, "url": url, "error": str(e)[:120], "items": []}
    soup = BeautifulSoup(html, "lxml")
    items = []
    cards = (soup.select("[class*='product-item']") or soup.select("[class*='ProductItem']")
             or soup.select("[class*='product-card']") or soup.select("a[href*='/product/']"))
    for c in cards[:limit]:
        try:
            title_node = c.select_one("[class*='title']") or c.select_one("a[title]") or c.select_one("h3")
            price_node = c.select_one("[class*='price']") or c.select_one("[class*='Price']")
            if not (title_node and price_node):
                continue
            title = (title_node.get("title") or title_node.get_text(strip=True))[:140]
            href = title_node.get("href", "") if hasattr(title_node, "get") else ""
            if href and not href.startswith("http"):
                href = "https:" + href if href.startswith("//") else "https://www.globalsources.com" + href
            m = re.search(r'([\d.]+)', price_node.get_text(" ", strip=True).replace("US$", "").replace("$", ""))
            price_usd = float(m.group(1)) if m else None
            if title and price_usd and 0.1 < price_usd < 1000:
                items.append({"title": title, "price_usd": price_usd, "source_url": href})
        except Exception:
            continue
    return {"keyword": keyword_en, "url": url, "count": len(items), "items": items}


def search_dhgate(keyword_en: str, use_proxy: bool = True, limit: int = 20) -> dict:
    """搜 DHgate.com（跨境批发，英文界面，反爬中等）。价格通常含 MOQ 阶梯。"""
    q = urllib.parse.quote(keyword_en)
    url = f"https://www.dhgate.com/wholesale/search.do?act=search&searchkey={q}"
    logger.info(f"🏭 搜 DHgate → {keyword_en}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return {"keyword": keyword_en, "url": url, "error": str(e)[:120], "items": []}

    soup = BeautifulSoup(html, "lxml")
    items = []
    cards = (soup.select("[class*='gallery-main']")
             or soup.select("[class*='listitem']")
             or soup.select("div.item-wrap"))
    for c in cards[:limit]:
        try:
            title_node = c.select_one("a[title]") or c.select_one("h3 a") or c.select_one("[class*='title']")
            price_node = c.select_one("[class*='price']") or c.select_one("span.price")
            if not (title_node and price_node):
                continue
            title = (title_node.get("title") or title_node.get_text(strip=True))[:140]
            href = title_node.get("href", "") if hasattr(title_node, "get") else ""
            if href and not href.startswith("http"):
                href = "https:" + href if href.startswith("//") else "https://www.dhgate.com" + href
            ptxt = price_node.get_text(" ", strip=True)
            m = re.search(r'([\d.]+)', ptxt.replace("US $", "").replace("$", ""))
            price_usd = float(m.group(1)) if m else None
            if title and price_usd and 0.1 < price_usd < 1000:
                items.append({"title": title, "price_usd": price_usd, "source_url": href})
        except Exception:
            continue
    return {"keyword": keyword_en, "url": url, "count": len(items), "items": items}


def _relevance_filter(items: list[dict], keyword_en: str, min_overlap: int = 1) -> list[dict]:
    """
    过滤明显不相关的采购结果（防 Made-in-China 返回『整体橱柜』当『水槽下置物架』）。
    要求商品标题与关键词至少有 min_overlap 个有意义词重叠。
    """
    stop = {"the", "a", "an", "for", "with", "and", "of", "to", "in", "pack", "set",
            "new", "hot", "sale", "high", "quality", "wholesale", "custom", "oem"}
    kw_words = {w for w in re.findall(r'[a-z]+', keyword_en.lower()) if w not in stop and len(w) > 2}
    if not kw_words:
        return items
    filtered = []
    for it in items:
        title_words = set(re.findall(r'[a-z]+', (it.get("title") or "").lower()))
        if len(kw_words & title_words) >= min_overlap:
            filtered.append(it)
    return filtered



def search_1688(keyword: str, use_proxy: bool = False, limit: int = 20) -> dict:
    """搜 1688，仅返回真实抓到的商品。失败返回 error。"""
    q = urllib.parse.quote(keyword)
    url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={q}"
    logger.info(f"🏭 搜 1688 → {keyword}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return {"keyword": keyword, "url": url, "error": str(e)[:120], "items": []}

    soup = BeautifulSoup(html, "lxml")

    # 检测被验证码挡
    title = soup.title.text.strip() if soup.title else ""
    if "captcha" in (title + html[:500]).lower() or "interception" in title.lower():
        return {"keyword": keyword, "url": url,
                "error": "blocked_by_alibaba_nc_captcha",
                "title_seen": title,
                "items": []}

    items: list[dict] = []
    cards = (soup.select("div.offer-card-box")
             or soup.select("div[class*='offer-card']")
             or soup.select("a[href*='offer/']"))
    for c in cards[:limit]:
        try:
            price_node = c.select_one("[class*='price']") or c.select_one("[class*='Price']")
            price_text = price_node.get_text(" ", strip=True) if price_node else ""
            title_node = c.select_one("[class*='title']") or c.select_one("h3")
            title = title_node.get_text(" ", strip=True)[:100] if title_node else ""
            prices = [float(x) for x in re.findall(r"\d+\.?\d*", price_text)]
            link = c.get("href") or c.select_one("a")
            href = link if isinstance(link, str) else (link.get("href") if link else "")
            if title and prices:
                items.append({"title": title, "price_cny": min(prices),
                               "max_price_cny": max(prices),
                               "source_url": href if href.startswith("http") else f"https:{href}"})
        except Exception:
            continue

    return {"keyword": keyword, "url": url, "count": len(items), "items": items}


def get_real_procurement_cost(category_keyword_zh: str, use_proxy: bool = False) -> dict:
    """
    获取真实采购成本 — 多级备用源（1688 → Made-in-China → Alibaba）。
    返回字段含 source_url 用于报告引用。
    """
    # L1: 1688
    r = search_1688(category_keyword_zh, use_proxy=use_proxy)
    
    # L1 失败 → L2 Made-in-China
    if r.get("error") or not r.get("items"):
        # 中英品类映射（让 LLM 也可以直接传英文 — 哪个语言更精准用哪个）
        cn_to_en = {
            # 蓝牙/电子
            "蓝牙耳机": "wireless earbuds", "耳机": "earphones",
            "智能手表": "smartwatch", "充电宝": "power bank",
            # 美容
            "美容": "beauty", "面部按摩": "facial massager",
            "led 面部": "led face mask", "美容仪": "beauty device",
            "脱毛": "hair removal", "刮痧": "gua sha",
            # 厨房
            "厨房收纳": "kitchen storage organizer",
            "厨房用品": "kitchen tools", "厨房": "kitchen",
            "餐具": "tableware",
            "保鲜盒": "food container",
            "调料瓶": "spice jar",
            "刀具": "kitchen knife",
            # 家居
            "智能家居": "smart home gadgets",
            "智能插座": "smart plug wifi",
            "智能灯": "smart led light",
            "温湿度计": "temperature humidity monitor",
            "感应灯": "motion sensor light",
            # 户外/运动
            "瑜伽垫": "yoga mat", "户外": "outdoor camping",
            "运动": "fitness sport", "露营": "camping gear",
            "健身": "fitness equipment",
            # 宠物
            "宠物": "pet supplies", "自动喂食": "automatic pet feeder",
            "宠物玩具": "pet toy",
            # 服饰/包
            "背包": "backpack",
            # 母婴
            "婴儿": "baby product",
        }
        keyword_en = category_keyword_zh
        # 多关键词组合时尝试匹配最长的中文片段
        matched = None
        for cn, en in sorted(cn_to_en.items(), key=lambda x: -len(x[0])):
            if cn in category_keyword_zh:
                matched = en
                break
        if matched:
            keyword_en = matched
        # 整体仍含中文 → 仅保留英文部分
        if any('\u4e00' <= ch <= '\u9fff' for ch in keyword_en):
            # 只保留英文/数字/空格
            en_chars = re.findall(r'[a-zA-Z0-9 ]+', category_keyword_zh)
            if en_chars:
                keyword_en = " ".join(en_chars).strip()
            else:
                keyword_en = "wholesale supplies"  # 兜底关键词
        
        logger.info(f"🏭 1688 fail，fallback Made-in-China: {keyword_en}")
        r2 = search_made_in_china(keyword_en, use_proxy=use_proxy)

        # 相关性过滤：剔除明显不相关的结果（防『整体橱柜』当『水槽下置物架』）
        r2_items_all = r2.get("items", [])
        r2_items = _relevance_filter(r2_items_all, keyword_en, min_overlap=1)
        # 过滤后太少（<3 件）说明匹配度差，放宽不过滤但标注低置信
        relevance_low = False
        if len(r2_items) < 3 and r2_items_all:
            r2_items = r2_items_all
            relevance_low = True

        if r2_items:
            prices_usd = sorted([it["price_usd"] for it in r2_items if it.get("price_usd")])
            n = len(prices_usd)
            if n > 0:
                return {
                    "category": category_keyword_zh,
                    "search_keyword_en": keyword_en,
                    "source": "made-in-china.com",
                    "source_url": r2["url"],
                    "real_data": True,
                    "relevance_confidence": "low" if relevance_low else "ok",
                    "samples": n,
                    "fx_rate_usd_cny": get_usd_cny_rate(),
                    "min_usd": prices_usd[0],
                    "p25_usd": prices_usd[max(0, n // 4)],
                    "median_usd": prices_usd[n // 2],
                    "p75_usd": prices_usd[min(n - 1, n * 3 // 4)],
                    "max_usd": prices_usd[-1],
                    "items": r2_items[:10],
                    "_note": ("1688 反爬，自动 fallback 到 Made-in-China.com（英文 B2B，反爬轻），价格通常比 1688 高 5-15%"
                              + ("。⚠️ 相关性较低（标题与关键词重叠少），请人工核对样品是否对应目标品类后再用于测算"
                                 if relevance_low else "")),
                }

        # L3: DHgate 兜底
        logger.info(f"🏭 Made-in-China 无匹配，fallback DHgate: {keyword_en}")
        r3 = search_dhgate(keyword_en, use_proxy=use_proxy)
        r3_items = _relevance_filter(r3.get("items", []), keyword_en, min_overlap=1) or r3.get("items", [])
        if r3_items:
            prices_usd = sorted([it["price_usd"] for it in r3_items if it.get("price_usd")])
            n = len(prices_usd)
            if n > 0:
                return {
                    "category": category_keyword_zh,
                    "search_keyword_en": keyword_en,
                    "source": "dhgate.com",
                    "source_url": r3["url"],
                    "real_data": True,
                    "samples": n,
                    "fx_rate_usd_cny": get_usd_cny_rate(),
                    "min_usd": prices_usd[0],
                    "p25_usd": prices_usd[max(0, n // 4)],
                    "median_usd": prices_usd[n // 2],
                    "p75_usd": prices_usd[min(n - 1, n * 3 // 4)],
                    "max_usd": prices_usd[-1],
                    "items": r3_items[:10],
                    "_note": "1688 + Made-in-China 均未匹配，fallback DHgate（跨境批发，价格含零售加价，仅供参考下限）",
                }

        # L4: GlobalSources 兜底
        logger.info(f"🏭 DHgate 无匹配，fallback GlobalSources: {keyword_en}")
        r4 = search_globalsources(keyword_en, use_proxy=use_proxy)
        r4_items = _relevance_filter(r4.get("items", []), keyword_en, min_overlap=1) or r4.get("items", [])
        if r4_items:
            prices_usd = sorted([it["price_usd"] for it in r4_items if it.get("price_usd")])
            n = len(prices_usd)
            if n > 0:
                return {
                    "category": category_keyword_zh,
                    "search_keyword_en": keyword_en,
                    "source": "globalsources.com",
                    "source_url": r4["url"],
                    "real_data": True,
                    "samples": n,
                    "fx_rate_usd_cny": get_usd_cny_rate(),
                    "min_usd": prices_usd[0],
                    "p25_usd": prices_usd[max(0, n // 4)],
                    "median_usd": prices_usd[n // 2],
                    "p75_usd": prices_usd[min(n - 1, n * 3 // 4)],
                    "max_usd": prices_usd[-1],
                    "items": r4_items[:10],
                    "_note": "前三源均未匹配，fallback GlobalSources（老牌国际 B2B，英文）",
                }

        return {
            "category": category_keyword_zh,
            "search_keyword_en": keyword_en,
            "source_url": r.get("url"),
            "real_data": False,
            "error": r.get("error", "no_items_parsed"),
            "fallback_tried": [
                {"source": "1688.com", "result": "blocked"},
                {"source": "made-in-china.com", "result": r2.get("error", "no_relevant_items")},
                {"source": "dhgate.com", "result": r3.get("error", "no_relevant_items")},
                {"source": "globalsources.com", "result": r4.get("error", "no_relevant_items")},
            ],
            "_strict_warning": ("❌ 1688 + Made-in-China + DHgate + GlobalSources 四源都未拿到匹配的真实采购成本。"
                                 "**禁止 LLM 自己写数字进 full_cost_breakdown**！"
                                 "必须在最终报告中明确标注：'采购成本未知，请用户提供供应商报价单/工厂询价 后重新测算'。"),
        }

    prices_cny = [it["price_cny"] for it in r["items"] if it.get("price_cny")]
    prices_cny.sort()
    fx = get_usd_cny_rate()
    n = len(prices_cny)
    return {
        "category": category_keyword_zh,
        "source": "1688.com",
        "source_url": r["url"],
        "real_data": True,
        "samples": n,
        "fx_rate_usd_cny": fx,
        "min_usd": round(prices_cny[0] / fx, 2),
        "p25_usd": round(prices_cny[max(0, n // 4)] / fx, 2),
        "median_usd": round(prices_cny[n // 2] / fx, 2),
        "p75_usd": round(prices_cny[min(n - 1, n * 3 // 4)] / fx, 2),
        "max_usd": round(prices_cny[-1] / fx, 2),
        "items": r["items"][:10],
    }
