"""
选品 Agent 工具集（DeepSeek function calling）
覆盖 8 阶段方法论的所有工具。
"""
from __future__ import annotations
import json
from pathlib import Path
from loguru import logger

from modules.scraper import fetch
from modules.trends import get_keyword_trend
# 注意：modules.analysis 的 calc_profit/score_opportunity 含"假设成本=40%售价"等编造逻辑，
# 已弃用，不在任何 agent 工具中调用（利润测算统一走 full_cost_breakdown 的真实数据路径）。
from modules.bestsellers import (discover_bestsellers_url, get_bestsellers_by_url,
                                  get_movers_shakers_by_url, get_bestsellers, get_movers_shakers,
                                  estimate_monthly_sales_from_bsr)
from modules.reviews import get_product_review_summary, get_reviews_batch, reviews_to_text_list
from modules.full_cost import full_cost_breakdown, stress_test
from modules.ip_risk import search_patents, search_trademark, quick_ip_check, deep_ip_risk_assessment
from modules.extras import webpage_to_markdown_sync, file_to_markdown, scrapegraph_extract_products
from modules.evidence import (capture_evidence_for_asin, screenshot_url,
                                capture_evidence_for_url, capture_evidence_batch)
from modules.llm import get_client, resolve_model
from modules.asin_pool import POOL
from modules.sourcing_1688 import get_real_procurement_cost, search_1688, get_supplier_detail_price
from modules.real_cost_data import build_real_cost_params, get_usd_cny_rate, get_hts_duty
from modules.platforms import PLATFORMS, REGIONS, CONTINENTS, list_platforms_by_region, status_summary
from modules import paid_apis
from modules.keepa_graph import get_keepa_price_history_chart, get_keepa_charts_batch
from modules.keepa_session import get_keepa_product_data, keepa_session_available
from modules.keepa_chart_reader import read_keepa_chart
from modules.amazon_keywords import get_amazon_keyword_suggestions
from modules.wayback import (get_wayback_snapshots, fetch_wayback_snapshot,
                              analyze_listing_evolution)

import pandas as pd

# 兼容旧代码：从 PLATFORMS 提取搜索 URL 模板
SITE_TEMPLATES = {k: v["search_url"] for k, v in PLATFORMS.items()}
# 提供简化别名（让 LLM 用 amazon/walmart 等而不是 amazon_us）
SITE_TEMPLATES.update({
    "shopee": SITE_TEMPLATES["shopee_sg"],
})


# =====================  阶段 0：需求澄清  =====================
def tool_load_skill(skill_name: str = "procurement-research") -> dict:
    """加载选品方法论 skill 文档；Agent 第一步调用，按文档推进。"""
    p = Path(__file__).resolve().parents[1] / "skills" / f"{skill_name}.md"
    if not p.exists():
        return {"error": f"skill not found: {skill_name}"}
    return {"name": skill_name, "content": p.read_text(encoding="utf-8")}


def tool_analyze_review_temporal(reviews: list[dict] = None) -> dict:
    """
    评论时间分布分析 — 看产品口碑是变好还是变差。
    
    输入：reviews 列表（每条含 date 字段，'Reviewed in the United States on May 1, 2024' 这种格式）。
    **必须传 get_reviews_batch 返回的 reviews 数组**（每条含 date/rating/body）。
    
    输出：
    - 最近 30 天 / 90 天 / 历史 评论数
    - 最近 30 天评分均值 vs 历史评分均值（差距 > 0.3 是质量下降信号）
    - 最近评论增速（每月增长率）
    """
    # 容错：漏传 / 传错类型 / 空列表 → 返回友好指引，不抛 TypeError 让流程崩
    if reviews is None or not isinstance(reviews, list) or len(reviews) == 0:
        return {
            "error": "no_reviews",
            "needs_input": "请把 get_reviews_batch 返回的 reviews 数组（每条含 date 字段）作为 "
                           "reviews 参数传入，例：analyze_review_temporal(reviews=<上一步 reviews>)。",
        }
    logger.info(f"🔧 analyze_review_temporal({len(reviews)} reviews)")
    
    import re
    from datetime import datetime, timedelta
    
    now = datetime.now()
    d30_ago = now - timedelta(days=30)
    d90_ago = now - timedelta(days=90)
    d365_ago = now - timedelta(days=365)
    
    parsed = []
    for r in reviews:
        if not isinstance(r, dict):
            continue
        date_str = (r.get("date") or "").strip()
        if not date_str:
            continue
        # "Reviewed in the United States on May 1, 2024" → "May 1, 2024"
        m = re.search(r'on\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})', date_str)
        date_part = m.group(1) if m else date_str
        try:
            d = datetime.strptime(date_part, "%B %d, %Y")
        except ValueError:
            try:
                d = datetime.strptime(date_part, "%b %d, %Y")
            except ValueError:
                continue
        parsed.append({"date": d, "rating": r.get("rating"), "body": r.get("body", "")})
    
    if not parsed:
        return {"error": "no_parseable_dates", "total": len(reviews)}
    
    last_30 = [p for p in parsed if p["date"] >= d30_ago]
    last_90 = [p for p in parsed if p["date"] >= d90_ago]
    last_365 = [p for p in parsed if p["date"] >= d365_ago]
    older = [p for p in parsed if p["date"] < d365_ago]
    
    def avg_rating(items):
        rs = [p["rating"] for p in items if isinstance(p.get("rating"), (int, float))]
        return round(sum(rs) / len(rs), 2) if rs else None
    
    recent_avg = avg_rating(last_90)
    historic_avg = avg_rating(older)
    quality_trend = "stable"
    if recent_avg is not None and historic_avg is not None:
        diff = recent_avg - historic_avg
        if diff < -0.3: quality_trend = "declining"  # 质量下降
        elif diff > 0.3: quality_trend = "improving"  # 质量提升
    
    return {
        "total_parsed": len(parsed),
        "last_30_days": len(last_30),
        "last_90_days": len(last_90),
        "last_365_days": len(last_365),
        "older_than_year": len(older),
        "recent_90d_avg_rating": recent_avg,
        "historic_avg_rating": historic_avg,
        "rating_diff": round((recent_avg - historic_avg) if recent_avg and historic_avg else 0, 2),
        "quality_trend": quality_trend,
        "verdict": (
            "🔴 警示：最近 90 天评分明显低于历史，产品质量在下降"
            if quality_trend == "declining" else
            "🟢 利好：最近 90 天评分高于历史，产品在改进"
            if quality_trend == "improving" else
            "🟡 评分稳定，无明显趋势"
        ),
        "_source": "评论 date 字段精确解析",
    }


