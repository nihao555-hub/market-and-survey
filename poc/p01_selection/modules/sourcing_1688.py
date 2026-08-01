"""
1688 真实采购成本（仅返回真实获取结果，不估算、不模拟）
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
    """搜 Made-in-China.com，英文界面反爬轻很多（curl_cffi 即可，不需要浏览器渲染）。"""
    q = urllib.parse.quote(keyword_en.replace(" ", "_"))
    url = f"https://www.made-in-china.com/products-search/hot-china-products/{q}.html"
    logger.info(f"🏭 搜 Made-in-China → {keyword_en}")
    try:
        html = fetch(url, use_proxy=use_proxy)
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
            logger.warning(f"[detail_price] 第{attempt}次获取失败: {last_err}")
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
    """搜 DHgate.com（跨境批发，英文界面，curl_cffi 即可）。价格通常含 MOQ 阶梯。"""
    q = urllib.parse.quote(keyword_en)
    url = f"https://www.dhgate.com/wholesale/search.do?act=search&searchkey={q}"
    logger.info(f"🏭 搜 DHgate → {keyword_en}")
    try:
        html = fetch(url, use_proxy=use_proxy)
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


# ════════════════════════════════════════════════════════════════════
# 型号级匹配（DHgate 兜底防"泛品类中位价"进入测算）
# ════════════════════════════════════════════════════════════════════
def build_model_query(category_en: str, attrs: dict | None = None) -> str:
    """
    用候选品属性构造型号级英文查询词。
    例：category_en="pet water fountain",
        attrs={"material": "stainless steel", "capacity": "3L"}
        → "stainless steel pet water fountain 3L"
    attrs 支持键：material / capacity / model_terms(list) / spec_terms(list)。
    """
    attrs = attrs or {}
    parts = []
    material = (attrs.get("material") or "").strip()
    if material:
        parts.append(material)
    parts.append(category_en.strip())
    capacity = (attrs.get("capacity") or "").strip()
    if capacity:
        parts.append(capacity)
    for t in (attrs.get("model_terms") or attrs.get("spec_terms") or []):
        t = str(t).strip()
        if t and t.lower() not in " ".join(parts).lower():
            parts.append(t)
    return " ".join(p for p in parts if p)


def _spec_terms(attrs: dict | None) -> list[str]:
    """从候选品属性提取规格词（材质/容量/自定义型号词）。"""
    attrs = attrs or {}
    terms = []
    for key in ("material", "capacity"):
        v = (attrs.get(key) or "").strip()
        if v:
            terms.append(v)
    for t in (attrs.get("model_terms") or attrs.get("spec_terms") or []):
        t = str(t).strip()
        if t:
            terms.append(t)
    return terms


def _term_in_title(term: str, title_lower: str) -> bool:
    """
    规格词命中判定。容量类（3L/7L/1gal）做去空格子串匹配（兼容 "3 L"/"3.0L"），
    其余按词匹配（防 "steel" 误中 "stainless" 之外的拼写）。
    """
    t = term.lower().strip()
    if not t:
        return False
    # 容量模式：数字+单位（l/ml/oz/gal）
    if re.fullmatch(r'\d+\.?\d*\s?(l|ml|oz|gal|gallon)s?', t):
        compact = re.sub(r'\s+', '', t)
        return compact in re.sub(r'\s+', '', title_lower)
    words = [w for w in re.findall(r'[a-z0-9]+', t) if w]
    return all(re.search(rf'\b{re.escape(w)}', title_lower) for w in words)


def model_match_items(items: list[dict], category_en: str,
                      attrs: dict | None = None) -> tuple[list[dict], dict]:
    """
    型号级匹配过滤：只有标题同时命中【类目词 + ≥1 个规格词（材质/容量）】的商品
    才算型号级匹配（match_level="model"），允许进入 full_cost_breakdown。
    泛品类结果（只中类目词）按数据零编造铁律拒绝用于测算。

    返回 (matched_items, match_info)：
      match_info = {matched_keywords, confidence, match_level, usable_for_cost_calc}
    """
    stop = {"the", "a", "an", "for", "with", "and", "of", "to", "in", "pack", "set",
            "new", "hot", "sale", "high", "quality", "wholesale", "custom", "oem"}
    cat_words = [w for w in re.findall(r'[a-z]+', category_en.lower())
                 if w not in stop and len(w) > 2]
    specs = _spec_terms(attrs)
    matched_items = []
    all_matched_kw: set[str] = set()
    for it in items:
        title_lower = (it.get("title") or "").lower()
        title_words = set(re.findall(r'[a-z]+', title_lower))
        cat_hit = [w for w in cat_words if w in title_words]
        spec_hit = [s for s in specs if _term_in_title(s, title_lower)]
        # 类目词要求命中 ≥2 个（或类目只有 1 个词时命中它），防"pet supplies"泛匹配
        need_cat = min(2, len(cat_words))
        if len(cat_hit) >= need_cat and spec_hit:
            it = dict(it)
            it["matched_keywords"] = sorted(set(cat_hit) | set(spec_hit))
            it["match_level"] = "model"
            matched_items.append(it)
            all_matched_kw.update(cat_hit + spec_hit)
    n_spec = len(specs)
    confidence = round(len(all_matched_kw) / max(1, len(cat_words) + n_spec), 2)
    info = {
        "matched_keywords": sorted(all_matched_kw),
        "confidence": confidence,
        "spec_terms": specs,
        "category_terms": cat_words,
        "match_level": "model" if matched_items else "none",
        "usable_for_cost_calc": bool(matched_items),
    }
    return matched_items, info


def search_dhgate_model_level(category_en: str, attrs: dict | None = None,
                              use_proxy: bool = True, limit: int = 20) -> dict:
    """
    DHgate 型号级兜底：用候选品属性（材质/容量/类目）构造型号级查询，
    只有型号级匹配的结果才返回为可用（usable_for_cost_calc=True）；
    匹配不到就如实返回 match_level="none"，不编造、不退化用泛品类价。
    """
    query = build_model_query(category_en, attrs)
    raw = search_dhgate(query, use_proxy=use_proxy, limit=limit)
    if raw.get("error") or not raw.get("items"):
        return {"query": query, "match_level": "none", "usable_for_cost_calc": False,
                "items": [], "error": raw.get("error", "no_items_parsed"),
                "source_url": raw.get("url")}
    matched, info = model_match_items(raw["items"], category_en, attrs)
    return {"query": query, "source_url": raw["url"], "count_raw": raw.get("count", 0),
            "count_matched": len(matched), "items": matched, **info}


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


def get_real_procurement_cost(category_keyword_zh: str, use_proxy: bool = False,
                              product_attrs: dict | None = None) -> dict:
    """
    获取真实采购成本 — 多级备用源（1688 → Made-in-China → DHgate → GlobalSources）。
    返回字段含 source_url 用于报告引用。

    product_attrs：候选品属性（{"material": "stainless steel", "capacity": "3L",
    "model_terms": [...]}）。提供后 DHgate 兜底会先走型号级查询，
    只有型号级匹配（标题同时命中类目词+规格词）的结果才标注
    match_level="model" / usable_for_cost_calc=True，允许进入 full_cost_breakdown；
    泛品类结果（如 "pet supplies" 中位价）一律 usable_for_cost_calc=False，
    按数据零编造铁律拒绝用于测算。
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
            "宠物饮水机": "pet water fountain", "宠物饮水": "pet water fountain",
            "宠物喂食器": "automatic pet feeder",
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

        # L3: DHgate 兜底（有候选品属性时优先型号级查询）
        r3_model = None
        if product_attrs:
            logger.info(f"🏭 Made-in-China 无匹配，DHgate 型号级查询: {keyword_en} attrs={product_attrs}")
            r3_model = search_dhgate_model_level(keyword_en, product_attrs, use_proxy=use_proxy)
            if r3_model.get("usable_for_cost_calc"):
                m_items = r3_model["items"]
                prices_usd = sorted([it["price_usd"] for it in m_items if it.get("price_usd")])
                n = len(prices_usd)
                if n > 0:
                    return {
                        "category": category_keyword_zh,
                        "search_keyword_en": r3_model["query"],
                        "source": "dhgate.com",
                        "source_url": r3_model.get("source_url"),
                        "real_data": True,
                        "match_level": "model",
                        "usable_for_cost_calc": True,
                        "matched_keywords": r3_model["matched_keywords"],
                        "confidence": r3_model["confidence"],
                        "samples": n,
                        "fx_rate_usd_cny": get_usd_cny_rate(),
                        "min_usd": prices_usd[0],
                        "p25_usd": prices_usd[max(0, n // 4)],
                        "median_usd": prices_usd[n // 2],
                        "p75_usd": prices_usd[min(n - 1, n * 3 // 4)],
                        "max_usd": prices_usd[-1],
                        "items": m_items[:10],
                        "_note": (f"1688 + Made-in-China 均未匹配，DHgate 型号级匹配成功"
                                  f"（查询词 '{r3_model['query']}'，命中关键词 "
                                  f"{r3_model['matched_keywords']}，置信度 {r3_model['confidence']}）。"
                                  f"型号级结果允许进入 full_cost_breakdown，价格含跨境零售加价，仅供参考下限"),
                    }
            logger.info(f"🏭 DHgate 型号级无匹配（{r3_model.get('error') or 'no_model_match'}），退回泛品类查询")

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
                    "match_level": "category",
                    "usable_for_cost_calc": False,
                    "samples": n,
                    "fx_rate_usd_cny": get_usd_cny_rate(),
                    "min_usd": prices_usd[0],
                    "p25_usd": prices_usd[max(0, n // 4)],
                    "median_usd": prices_usd[n // 2],
                    "p75_usd": prices_usd[min(n - 1, n * 3 // 4)],
                    "max_usd": prices_usd[-1],
                    "items": r3_items[:10],
                    "_note": "1688 + Made-in-China 均未匹配，fallback DHgate（跨境批发，价格含零售加价，仅供参考下限）",
                    "_strict_warning": ("⚠️ 此为泛品类结果（match_level=category，如 'pet supplies' 中位价），"
                                         "非具体型号报价，usable_for_cost_calc=False，**禁止进入 full_cost_breakdown**。"
                                         "请提供候选品属性（材质/容量）重试型号级匹配，或改用 "
                                         "get_supplier_detail_price 抓详情页 MOQ 阶梯价 / 请用户提供供应商报价单。"),
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