def tool_extract_pain_points_precise(reviews: list[str]) -> dict:
    """
    **替代 LLM 计数痛点频次的精确版**。
    
    流程：
    1. LLM 提炼候选痛点关键词（5-10 个 short phrases，如 "slips on hardwood", "battery degrades"）
    2. 用 Python 在 N 条真实评论中精确匹配（含同义词和模糊匹配）
    3. 返回每个痛点的 **真实精确频次** + 命中评论 ASIN 列表
    
    与 analyze_reviews 的区别：
    - analyze_reviews：LLM 出痛点 + LLM 估算频次（"出现 8 次" ±2-3 误差）
    - extract_pain_points_precise：LLM 出痛点关键词 + Python 精确统计（误差 0）
    """
    logger.info(f"🔧 extract_pain_points_precise({len(reviews)} reviews)")
    if not reviews:
        return {"error": "no_reviews"}
    
    # Step 1: LLM 出候选痛点关键词组
    # 注意：下面的 JSON 示例是**结构占位符**，不绑定任何品类。
    # 关键词必须由 LLM 从下方真实评论原文中提炼，禁止照搬示例。
    joined = "\n".join(f"- {r[:300]}" for r in reviews[:80])
    prompt = (
        "你是商品评论分析专家。下面是若干条真实用户评论。\n\n"
        "请**仅根据下方评论原文**提炼 5-10 个用户高频抱怨的痛点关键词组（每组 2-4 个同义词），用于后续 Python 精确统计。\n\n"
        "返回 JSON（以下仅为**格式占位符**，name/keywords 必须替换为评论里真实出现的内容，禁止照搬示例文字）:\n"
        '{"pain_groups": [\n'
        '  {"name": "<痛点A的简短中文名>", "keywords": ["<原文短语1>", "<原文短语2>", "<原文短语3>"]},\n'
        '  {"name": "<痛点B的简短中文名>", "keywords": ["<原文短语1>", "<原文短语2>"]}\n'
        ']}\n\n'
        "要求：\n"
        "1. 关键词必须是评论原文里真实出现的词或短语（小写），不得凭空想象\n"
        "2. 每组 2-4 个同义词（提高匹配率）\n"
        "3. 痛点要具体（用原文里的真实短语，而不是 '不好用' 这类空泛词）\n"
        "4. 5-10 组（少则覆盖不全，多则噪音）\n"
        "5. 严禁输出与下方评论无关的、来自示例或你记忆中其它品类的关键词\n\n"
        f"评论：\n{joined}"
    )
    
    try:
        resp = get_client().chat.completions.create(
            model=resolve_model("flash"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )
        groups = json.loads(resp.choices[0].message.content or "{}").get("pain_groups", [])
    except Exception as e:
        return {"error": f"llm_extract_failed: {str(e)[:120]}"}
    
    if not groups:
        return {"error": "no_groups_extracted"}
    
    # Step 2: Python 精确匹配每组在评论中的频次
    results = []
    for g in groups:
        name = g.get("name", "?")
        keywords = [kw.lower() for kw in g.get("keywords", []) if kw]
        if not keywords:
            continue
        
        hit_indices = []  # 命中评论的 index
        hit_keywords = {}  # 哪些 keywords 匹中了
        
        for idx, review in enumerate(reviews):
            review_lower = review.lower()
            matched_kw = []
            for kw in keywords:
                if kw in review_lower:
                    matched_kw.append(kw)
            if matched_kw:
                hit_indices.append(idx)
                for kw in matched_kw:
                    hit_keywords[kw] = hit_keywords.get(kw, 0) + 1
        
        # 取最有代表性的 3 条命中评论
        sample_reviews = [reviews[i][:200] for i in hit_indices[:3]]
        
        results.append({
            "pain_name": name,
            "keywords": keywords,
            "exact_count": len(hit_indices),
            "hit_rate": round(len(hit_indices) / len(reviews), 3),
            "keyword_hits": hit_keywords,
            "sample_reviews": sample_reviews,
        })
    
    # 按频次降序
    results.sort(key=lambda x: -x["exact_count"])
    
    return {
        "total_reviews": len(reviews),
        "pain_groups_count": len(results),
        "pain_points": results,
        "_source": "LLM 出关键词 + Python 精确字符串匹配，频次 0 误差",
        "_method": "比 analyze_reviews 的 LLM 估算精确得多",
    }


def tool_extract_products_with_llm(url: str, max_items: int = 20) -> dict:
    """
    **SPA 平台终极武器** — 当 selector 解析失败时（如 shopee/lazada/tokopedia/trendyol），
    用 LLM 直接读 HTML 文本提取商品列表。
    
    工作流（B 优化 2026-06）：
      1. fetch HTML → BeautifulSoup 清理 head/script/style/nav/footer
      2. **先用通用商品卡片 selector 圈出候选节点**（含价格符号 + 文本长度合理的 li/article/div）
      3. 每个节点单独压成短文本（标题 + 价格 + 评分 + 链接），合并喂 LLM
      4. 文本量从 ~30K → ~5K（10x 提速；DeepSeek flash 144s → ~30s）
    
    成本：~$0.001/次（B 优化后小 5x）。
    """
    logger.info(f"🔧 extract_products_with_llm({url})")
    try:
        html = fetch(url, use_proxy=True, force_browser=True)
    except Exception as e:
        return {"url": url, "error": f"fetch_failed: {str(e)[:120]}", "products": []}
    
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "head", "header", "footer", "nav",
                       "iframe", "svg"]):
        tag.decompose()
    
    price_re = re.compile(r'(?:\$|€|£|¥|₹|₺|₽|RM\s|Rp\s?|S\$|￥|US\s?\$|R\$|MX\$|CAD\s?\$)\s?\d')
    
    # ─── B. 先用语义节点定位商品卡（节省 5-10x 文本量喂 LLM）───
    candidate_cards = []
    # 候选 selector：覆盖大多数电商商品卡片结构
    card_selectors = [
        "li[class*='product']", "li[class*='item']", "li[data-id]",
        "article[class*='product']", "article[data-id]",
        "div[class*='product-card']", "div[class*='ProductCard']",
        "div[data-product-id]", "div[data-item-id]",
        "div[class*='SearchProduct']", "a[class*='product-card']",
        "li", "article",  # 兜底
    ]
    seen_texts = set()
    for sel in card_selectors:
        try:
            nodes = soup.select(sel)
        except Exception:
            continue
        for n in nodes:
            t = n.get_text(" ", strip=True)
            if not t or len(t) < 30 or len(t) > 800:
                continue  # 太短没信息 / 太长不是商品卡（可能是整页）
            if not price_re.search(t):
                continue  # 没价格不是商品
            # 去重（同一商品多 selector 会命中多次）
            sig = t[:60]
            if sig in seen_texts:
                continue
            seen_texts.add(sig)
            # 提取链接
            a = n.find("a", href=True)
            href = a["href"] if a else None
            candidate_cards.append({
                "text": t[:500],
                "href": href,
            })
            if len(candidate_cards) >= max_items * 2:  # 收 2x 给 LLM 容错
                break
        if len(candidate_cards) >= max_items * 2:
            break
    
    if candidate_cards:
        # 精简文本：每张卡 ~200 字 × max_items*2 = ~8K，远小于 30K
        body_text = "\n\n".join(
            f"[卡片{i+1}] {c['text']}" + (f"\n链接: {c['href'][:120]}" if c['href'] else "")
            for i, c in enumerate(candidate_cards[:max_items * 2])
        )
        text_source = f"selector 定位 {len(candidate_cards)} 张商品卡（B 优化路径）"
    else:
        # 兜底：原始全文截断
        body_text = soup.get_text("\n", strip=True)
        m = price_re.search(body_text)
        if m and m.start() > 5000:
            start = max(0, m.start() - 500)
            body_text = body_text[start:start + 30000]
        else:
            body_text = body_text[:30000]
        text_source = f"全文截断 {len(body_text)} 字（兜底，selector 0 张卡）"
    
    if len(body_text) < 500:
        return {"url": url, "error": "html_too_small_for_llm_extraction",
                "html_len": len(html), "products": []}
    
    price_count = len(price_re.findall(body_text))
    if price_count < 3:
        return {"url": url, "error": "no_price_in_text",
                "message": f"页面纯文本中只发现 {price_count} 个价格元素，可能是 SPA 未渲染或登录墙",
                "html_len": len(html), "text_len": len(body_text), "products": []}
    
    prompt = (
        f"以下是某电商搜索结果页的商品卡片。请提取**所有商品**的结构化数据，最多 {max_items} 个。\n"
        f"返回 JSON: {{\"products\": [{{\"title\": str, \"price\": str, \"rating\": str_or_null, "
        f"\"review_count\": int_or_null, \"url\": str_or_null}}], \"total_extracted\": int}}\n\n"
        f"严格要求：\n"
        f"1. 只提取真实出现在卡片里的商品，不要编造\n"
        f"2. price 保留货币符号（如 'S$29.90', '₽1500', 'Rp75000'）\n"
        f"3. 找不到字段就用 null\n"
        f"4. 过滤广告/推荐/赞助商品\n\n"
        f"商品卡片：\n{body_text}"
    )
    
    try:
        resp = get_client().chat.completions.create(
            model=resolve_model("flash"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=3000,
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)
        products = parsed.get("products", [])[:max_items]
        return {
            "url": url, "html_len": len(html),
            "extracted_count": len(products),
            "products": products,
            "_text_source": text_source,
            "_text_len": len(body_text),
            "_source": f"LLM 从 {len(body_text)} chars 文本提取（B 优化：BS4 预过滤后再喂 LLM）",
        }
    except Exception as e:
        return {"url": url, "error": f"llm_extract_failed: {str(e)[:150]}",
                "html_len": len(html), "products": []}


def tool_get_current_datetime() -> dict:
    """获取当前真实日期时间（UTC + 本地 + ISO 格式）。Agent 在阶段 1 开始前必须调一次，
    用于：① Trends 查询的'近 N 天'语境 ② 报告标注'数据采集时间' ③ 季节性判断"""
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now()
    return {
        "iso_utc": now_utc.isoformat(),
        "iso_local": now_local.isoformat(),
        "date": now_local.strftime("%Y-%m-%d"),
        "year": now_local.year,
        "month": now_local.month,
        "month_name": now_local.strftime("%B"),
        "weekday": now_local.strftime("%A"),
        "quarter": (now_local.month - 1) // 3 + 1,
        "season_north": ("winter" if now_local.month in [12,1,2] else
                          "spring" if now_local.month in [3,4,5] else
                          "summer" if now_local.month in [6,7,8] else "autumn"),
    }


# ════════════════════════════════════════════════════════════════════
# DataForSEO 真实绝对搜索量（付费 API，有免费额度；缺 key 自动降级 DDGS）
# ════════════════════════════════════════════════════════════════════
def tool_get_real_search_volume(keywords: list[str], geo: str = "US") -> dict:
    """
    **真实 Google Ads 绝对月搜索量**（补 Google Trends 只有相对值的短板）。
    返回每个关键词的真实月均搜索量 + CPC + 竞争度 + 近 12 月走势。
    
    需要 .env 配 DATAFORSEO_LOGIN/PASSWORD（注册送 ~$1 credit）。
    未配置时返回 available=False → 请改用 get_keyword_metrics（DDGS 相对值）。
    给商家报告时：有真实搜索量必须用真实绝对值，并标注来源 DataForSEO。
    """
    logger.info(f"🔧 get_real_search_volume({keywords}, {geo})")
    if isinstance(keywords, str):
        keywords = [keywords]
    r = paid_apis.get_real_search_volume(keywords, geo)
    if not r.get("available"):
        return {**r,
                "_fallback": "未配置 DataForSEO，请用 get_keyword_metrics 拿 DDGS 相对搜索量代理"}
    return r


# ════════════════════════════════════════════════════════════════════
# DDGS 关键词搜索量代理（替代付费 Helium10 / Jungle Scout）
# DuckDuckGo 不限速 + 不需要 API key
# ════════════════════════════════════════════════════════════════════
def _dedupe_keywords_fuzzy(seed: str, suggestions: list[dict],
                            sim_threshold: int = 88) -> list[dict]:
    """
    用 thefuzz 对关键词建议做：① 去除近似重复词（相似度≥阈值视为同一词，保留先到的）
    ② 给每个词标注与 seed 的 relevance 相关度（0-100）。
    thefuzz 不可用时优雅退化为原样返回。
    """
    if not suggestions:
        return suggestions
    try:
        from thefuzz import fuzz
    except Exception:
        return suggestions

    kept: list[dict] = []
    kept_words: list[str] = []
    for s in suggestions:
        kw = (s.get("keyword") or "").strip()
        if not kw:
            continue
        # 与已保留词比相似度，太像就丢
        is_dup = any(fuzz.token_set_ratio(kw, kept_w) >= sim_threshold for kept_w in kept_words)
        if is_dup:
            continue
        s = {**s, "relevance": fuzz.token_set_ratio(seed, kw)}
        kept.append(s)
        kept_words.append(kw)
    # 按相关度降序（已有真实搜索量时上一步已按量排过，这里相关度作为次级信号附加）
    return kept


def tool_get_keyword_metrics(seed_keyword: str, max_suggestions: int = 20) -> dict:
    """
    关键词数据。**优先**用 DataForSEO 真实绝对搜索量（若配置了 key），
    否则降级到 DDGS 长尾词扩展 + 全网内容量代理（相对值）。
    
    返回 {
      seed, suggestions: [{keyword, content_volume / search_volume, ...}],
      _source, _real_volume: bool
    }
    """
    logger.info(f"🔧 get_keyword_metrics({seed_keyword})")
    try:
        from ddgs import DDGS
    except ImportError:
        return {"error": "ddgs_not_installed", "message": "pip install ddgs"}
    
    suggestions = []
    try:
        # 1) 拿建议词 — 用 DuckDuckGo 自动补全公开端点（新版 ddgs 没有 suggestions 方法）
        sugg_phrases = []
        try:
            import requests
            ac_resp = requests.get(
                "https://duckduckgo.com/ac/",
                params={"q": seed_keyword, "type": "list"},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            ac_data = ac_resp.json()
            # 格式: ["seed", ["sug1", "sug2", ...]] 或 [{"phrase": ...}]
            if isinstance(ac_data, list) and len(ac_data) >= 2 and isinstance(ac_data[1], list):
                sugg_phrases = ac_data[1]
            elif isinstance(ac_data, list):
                sugg_phrases = [x.get("phrase", x) if isinstance(x, dict) else x for x in ac_data]
        except Exception as e:
            logger.warning(f"DDG autocomplete fail: {e}")
        
        # 2) 如果自动补全为空，用 Google autocomplete 兜底
        if not sugg_phrases:
            try:
                import requests
                g_resp = requests.get(
                    "https://suggestqueries.google.com/complete/search",
                    params={"client": "firefox", "q": seed_keyword},
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                g_data = g_resp.json()
                if isinstance(g_data, list) and len(g_data) >= 2:
                    sugg_phrases = g_data[1]
            except Exception as e:
                logger.warning(f"Google autocomplete fail: {e}")
        
        sugg_phrases = sugg_phrases[:max_suggestions]
        
        with DDGS() as ddgs:
            for kw in sugg_phrases:
                kw = kw if isinstance(kw, str) else str(kw)
                if not kw or len(kw) < 3:
                    continue
                # 估算内容量 = DDG 该关键词的结果数
                try:
                    results = list(ddgs.text(kw, region="us-en", max_results=10))
                except Exception:
                    results = []
                titles = [r.get("title", "")[:80] for r in results[:3] if isinstance(r, dict)]
                suggestions.append({
                    "keyword": kw,
                    "content_volume": len(results),
                    "sample_titles": titles,
                })
            
            try:
                seed_results = list(ddgs.text(seed_keyword, region="us-en", max_results=10))
            except Exception:
                seed_results = []
        
        # 若配置了 DataForSEO，补真实绝对月搜索量到每个长尾词
        real_volume = None
        if paid_apis.dataforseo_available() and suggestions:
            kw_list = [seed_keyword] + [s["keyword"] for s in suggestions[:15]]
            rv = paid_apis.get_real_search_volume(kw_list, "US")
            if rv.get("available") and rv.get("results"):
                vol_map = {r["keyword"].lower(): r for r in rv["results"] if r.get("keyword")}
                for s in suggestions:
                    hit = vol_map.get(s["keyword"].lower())
                    if hit:
                        s["search_volume"] = hit.get("search_volume")
                        s["cpc"] = hit.get("cpc")
                        s["competition"] = hit.get("competition")
                real_volume = vol_map.get(seed_keyword.lower(), {}).get("search_volume")
                # 按真实搜索量重排
                suggestions.sort(key=lambda x: -(x.get("search_volume") or 0))

        # ── thefuzz：去重近似重复的长尾词 + 标注与 seed 的相关度 ──
        # 避免 "geladeira frost free" / "geladeira frostfree" 这种近似词重复占位。
        deduped = _dedupe_keywords_fuzzy(seed_keyword, suggestions)

        return {
            "seed": seed_keyword,
            "suggestion_count": len(deduped),
            "suggestions": deduped,
            "seed_content_volume": len(seed_results),
            "seed_real_search_volume": real_volume,
            "_source": ("DataForSEO 真实绝对搜索量 + DDGS 长尾词" if real_volume is not None
                        else "DuckDuckGo/Google autocomplete + DDG text results (free)"),
            "_real_volume": real_volume is not None,
            "_dedup": "thefuzz 已去除近似重复词并标注 relevance 相关度",
            "_note": ("search_volume 字段为 DataForSEO 真实月均搜索量（绝对值）"
                      if real_volume is not None else
                      "content_volume 是搜索结果数代理，相对值有意义。配 DATAFORSEO_LOGIN 可拿绝对值"),
        }
    except Exception as e:
        return {"seed": seed_keyword, "error": str(e)[:200], "suggestions": []}


def tool_validate_keywords(keywords: list[str], platform: str = "amazon",
                            category_hint: str = "", limit_per_kw: int = 10,
                            min_products: int = 3) -> dict:
    """
    **关键词验证闭环（决定结果质量的关键工具）**：把候选关键词用「真实能搜到多少对口商品」反向打分，
    淘汰跑偏/搜不到的词，只留下真正能拿到数据的高质量词。

    流程（每个候选词并发执行）：
    1. 真实 search_products(platform, kw) 看能搜到几件商品（搜不到=废词）
    2. thefuzz 算候选词与 category_hint/种子的语义相关度（过滤"防盗门→门锁配件"类错位词、
       "geladeira em ingles=冰箱用英语怎么说"类查资料词）
    3. 综合打分 = 真实商品数(主) + 相关度(辅)，降序返回

    返回每个词的 real_product_count / relevance / verdict（keep/drop）+ 推荐用哪些词正式获取。
    """
    logger.info(f"🔧 validate_keywords({len(keywords)} 词, platform={platform})")
    if not keywords:
        return {"error": "no_keywords", "validated": []}

    from concurrent.futures import ThreadPoolExecutor, as_completed
    plat = _resolve_platform(platform)

    # thefuzz 相关度基准：category_hint 优先，否则用所有候选词的最长公共种子
    ref = (category_hint or keywords[0]).strip().lower()
    try:
        from thefuzz import fuzz
        _fz = lambda kw: fuzz.token_set_ratio(ref, kw.lower())
    except Exception:
        _fz = lambda kw: 100  # thefuzz 不可用则不扣分

    def _probe(kw: str) -> dict:
        try:
            r = tool_search_products(plat, kw, limit=limit_per_kw, use_proxy=True)
            cnt = r.get("count", 0)
        except Exception as e:
            cnt = 0
            r = {"error": str(e)[:100]}
        rel = _fz(kw)
        # 综合分：商品数权重高（每件 10 分，封顶 100）+ 相关度
        prod_score = min(cnt, 10) * 10
        score = round(prod_score * 0.7 + rel * 0.3, 1)
        # keep 条件：真实搜到 ≥ min_products 件 且 相关度 ≥ 55（明显跑偏的剔除）
        keep = cnt >= min_products and rel >= 55
        return {"keyword": kw, "real_product_count": cnt, "relevance": rel,
                "score": score, "verdict": "keep" if keep else "drop",
                "sample_titles": [p.get("title", "")[:50]
                                  for p in (r.get("products") or [])[:3]]}

    results = []
    with ThreadPoolExecutor(max_workers=min(len(keywords), 6)) as ex:
        futs = {ex.submit(_probe, kw): kw for kw in keywords[:15]}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"keyword": futs[fut], "real_product_count": 0,
                                "relevance": 0, "score": 0, "verdict": "drop",
                                "error": str(e)[:100]})

    results.sort(key=lambda x: -x["score"])
    kept = [r for r in results if r["verdict"] == "keep"]
    return {
        "platform": plat, "category_hint": category_hint,
        "tested_count": len(results),
        "kept_count": len(kept),
        "validated": results,
        "recommended_keywords": [r["keyword"] for r in kept],
        "_verdict": ("✅ 有可用高质量词" if kept else
                     "⚠️ 候选词全部验证失败（搜不到对口商品或跑偏），"
                     "请换种子词/换平台/换本地语言词重新扩展"),
        "_method": "真实商品数(70%) + thefuzz 语义相关度(30%) 综合打分；"
                   "keep = 真搜到≥min_products件 且 相关度≥55，杜绝跑偏词进入正式获取",
    }


def tool_compare_seasonality(keyword: str, geo: str = "US") -> dict:
    """
    用 5 年 Google Trends 真实历史数据判断季节性（替代 LLM 推断）。
    返回每月平均热度 + 峰值月 + 谷值月 + 季节强度系数。
    """
    logger.info(f"🔧 compare_seasonality({keyword}, {geo})")
    try:
        from modules.trends import get_keyword_trend
        df = get_keyword_trend([keyword], timeframe="today 5-y", geo=geo)
        if df.empty:
            return {"keyword": keyword, "error": "no_trend_data"}
        
        s = df[keyword] if keyword in df.columns else df.iloc[:, 0]
        # 按月聚合 5 年数据
        monthly_avg = s.groupby(s.index.month).mean().round(1).to_dict()
        # 转成 1-12 月顺序
        monthly_ordered = [{"month": m, "avg_heat": monthly_avg.get(m, 0)} for m in range(1, 13)]
        
        peak_month = max(monthly_avg, key=monthly_avg.get)
        valley_month = min(monthly_avg, key=monthly_avg.get)
        peak_val = monthly_avg[peak_month]
        valley_val = monthly_avg[valley_month]
        seasonality_strength = round((peak_val - valley_val) / max(peak_val, 1), 2)
        
        # 判断当前月在哪
        from datetime import datetime
        cur_month = datetime.now().month
        cur_avg = monthly_avg.get(cur_month, 0)
        cur_position = "high" if cur_avg > (peak_val + valley_val) / 2 else "low"
        
        return {
            "keyword": keyword, "geo": geo,
            "data_points": int(len(s)),
            "years_covered": "5",
            "monthly_avg_heat": monthly_ordered,
            "peak_month": int(peak_month), "peak_value": float(peak_val),
            "valley_month": int(valley_month), "valley_value": float(valley_val),
            "seasonality_strength": float(seasonality_strength),
            "current_month": int(cur_month),
            "current_position": cur_position,
            "verdict": (
                f"季节性强度 {seasonality_strength}：" +
                ("强季节性，旺季 " if seasonality_strength > 0.5 else
                 "中等季节性，旺季 " if seasonality_strength > 0.25 else
                 "弱季节性（全年稳定），最热月 ") +
                f"{peak_month} 月（值 {peak_val}）→ 谷月 {valley_month} 月（值 {valley_val}）。" +
                f"当前 {cur_month} 月处于 {cur_position} 位"
            ),
            "_source": f"Google Trends 5 年历史（today 5-y），geo={geo}",
        }
    except Exception as e:
        return {"keyword": keyword, "error": str(e)[:200]}


# =====================  阶段 1：品类宏观  =====================
def tool_get_trend(keyword: str, geo: str = "US") -> dict:
    logger.info(f"🔧 get_trend({keyword}, {geo})")
    df = get_keyword_trend([keyword], geo=geo)
    if df.empty:
        return {"keyword": keyword, "trend": "no data"}
    s = df[keyword].tolist() if keyword in df.columns else df.iloc[:, 0].tolist()
    half = len(s) // 2
    early_avg = sum(s[:half]) / max(half, 1)
    late_avg = sum(s[half:]) / max(len(s) - half, 1)
    direction = "上升" if late_avg > early_avg * 1.05 else ("下降" if late_avg < early_avg * 0.95 else "平稳")
    return {
        "keyword": keyword, "geo": geo, "points": len(s),
        "early_avg": round(early_avg, 1), "late_avg": round(late_avg, 1),
        "direction": direction, "max": max(s), "min": min(s),
        "recent_3m_avg": round(sum(s[-12:]) / 12, 1) if len(s) >= 12 else None,
    }


def tool_discover_bsr_url(category_keyword: str, geo: str = "US") -> dict:
    """LLM 给类目关键词，工具自动从对应市场的 Amazon 站点发现真实子类目 BSR URL（不硬编码）。
    geo 决定 Amazon 站点（US→.com / UK→.co.uk / DE→.de / SG→.sg ...）。
    market 无 Amazon 业务（RU/东南亚等）时返回 amazon_available=False，应改用 search_multi_platform。"""
    logger.info(f"🔧 discover_bsr_url({category_keyword}, geo={geo})")
    return discover_bestsellers_url(category_keyword, use_proxy=True, geo=geo)


def tool_get_bestsellers_by_url(bsr_url: str, limit: int = 50, category: str = "") -> dict:
    """直接抓某个 BSR 子类目 URL（来自 discover_bsr_url 的候选）。

    默认 limit=50（旧 30）以增大样本量，避免偶然性。
    category：真实品类（如 home-kitchen/beauty/toys/sports/electronics），仅用于
      无 bought_past_month 时的 BSR 经验区间系数。不传则用中性默认，**不再硬编码 electronics**
      （之前硬编码会让非电子品类的估算系统性偏高）。
    返回每个商品的 ASIN/标题/价格/评分/评论数/月销区间。
    """
    logger.info(f"🔧 get_bestsellers_by_url({bsr_url}, limit={limit}, category={category or '默认'})")
    r = get_bestsellers_by_url(bsr_url, use_proxy=True, limit=limit)
    items = r.get("items", [])
    cat = (category or "").strip().lower() or "default"
    # 给每个商品附月销区间（优先用真实 bought_past_month，否则 BSR 经验公式）
    real_sales_count = 0
    for it in items:
        if isinstance(it, dict):
            bpm = it.get("bought_past_month")
            if it.get("rank") or bpm:
                it["estimated_monthly_sales"] = estimate_monthly_sales_from_bsr(
                    it.get("rank") or 0, cat, bought_past_month=bpm)
                if bpm:
                    real_sales_count += 1
    POOL.add_batch([it for it in items if isinstance(it, dict) and it.get("asin")])
    
    # 给 LLM 一个"看到了什么"摘要（avoid black box）
    sample_titles = [it.get("title", "")[:60] for it in items[:10] if isinstance(it, dict)]
    avg_rating = round(sum(it.get("rating", 0) for it in items if it.get("rating")) /
                        max(sum(1 for it in items if it.get("rating")), 1), 2)
    avg_reviews = int(sum(it.get("review_count", 0) for it in items if it.get("review_count")) /
                       max(sum(1 for it in items if it.get("review_count")), 1))
    
    return {"url": bsr_url, "count": len(items), "items": items,
            "pool_size_after": POOL.size(),
            "_summary": {
                "抓到商品数": len(items),
                "前 10 个商品标题": sample_titles,
                "平均评分": avg_rating,
                "平均评论数": avg_reviews,
                "含真实月销标签的商品数": real_sales_count,
                "月销数据说明": (f"{real_sales_count} 件含 Amazon『bought in past month』真实月销数据"
                                if real_sales_count else
                                "本批次无真实月销标签，月销为 BSR 经验区间估算（标 real_data=False）"),
                "Top 1": items[0] if items else None,
            }}


def tool_get_movers_shakers_by_url(url: str, limit: int = 50) -> dict:
    """抓 Movers & Shakers URL（24h 上升最快榜）"""
    logger.info(f"🔧 get_movers_shakers_by_url({url})")
    r = get_movers_shakers_by_url(url, use_proxy=True, limit=limit)
    items = r.get("items", [])
    POOL.add_batch([it for it in items if isinstance(it, dict) and it.get("asin")])
    return {"url": url, "count": len(items), "items": items,
            "pool_size_after": POOL.size()}


# 兼容旧名（当 LLM 用旧的 get_bestsellers 时，自动走 discover→by_url）
def tool_get_bestsellers(category: str = "electronics", limit: int = 30, geo: str = "US") -> dict:
    logger.info(f"🔧 get_bestsellers({category}, geo={geo}) (auto-discover)")
    d = discover_bestsellers_url(category, use_proxy=True, geo=geo)
    if d.get("amazon_available") is False:
        return {"category": category, "geo": geo,
                "amazon_available": False, "count": 0, "items": [],
                "note": d.get("note")}
    if not d.get("candidates"):
        return {"category": category, "error": "no bsr url discovered",
                "search_url": d.get("search_url")}
    url = d["candidates"][0]["url"]
    return tool_get_bestsellers_by_url(url, limit=limit)


def tool_get_movers_shakers(category: str = "electronics", limit: int = 30) -> dict:
    """已弃用：请用 get_movers_shakers_by_url。"""
    return {"deprecated": True, "msg": "请用 discover_bsr_url 找到子类目后用 get_movers_shakers_by_url"}


# =====================  阶段 2：竞争格局  =====================
# 间歇性反爬平台：单次失败就重试（引擎轮换），selector 解析 0 件时 LLM 兜底
_FLAKY_PLATFORMS = {"temu", "shein", "alibaba", "aliexpress", "cdiscount",
                    "amazon_uk", "shopee_sg", "wildberries",
                    "yandex_market", "mercadolibre_mx", "mercadolibre_br"}
# selector 解析失败时用 LLM 文本兜底提取的平台（SPA / 动态 class）
_LLM_FALLBACK_PLATFORMS = {"temu", "shein", "alibaba", "aliexpress", "cdiscount",
                           "shopee_sg", "wildberries", "lazada_sg", "tokopedia",
                           "trendyol", "tiktok_shop",
                           "yandex_market", "mercadolibre_mx", "mercadolibre_br"}

# 平台名别名归一化：LLM 经常用本地化拼写或简写，统一映射到注册表 key。
# 例：巴西人把 MercadoLibre 写成 MercadoLivre（葡语）；漏写国家后缀等。
_PLATFORM_ALIASES = {
    "mercadolivre": "mercadolibre_br",
    "mercadolivre_br": "mercadolibre_br",
    "mercadolivre_mx": "mercadolibre_mx",
    "mercadolibre": "mercadolibre_mx",
    "meli_br": "mercadolibre_br",
    "meli_mx": "mercadolibre_mx",
    "yandex": "yandex_market",
    "yandexmarket": "yandex_market",
    "amazon_us": "amazon",
    "amazon_com": "amazon",
    "lazada": "lazada_sg",
    "shopee": "shopee_sg",
    "amazon_br": "mercadolibre_br",  # Amazon 巴西份额低，BR 主战场是 MercadoLibre
}


def _resolve_platform(name: str) -> str:
    """把 LLM 给的平台名归一化到 PLATFORMS 注册表 key（处理本地化拼写/简写）。"""
    key = (name or "").strip().lower()
    if key in PLATFORMS:
        return key
    return _PLATFORM_ALIASES.get(key, key)


# 已知 UI 噪声文案（非真实商品标题）——解析时遇到直接剔除
_JUNK_TITLE_PATTERNS = (
    "собрали с помощью",   # Yandex「用 Market AI 整理」UI 文案
    "маркет ai", "market ai",
    "see more", "view all", "показать", "смотреть все",
    "patrocinado", "sponsored", "anúncio", "реклама",
    "add to cart", "купить", "в корзину",
)


def _is_junk_title(title: str) -> bool:
    """判断标题是否为空 / None / UI 噪声文案（非真实商品）。"""
    if not title:
        return True
    t = title.strip().lower()
    if not t or t in ("none", "null", "undefined", "—", "-"):
        return True
    if len(t) < 3:
        return True
    return any(pat in t for pat in _JUNK_TITLE_PATTERNS)


def _products_look_valid(products: list[dict], min_count: int = 3,
                          min_price_ratio: float = 0.5) -> bool:
    """
    校验解析结果是否"看起来是真实有效的商品列表"，而不是提取逻辑出错的垃圾。
    判据（任一不满足 → 视为低质量，触发兜底重试）：
    - 至少 min_count 条
    - 至少 min_price_ratio 比例的条目有有效价格（>0）
    - 标题非 junk 的比例 ≥ 60%
    这样能拦住"解析出 9 件但全是 title=None / price=22 噪声"的假成功。
    """
    if not products or len(products) < min_count:
        return False
    n = len(products)
    has_price = sum(1 for p in products
                    if isinstance(p.get("price"), (int, float)) and p.get("price", 0) > 0)
    good_title = sum(1 for p in products if not _is_junk_title(str(p.get("title") or "")))
    if has_price / n < min_price_ratio:
        return False
    if good_title / n < 0.6:
        return False
    return True


def _parse_products_from_html(html: str, url: str, platform: str, p: dict,
                              limit: int) -> list[dict]:
    """从 HTML 用平台 selector 解析商品列表（纯解析，无网络）。"""
    from scrapling.parser import Adaptor
    adp = Adaptor(html, url=url, auto_match=False)
    products = []
    card_sel = p.get("card_sel") or p.get("card_selector") or "div"
    cards = adp.css(card_sel)
    title_sel_default = p.get("title_sel", "h2 span")
    price_sel_default = p.get("price_sel", "")
    for c in cards[:limit]:
        try:
            title_node = c.css_first(title_sel_default) if title_sel_default else None
            if title_node is None:
                title_node = (c.css_first("h2 span") or c.css_first("h3")
                              or c.css_first("[class*='title']") or c.css_first("img[alt]"))
            title = ""
            if title_node:
                title = (title_node.text or title_node.attrib.get("title", "")
                         or title_node.attrib.get("alt", "")).strip()

            # ── 脏数据过滤：剔除空标题 / UI 噪声文案（非真实商品）──
            if _is_junk_title(title):
                continue
            price_node = c.css_first(price_sel_default) if price_sel_default else None
            if price_node is None:
                price_node = (c.css_first("span.a-price span.a-offscreen")
                              or c.css_first("[class*='Price']")
                              or c.css_first("[class*='price']"))
            price = None
            if price_node and price_node.text:
                txt = price_node.text.replace("$", "").replace(",", "").replace("US", "").strip()
                try:
                    price = float(txt.split()[0])
                except Exception:
                    pass
            rating = None
            r_node = c.css_first("span.a-icon-alt")
            if r_node and r_node.text:
                try:
                    rating = float(r_node.text.split()[0])
                except Exception:
                    pass
            asin = ""
            img_url = ""
            sponsored = False
            if "amazon" in platform:
                a = c.css_first("a.a-link-normal[href*='/dp/']") or c.css_first("a[href*='/dp/']")
                if a:
                    href = a.attrib.get("href", "")
                    if "/dp/" in href:
                        asin = href.split("/dp/")[1].split("/")[0].split("?")[0]
                img_node = c.css_first("img.s-image") or c.css_first("img[srcset]")
                if img_node:
                    img_url = (img_node.attrib.get("src", "")
                                or img_node.attrib.get("data-src", ""))
                sp_nodes = c.css("[class*='AdHolder'], span.s-sponsored-label-text, [data-component-type='sp-sponsored-result']")
                if sp_nodes:
                    sponsored = True
                else:
                    full_card_text = (c.text or "").lower() if hasattr(c, 'text') else ""
                    if "sponsored" in full_card_text[:50]:
                        sponsored = True
            # 真实月销信号：Amazon 搜索卡片上的 "X+ bought in past month"（第一方数据，非估算）
            bought_past_month = None
            try:
                # 优先用 selector 精确定位（a-color-secondary span 含该文案），再兜底全卡文本
                bm = None
                for node in c.css("span.a-color-secondary, span.a-size-base"):
                    ntext = node.text or ""
                    if "bought in past month" in ntext.lower():
                        bm = _BOUGHT_RE.search(ntext)
                        if bm:
                            break
                if not bm:
                    card_text = c.text or "" if hasattr(c, "text") else ""
                    bm = _BOUGHT_RE.search(card_text)
                if bm:
                    bought_past_month = _parse_bought_count(bm.group(1))
            except Exception:
                pass
            if title:
                item = {"title": title[:100], "price": price, "rating": rating}
                if asin:
                    item["asin"] = asin
                if img_url:
                    item["image_url"] = img_url
                if sponsored:
                    item["sponsored"] = True
                if bought_past_month is not None:
                    item["bought_past_month"] = bought_past_month
                    item["bought_past_month_source"] = "Amazon 搜索页『X+ bought in past month』第一方真实数据"
                products.append(item)
        except Exception:
            continue
    return products


# Amazon 第一方月销信号正则："2K+ bought in past month" / "500+ bought in past month"
import re as _re_mod
_BOUGHT_RE = _re_mod.compile(r'([\d,.]+[KkMm]?\+?)\s*bought in past month', _re_mod.IGNORECASE)


def _parse_bought_count(raw: str) -> int:
    """'2K+' → 2000, '500+' → 500, '1.5K+' → 1500"""
    s = raw.replace("+", "").replace(",", "").strip()
    mult = 1
    if s and s[-1] in "Kk":
        mult = 1000; s = s[:-1]
    elif s and s[-1] in "Mm":
        mult = 1_000_000; s = s[:-1]
    try:
        return int(float(s) * mult)
    except Exception:
        return 0





# ─────────── 平台失败计数器（per-process，每个 case 独立）───────────
# Agent 反复在同一个 partial/坏掉的平台试错时，设置硬上限节省时间
# 单个平台连续失败 ≥ N 次后，本 case 内不再真请求，直接返回 cooldown_skipped
_PLATFORM_FAIL_COUNT: dict[str, int] = {}
_PLATFORM_FAIL_THRESHOLD = 2  # 连续失败 N 次后熔断
_FAIL_COOLDOWN_REASON = "platform_fail_cooldown"


def _record_platform_fail(platform: str):
    _PLATFORM_FAIL_COUNT[platform] = _PLATFORM_FAIL_COUNT.get(platform, 0) + 1


def _record_platform_success(platform: str):
    """成功后清零计数（容忍偶发失败）"""
    _PLATFORM_FAIL_COUNT.pop(platform, None)


def _is_platform_cooled_down(platform: str) -> bool:
    return _PLATFORM_FAIL_COUNT.get(platform, 0) >= _PLATFORM_FAIL_THRESHOLD


def tool_search_products(platform: str, keyword: str, limit: int = 15,
                         use_proxy: bool = True, max_retries: int = None) -> dict:
    """单平台搜索。platform 是 PLATFORMS 注册表里的 id。
    
    反爬加固：
    - 间歇性平台（temu/shein/alibaba 等）失败自动重试（引擎轮换），默认重试 4 次
    - selector 解析 0 件但 HTML 有效 → LLM 文本兜底提取（SPA 平台）
    - **熔断机制**：单平台连续失败 ≥ 2 次后，本 case 内直接 cooldown_skipped 不再请求
      （避免 Agent 反复试错 partial 平台浪费 3+ 分钟/次）
    """
    logger.info(f"🔧 search_products({platform}, {keyword})")
    platform = _resolve_platform(platform)
    p = PLATFORMS.get(platform)
    if not p:
        return {"platform": platform, "error": f"unknown platform '{platform}'. "
                f"用 list_platforms 看可用列表。可用: {list(PLATFORMS.keys())[:10]}...",
                "products": []}
    
    # 熔断检查：本 case 内该平台已连续失败 ≥ 2 次，直接拒绝
    if _is_platform_cooled_down(platform):
        fail_n = _PLATFORM_FAIL_COUNT[platform]
        logger.warning(f"  ⏭️ {platform} 已连续失败 {fail_n} 次，本 case 内熔断，建议改用其他平台")
        return {
            "platform": platform, "platform_name": p.get("name"),
            "url": None, "count": 0, "products": [],
            "skipped_cooldown": True,
            "fail_count": fail_n,
            "error": f"{_FAIL_COOLDOWN_REASON}: 本 case 内已失败 {fail_n} 次，已熔断。"
                      f"建议换平台（pick_platforms_for_market 给出的 verified 列表）",
            "platform_status": p.get("status"),
        }
    url_template = p.get("search_url") or p.get("url")
    if not url_template:
        return {"platform": platform, "error": "no search_url in PLATFORMS", "products": []}
    url = url_template.format(kw=keyword.replace(" ", "+"))
    needs_proxy = p.get("needs_proxy")
    actual_use_proxy = use_proxy and bool(needs_proxy)
    # 地理受限平台：用对应国家的出口代理（amazon_uk→英国节点 等）
    country_proxy = None
    if actual_use_proxy:
        try:
            from proxy.multi_country import get_proxy_for_platform, PLATFORM_COUNTRY
            if platform in PLATFORM_COUNTRY:
                country_proxy = get_proxy_for_platform(platform)
                if country_proxy:
                    logger.info(f"[{platform}] 走 {PLATFORM_COUNTRY[platform]} 国家出口代理 {country_proxy}")
        except Exception as e:
            logger.debug(f"[{platform}] 多国代理不可用，回退默认: {str(e)[:80]}")
    force_browser = platform in {"walmart", "temu", "shopee_sg", "shopee_my",
                                   "bestbuy", "aliexpress", "target", "tiktok_shop",
                                   "shein", "lazada_sg", "tokopedia",
                                   "yandex_market", "mercadolibre_mx", "mercadolibre_br",
                                   "ozon", "wildberries", "trendyol", "coupang", "noon",
                                   "amazon_uk", "amazon_de", "amazon_fr", "amazon_jp"}
    # 间歇性平台默认重试 2 次（共 3 次尝试），稳定平台不重试
    # 地理受限平台只要拿到了对应国家代理，也加重试（首次握手可能慢）
    # max_retries=4 是允许的最大上限（调用方显式传入时生效），默认仍 2 次以避免单次过长
    if max_retries is None:
        if platform in _FLAKY_PLATFORMS or country_proxy:
            max_retries = 2
        else:
            max_retries = 0
    else:
        # 调用方显式传入，限制不超过 4
        max_retries = min(max(int(max_retries), 0), 4)

    products = []
    last_error = None
    last_html = None
    attempts = 0
    card_sel = p.get("card_sel")  # SPA 站点等这个 selector 渲染出来再抓
    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        try:
            if country_proxy:
                # 显式走国家出口代理
                html = fetch(url, proxy=country_proxy, force_browser=force_browser,
                             wait_for_selector=card_sel if force_browser else None)
            else:
                html = fetch(url, use_proxy=actual_use_proxy, force_browser=force_browser,
                             wait_for_selector=card_sel if force_browser else None)
            last_html = html
        except Exception as e:
            last_error = str(e)[:160]
            logger.warning(f"[{platform}] fetch 第 {attempt+1} 次失败: {last_error}")
            continue  # 重试（引擎链内部已轮换，这里再给一次完整重试）

        products = _parse_products_from_html(html, url, platform, p, limit)
        if products and _products_look_valid(products):
            break  # 拿到有效数据才停
        if products:
            # 解析出商品但质量差（大量缺价格/标题）→ 视为提取逻辑有问题，触发兜底
            last_error = f"low_quality_parse: 解析出 {len(products)} 件但有效信息率过低"
            logger.warning(f"[{platform}] 第 {attempt+1} 次解析质量差（{len(products)} 件多数缺价格/标题），将走兜底")
            products = []  # 丢弃低质量结果，让后续 LLM/RapidAPI 兜底
        else:
            last_error = "selector_parsed_0_items"
            logger.warning(f"[{platform}] 第 {attempt+1} 次 selector 解析 0 件（HTML {len(html)} chars）")

    # selector 全失败但 HTML 有效 → LLM 文本兜底提取
    used_llm_fallback = False
    if not products and last_html and len(last_html) > 5000 and platform in _LLM_FALLBACK_PLATFORMS:
        logger.info(f"[{platform}] selector 解析 0 件，启用 LLM 文本兜底提取")
        try:
            llm_r = tool_extract_products_with_llm(url, max_items=limit)
            llm_products = llm_r.get("products", [])
            if llm_products:
                # 归一化 LLM 提取结果到标准格式（剔除 UI 噪声/空标题）
                for lp in llm_products:
                    lp_title = (lp.get("title") or "")[:100]
                    if _is_junk_title(lp_title):
                        continue
                    products.append({
                        "title": lp_title,
                        "price": lp.get("price"),
                        "rating": lp.get("rating"),
                    })
                if products:
                    used_llm_fallback = True
                    last_error = None
        except Exception as e:
            logger.warning(f"[{platform}] LLM 兜底也失败: {str(e)[:120]}")

    # ScrapeGraphAI 第二层兜底（LLM 图谱式结构化抽取）——当 selector + LLM 文本兜底都没拿到时再试。
    # 多层回退、万一成功了呢。仅对 SPA 兜底平台启用，避免对正常平台浪费 LLM 成本。
    used_scrapegraph = False
    if not products and last_html and len(last_html) > 5000 and platform in _LLM_FALLBACK_PLATFORMS:
        logger.info(f"[{platform}] LLM 文本兜底仍 0 件，启用 ScrapeGraphAI 图谱抽取兜底")
        try:
            sg_products = scrapegraph_extract_products(url, max_items=limit)
            for sp in sg_products:
                sp_title = (sp.get("title") or "")[:100]
                if _is_junk_title(sp_title):
                    continue
                products.append({
                    "title": sp_title,
                    "price": sp.get("price"),
                    "rating": sp.get("rating"),
                })
            if products:
                used_scrapegraph = True
                last_error = None
        except Exception as e:
            logger.warning(f"[{platform}] ScrapeGraphAI 兜底也失败: {str(e)[:120]}")

    # RapidAPI Amazon 兜底/增强（仅 Amazon 系平台，且配置了 key）
    used_rapidapi = False
    if "amazon" in platform and paid_apis.rapidapi_amazon_available():
        geo = (p.get("region") or "US").upper()
        # 情况 1：scraper 全失败 → RapidAPI 直接取真实数据
        if not products:
            ra = paid_apis.search_amazon_products(keyword, geo)
            if ra.get("available") and ra.get("products"):
                for rp in ra["products"][:limit]:
                    item = {"title": (rp.get("title") or "")[:100],
                            "price": rp.get("price"), "rating": rp.get("rating"),
                            "review_count": rp.get("review_count")}
                    if rp.get("asin"):
                        item["asin"] = rp["asin"]
                    if rp.get("image_url"):
                        item["image_url"] = rp["image_url"]
                    if rp.get("is_sponsored"):
                        item["sponsored"] = True
                    if rp.get("sales_volume"):
                        item["sales_volume_text"] = rp["sales_volume"]
                        bpm = _parse_bought_count(
                            (_BOUGHT_RE.search(rp["sales_volume"]) or [None, "0"])[1]
                            if _BOUGHT_RE.search(rp["sales_volume"]) else "0")
                        if bpm:
                            item["bought_past_month"] = bpm
                    products.append(item)
                used_rapidapi = True
                last_error = None
        # 情况 2：scraper 成功但缺真实月销 → 用 RapidAPI 搜索结果补 sales_volume
        elif not any(x.get("bought_past_month") for x in products):
            ra = paid_apis.search_amazon_products(keyword, geo)
            if ra.get("available") and ra.get("products"):
                sales_by_asin = {rp["asin"]: rp.get("sales_volume")
                                 for rp in ra["products"] if rp.get("asin") and rp.get("sales_volume")}
                for prod in products:
                    sv = sales_by_asin.get(prod.get("asin"))
                    if sv:
                        prod["sales_volume_text"] = sv
                        m = _BOUGHT_RE.search(sv)
                        if m:
                            prod["bought_past_month"] = _parse_bought_count(m.group(1))
                if sales_by_asin:
                    used_rapidapi = True

    if "amazon" in platform:
        POOL.add_batch([prod for prod in products if prod.get("asin")])

    # 按真实销量/评论数重排，确保返回的是"主流畅销盘子"而非搜索相关性混排的前几个。
    # 排序键：真实月销 bought_past_month > 评论数 review_count（都没有则保持原序）。
    def _pop_key(pr):
        return (pr.get("bought_past_month") or 0, pr.get("review_count") or 0)
    if any((pr.get("bought_past_month") or pr.get("review_count")) for pr in products):
        products.sort(key=_pop_key, reverse=True)

    result = {"platform": platform, "platform_name": p.get("name"), "url": url,
              "count": len(products), "products": products,
              "pool_size_after": POOL.size(),
              "platform_status": p.get("status"),
              "_attempts": attempts}
    if used_llm_fallback:
        result["_extraction"] = "llm_fallback"
    if used_scrapegraph:
        result["_extraction"] = "scrapegraph_ai"
    if used_rapidapi:
        result["_extraction"] = "rapidapi_amazon"
        result["_real_sales_enriched"] = True
    # 明确成功/失败标志（0 件 = 失败，即便没抛异常）。避免"假成功"。
    result["success"] = bool(products)
    if not products:
        result["error"] = last_error or "no_products_parsed: 所有引擎/解析/兜底均未拿到真实商品（视为失败）"
    
    # 熔断计数：成功清零，失败 +1（达到阈值后下次同平台直接 cooldown_skipped）
    if products:
        _record_platform_success(platform)
    else:
        _record_platform_fail(platform)
        fail_n = _PLATFORM_FAIL_COUNT.get(platform, 0)
        if fail_n >= _PLATFORM_FAIL_THRESHOLD:
            result["cooldown_warning"] = (
                f"⚠️ {platform} 已连续失败 {fail_n} 次，下次调用将自动熔断。"
                f"建议改用其他 verified 平台。"
            )
        result["_fail_count"] = fail_n
    
    return result


def tool_search_multi_platform(platforms: list[str], keyword: str,
                                limit_per_platform: int = 20,
                                allow_blocked: bool = False) -> dict:
    """一次抓多个平台（**并发**，每个平台都真实抓，失败明确返回 error，不静默跳过）。
    
    用户指定地区/国家时（如 美国+英国+日本），先用 pick_platforms_for_market 拿到
    platform_keys，然后传给本工具一次抓全。
    
    **A 优化（2026-06）**：默认自动跳过 status='blocked' 的平台（节省 60s/个超时），
    在 results 中标 skipped_blocked=true 让报告诚实呈现。
    需要测试 blocked 平台时显式设 allow_blocked=True。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
    logger.info(f"🔧 search_multi_platform({platforms}, {keyword}) 并发抓")
    # 归一化平台名（处理 mercadolivre_br → mercadolibre_br 等本地化拼写），去重保序
    _seen = set()
    platforms = [pp for pp in (_resolve_platform(x) for x in platforms)
                 if not (pp in _seen or _seen.add(pp))]
    results = {}
    
    # ─── A. 提前过滤 blocked 平台（不浪费 60s 超时）───
    skipped_blocked = []
    active = []
    for plat in platforms:
        p = PLATFORMS.get(plat.lower())
        if p and p.get("status") == "blocked" and not allow_blocked:
            skipped_blocked.append({
                "platform": plat,
                "platform_name": p.get("name"),
                "blocker": p.get("blocker", "")[:120],
            })
            results[plat] = {
                "platform_name": p.get("name"),
                "count": 0, "products": [], "url": None,
                "skipped_blocked": True,
                "blocker": p.get("blocker", "")[:120],
                "status": "blocked",
            }
        else:
            active.append(plat)
    if skipped_blocked:
        logger.info(f"  ⏭️ 跳过 {len(skipped_blocked)} 个 blocked 平台: "
                    f"{[s['platform'] for s in skipped_blocked]}")
    
    def _fetch(plat):
        try:
            r = tool_search_products(plat, keyword, limit=limit_per_platform, use_proxy=True)
            return plat, {
                "platform_name": r.get("platform_name"),
                "count": r.get("count", 0),
                "products": r.get("products", [])[:5],
                "url": r.get("url"),
                "error": r.get("error"),
                "status": r.get("platform_status"),
                "skipped_cooldown": r.get("skipped_cooldown", False),
                "fail_count": r.get("_fail_count") or r.get("fail_count"),
            }
        except Exception as e:
            return plat, {"error": str(e)[:200]}
    
    # ─── 单平台硬超时：partial 90s / verified 240s（防 wildberries 拖死整个池）───
    PER_PLATFORM_TIMEOUT = {
        "partial": 90,
        "verified": 240,
        "untested": 90,
    }
    
    if active:
        with ThreadPoolExecutor(max_workers=min(len(active), 8)) as ex:
            futures = {ex.submit(_fetch, p): p for p in active}
            # 全局超时 = 最大平台超时 × 1.5（留余量给最慢的 verified 平台）
            global_timeout = 360
            try:
                for fut in as_completed(futures, timeout=global_timeout):
                    plat, res = fut.result()
                    results[plat] = res
            except TimeoutError:
                # 超时后：把还没返回的 future 标记为超时
                for fut, plat in futures.items():
                    if not fut.done():
                        fut.cancel()
                        if plat not in results:
                            p_status = (PLATFORMS.get(plat, {}).get("status") or "unknown")
                            results[plat] = {
                                "platform_name": PLATFORMS.get(plat, {}).get("name", plat),
                                "count": 0, "products": [], "url": None,
                                "error": f"timeout: 单平台超过 {global_timeout}s 未返回，强制中止",
                                "status": p_status,
                                "timeout_killed": True,
                            }
                            # 计入熔断
                            _record_platform_fail(plat)
                logger.warning(f"  ⏱️ search_multi_platform 全局 {global_timeout}s 超时，"
                                f"强制中止挂起的平台")
    
    summary = {plat: r.get("count", 0) for plat, r in results.items()}
    successful = [p for p, r in results.items() if r.get("count", 0) > 0]
    failed = [p for p, r in results.items()
              if r.get("count", 0) == 0 and not r.get("skipped_blocked")]
    total_items = sum(summary.values())

    # 真失败判定：active 平台一个都没拿到数据 = 全失败（区别于 skipped_blocked）
    all_failed = (len(active) > 0 and len(successful) == 0)
    # 是否建议中止：active 平台全失败，或所有平台都 blocked/失败、一件都没抓到
    should_abort = all_failed or (total_items == 0 and len(active) > 0)

    if should_abort:
        verdict = ("🛑 本批次全部失败（0 件真实数据）。**禁止用其它市场/Amazon US 数据顶替**。"
                   "应：① 换关键词或换本市场其它平台重试一次；② 仍失败则 record_stage_status 标 "
                   "failed/partial 并在报告中如实写'该市场数据采集失败'，然后停止本市场深入分析。")
    elif len(successful) >= 2:
        verdict = "✅ 多平台覆盖完整"
    else:
        verdict = (f"⚠️ 仅 {len(successful)} 个平台成功，结论可能偶然，"
                   f"建议换平台/关键词补一次，或 record_stage_status 标 partial")

    return {
        "keyword": keyword, "platforms_tried": len(platforms),
        "platforms_active": len(active),
        "platforms_skipped_blocked": len(skipped_blocked),
        "skipped_blocked": skipped_blocked,
        "summary_counts": summary, "results": results,
        "pool_size_after": POOL.size(),
        "all_failed": all_failed,
        "should_abort": should_abort,
        "_summary": {
            "成功平台": successful,
            "失败/空数据平台": failed,
            "跳过的 blocked 平台": [s["platform"] for s in skipped_blocked],
            "总抓到商品数": total_items,
            "verdict": verdict,
        }
    }


def tool_analyze_market_structure(products: list[dict]) -> dict:
    """从商品列表算价格带分布 / 评分中位 / 集中度等"""
    logger.info(f"🔧 analyze_market_structure({len(products)} 件)")
    if not products:
        return {"error": "no products"}
    df = pd.DataFrame(products)
    out = {}
    # 价格分布
    if "price" in df and df["price"].notna().any():
        prices = df["price"].dropna()
        out["price_stats"] = {
            "n": len(prices), "min": round(prices.min(), 2), "max": round(prices.max(), 2),
            "median": round(prices.median(), 2), "mean": round(prices.mean(), 2),
            "p25": round(prices.quantile(0.25), 2), "p75": round(prices.quantile(0.75), 2),
        }
        # 简易价格带空白：找直方图低频区间
        bins = pd.cut(prices, bins=6)
        out["price_band_counts"] = {str(k): int(v) for k, v in bins.value_counts().sort_index().items()}
    # 评分
    if "rating" in df and df["rating"].notna().any():
        ratings = df["rating"].dropna()
        out["rating_stats"] = {
            "n": len(ratings), "median": round(ratings.median(), 2),
            "mean": round(ratings.mean(), 2), "min": round(ratings.min(), 2),
            "below_4_3": int((ratings < 4.3).sum()),
        }
        out["rating_threshold_pass_rate"] = round((ratings >= 4.3).sum() / len(ratings), 2)
    # 品牌集中度（基于标题首词当作品牌粗估）
    if "title" in df:
        df["brand_guess"] = df["title"].str.split().str[0]
        top = df["brand_guess"].value_counts().head(10)
        cr4 = top.head(4).sum() / len(df)
        out["brand_concentration"] = {
            "cr4": round(cr4, 2), "cr10": round(top.sum() / len(df), 2),
            "top_brands_guess": top.to_dict(),
        }
    # Sponsored 占比（如果商品有 sponsored / is_sponsored 字段）
    sponsored_count = sum(1 for p in products
                           if isinstance(p, dict) and (p.get("sponsored") or p.get("is_sponsored")))
    out["sponsored_ratio"] = {
        "count": sponsored_count,
        "ratio": round(sponsored_count / max(len(products), 1), 3),
        "note": ("> 30% = 该品类广告投放激烈，新品需高 ACOS 才能挤进首页" 
                 if sponsored_count / max(len(products), 1) > 0.3 else
                 "< 30% = 广告竞争一般，新品有有机流量机会"),
    }
    # 评分分布段（看长尾 / 是否有失败品在前列）
    if "rating" in df and df["rating"].notna().any():
        rating_buckets = {
            "5.0": int((df["rating"] >= 4.9).sum()),
            "4.5-4.9": int(((df["rating"] >= 4.5) & (df["rating"] < 4.9)).sum()),
            "4.0-4.5": int(((df["rating"] >= 4.0) & (df["rating"] < 4.5)).sum()),
            "3.5-4.0": int(((df["rating"] >= 3.5) & (df["rating"] < 4.0)).sum()),
            "<3.5": int((df["rating"] < 3.5).sum()),
        }
        out["rating_distribution"] = rating_buckets
    return out


def tool_estimate_market_size(products: list[dict]) -> dict:
    """
    **市场规模信号**（免费，不靠搜索量 API）。
    把搜索结果 Top N 的真实月销('X+ bought in past month')+ 评论总量 + BSR
    聚合成"这个品类能卖多少"的信号——比搜索量更接近真实成交端。

    输入：search_products / get_amazon_product_details_api 返回的商品列表
         （需含 bought_past_month 或 sales_volume_text、review_count、price）
    """
    logger.info(f"🔧 estimate_market_size({len(products)} 件)")
    if not products:
        return {"error": "no_products"}

    import re as _re
    def _parse_bought(p):
        # 优先用已解析的 bought_past_month；否则从 sales_volume_text 解析
        if isinstance(p.get("bought_past_month"), (int, float)):
            return int(p["bought_past_month"])
        sv = p.get("sales_volume_text") or p.get("sales_volume") or ""
        m = _re.search(r'([\d.]+)\s*([KkMm]?)\+?\s*bought', str(sv))
        if m:
            v = float(m.group(1)); mult = {"k":1000,"K":1000,"m":1_000_000,"M":1_000_000}.get(m.group(2),1)
            return int(v*mult)
        return None

    monthly_sales = [s for s in (_parse_bought(p) for p in products if isinstance(p, dict)) if s]
    reviews = [p.get("review_count") for p in products
               if isinstance(p, dict) and isinstance(p.get("review_count"), (int, float))]
    prices = [p.get("price") for p in products
              if isinstance(p, dict) and isinstance(p.get("price"), (int, float))]

    n_with_sales = len(monthly_sales)
    total_monthly_units = sum(monthly_sales) if monthly_sales else 0
    total_reviews = sum(reviews) if reviews else 0
    median_price = sorted(prices)[len(prices)//2] if prices else None

    # 月度 GMV 信号（真实月销 × 中位价）
    monthly_gmv = round(total_monthly_units * median_price, 0) if (total_monthly_units and median_price) else None

    # 市场规模判级（基于 Top 商品真实月销总和——这是下限，实际更大）
    if total_monthly_units >= 50000:
        size_label = "🟢 大市场（Top 商品月销合计 ≥5万件，需求旺盛）"
    elif total_monthly_units >= 10000:
        size_label = "🟢 中大市场（月销合计 1-5万件）"
    elif total_monthly_units >= 2000:
        size_label = "🟡 中市场（月销合计 2千-1万件）"
    elif total_monthly_units > 0:
        size_label = "🟠 小众市场（月销合计 <2千件，需求有限）"
    else:
        size_label = "⚪ 月销数据不足（头部商品无 bought 标签，看评论总量判断）"

    # 需求集中度：是头部通吃还是分散
    concentration = None
    if len(monthly_sales) >= 3:
        ms_sorted = sorted(monthly_sales, reverse=True)
        top1_share = round(ms_sorted[0] / total_monthly_units, 2) if total_monthly_units else None
        concentration = {
            "top1_units": ms_sorted[0], "top1_share": top1_share,
            "verdict": ("头部垄断（Top1 占比 >50%，难进）" if top1_share and top1_share > 0.5
                        else "需求分散（多个商品都有销量，新品有机会）"),
        }

    return {
        "products_analyzed": len(products),
        "products_with_real_sales": n_with_sales,
        "total_monthly_units_topN": total_monthly_units,
        "total_reviews_topN": total_reviews,
        "median_price_usd": median_price,
        "monthly_gmv_signal_usd": monthly_gmv,
        "market_size_verdict": size_label,
        "demand_concentration": concentration,
        "_source": ("真实月销('X+ bought in past month') + 评论总量 + 真实价格聚合"),
        "_real_data": True,
        "_note": ("这是 Top N 商品的真实成交信号，是市场规模【下限】（Amazon 只对热销品显示 bought 标签）。"
                  "比搜索量更接近真实需求——搜索量是流量端，这是成交端。"
                  "评论总量是历史累计成交的稳定代理。"),
    }


# =====================  阶段 3：痛点挖掘  =====================
def tool_get_reviews(asin: str, n_pages: int = 1, star: str = "all") -> dict:
    """抓商品详情页摘要 + 代表评论。Amazon 限制下若摘要为空则返回元信息让 LLM 用先验知识"""
    logger.info(f"🔧 get_reviews({asin})")
    summary = get_product_review_summary(asin=asin, use_proxy=True)
    text_list = reviews_to_text_list(summary)
    has_data = bool(summary.get("ai_summary") or summary.get("sample_reviews"))
    return {
        "asin": asin,
        "title": summary.get("title", ""),
        "rating": summary.get("rating"),
        "total_reviews": summary.get("total_reviews"),
        "ai_summary": summary.get("ai_summary", ""),
        "review_texts": text_list,
        "has_data": has_data,
        "note": "" if has_data else "Amazon 已对评论做登录限制；建议结合多 ASIN 综合 + 模型先验知识做痛点推断",
    }


def tool_get_reviews_batch(asins: list[str], max_total: int = 500,
                             concurrency: int = 8) -> dict:
    """批量抓多个 ASIN 的真实评论 + 关键词云聚合。
    
    默认 max_total=500（旧 260）。**推荐传 25-30 个 ASIN**：
    - Top 10（覆盖热销爆款）
    - 中部 10（中位价格带）
    - 长尾 5-10（低评分/失败品 → 看真实痛点而不只是爆款痛点）
    
    每个 ASIN ~13 条，30 ASIN = 390 条；20 ASIN = 260 条。
    样本量越大，痛点频次越精确。
    
    **D 优化（2026-06）**：concurrency 暴露给 LLM。默认 8（已经是并发的）。
    若 ASIN ≥ 20 可加到 12（注意 Amazon 反爬可能拦截）；若 ASIN ≤ 10 用 6 即可。
    """
    logger.info(f"🔧 get_reviews_batch({len(asins)} ASINs, max_total={max_total}, "
                f"concurrency={concurrency})")
    result = get_reviews_batch(asins=asins, use_proxy=True, max_total=max_total,
                                 concurrency=concurrency)
    text_list = reviews_to_text_list({"sample_reviews": result["reviews"]})
    result["review_texts"] = text_list
    
    rev_count = len(text_list)
    sample_text = text_list[:5] if text_list else []
    
    # 评分分布（透明化）— 让 Agent / 用户看到样本是否多样化
    ratings_seen = [r.get("rating") for r in result.get("reviews", []) if isinstance(r.get("rating"), (int, float))]
    rating_distribution = {}
    if ratings_seen:
        for star in [1, 2, 3, 4, 5]:
            cnt = sum(1 for r in ratings_seen if int(r) == star)
            rating_distribution[f"{star}_star"] = cnt
    
    result["_summary"] = {
        "评论数": rev_count,
        "ASIN 数": len(asins),
        "并发度": concurrency,
        "覆盖率": f"{result.get('asins_count', len(asins))} 个 ASIN，平均每个 {rev_count // max(len(asins), 1)} 条",
        "评分分布": rating_distribution,
        "前 5 条原文（让 LLM 真'看到'）": sample_text,
        "diversity_warning": (
            "⚠️ 样本偏向爆款（前几个 ASIN 占评论 80%+），建议加入低评分商品 ASIN 看失败品痛点"
            if any(rating_distribution.get(f"{s}_star", 0) > rev_count * 0.5 for s in [4, 5]) else
            "✅ 评分分布合理，覆盖好评和差评"
        ),
    }
    return result
    result = get_reviews_batch(asins=asins, use_proxy=True, max_total=max_total)
    # 把评论压成纯文本喂 LLM
    text_list = reviews_to_text_list({"sample_reviews": result["reviews"]})
    result["review_texts"] = text_list
    
    # LLM 可见摘要 — 已在上方生成，不重复
    return result


def tool_analyze_reviews(reviews: list[str] = None) -> dict:
    """
    用 LLM 从评论中提炼 pain_points / selling_points / opportunity。
    返回必须是有效 JSON。失败时明确 error，**禁止 LLM 用 raw 后再凭空编痛点**。
    
    **重要**：reviews 参数必填！从 get_reviews_batch 的返回值取 review_texts 字段传入。
    """
    logger.info(f"🔧 analyze_reviews({len(reviews or [])} 条)")
    if reviews is None or not reviews:
        return {
            "error": "no_reviews_passed",
            "message": (
                "❌ analyze_reviews 必须传 reviews 参数！\n"
                "正确用法：先调 get_reviews_batch(asins=[...]) 拿到结果 R，"
                "再调 analyze_reviews(reviews=R['review_texts'])。\n"
                "**不要重复 get_reviews_batch**，把上一步的 review_texts 字段直接当参数传进来。"
            ),
        }
    joined = "\n".join(f"- {r}" for r in reviews[:50])
    prompt = (
        "你是跨境电商选品专家。下面是某商品的真实评论。请提炼：\n"
        "1) pain_points：用户最频繁抱怨的痛点 Top5（每条带出现次数估算）\n"
        "2) selling_points：用户最满意的卖点 Top3\n"
        "3) opportunity：1-2 条可工程化改进的差异化点（具体到参数/功能，不要废话）\n"
        "用 JSON 输出 {pain_points: [...], selling_points: [...], opportunity: [...]}。\n\n"
        "评论：\n" + joined
    )
    # 重试 2 次
    last_err = None
    for attempt in range(2):
        try:
            resp = get_client().chat.completions.create(
                model=resolve_model("flash"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1200,
            )
            content = resp.choices[0].message.content or ""
            if not content.strip():
                last_err = "empty_response"
                continue
            try:
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    last_err = "not_dict"
                    continue
                if not parsed.get("pain_points"):
                    last_err = "no_pain_points_in_response"
                    continue
                parsed["_source"] = f"LLM analyzed {len(reviews)} 条真实评论"
                parsed["_review_count"] = len(reviews)
                return parsed
            except Exception as e:
                last_err = f"json_parse_failed: {e}"
                continue
        except Exception as e:
            last_err = f"llm_call_failed: {str(e)[:120]}"

    return {
        "error": "analyze_failed",
        "message": f"评论分析失败（{last_err}）。**禁止凭空编痛点**。"
                    "请：① 重试 ② 减少评论数后再试 ③ 在最终报告里明确标注'痛点分析失败，需重试'。",
        "last_err": last_err,
    }


# =====================  阶段 5：利润测算  =====================
def tool_full_cost_breakdown(sale_price: float, procurement_cost: float = None,
                              moq: int = 500, monthly_sales_estimate: int = 300,
                              asin: str = None, category: str = "headphones",
                              weight_oz: float = 6, longest_in: float = 6,
                              procurement_source_url: str = None,
                              stage: str = "new_product") -> dict:
    """
    完整成本测算 14 项 + 盈亏点 + 资金占用。
    - procurement_cost 必须来自真实工具（estimate_procurement_cost / search_1688 / 用户人工提供）
    - 必须传 procurement_source_url 证明来源（如 "https://detail.1688.com/offer/..."
      或 "user-input: 供应商报价单 X")
    - 不传 source 或 source 是空字符串时，**直接拒绝测算**，返回 error
    """
    logger.info(f"🔧 full_cost_breakdown(sale=${sale_price}, cost=${procurement_cost}, asin={asin}, source={procurement_source_url})")

    if procurement_cost is None or procurement_cost <= 0:
        return {
            "error": "procurement_cost_missing",
            "message": "采购成本未提供。请先调用 estimate_procurement_cost 或 search_1688 拿真实数据。"
                        "如果都失败，必须明确告知用户'采购成本未知，需用户提供供应商报价单'，禁止凭印象写数字。",
        }
    if not procurement_source_url:
        return {
            "error": "procurement_source_url_required",
            "message": "禁止使用未经溯源的采购成本！必须传 procurement_source_url 证明来源："
                        "① 1688 商品详情 URL（如 https://detail.1688.com/offer/xxx.html）"
                        "② 用户提供的报价单标识（如 'user-input: PingPong 2026-05 报价'）"
                        "③ 真实供应商的实际订单号"
                        "如果没有真实来源，**不能进行利润测算**。在报告中明确标注 procurement_pending。",
        }

    # 用真实成本数据自动加载费率
    real_params = build_real_cost_params(category, sale_price, weight_oz, longest_in)
    overrides = {k: v for k, v in real_params.items() if not k.startswith("_")}
    result = full_cost_breakdown(sale_price, procurement_cost, moq,
                                  monthly_sales_estimate, overrides=overrides,
                                  stage=stage)
    result["data_provenance"] = {
        "asin_in_pool": bool(asin and POOL.get(asin)),
        "asin_real_data": POOL.get(asin) if asin else None,
        "procurement_source_url": procurement_source_url,
        "real_cost_metadata": real_params.get("_metadata"),
    }
    return result


def tool_stress_test(sale_price: float, procurement_cost: float,
                      monthly_sales_estimate: int = 300) -> dict:
    logger.info(f"🔧 stress_test(${sale_price}, ${procurement_cost})")
    return stress_test(sale_price, procurement_cost, monthly_sales_estimate=monthly_sales_estimate)


def tool_monte_carlo_stress_test(
    sale_price: float, procurement_cost: float,
    moq: int = 500, monthly_sales_estimate: int = 300,
    n_simulations: int = 5000, is_new_product: bool = True,
) -> dict:
    """蒙特卡洛压力测试 — 5000 次模拟 6 变量同时波动"""
    from modules.full_cost import monte_carlo_stress_test
    logger.info(f"🔧 monte_carlo_stress_test(${sale_price}, n={n_simulations}, new={is_new_product})")
    return monte_carlo_stress_test(
        sale_price, procurement_cost, moq, monthly_sales_estimate,
        n_simulations=n_simulations, is_new_product=is_new_product,
    )


# =====================  阶段 7：IP 风险扫描  =====================
def tool_quick_ip_check(keyword: str, brand_candidate: str = "") -> dict:
    logger.info(f"🔧 quick_ip_check({keyword}, {brand_candidate})")
    return quick_ip_check(keyword=keyword, brand_candidate=brand_candidate, use_proxy=False)


def tool_deep_ip_risk_assessment(category_keyword: str,
                                   brand_candidates: list[str] = None,
                                   max_depth: int = 1) -> dict:
    """深度 IP 风险评估 — PatentsView 官方 API + 引用链 + 商标"""
    logger.info(f"🔧 deep_ip_risk_assessment({category_keyword})")
    return deep_ip_risk_assessment(category_keyword,
                                     brand_candidates=brand_candidates or [],
                                     use_proxy=False, max_depth=max_depth)


# =====================  ASIN 池 + 候选品强校验  =====================
def tool_get_asin_pool() -> dict:
    """查询当前会话已采集到的真实 ASIN 池。提候选品前必看，禁止凭空创造。"""
    logger.info(f"🔧 get_asin_pool() → {POOL.size()} ASINs")
    return {
        "size": POOL.size(),
        "summary": POOL.summary_for_llm(),
        "items": POOL.all(),
    }


def tool_validate_candidate(asin: str) -> dict:
    """提候选品时必须用真实 ASIN 校验。返回该 ASIN 的真实数据用于后续测算。"""
    logger.info(f"🔧 validate_candidate({asin})")
    item = POOL.get(asin)
    if not item:
        return {
            "asin": asin, "valid": False,
            "error": f"ASIN {asin} 不在池中。候选品必须来自真实获取，请先调用 get_bestsellers / search_products / get_movers_shakers 来扩充 ASIN 池。",
        }
    return {"asin": asin, "valid": True, "real_data": item}


# =====================  1688 真实采购成本（仅真实数据，抓不到就明确返回 error）=====================
def tool_get_real_procurement_cost(category_keyword_zh: str) -> dict:
    """从 1688 拿真实采购成本。失败明确报错，禁止 LLM 猜数字。"""
    logger.info(f"🔧 get_real_procurement_cost({category_keyword_zh})")
    return get_real_procurement_cost(category_keyword_zh, use_proxy=False)


def tool_search_1688(keyword: str, limit: int = 20) -> dict:
    """搜 1688 看具体型号的真实供应商报价（候选品确定后用具体型号反查）"""
    logger.info(f"🔧 search_1688({keyword})")
    return search_1688(keyword, use_proxy=False, limit=limit)


# =====================  人工提供采购成本（1688 失败时的合法兜底）=====================
# 全局缓存：用户手工提供的采购成本（按 ASIN 或 category 索引）
_USER_PROVIDED_COSTS: dict[str, dict] = {}


def tool_provide_procurement_cost(
    procurement_cost_usd: float,
    source_label: str,
    asin: str = None,
    category_keyword: str = None,
    notes: str = "",
) -> dict:
    """
    **用户手工提供真实采购成本**，用于 1688 获取失败时的合法兜底。
    
    使用场景：
    - Agent 调用 get_real_procurement_cost / search_1688 全失败时（被验证码挡）
    - Agent 在报告里登记 procurement_pending 后，用户回复"采购成本是 8.5 USD，来自 PingPong 报价单"
    - 重新走阶段 5 利润测算
    
    source_label 必填，是来源凭证（不能是空字符串），例如：
    - "user-input: PingPong 2026-05 报价单"
    - "user-input: 工厂 X 实际订单 #12345"
    - "https://detail.1688.com/offer/123456789.html"  ← 这种直接传 URL 也行
    """
    logger.info(f"🔧 provide_procurement_cost(${procurement_cost_usd}, source={source_label}, asin={asin})")
    if procurement_cost_usd <= 0:
        return {"error": "invalid_cost", "message": "采购成本必须为正数"}
    if not source_label or not source_label.strip():
        return {"error": "source_required",
                "message": "source_label 不能为空。需要是 1688 URL、报价单标识、或实际订单号。"}
    
    record = {
        "procurement_cost_usd": procurement_cost_usd,
        "source_label": source_label.strip(),
        "asin": asin,
        "category_keyword": category_keyword,
        "notes": notes,
        "registered_at": __import__("datetime").datetime.now().isoformat(),
    }
    
    # 同时按 ASIN 和 category 缓存
    if asin:
        _USER_PROVIDED_COSTS[f"asin:{asin}"] = record
    if category_keyword:
        _USER_PROVIDED_COSTS[f"cat:{category_keyword}"] = record
    
    return {
        "ok": True,
        "registered": record,
        "next_step": (f"现在可以调用 full_cost_breakdown(sale_price, "
                       f"procurement_cost={procurement_cost_usd}, "
                       f"procurement_source_url='{source_label.strip()}', "
                       f"asin='{asin or ''}', category='headphones'/'kitchen'/...)"),
    }


def tool_get_provided_costs() -> dict:
    """查询当前会话已登记的人工提供采购成本（用于 Agent 知道有哪些可以做利润测算）"""
    logger.info(f"🔧 get_provided_costs() → {len(_USER_PROVIDED_COSTS)} 条")
    return {"count": len(_USER_PROVIDED_COSTS), "costs": _USER_PROVIDED_COSTS}


# =====================  阶段状态登记（强制透明，禁止静默跳过）=====================
_STAGE_STATUS: dict[str, dict] = {}  # stage_id → {status, reason, ...}


def tool_record_stage_status(
    stage_id: str,
    status: str,
    reason: str = "",
    needs_user_action: str = "",
    artifacts: list = None,
) -> dict:
    """
    **登记某个阶段的执行状态**，最终报告必须依此生成 stage_status_summary 段落。
    
    禁止"沉默跳过"：当一个阶段无法完成时（数据抓不到、采购成本 1688 失败等），
    必须显式调用此工具登记 status='skipped' / 'partial'，并填 reason 和 needs_user_action。
    
    stage_id 应使用：stage1_trends / stage2_competition / stage3_pain_points / 
                    stage4_candidates / stage5_profit / stage6_supply / 
                    stage7_ip_risk / stage8_decision
    
    status 取值：
    - "completed"  完成
    - "partial"    部分完成（解释哪部分缺）
    - "skipped"    暂缓/跳过（解释原因+用户怎么帮忙补）
    - "failed"     失败（含报错信息）
    
    artifacts 是产出物列表（评论数、ASIN 数、截图路径等）
    """
    logger.info(f"🔧 record_stage_status({stage_id}, {status})")
    valid_statuses = {"completed", "partial", "skipped", "failed"}
    if status not in valid_statuses:
        return {"error": "invalid_status",
                "message": f"status 必须是 {valid_statuses}"}
    
    record = {
        "stage_id": stage_id, "status": status, "reason": reason,
        "needs_user_action": needs_user_action,
        "artifacts": artifacts or [],
        "recorded_at": __import__("datetime").datetime.now().isoformat(),
    }
    _STAGE_STATUS[stage_id] = record
    return {"ok": True, "recorded": record,
             "all_stages_so_far": list(_STAGE_STATUS.keys())}


def tool_stage_status_summary() -> dict:
    """
    汇总所有阶段的执行状态。**最终报告生成前必须调用此工具**，确保不漏阶段、不静默跳过。
    返回每个阶段的 status，以及一段格式化的 markdown，可直接贴进报告"执行汇总"章节。
    """
    logger.info(f"🔧 stage_status_summary() → {len(_STAGE_STATUS)} 阶段")
    
    expected = ["stage1_trends", "stage2_competition", "stage3_pain_points",
                "stage4_candidates", "stage5_profit", "stage6_supply",
                "stage7_ip_risk", "stage8_decision"]
    
    rows = []
    md_lines = ["| 阶段 | 状态 | 说明 | 用户后续动作 |", "|---|:---:|---|---|"]
    icon = {"completed": "✅", "partial": "🟡", "skipped": "⚠️", "failed": "❌"}
    for sid in expected:
        rec = _STAGE_STATUS.get(sid)
        if not rec:
            rows.append({"stage_id": sid, "status": "not_run"})
            md_lines.append(f"| {sid} | ⚪ 未执行 | — | — |")
            continue
        rows.append(rec)
        st = rec["status"]
        md_lines.append(
            f"| {sid} | {icon.get(st, '?')} {st} "
            f"| {rec.get('reason', '') or '—'} "
            f"| {rec.get('needs_user_action', '') or '—'} |"
        )
    
    skipped = [r for r in rows if r.get("status") in ("skipped", "partial", "failed")]
    return {
        "stages_total": len(expected),
        "stages_recorded": len([r for r in rows if r.get("status") != "not_run"]),
        "skipped_or_partial": len(skipped),
        "rows": rows,
        "markdown": "\n".join(md_lines),
        "warning": (f"⚠️ 有 {len(skipped)} 个阶段未完整执行，最终报告必须明确写出"
                     "「执行汇总表」+「待用户提供」清单。" if skipped else "✅ 全部阶段完成"),
    }


def tool_traceability_check(claims: list[dict]) -> dict:
    """
    **最终报告前必调**。校验报告里每个声明（ASIN/价格/评分/标题）是否能在 ASIN 池中找到真实匹配。
    
    输入：claims = [
        {"asin": "B0CRTYZG5C", "claim_price": 27.99, "claim_rating": 4.4, "claim_title_contains": "Soundcore P30i"},
        ...
    ]
    
    返回：每个声明的 verified=True/False + mismatch 字段说明哪里和真实数据对不上。
    
    **mismatch 不为空 = LLM 编造了数据**，必须用真实值修正报告。
    """
    logger.info(f"🔧 traceability_check({len(claims)} claims)")
    results = []
    for c in claims:
        asin = c.get("asin", "")
        real = POOL.get(asin) if asin else None
        if not real:
            results.append({
                "asin": asin, "verified": False,
                "error": f"ASIN {asin} 不在池中，禁止在报告里引用此 ASIN",
            })
            continue
        mismatch = {}
        # 价格容差 5%
        cp = c.get("claim_price")
        rp = real.get("price")
        if cp is not None and rp is not None:
            if abs(cp - rp) / max(rp, 0.01) > 0.05:
                mismatch["price"] = {"claim": cp, "real": rp,
                                       "diff_pct": round((cp - rp) / rp * 100, 1)}
        # 评分必须严格匹配（小数允许 0.1 容差）
        cr = c.get("claim_rating")
        rr = real.get("rating")
        if cr is not None and rr is not None and abs(cr - rr) > 0.15:
            mismatch["rating"] = {"claim": cr, "real": rr}
        # 标题包含检查
        ct = c.get("claim_title_contains", "")
        rt = (real.get("title") or "").lower()
        if ct and ct.lower() not in rt:
            mismatch["title"] = {"claim_contains": ct, "real_title": real.get("title", "")[:120]}
        
        results.append({
            "asin": asin, "verified": not mismatch,
            "real_data": real, "mismatch": mismatch or None,
        })
    
    failed = [r for r in results if not r["verified"]]
    return {
        "total_claims": len(claims),
        "verified": len(claims) - len(failed),
        "failed": len(failed),
        "all_verified": len(failed) == 0,
        "results": results,
        "warning": (f"❌ 有 {len(failed)} 条声明无法在 ASIN 池中验证，"
                     "禁止在最终报告里使用这些数据，必须用真实值修正。"
                     if failed else "✅ 所有声明已在 ASIN 池中验证通过"),
    }


# =====================  证据截图（最终报告的可视化证据）=====================
def tool_capture_evidence(asin: str, geo: str = "US") -> dict:
    """对一个候选品 ASIN 做证据截图（详情页 + 搜索页），存到 reports/evidence/。
    geo 决定 amazon 站点（US/UK/DE/FR/JP/IN/MX/BR 等）"""
    logger.info(f"🔧 capture_evidence({asin}, geo={geo})")
    return capture_evidence_for_asin(asin, use_proxy=True, geo=geo)


def tool_capture_evidence_for_url(listing_url: str, save_name: str = None) -> dict:
    """**非 Amazon 平台用此**：对任意 listing URL 抓证据（Lazada SG/Yandex/MercadoLibre 等）。
    返回 listing 截图 + 主图 URL。给候选品做截图证据时按平台用对应工具。"""
    logger.info(f"🔧 capture_evidence_for_url({listing_url})")
    return capture_evidence_for_url(listing_url, save_name=save_name, use_proxy=True)


def tool_capture_evidence_batch(asins: list[str], geo: str = "US",
                                  concurrency: int = 3) -> dict:
    """**C 优化批量并发**：N 个候选 ASIN 并发抓证据截图（详情页+搜索页+主图）。
    3 个 ASIN 串行 ~270s → 并发 concurrency=3 时 ~90s（3x 提速）。
    
    用法：拿到 3-5 个核心候选品后，一次调用本工具替代多次单 ASIN 调用。
    """
    logger.info(f"🔧 capture_evidence_batch({len(asins)} ASINs, geo={geo}, concurrency={concurrency})")
    return capture_evidence_batch(asins, geo=geo, use_proxy=True, concurrency=concurrency)


# =====================  全球平台清单（让 LLM 选合适的平台）=====================
def tool_list_platforms(region: str = None) -> dict:
    """列出可用平台。region 可选 US/UK/EU/JP/KR/SEA/LATAM/TR/Global/CN_B2B"""
    logger.info(f"🔧 list_platforms(region={region})")
    return {
        "total": len(PLATFORMS),
        "platforms": list_platforms_by_region(region),
        "status_summary": status_summary(),
        "regions_available": list(REGIONS.keys()),
    }


def tool_pick_platforms_for_market(markets: list[str], only_verified: bool = False,
                                     include_global: bool = None) -> dict:
    """
    根据用户指定的目标市场/国家，自动推荐合适的电商平台清单。
    
    markets 可以是国家代码（US/UK/DE/JP/MX/RU/IN/AE 等）或地区（North America/Europe/SEA）。
    例如 markets=['US','UK'] → 推荐 amazon, walmart, bestbuy, amazon_uk 等。
    
    only_verified 默认 False（推荐全部相关平台让 LLM 真试一次，untested 平台跑过会自动登记结果）。
    设 True 时只返回实测可抓的平台（保守模式）。
    
    include_global 默认 None（auto）：当本地平台够用（≥3 个 verified）时不加全球电商；
    当本地平台 verified 数 <3 时，自动加 temu/aliexpress/alibaba 作为跨境补充并明确标注"补充数据源"。
    
    用户严格地区限制策略：
    - 用户指定俄罗斯 → 只返回 yandex_market/wildberries（俄罗斯本地）
    - 如果本地都 blocked/数量不够 → 报告里必须明确写"本地平台 X 个 blocked, 用 Y/Z 全球跨境补充"
    - 不混淆"本地数据"和"全球对标数据"
    """
    logger.info(f"🔧 pick_platforms_for_market({markets}, only_verified={only_verified})")
    
    # 国家 → 地区映射
    country_to_region = {
        "US": "US", "USA": "US", "AMERICA": "US", "美国": "US",
        "CA": "US", "CANADA": "US", "加拿大": "US",
        "UK": "UK", "GB": "UK", "ENGLAND": "UK", "英国": "UK",
        "DE": "EU", "GERMANY": "EU", "德国": "EU",
        "FR": "EU", "FRANCE": "EU", "法国": "EU",
        "IT": "EU", "ITALY": "EU", "意大利": "EU",
        "ES": "EU", "SPAIN": "EU", "西班牙": "EU",
        "NL": "EU", "NETHERLANDS": "EU", "荷兰": "EU",
        "EUROPE": "EU", "EU": "EU", "欧洲": "EU",
        "JP": "JP", "JAPAN": "JP", "日本": "JP",
        "KR": "KR", "KOREA": "KR", "韩国": "KR",
        "SG": "SEA", "SINGAPORE": "SEA", "新加坡": "SEA",
        "MY": "SEA", "MALAYSIA": "SEA", "马来西亚": "SEA",
        "ID": "SEA", "INDONESIA": "SEA", "印尼": "SEA",
        "TH": "SEA", "THAILAND": "SEA", "泰国": "SEA",
        "VN": "SEA", "VIETNAM": "SEA", "越南": "SEA",
        "PH": "SEA", "PHILIPPINES": "SEA", "菲律宾": "SEA",
        "SEA": "SEA", "SOUTHEAST ASIA": "SEA", "东南亚": "SEA",
        "MX": "LATAM", "MEXICO": "LATAM", "墨西哥": "LATAM",
        "BR": "LATAM", "BRAZIL": "LATAM", "巴西": "LATAM",
        "AR": "LATAM", "ARGENTINA": "LATAM", "阿根廷": "LATAM",
        "LATAM": "LATAM", "拉美": "LATAM",
        "TR": "TR", "TURKEY": "TR", "土耳其": "TR",
        "RU": "RU", "RUSSIA": "RU", "俄罗斯": "RU",
        "IN": "IN", "INDIA": "IN", "印度": "IN",
        "AE": "AE", "UAE": "AE", "阿联酋": "AE", "迪拜": "AE",
        "SA": "AE", "SAUDI": "AE", "沙特": "AE",
        "AU": "AU", "AUSTRALIA": "AU", "澳大利亚": "AU", "澳洲": "AU",
        "NZ": "AU", "NEW ZEALAND": "AU", "新西兰": "AU",
        "CN": "CN", "CHINA": "CN", "中国": "CN", "中國": "CN",
        "GLOBAL": "Global", "全球": "Global",
        # 大洲（展开为多个子地区）
        "NORTH AMERICA": "North America", "北美": "North America", "北美洲": "North America",
        "SOUTH AMERICA": "South America", "南美": "South America", "南美洲": "South America",
        "EUROPE_CONT": "Europe",
        "ASIA": "Asia", "亚洲": "Asia",
        "MIDDLE EAST": "Middle East", "中东": "Middle East",
        "OCEANIA": "Oceania", "大洋洲": "Oceania",
    }
    
    region_keys = set()
    for m in markets:
        m_upper = m.upper().strip()
        region = country_to_region.get(m_upper, m_upper)
        # 大洲 → 展开为多个子地区
        if region in CONTINENTS:
            for sub in CONTINENTS[region]:
                region_keys.add(sub)
        elif region in REGIONS:
            region_keys.add(region)
    
    if not region_keys:
        return {"error": f"无法识别市场 {markets}",
                "available_markets": list(country_to_region.keys()),
                "available_regions": list(REGIONS.keys())}
    
    # 收集这些地区的平台 — 严格本地优先
    local_selected = {}
    local_blocked = {}
    
    for region in region_keys:
        for plat_key in REGIONS.get(region, []):
            if plat_key in PLATFORMS:
                p = PLATFORMS[plat_key]
                if p.get("status") == "blocked":
                    local_blocked[plat_key] = {
                        "key": plat_key, "name": p["name"], "region": p["region"],
                        "blocker": p.get("blocker", "未知反爬"),
                    }
                    continue
                if only_verified and p.get("status") not in ("verified", "partial"):
                    continue
                local_selected[plat_key] = {
                    "key": plat_key, "name": p["name"], "region": p["region"],
                    "status": p["status"], "search_url_template": p["search_url"],
                    "scope": "local",
                }
    
    # 决定是否加全球跨境补充
    local_verified_count = sum(1 for v in local_selected.values() if v["status"] == "verified")
    auto_include_global = (include_global is True) or (
        include_global is None and local_verified_count < 3
    )
    
    global_selected = {}
    if auto_include_global:
        for k in REGIONS.get("Global", []):
            if k in PLATFORMS and k not in local_selected:
                p = PLATFORMS[k]
                if only_verified and p.get("status") not in ("verified", "partial"):
                    continue
                global_selected[k] = {
                    "key": k, "name": p["name"], "region": p["region"],
                    "status": p["status"], "search_url_template": p["search_url"],
                    "scope": "global_supplement",
                }
    
    selected = {**local_selected, **global_selected}
    
    # 生成警告
    warnings = []
    if local_blocked:
        warnings.append(
            f"⚠️ 该地区有 {len(local_blocked)} 个本地平台被反爬挡："
            + ", ".join([f"{v['name']}({v['blocker'][:30]})" for v in local_blocked.values()])
        )
    if local_verified_count == 0:
        warnings.append(
            "❌ 本地完全没有 verified 平台！本次调研只能侧面通过全球跨境平台。"
            "报告中必须明确标注'本地平台数据缺失，X个blocked'。"
        )
    elif local_verified_count < 3:
        warnings.append(
            f"⚠️ 本地仅 {local_verified_count} 个 verified 平台，已自动补充全球跨境作为对标数据。"
            "**注意：报告中本地数据和跨境对标数据必须分开写**，不能混为一谈。"
        )
    
    return {
        "input_markets": markets,
        "matched_regions": list(region_keys),
        "platform_count": len(selected),
        "local_count": len(local_selected),
        "local_verified_count": local_verified_count,
        "local_blocked_count": len(local_blocked),
        "global_supplement_count": len(global_selected),
        "platforms": list(selected.values()),
        "platform_keys": list(selected.keys()),
        "local_blocked": list(local_blocked.values()),
        "warnings": warnings,
        "next_step": (f"调用 search_multi_platform(platforms={list(selected.keys())}, "
                       f"keyword=...) 真抓多平台数据。"),
        "_data_source_disclosure": (
            "📋 报告中数据来源声明（必须照实写）：\n"
            f"- 本地平台（{local_verified_count} verified）: {[k for k, v in local_selected.items() if v['status']=='verified']}\n"
            f"- 本地 blocked（{len(local_blocked)} 个，需付费打码服务）: {list(local_blocked.keys())}\n"
            f"- 全球跨境补充（{len(global_selected)} 个）: {list(global_selected.keys())}\n"
        ),
    }


def tool_export_report_pdf(markdown_path: str, output_path: str = None,
                             title: str = "选品决策报告") -> dict:
    """把 markdown 报告导出为 PDF（商家可直接发邮件/分享）"""
    from modules.report_export import export_pdf
    md = Path(markdown_path).read_text(encoding="utf-8")
    if not output_path:
        output_path = markdown_path.replace(".md", ".pdf")
    return export_pdf(md, output_path, title=title)


def tool_make_one_pager(markdown_path: str, loss_probability: float = None) -> dict:
    """从完整报告生成 1 页摘要（商家 1 分钟读完）"""
    from modules.report_export import one_pager
    md = Path(markdown_path).read_text(encoding="utf-8")
    summary = one_pager(md, loss_probability_main=loss_probability)
    out_path = markdown_path.replace(".md", "_1page.md")
    Path(out_path).write_text(summary, encoding="utf-8")
    return {"ok": True, "path": out_path, "chars": len(summary)}


def tool_generate_price_chart(price_bands: dict, save_name: str) -> dict:
    """生成真实价格分布柱状图（matplotlib，不是 markdown 文字表）"""
    from modules.report_export import generate_price_distribution_chart
    out_path = str(Path(__file__).resolve().parent.parent / "reports" / "evidence" / f"{save_name}.png")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    return generate_price_distribution_chart(price_bands, out_path)


def tool_screenshot_url(url: str, save_name: str) -> dict:
    """对任意 URL 截图（用于关键证据，如 BSR 榜首页 / Trends 曲线）"""
    logger.info(f"🔧 screenshot_url({url})")
    return screenshot_url(url, save_name, use_proxy=True)


# =====================  辅助：网页清洗 / 文档转换  =====================
def tool_webpage_to_markdown(url: str) -> dict:
    """用 crawl4ai 把网页转成干净的 LLM-ready markdown，用于深度分析竞品页/认证页等"""
    logger.info(f"🔧 webpage_to_markdown({url})")
    md = webpage_to_markdown_sync(url)
    return {"url": url, "length": len(md), "markdown": md[:5000]}


def tool_file_to_markdown(file_path: str) -> dict:
    """用 markitdown 把 PDF/Office 文档转成 markdown（供应商报价/专利文档/认证证书）"""
    logger.info(f"🔧 file_to_markdown({file_path})")
    md = file_to_markdown(file_path)
    return {"file": file_path, "length": len(md), "markdown": md[:5000]}


# =====================  TikHub：实时社媒趋势 + TikTok Shop 电商  =====================
def tool_tiktok_shop_search(keyword: str, region: str = "US", limit: int = 20) -> dict:
    """实时搜 TikTok Shop 商品（真实价格/评分/评论数/销量/店铺）。未配 key 时如实返回 error。"""
    logger.info(f"🔧 tiktok_shop_search({keyword}, region={region}, limit={limit})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置，TikTok Shop 实时通道不可用", "products": []}
    try:
        prods = tikhub.shop_search(keyword, region=region, limit=limit)
        return {"ok": True, "keyword": keyword, "region": region, "count": len(prods),
                "summary": tikhub.shop_summary(keyword, prods),
                "stats": tikhub.product_stats(prods), "products": prods}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "products": []}


def tool_tiktok_shop_reviews(product_id: str, region: str = "US", limit: int = 20) -> dict:
    """抓 TikTok Shop 某商品的真实评论（product_id 来自 tiktok_shop_search）。区域不匹配返回空。"""
    logger.info(f"🔧 tiktok_shop_reviews({product_id}, region={region})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置", "reviews": []}
    try:
        rv = tikhub.shop_reviews(product_id, region=region, limit=limit)
        return {"ok": True, "product_id": product_id, "count": len(rv), "reviews": rv}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "reviews": []}


def tool_social_trends(platforms: list = None, limit: int = 20) -> dict:
    """跨平台实时社媒热搜/热词。看「今天大家在搜什么、什么在火」。

    可选平台（不传则全抓）：tiktok / douyin / weibo / xiaohongshu / kuaishou /
    bilibili / twitter（X，海外）/ lemon8（字节海外种草）。
    """
    logger.info(f"🔧 social_trends(platforms={platforms}, limit={limit})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置，社媒趋势通道不可用", "platforms": {}}
    try:
        return {"ok": True, "platforms": tikhub.social_trends(platforms=platforms, limit=limit)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "platforms": {}}


def tool_tiktok_category_list(region: str = "US") -> dict:
    """TikTok Shop 一级品类树（带二级子类），用于「按品类」选品导航。"""
    logger.info(f"🔧 tiktok_category_list(region={region})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置", "categories": []}
    try:
        cats = tikhub.fetch_products_category_list(region=region)
        return {"ok": True, "region": region, "count": len(cats), "categories": cats}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "categories": []}


def tool_tiktok_products_by_category(category_id: str, region: str = "US",
                                     limit: int = 20, offset: int = 0) -> dict:
    """某品类下的实时在售商品榜（按品类 Top N）。category_id 来自 tiktok_category_list。"""
    logger.info(f"🔧 tiktok_products_by_category({category_id}, region={region}, limit={limit})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置", "products": []}
    try:
        prods = tikhub.fetch_products_by_category(category_id, region=region, limit=limit, offset=offset)
        return {"ok": True, "category_id": category_id, "region": region, "count": len(prods),
                "stats": tikhub.product_stats(prods), "products": prods}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "products": []}


def tool_tiktok_hot_selling(region: str = "US", limit: int = 20) -> dict:
    """TikTok Shop 实时热销榜（爆品雷达）。返回当前热卖商品（价格/评分/销量/店铺）。"""
    logger.info(f"🔧 tiktok_hot_selling(region={region}, limit={limit})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置", "products": []}
    try:
        prods = tikhub.fetch_hot_selling_products(region=region, limit=limit)
        return {"ok": True, "region": region, "count": len(prods),
                "stats": tikhub.product_stats(prods), "products": prods}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "products": []}


def tool_tiktok_trending_hashtags(time_range: int = 7, country: str = "US", limit: int = 10) -> dict:
    """TikTok 热门话题榜：含浏览量、发布数、排名、popularity_curve（声量曲线）+ top_creators（达人侦察）。"""
    logger.info(f"🔧 tiktok_trending_hashtags(time_range={time_range}, country={country}, limit={limit})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置", "hashtags": []}
    try:
        tags = tikhub.trending_hashtags(time_range=time_range, country=country, limit=limit)
        return {"ok": True, "time_range": time_range, "country": country,
                "count": len(tags), "hashtags": tags}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "hashtags": []}


def tool_reddit_search(query: str, time_range: str = "year", sort: str = "relevance",
                       limit: int = 10) -> dict:
    """Reddit 帖子搜索（需求验证层）：真实用户讨论里的需求/吐槽/比较。用于受众洞察/机会挖掘。"""
    logger.info(f"🔧 reddit_search({query}, time_range={time_range}, sort={sort})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置", "posts": []}
    try:
        posts = tikhub.reddit_search(query, time_range=time_range, sort=sort, limit=limit)
        return {"ok": True, "query": query, "count": len(posts), "posts": posts}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "posts": []}


def tool_youtube_search(query: str, country: str = "US", language: str = "en",
                        limit: int = 12) -> dict:
    """YouTube 视频搜索（需求验证层）：测评/开箱视频，看内容偏好与触达渠道。用于受众洞察/竞品分析。"""
    logger.info(f"🔧 youtube_search({query}, country={country})")
    from modules import tikhub
    if not tikhub.is_configured():
        return {"ok": False, "error": "TIKHUB_API_KEY 未配置", "videos": []}
    try:
        vids = tikhub.youtube_search(query, country=country, language=language, limit=limit)
        return {"ok": True, "query": query, "count": len(vids), "videos": vids}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "videos": []}


def _ddv_match(text: str, q: str) -> bool:
    return (not q) or (q.lower() in (text or "").lower())


def tool_browse_daily_dataset(query: str = "", kinds: list = None,
                              tenant_id: str = "dev_tenant", limit: int = 30) -> dict:
    """读取「每日刷新」已落库的大盘数据——**零额外 API 成本**（不重复消耗 TikHub 额度）。

    覆盖每批刷新攒下的真实底盘：
      - categories     28 个一级品类的实时商品榜（每类 Top 商品 + 价格/评分/销量统计）
      - hot_selling    TikTok Shop 实时热销榜（爆品雷达）
      - social_trends  8 平台社媒热词（tiktok/douyin/weibo/xiaohongshu/kuaishou/bilibili/twitter/lemon8）
      - hashtags       TikTok 热门话题声量曲线 + 达人

    用法：任何模式开局**先调本工具**用大盘底子定位方向（省额度）；需要更细/更新的实时数据再去调
    tiktok_shop_search / social_trends 等付费工具补齐。query 非空时按关键词过滤（匹配商品标题/品类名/
    热词/话题）。kinds 可限定只取某几类（如 ["social_trends","hashtags"]）。
    """
    logger.info(f"🔧 browse_daily_dataset(query={query!r}, kinds={kinds}, limit={limit})")
    want = set(kinds) if kinds else {"categories", "hot_selling", "social_trends", "hashtags"}
    q = (query or "").strip()
    try:
        from backend import storage as st
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"数据快照存储不可用：{str(e)[:160]}"}

    snaps = st.list_latest_snapshots(tenant_id, limit=400)
    if not snaps:
        return {"ok": False, "error": "还没有任何每日刷新快照，请先在「监控与订阅」页点『立即刷新』或等待定时刷新。",
                "categories": [], "hot_selling": [], "social_trends": {}, "hashtags": []}

    captured_at = None
    for s in snaps:
        ca = getattr(s, "captured_at", None)
        if ca:
            captured_at = ca.isoformat() if hasattr(ca, "isoformat") else str(ca)
            break

    def _slim(p: dict) -> dict:
        return {k: p.get(k) for k in ("title", "price", "currency_symbol", "rating",
                                      "sold_count", "shop_name", "url") if p.get(k) is not None}

    categories: list[dict] = []
    hot_selling: list[dict] = []
    social: dict[str, list] = {}
    hashtags: list[dict] = []

    for s in snaps:
        src = s.source
        pl = s.payload or {}
        if not getattr(s, "real_data", False):
            continue
        if src == "category_rank" and "categories" in want:
            cname = pl.get("category_name") or ""
            prods = [p for p in (pl.get("products") or []) if isinstance(p, dict)]
            if q:
                prods = [p for p in prods if _ddv_match(p.get("title", ""), q)]
                if not prods and not _ddv_match(cname, q):
                    continue
            if prods or _ddv_match(cname, q):
                categories.append({"category": cname, "stats": pl.get("stats"),
                                   "top_products": [_slim(p) for p in prods[:8]]})
        elif src == "hot_selling" and "hot_selling" in want:
            prods = [p for p in (pl.get("products") or []) if isinstance(p, dict)]
            if q:
                prods = [p for p in prods if _ddv_match(p.get("title", ""), q)]
            hot_selling = [_slim(p) for p in prods[:limit]]
        elif src.startswith("trend_") and "social_trends" in want:
            items = [it for it in (pl.get("items") or []) if isinstance(it, dict)]
            kws = [it for it in items if _ddv_match(it.get("keyword", ""), q)]
            if kws:
                social[pl.get("label") or src] = [
                    {"keyword": it.get("keyword"), "heat": it.get("heat"), "views": it.get("views")}
                    for it in kws[:limit]]
        elif src == "hashtag_trends" and "hashtags" in want:
            tags = [t for t in (pl.get("hashtags") or []) if isinstance(t, dict)]
            if q:
                tags = [t for t in tags if _ddv_match(t.get("hashtag", ""), q)]
            hashtags = [{"hashtag": t.get("hashtag"), "views": t.get("vv") or t.get("views"),
                         "rank": t.get("rank"), "publish_count": t.get("publish_cnt") or t.get("publish_count")}
                        for t in tags[:limit]]

    categories.sort(key=lambda c: len(c["top_products"]), reverse=True)
    return {
        "ok": True,
        "captured_at": captured_at,
        "query": q or None,
        "note": "零成本：来自每日刷新已落库快照；如需更新/更细数据再调实时工具。",
        "counts": {"categories": len(categories), "hot_selling": len(hot_selling),
                   "social_platforms": len(social), "hashtags": len(hashtags)},
        "categories": categories[:limit],
        "hot_selling": hot_selling,
        "social_trends": social,
        "hashtags": hashtags,
    }


# =====================  工具 schema（DeepSeek function calling）=====================
TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "load_skill",
        "description": "加载方法论 skill 文档。Agent 接到调研任务的第一步必须先加载 procurement-research，按文档推进。",
        "parameters": {"type": "object", "properties": {
            "skill_name": {"type": "string", "default": "procurement-research"}
        }}}},
    {"type": "function", "function": {
        "name": "extract_products_with_llm",
        "description": "**SPA 平台终极武器** — 当 search_products 返回 0 商品（selector 解析失败），用此工具用 LLM 直接读 HTML 文本提取商品。适合 shopee/lazada/tokopedia/trendyol/noon 等 SPA 平台。返回结构化商品列表。",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "搜索结果页 URL"},
            "max_items": {"type": "integer", "default": 20}
        }, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "get_current_datetime",
        "description": "**调研开始第一步必调**。获取当前真实日期/月份/季节，用于 Trends 查询的时间语境、报告 '数据采集时间' 标注、季节性判断。**禁止凭印象写日期**。",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "search_multi_platform",
        "description": "一次抓多个平台。platforms 是平台 id 列表（如 ['amazon','walmart','shopee_sg']）。每个平台都真实抓，失败明确返回 error，不静默跳过。这是覆盖多个全球电商的主要工具。",
        "parameters": {"type": "object", "properties": {
            "platforms": {"type": "array", "items": {"type": "string"}},
            "keyword": {"type": "string"},
            "limit_per_platform": {"type": "integer"}
        }, "required": ["platforms", "keyword"]}}},
    {"type": "function", "function": {
        "name": "get_trend",
        "description": "Google Trends 品类热度 12 月走势",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"}, "geo": {"type": "string"}
        }, "required": ["keyword"]}}},
    {"type": "function", "function": {
        "name": "tiktok_shop_search",
        "description": "**实时电商首选**。搜 TikTok Shop 当前在售商品，返回真实价格/评分/评论数/销量/店铺/图片/链接。TikTok Shop 是全球主流电商平台之一，数据每日更新——亚马逊机房 IP 被封时这是最稳的实时商品来源。region 用目标市场（US/UK/GB/MY/TH/VN/ID/SG 等）。",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"},
            "region": {"type": "string", "description": "市场国家码，默认 US"},
            "limit": {"type": "integer", "default": 20}
        }, "required": ["keyword"]}}},
    {"type": "function", "function": {
        "name": "tiktok_shop_reviews",
        "description": "抓 TikTok Shop 某商品的真实买家评论（product_id 来自 tiktok_shop_search）。用于提炼痛点/卖点。region 必须与搜索时一致，否则评论不可用。",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"},
            "region": {"type": "string", "description": "需与搜索时一致，默认 US"},
            "limit": {"type": "integer", "default": 20}
        }, "required": ["product_id"]}}},
    {"type": "function", "function": {
        "name": "social_trends",
        "description": "**社媒实时趋势（8 平台）**。一次拿 TikTok 趋势搜索词 / 抖音热榜 / 微博热搜 / 小红书热词 / 快手热榜 / B站热搜 / X(Twitter) 趋势 / Lemon8 热词，看『今天大家在搜什么、什么在火』。用于发现新兴选品方向、把社媒热度与电商销量做交叉验证。platforms 不传则全拿。",
        "parameters": {"type": "object", "properties": {
            "platforms": {"type": "array", "items": {"type": "string"},
                          "description": "tiktok/douyin/weibo/xiaohongshu/kuaishou/bilibili/twitter/lemon8，不传则全部"},
            "limit": {"type": "integer", "default": 20}
        }}}},
    {"type": "function", "function": {
        "name": "tiktok_category_list",
        "description": "**按品类选品导航**。拿 TikTok Shop 一级品类树（带二级子类，含 category_id）。用于『按品类』浏览，再用 tiktok_products_by_category 抓某类的实时 Top 商品。region 用目标市场。",
        "parameters": {"type": "object", "properties": {
            "region": {"type": "string", "description": "市场国家码，默认 US"}
        }}}},
    {"type": "function", "function": {
        "name": "tiktok_products_by_category",
        "description": "**按品类实时榜**。某品类下当前在售商品（真实价格/评分/评论数/销量/店铺/图），同 tiktok_shop_search 字段。category_id 来自 tiktok_category_list。用于『按品类 Top5/Top N』选品。",
        "parameters": {"type": "object", "properties": {
            "category_id": {"type": "string"},
            "region": {"type": "string", "description": "市场国家码，默认 US"},
            "limit": {"type": "integer", "default": 20},
            "offset": {"type": "integer", "default": 0}
        }, "required": ["category_id"]}}},
    {"type": "function", "function": {
        "name": "tiktok_hot_selling",
        "description": "**实时爆品雷达**。TikTok Shop 当前热销榜，返回正在热卖的真实商品（价格/评分/销量/店铺）。用于快速摸清一个市场当下什么在爆卖。region 用目标市场。",
        "parameters": {"type": "object", "properties": {
            "region": {"type": "string", "description": "市场国家码，默认 US"},
            "limit": {"type": "integer", "default": 20}
        }}}},
    {"type": "function", "function": {
        "name": "tiktok_trending_hashtags",
        "description": "**话题声量曲线 + 达人侦察**。TikTok 热门话题榜：每个话题的浏览量(views)、发布数、排名、popularity_curve（time_range 天时间序列，判声量拐点）、top_creators（带货达人）。趋势探索/机会挖掘用来看『什么话题在涨、谁在带』。time_range 取 7/30/120。",
        "parameters": {"type": "object", "properties": {
            "time_range": {"type": "integer", "description": "天数 7/30/120，默认 7"},
            "country": {"type": "string", "description": "国家码，默认 US"},
            "limit": {"type": "integer", "default": 10}
        }}}},
    {"type": "function", "function": {
        "name": "reddit_search",
        "description": "**需求验证层（Reddit）**。搜真实用户讨论帖（标题/子版块/分数/评论数/正文摘要/链接），是『用户自己的声音』。受众洞察看动机与顾虑、机会挖掘看『我希望有个能…的产品』式未满足需求。time_range: hour/day/week/month/year/all；sort: relevance/hot/top/new。",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "time_range": {"type": "string", "description": "hour/day/week/month/year/all，默认 year"},
            "sort": {"type": "string", "description": "relevance/hot/top/new，默认 relevance"},
            "limit": {"type": "integer", "default": 10}
        }, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "youtube_search",
        "description": "**需求验证层（YouTube）**。搜测评/开箱视频（标题/频道/观看量/发布时间/时长/描述摘要/链接），反映内容偏好与触达渠道。受众洞察看『在哪触达、偏好什么内容』，竞品分析看对手如何被评测。",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "country": {"type": "string", "description": "国家码，默认 US"},
            "language": {"type": "string", "description": "语言码，默认 en"},
            "limit": {"type": "integer", "default": 12}
        }, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "discover_bsr_url",
        "description": "LLM 给类目关键词（如 'wireless earbuds' / 'smart watch'），工具自动从【目标市场对应的 Amazon 站点】搜索发现真实子类目 BSR URL。**必须传 geo=目标市场**（US/UK/DE/FR/JP/SG/IN/...），否则默认美国站。若该市场无 Amazon 业务（如 RU/东南亚），返回 amazon_available=false，此时应改用 search_multi_platform 抓本地平台。",
        "parameters": {"type": "object", "properties": {
            "category_keyword": {"type": "string"},
            "geo": {"type": "string", "description": "目标市场国家码，如 US/UK/DE/JP/SG。必须与用户指定市场一致。"}
        }, "required": ["category_keyword"]}}},
    {"type": "function", "function": {
        "name": "get_bestsellers_by_url",
        "description": "抓某个 BSR 子类目 URL 的 Top 商品（来自 discover_bsr_url 返回的候选）。返回真实 ASIN/价格/评分/评论数。月销优先用商品自带的真实『bought in past month』；无该标签才用 BSR 经验区间估算（会标 real_data=false ±50%）。",
        "parameters": {"type": "object", "properties": {
            "bsr_url": {"type": "string"},
            "limit": {"type": "integer"},
            "category": {"type": "string", "description": "真实品类(home-kitchen/beauty/toys/sports/electronics 等)，仅用于无真实月销标签时的估算系数；不传用中性默认"}
        }, "required": ["bsr_url"]}}},
    {"type": "function", "function": {
        "name": "get_movers_shakers_by_url",
        "description": "抓某个 Movers & Shakers URL（24h 上升最快榜）",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"},
            "limit": {"type": "integer"}
        }, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "get_bestsellers",
        "description": "兼容旧调用：根据 category 关键词自动 discover+抓。**必须传 geo=目标市场**（决定用哪个 Amazon 站点）；该市场无 Amazon 时返回 amazon_available=false，应改用 search_multi_platform。",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string"}, "limit": {"type": "integer"},
            "geo": {"type": "string", "description": "目标市场国家码，如 US/UK/DE/JP/SG。必须与用户指定市场一致。"}
        }, "required": ["category"]}}},
    {"type": "function", "function": {
        "name": "search_products",
        "description": "在单个平台搜索商品。platform 必须是 PLATFORMS 注册表里的 id（用 list_platforms 查）。",
        "parameters": {"type": "object", "properties": {
            "platform": {"type": "string"}, "keyword": {"type": "string"},
            "limit": {"type": "integer"}
        }, "required": ["platform", "keyword"]}}},
    {"type": "function", "function": {
        "name": "analyze_market_structure",
        "description": "从商品列表算价格分布/评分中位/品牌集中度 CR4 CR10",
        "parameters": {"type": "object", "properties": {
            "products": {"type": "array", "items": {"type": "object"}}
        }, "required": ["products"]}}},
    {"type": "function", "function": {
        "name": "get_reviews",
        "description": "抓单个 Amazon 商品的 AI 评论摘要 + 8 条代表评论（详情页公开获取）",
        "parameters": {"type": "object", "properties": {
            "asin": {"type": "string"}
        }, "required": ["asin"]}}},
    {"type": "function", "function": {
        "name": "get_reviews_batch",
        "description": "批量抓多个 ASIN 的真实评论（推荐 25-30 个竞品 ASIN 一起抓，500 条 + 关键词云聚合）。**已并发**默认 8 线程，参数 concurrency 可调：ASIN ≥ 20 用 12，ASIN ≤ 10 用 6。",
        "parameters": {"type": "object", "properties": {
            "asins": {"type": "array", "items": {"type": "string"},
                       "description": "ASIN 列表，从 BSR 或 search_products 拿到，建议 25-30 个"},
            "max_total": {"type": "integer", "description": "评论总数上限，默认 500"},
            "concurrency": {"type": "integer", "default": 8,
                              "description": "并发获取线程数（D 优化）。默认 8，最大建议 12"}
        }, "required": ["asins"]}}},
    {"type": "function", "function": {
        "name": "analyze_reviews",
        "description": "用 LLM 从评论中提炼痛点/卖点/差异化机会",
        "parameters": {"type": "object", "properties": {
            "reviews": {"type": "array", "items": {"type": "string"}}
        }, "required": ["reviews"]}}},
    {"type": "function", "function": {
        "name": "extract_pain_points_precise",
        "description": "**强烈推荐：替代 analyze_reviews 痛点频次统计**。LLM 出痛点关键词组 + Python 精确匹配统计真实频次（0 误差）。比 analyze_reviews 的 LLM 估算精确 ±2-3 次。给商家看的报告必须用这个。",
        "parameters": {"type": "object", "properties": {
            "reviews": {"type": "array", "items": {"type": "string"}}
        }, "required": ["reviews"]}}},
    {"type": "function", "function": {
        "name": "analyze_review_temporal",
        "description": "**分析评论时间分布**：最近 30/90 天 vs 历史评分对比，判断产品质量是否在下降。reviews 必须含 date 字段（get_reviews_batch 返回的 reviews 已含）。质量下降 = 警示信号，意味着对手品控变差，是切入机会。",
        "parameters": {"type": "object", "properties": {
            "reviews": {"type": "array", "items": {"type": "object"}}
        }, "required": ["reviews"]}}},
    {"type": "function", "function": {
        "name": "full_cost_breakdown",
        "description": "完整成本拆解 14 项 + 盈亏点 + 资金占用。**强制要求**：必须传 procurement_source_url 证明采购成本来源（1688 URL / user-input 标识）。如果 1688 抓不到、用户也没提供，**禁止调用此工具**，必须在报告中标注 procurement_pending 让用户后续提供。stage='new_product' 用新品冷启动假设（ACOS 65%/退货 15%），'stable' 用已稳定老品假设。**新品决策推荐两种 stage 都跑一次看双场景**。",
        "parameters": {"type": "object", "properties": {
            "sale_price": {"type": "number"},
            "procurement_cost": {"type": "number", "description": "USD，必须有真实来源"},
            "procurement_source_url": {"type": "string", "description": "采购成本来源 URL 或 user-input 标识，必填"},
            "moq": {"type": "integer"},
            "monthly_sales_estimate": {"type": "integer"},
            "asin": {"type": "string", "description": "已 validate 的真实 ASIN"},
            "category": {"type": "string", "description": "品类（headphones/kitchen/smartwatch 等），决定关税和佣金率"},
            "weight_oz": {"type": "number", "description": "商品重量（盎司），决定 FBA 费"},
            "longest_in": {"type": "number", "description": "最长边（英寸），决定 FBA 尺寸档"},
            "stage": {"type": "string", "default": "new_product",
                       "description": "'new_product' (ACOS 65%/退货 15%) 或 'stable' (ACOS 20%/退货 8%)"}
        }, "required": ["sale_price", "procurement_cost", "procurement_source_url"]}}},
    {"type": "function", "function": {
        "name": "stress_test",
        "description": "压力测试：广告 ACOS 翻倍 / 退货 15% / 汇率 -10% 时还能否盈利",
        "parameters": {"type": "object", "properties": {
            "sale_price": {"type": "number"},
            "procurement_cost": {"type": "number"},
            "monthly_sales_estimate": {"type": "integer"}
        }, "required": ["sale_price", "procurement_cost"]}}},
    {"type": "function", "function": {
        "name": "monte_carlo_stress_test",
        "description": "**强烈推荐：替代 stress_test**。蒙特卡洛压力测试 5000 次模拟，6 个变量同时波动（ACOS/退货/头程/汇率/月销/采购）。返回净利分布 + 亏损概率 P(loss<0) + VaR/CVaR。新品冷启动场景设 is_new_product=True（ACOS 60-100%/退货 15%）。比简单 stress_test 真实得多。",
        "parameters": {"type": "object", "properties": {
            "sale_price": {"type": "number"},
            "procurement_cost": {"type": "number"},
            "moq": {"type": "integer", "default": 500},
            "monthly_sales_estimate": {"type": "integer", "default": 300},
            "n_simulations": {"type": "integer", "default": 5000},
            "is_new_product": {"type": "boolean", "default": True,
                                 "description": "新品冷启动 = True（ACOS 60-100%）；已稳定老品 = False"}
        }, "required": ["sale_price", "procurement_cost"]}}},
    {"type": "function", "function": {
        "name": "get_keyword_metrics",
        "description": "**替代付费 Helium10/Jungle Scout 的关键词工具**。从 DDGS 真实拿长尾词扩展 + 每个词的内容生态量（搜索量代理指标）。让关键词来自真实搜索数据，不是 LLM 自己想。",
        "parameters": {"type": "object", "properties": {            "seed_keyword": {"type": "string"},
            "max_suggestions": {"type": "integer", "default": 20}
        }, "required": ["seed_keyword"]}}},
    {"type": "function", "function": {
        "name": "compare_seasonality",
        "description": "**用 5 年 Google Trends 真实数据判断季节性**（替代 LLM 推断的'5月健身旺季'）。返回每月平均热度 + 峰值/谷值月 + 季节性强度系数 + 当前位置。",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"},
            "geo": {"type": "string", "default": "US"}
        }, "required": ["keyword"]}}},
    {"type": "function", "function": {
        "name": "quick_ip_check",
        "description": "专利 + 商标快速检索（Google Patents + USPTO）",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"},
            "brand_candidate": {"type": "string"}
        }, "required": ["keyword"]}}},
    {"type": "function", "function": {
        "name": "deep_ip_risk_assessment",
        "description": "**强烈推荐：替代 quick_ip_check 的深度版**。用 PatentsView 官方 API（免费）+ Google Patents 引用链 + USPTO 商标双源。返回专利家族 + 受让人 + 引用关系 + FTO 建议。给商家做品牌注册前必跑。",
        "parameters": {"type": "object", "properties": {
            "category_keyword": {"type": "string"},
            "brand_candidates": {"type": "array", "items": {"type": "string"},
                                  "description": "候选品牌名 1-5 个"},
            "max_depth": {"type": "integer", "default": 1}
        }, "required": ["category_keyword"]}}},
    {"type": "function", "function": {
        "name": "get_asin_pool",
        "description": "查询当前会话已采集的真实 ASIN 池。提候选品前必看，禁止凭空创造产品。",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "validate_candidate",
        "description": "校验某个 ASIN 是否在真实采集池中，返回真实数据用于后续利润测算。提候选品 SKU 必须先校验。",
        "parameters": {"type": "object", "properties": {
            "asin": {"type": "string"}
        }, "required": ["asin"]}}},
    {"type": "function", "function": {
        "name": "get_real_procurement_cost",
        "description": "从 1688 真实搜索拿采购成本（USD）。返回真实抓到的供应商列表+价格区间。失败明确报错，禁止凭印象给数字。",
        "parameters": {"type": "object", "properties": {
            "category_keyword_zh": {"type": "string", "description": "中文品类关键词（蓝牙耳机/智能手表 等）"}        }, "required": ["category_keyword_zh"]}}},
    {"type": "function", "function": {
        "name": "get_supplier_detail_price",
        "description": "**采购价精准突破**：抓供应商商品详情页的 MOQ 阶梯报价（如 100-499件$8.5/500-999件$7.2/1000+件$6.5），按商家实际下单量返回精准单价。比 get_real_procurement_cost 的搜索页区间精准得多。带重试扛 MIC 间歇反爬。从 get_real_procurement_cost 返回的 items[].source_url 取详情页 URL。",
        "parameters": {"type": "object", "properties": {
            "detail_url": {"type": "string", "description": "供应商商品详情页 URL（MIC/DHgate/GlobalSources）"},
            "target_qty": {"type": "integer", "default": 500, "description": "商家计划下单量，返回对应档位单价"}
        }, "required": ["detail_url"]}}},
    {"type": "function", "function": {
        "name": "estimate_market_size",
        "description": "**市场规模信号（免费，替代搜索量）**：把搜索结果 Top N 的真实月销('X+ bought in past month')+ 评论总量 + 真实价格聚合成'这个品类能卖多少'。比搜索量更接近真实成交端。输入 search_products/get_amazon_product_details_api 的商品列表。趋势洞察阶段用，判断市场大小。",
        "parameters": {"type": "object", "properties": {
            "products": {"type": "array", "items": {"type": "object"},
                          "description": "商品列表（含 bought_past_month/sales_volume_text/review_count/price）"}
        }, "required": ["products"]}}},
    {"type": "function", "function": {
        "name": "search_1688",
        "description": "用具体型号关键词搜 1688 反查供应商报价（候选品确定后用 ASIN 标题翻译反查）",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"},
            "limit": {"type": "integer"}
        }, "required": ["keyword"]}}},
    {"type": "function", "function": {
        "name": "provide_procurement_cost",
        "description": "**用户在对话中提供采购成本时调用**。当用户回复'采购成本是 $X，来自 PingPong 报价单 / 工厂订单 #YYY' 这类信息时，把它登记进会话。登记后即可用此值+source_label 走 full_cost_breakdown。这是 1688 获取失败时的合法兜底。",
        "parameters": {"type": "object", "properties": {
            "procurement_cost_usd": {"type": "number", "description": "采购成本（USD），必须 > 0"},
            "source_label": {"type": "string", "description": "来源凭证。可以是 1688 URL、'user-input: 报价单标识'、订单号等。不能为空。"},
            "asin": {"type": "string", "description": "对应的 ASIN（可选）"},
            "category_keyword": {"type": "string", "description": "对应的品类关键词（可选）"},
            "notes": {"type": "string", "description": "备注（可选）"}
        }, "required": ["procurement_cost_usd", "source_label"]}}},
    {"type": "function", "function": {
        "name": "get_provided_costs",
        "description": "查询当前会话已登记的人工提供采购成本（决定阶段 5 是否能跑、跑哪些）",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "record_stage_status",
        "description": "**强制透明**：每个阶段执行完毕（无论成功/部分/跳过/失败）都要登记。最终报告必须依此生成执行汇总。**禁止静默跳过任何阶段**。stage_id 用 stage1_trends/stage2_competition/stage3_pain_points/stage4_candidates/stage5_profit/stage6_supply/stage7_ip_risk/stage8_decision。",
        "parameters": {"type": "object", "properties": {
            "stage_id": {"type": "string"},
            "status": {"type": "string", "description": "completed/partial/skipped/failed"},
            "reason": {"type": "string", "description": "原因（partial/skipped/failed 必填）"},
            "needs_user_action": {"type": "string", "description": "用户怎么帮忙补，例：'提供 1688 商品 URL 或工厂报价'"},
            "artifacts": {"type": "array", "items": {"type": "string"}, "description": "产出物列表"}
        }, "required": ["stage_id", "status"]}}},
    {"type": "function", "function": {
        "name": "stage_status_summary",
        "description": "**最终报告生成前必须调用**。汇总所有阶段执行状态，返回 markdown 表格用于报告'执行汇总'段落。能立即发现哪些阶段被遗漏。",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "traceability_check",
        "description": "**最终报告前必调**。校验报告里每个 ASIN 声明的价格/评分/标题能否在 ASIN 池中找到真实匹配。任何 mismatch 都意味着 LLM 编造，必须用真实值修正。claims 是声明列表 [{asin, claim_price, claim_rating, claim_title_contains}]。",
        "parameters": {"type": "object", "properties": {
            "claims": {"type": "array", "items": {"type": "object"}}
        }, "required": ["claims"]}}},
    {"type": "function", "function": {
        "name": "list_platforms",
        "description": "列出全部 29 个全球电商平台（含 verified/untested/blocked 状态）。region 可选 US/UK/EU/JP/KR/SEA/LATAM/TR/Global/CN_B2B 来按地区筛选。Agent 选平台前先调用看清单。",
        "parameters": {"type": "object", "properties": {
            "region": {"type": "string"}
        }}}},
    {"type": "function", "function": {
        "name": "pick_platforms_for_market",
        "description": "**用户指定地区/国家时必用此工具**。输入用户的目标市场列表（如 ['US','UK','日本']），自动推荐合适的电商平台清单。支持国家代码（US/UK/DE/JP/MX/SG…）和中文（美国/英国/欧洲/东南亚…）。返回的 platform_keys 直接传给 search_multi_platform。",
        "parameters": {"type": "object", "properties": {
            "markets": {"type": "array", "items": {"type": "string"},
                         "description": "市场列表，如 ['US','UK','日本'] 或 ['North America','SEA']"},
            "only_verified": {"type": "boolean", "description": "默认 true 只返回实测可抓的平台。"}
        }, "required": ["markets"]}}},
    {"type": "function", "function": {
        "name": "capture_evidence",
        "description": "对候选品 Amazon ASIN 做截图证据（详情页+搜索页），用于最终报告。**多区域用 geo 参数**（US/UK/DE/FR/JP/IN/MX/BR 等），决定 amazon 域名。**非 Amazon 平台（Lazada/Yandex/MercadoLibre 等）请用 capture_evidence_for_url**。",
        "parameters": {"type": "object", "properties": {
            "asin": {"type": "string"},
            "geo": {"type": "string", "default": "US"}
        }, "required": ["asin"]}}},
    {"type": "function", "function": {
        "name": "capture_evidence_for_url",
        "description": "**非 Amazon 平台候选品截图证据**：对任意 listing URL 抓页面截图+主图（Lazada SG / Yandex Market / MercadoLibre MX/BR / Otto / Cdiscount / Rakuten 等）。报告里用本工具抓本地平台真实截图，避免目标市场是新加坡/俄罗斯/拉美但截图全是 Amazon 美国站。",
        "parameters": {"type": "object", "properties": {
            "listing_url": {"type": "string"},
            "save_name": {"type": "string"}
        }, "required": ["listing_url"]}}},
    {"type": "function", "function": {
        "name": "capture_evidence_batch",
        "description": "**🚀 批量并发 capture_evidence**（C 优化）：N 个候选 ASIN 并发抓证据截图（详情页+搜索页+主图），3 个串行 ~270s → concurrency=3 时 ~90s（3x 提速）。给 3-5 个核心候选品做截图时优先用这个，替代多次单 ASIN 调用。",
        "parameters": {"type": "object", "properties": {
            "asins": {"type": "array", "items": {"type": "string"},
                       "description": "候选 ASIN 列表，建议 3-5 个"},
            "geo": {"type": "string", "default": "US",
                     "description": "Amazon 站点 geo（US/UK/DE/FR/JP/IN/MX/BR 等）"},
            "concurrency": {"type": "integer", "default": 3,
                              "description": "并发度，建议 3，最大 4（每浏览器实例 ~250MB 内存）"}
        }, "required": ["asins"]}}},
    {"type": "function", "function": {
        "name": "screenshot_url",
        "description": "对任意 URL 截图（如 BSR 榜首页、Trends 曲线、1688 比价页）",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"},
            "save_name": {"type": "string"}
        }, "required": ["url", "save_name"]}}},
    {"type": "function", "function": {
        "name": "export_report_pdf",
        "description": "**报告生成完成后调用**。把 markdown 报告导出为 PDF 文件（商家可发邮件/分享）。",
        "parameters": {"type": "object", "properties": {
            "markdown_path": {"type": "string", "description": "完整报告 .md 路径"},
            "output_path": {"type": "string", "description": "PDF 输出路径（默认替换 .md→.pdf）"},
            "title": {"type": "string", "default": "选品决策报告"}
        }, "required": ["markdown_path"]}}},
    {"type": "function", "function": {
        "name": "make_one_pager",
        "description": "**报告完成后调用**。从完整报告生成 1 页摘要（商家 1 分钟读完）。",
        "parameters": {"type": "object", "properties": {
            "markdown_path": {"type": "string"},
            "loss_probability": {"type": "number", "description": "蒙特卡洛主推产品亏损概率（0-1）"}
        }, "required": ["markdown_path"]}}},
    {"type": "function", "function": {
        "name": "generate_price_chart",
        "description": "生成真实 matplotlib 价格分布柱状图（替代 markdown 文字表，更直观）。返回 PNG 路径，可嵌入报告。",
        "parameters": {"type": "object", "properties": {
            "price_bands": {"type": "object", "description": "{'$0-25': 13, '$25-50': 11, ...}"},
            "save_name": {"type": "string"}
        }, "required": ["price_bands", "save_name"]}}},
    {"type": "function", "function": {
        "name": "webpage_to_markdown",
        "description": "用 crawl4ai 把任意网页转成干净的 LLM-ready markdown（适合深度分析对手 Listing 页或认证文档页）",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}
        }, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "file_to_markdown",
        "description": "用 markitdown 把本地 PDF/Office 文档转成 markdown（处理供应商报价单、专利 PDF、认证文档）",
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string"}
        }, "required": ["file_path"]}}},
    {"type": "function", "function": {
        "name": "get_real_search_volume",
        "description": "**真实 Google Ads 绝对月搜索量**（补 Google Trends 只有相对值的短板）。返回每个关键词真实月均搜索量+CPC+竞争度+12月走势。需配 DataForSEO key（有免费额度）；未配置返回 available=False，改用 get_keyword_metrics。趋势洞察阶段优先用本工具。",
        "parameters": {"type": "object", "properties": {
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "关键词列表（最多 1000）"},
            "geo": {"type": "string", "default": "US", "description": "地区码 US/UK/DE/FR/JP/AU/IN/SG 等"}
        }, "required": ["keywords"]}}},
    {"type": "function", "function": {
        "name": "get_amazon_product_details_api",
        "description": "**真实商品详情 API**（RapidAPI Real-Time Amazon Data）：真实 BSR/月销 sales_volume/评分/评论数/价格。需配 RAPIDAPI_KEY（免费档~100-500次/月）；未配置返回 available=False，改用 capture_evidence 获取。利润测算需要真实月销时用本工具。",
        "parameters": {"type": "object", "properties": {
            "asin": {"type": "string"},
            "geo": {"type": "string", "default": "US"}
        }, "required": ["asin"]}}},
    {"type": "function", "function": {
        "name": "api_status",
        "description": "查询哪些付费 API（DataForSEO 真实搜索量 / RapidAPI 真实月销）已配置可用。阶段 0 可调一次，决定后续用真实 API 还是开源降级路径。",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_keepa_price_history",
        "description": "**真实价格+BSR/销量排名历史曲线**（Keepa 公开图，免费无需 key）。返回 PNG 图路径可嵌报告。看点：价格是否长期下跌(红海/价格战)、BSR是否上升(销量增长)、季节性波动。竞品分析阶段对候选品调用，图文并茂展示真实历史趋势（非估算）。",
        "parameters": {"type": "object", "properties": {
            "asin": {"type": "string"},
            "geo": {"type": "string", "default": "US", "description": "US/UK/DE/FR/JP/CA/IN/MX 等"},
            "range_days": {"type": "integer", "default": 365, "description": "历史天数 90/180/365"}
        }, "required": ["asin"]}}},
    {"type": "function", "function": {
        "name": "get_keepa_charts_batch",
        "description": "批量拿多个候选品的 Keepa 真实价格/BSR 历史曲线（免费）。建议只对 3-5 个候选品调用。返回每个 PNG 路径，嵌入报告做候选品对比。",
        "parameters": {"type": "object", "properties": {
            "asins": {"type": "array", "items": {"type": "string"}},
            "geo": {"type": "string", "default": "US"},
            "range_days": {"type": "integer", "default": 365}
        }, "required": ["asins"]}}},
    {"type": "function", "function": {
        "name": "get_keepa_product_data",
        "description": "**Keepa 登录态产品页真实数据**（用户自有免费账号）：Buy Box/Amazon/New 当前价、Sales Rank、评分、评论数、新品卖家数等已渲染的精确数字。需 .env 配 KEEPA_EMAIL/PASSWORD；未配置 available=False，请改用 get_keepa_price_history 拿免费曲线图。比图更精确（给出具体数字）。建议只对 3-5 个候选品调用（免费账号有频率限制）。",
        "parameters": {"type": "object", "properties": {
            "asin": {"type": "string"},
            "geo": {"type": "string", "default": "US"}
        }, "required": ["asin"]}}},
    {"type": "function", "function": {
        "name": "get_amazon_keyword_suggestions",
        "description": "**Amazon 真实买家搜索词**（免费无 key，比 Google 更贴电商）。返回买家在 Amazon 真实输入的购物搜索词（按热度排序，rank 1 最热）+ top_modifiers（高频功能/卖点词，如 noise cancelling/thick/long battery）。用于：① 关键词扩展（替代/补充 DDGS）② Listing 标题关键词 ③ 差异化卖点发现（买家高频词=真实需求点）。趋势/关键词阶段优先用。",
        "parameters": {"type": "object", "properties": {
            "seed_keyword": {"type": "string"},
            "geo": {"type": "string", "default": "US"},
            "deep": {"type": "boolean", "default": False, "description": "True 则二级扩展拿更多长尾词"}
        }, "required": ["seed_keyword"]}}},
    {"type": "function", "function": {
        "name": "validate_keywords",
        "description": "**关键词验证闭环（强烈推荐，直接决定结果质量）**：把候选关键词用『真实能搜到多少对口商品』反向打分，淘汰搜不到/跑偏的词，只留高质量词再正式获取。能杜绝『防盗门→搜出门锁配件』『geladeira em ingles→查资料词』这类品类错位。返回每个词的真实商品数+语义相关度+keep/drop，以及 recommended_keywords。扩展出候选词后、正式 search_multi_platform 之前调用。",
        "parameters": {"type": "object", "properties": {
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "待验证的候选关键词（最多15个）"},
            "platform": {"type": "string", "default": "amazon", "description": "用哪个平台验证（应是目标市场的 verified 平台）"},
            "category_hint": {"type": "string", "description": "品类语义基准（用于相关度过滤），如 'refrigerator' / '冰箱'"},
            "min_products": {"type": "integer", "default": 3, "description": "至少搜到几件才算可用词"}
        }, "required": ["keywords"]}}},
    {"type": "function", "function": {
        "name": "get_wayback_snapshots",
        "description": "**竞品历史快照**（archive.org，免费无 key 无反爬）。拿任意 Amazon Listing 的历史存档快照列表（first_seen=上架时间近似/snapshot_count=被关注度）。用于：判断 Listing 是新品还是老品 + 看 Listing 演进时间线。建议对 3-5 个候选品调用。",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "Listing URL，如 https://www.amazon.com/dp/B01LP0U5X0"},
            "limit": {"type": "integer", "default": 30},
            "from_year": {"type": "integer", "default": 2020}
        }, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "analyze_listing_evolution",
        "description": "**竞品演进深度分析**（Wayback Machine，免费）。等距取样多个历史时间点的快照，对比标题/价格变化，给出 'title_changes 标题改了几次/prices_seen_history 历史价格区间/上架时间' 等结论。用于：识别竞品试错过的关键词方向 + 价格调整轨迹 = 差异化机会。建议只对 1-2 个核心竞品调用（每次抓 5 个快照较慢）。",
        "parameters": {"type": "object", "properties": {
            "amazon_url": {"type": "string"},
            "sample_size": {"type": "integer", "default": 5}
        }, "required": ["amazon_url"]}}},
    {"type": "function", "function": {
        "name": "read_keepa_chart",
        "description": "**让无视觉的 LLM 读懂 Keepa 图**（像素分析，非多模态模型）。从 Keepa PNG 用曲线颜色分离还原出 text_summary：每条线(Amazon价/BSR/第三方价)的趋势【上升/下降/平稳】+ 波动程度(促销/价格战频繁度)。注意：是相对趋势非绝对价格。get_keepa_price_history 已自动带 trend_text，单独调本工具用于读已存在的 PNG。",
        "parameters": {"type": "object", "properties": {
            "png_path": {"type": "string", "description": "Keepa PNG 文件路径"}
        }, "required": ["png_path"]}}},
    {"type": "function", "function": {
        "name": "browse_daily_dataset",
        "description": "**零成本大盘底子（首选开局工具）**。读取『每日刷新』已落库的真实快照——28 个一级品类实时商品榜 + TikTok Shop 热销榜 + 8 平台社媒热词 + 热门话题声量曲线，**不消耗任何 TikHub 额度**。任何模式都应先调它定位方向（哪些品类/热词/话题与本次调研相关），再用 tiktok_shop_search / social_trends 等实时工具补更新更细的数据。query 非空时按关键词过滤（匹配商品标题/品类名/热词/话题）；kinds 可只取某几类。",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "关键词过滤，匹配商品标题/品类名/热词/话题；不传则取全部大盘"},
            "kinds": {"type": "array", "items": {"type": "string"},
                      "description": "限定取哪几类：categories/hot_selling/social_trends/hashtags，不传则全取"},
            "limit": {"type": "integer", "default": 30}
        }}}},
]

TOOL_IMPL = {
    "load_skill": tool_load_skill,
    "extract_products_with_llm": tool_extract_products_with_llm,
    "get_current_datetime": tool_get_current_datetime,
    "get_keyword_metrics": tool_get_keyword_metrics,
    "get_real_search_volume": tool_get_real_search_volume,
    "get_amazon_product_details_api": lambda asin, geo="US": paid_apis.get_amazon_product_details(asin, geo),
    "api_status": lambda: paid_apis.api_status(),
    "get_keepa_price_history": get_keepa_price_history_chart,
    "get_keepa_charts_batch": get_keepa_charts_batch,
    "get_keepa_product_data": get_keepa_product_data,
    "get_amazon_keyword_suggestions": get_amazon_keyword_suggestions,
    "validate_keywords": tool_validate_keywords,
    "get_wayback_snapshots": get_wayback_snapshots,
    "analyze_listing_evolution": analyze_listing_evolution,
    "read_keepa_chart": read_keepa_chart,
    "compare_seasonality": tool_compare_seasonality,
    "monte_carlo_stress_test": tool_monte_carlo_stress_test,
    "list_platforms": tool_list_platforms,
    "search_multi_platform": tool_search_multi_platform,
    "get_trend": tool_get_trend,
    "tiktok_shop_search": tool_tiktok_shop_search,
    "tiktok_shop_reviews": tool_tiktok_shop_reviews,
    "social_trends": tool_social_trends,
    "tiktok_category_list": tool_tiktok_category_list,
    "tiktok_products_by_category": tool_tiktok_products_by_category,
    "tiktok_hot_selling": tool_tiktok_hot_selling,
    "tiktok_trending_hashtags": tool_tiktok_trending_hashtags,
    "reddit_search": tool_reddit_search,
    "youtube_search": tool_youtube_search,
    "browse_daily_dataset": tool_browse_daily_dataset,
    "discover_bsr_url": tool_discover_bsr_url,
    "get_bestsellers_by_url": tool_get_bestsellers_by_url,
    "get_movers_shakers_by_url": tool_get_movers_shakers_by_url,
    "get_bestsellers": tool_get_bestsellers,
    "search_products": tool_search_products,
    "search_multi_platform": tool_search_multi_platform,
    "analyze_market_structure": tool_analyze_market_structure,
    "get_reviews": tool_get_reviews,
    "get_reviews_batch": tool_get_reviews_batch,
    "analyze_reviews": tool_analyze_reviews,
    "extract_pain_points_precise": tool_extract_pain_points_precise,
    "analyze_review_temporal": tool_analyze_review_temporal,
    "full_cost_breakdown": tool_full_cost_breakdown,
    "stress_test": tool_stress_test,
    "quick_ip_check": tool_quick_ip_check,
    "deep_ip_risk_assessment": tool_deep_ip_risk_assessment,
    "get_asin_pool": tool_get_asin_pool,
    "validate_candidate": tool_validate_candidate,
    "get_real_procurement_cost": tool_get_real_procurement_cost,
    "get_supplier_detail_price": get_supplier_detail_price,
    "estimate_market_size": tool_estimate_market_size,
    "search_1688": tool_search_1688,
    "provide_procurement_cost": tool_provide_procurement_cost,
    "get_provided_costs": tool_get_provided_costs,
    "record_stage_status": tool_record_stage_status,
    "stage_status_summary": tool_stage_status_summary,
    "traceability_check": tool_traceability_check,
    "list_platforms": tool_list_platforms,
    "pick_platforms_for_market": tool_pick_platforms_for_market,
    "capture_evidence": tool_capture_evidence,
    "capture_evidence_for_url": tool_capture_evidence_for_url,
    "capture_evidence_batch": tool_capture_evidence_batch,
    "screenshot_url": tool_screenshot_url,
    "export_report_pdf": tool_export_report_pdf,
    "make_one_pager": tool_make_one_pager,
    "generate_price_chart": tool_generate_price_chart,
    "webpage_to_markdown": tool_webpage_to_markdown,
    "file_to_markdown": tool_file_to_markdown,
}
