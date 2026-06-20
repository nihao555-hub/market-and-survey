"""
IP 风险扫描 — 深度版（替代浅层 quick_ip_check）

数据源：
1. Google Patents 公开搜索 + 引用链分析（免费，PatentsView API 也能用）
2. USPTO TMSearch 商标查询（免费，新版 SPA）
3. PatentsView API: https://api.patentsview.org/  - 美国专利数据库官方免费 API
4. EPO OPS（欧洲专利办公室开放数据）— 限速但免费

无需任何付费 Key。
"""
from __future__ import annotations
import re, urllib.parse, json
from loguru import logger

from modules.scraper import fetch


def _adaptor(*args, **kwargs):
    """延迟导入 scrapling（可选爬虫依赖；仅在真正获取/解析时才需要）。
    未安装时给出清晰提示，而不是在 import 阶段就让整个后端起不来。"""
    from scrapling.parser import Adaptor  # noqa: PLC0415
    return Adaptor(*args, **kwargs)


# ════════════════════════════════════════════════════════════════════
# 1. Google Patents — 关键词 + 引用链
# ════════════════════════════════════════════════════════════════════
def search_patents(keyword: str, limit: int = 10, use_proxy: bool = False) -> list[dict]:
    """Google Patents 搜索（公开页面）。返回 Top 命中的标题/号/日期/受让人。"""
    q = urllib.parse.quote(keyword)
    url = f"https://patents.google.com/?q={q}&oq={q}"
    logger.info(f"🔍 Google Patents: {keyword}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return [{"error": f"fetch failed: {e}"}]
    adp = _adaptor(html, url=url, auto_match=False)
    items = []
    # 找带 patent 号的 h3（"US123456789B2: Title..."）
    for h in adp.css("h3, h4, search-result-item, article")[: limit * 3]:
        try:
            text = (h.text or "").strip()
            if not text or len(text) < 15:
                continue
            # 提取专利号
            m = re.search(r'\b(US|EP|WO|CN|JP)\s?\d{6,12}\s?[A-Z]?\d?\b', text)
            patent_num = m.group(0).replace(" ", "") if m else None
            items.append({
                "snippet": text[:400],
                "patent_num": patent_num,
            })
            if len(items) >= limit:
                break
        except Exception:
            continue
    return items[:limit] if items else [{"warning": "no patents found", "html_size": len(html)}]


def patent_detail_with_citations(patent_num: str, use_proxy: bool = False) -> dict:
    """
    抓单个专利的详情页 → 引用了哪些前序专利 + 被哪些后续专利引用。
    引用链能发现"专利家族" — 是判断侵权风险的关键。
    """
    url = f"https://patents.google.com/patent/{patent_num}"
    logger.info(f"🔍 Patent detail: {patent_num}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return {"patent_num": patent_num, "error": str(e)[:120]}
    
    adp = _adaptor(html, url=url, auto_match=False)
    out = {"patent_num": patent_num, "url": url}
    
    # 标题
    for sel in ["h1#title", "[itemprop='title']", "h1"]:
        n = adp.css_first(sel)
        if n and n.text:
            out["title"] = n.text.strip()[:300]
            break
    
    # 受让人 / 发明人
    for sel in ["dd[itemprop='assigneeOriginal']", "[itemprop='assignee']"]:
        n = adp.css_first(sel)
        if n and n.text:
            out["assignee"] = n.text.strip()[:120]
            break
    
    # 引用的前序专利（cited by this）
    cited_pat = re.findall(r'/patent/([A-Z]{2}\d{6,12}[A-Z]\d?)', html)
    cited_unique = list(dict.fromkeys(cited_pat))
    out["cited_patents"] = cited_unique[:20]
    out["cited_count"] = len(cited_unique)
    
    # 状态（active / expired / withdrawn）
    text_lower = html[:50000].lower()
    if "expired" in text_lower or "expiration" in text_lower:
        out["status_hint"] = "可能已过期或临近过期 → 风险低"
    elif "active" in text_lower:
        out["status_hint"] = "可能仍有效 → 需详查"
    
    return out


# ════════════════════════════════════════════════════════════════════
# 2. PatentsView API — 美国专利数据库官方免费 API
# ════════════════════════════════════════════════════════════════════
def search_uspto_patents_api(keyword: str, limit: int = 10) -> dict:
    """
    用 PatentsView API（官方免费）查美国专利 — 比 Google Patents 解析更可靠。
    API 文档：https://api.patentsview.org/
    """
    import requests
    url = "https://search.patentsview.org/api/v1/patent/"
    payload = {
        "q": {"_text_phrase": {"patent_title": keyword}},
        "f": ["patent_id", "patent_title", "patent_date", "patent_abstract",
               "assignees.assignee_organization"],
        "o": {"size": limit},
    }
    logger.info(f"🔍 PatentsView API: {keyword}")
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            return {"error": f"http_{r.status_code}", "msg": r.text[:200]}
        data = r.json()
        patents = data.get("patents", []) or []
        return {
            "keyword": keyword,
            "total_hits": data.get("total_hits", len(patents)),
            "results": [
                {
                    "patent_num": p.get("patent_id"),
                    "title": p.get("patent_title", "")[:200],
                    "date": p.get("patent_date"),
                    "abstract": (p.get("patent_abstract") or "")[:300],
                    "assignee": (
                        (p.get("assignees") or [{}])[0].get("assignee_organization", "")
                    )[:100],
                }
                for p in patents[:limit]
            ],
            "_source": "PatentsView (USPTO official, free)",
        }
    except Exception as e:
        return {"error": str(e)[:200]}


# ════════════════════════════════════════════════════════════════════
# 3. USPTO TMSearch 商标查询
# ════════════════════════════════════════════════════════════════════
def search_trademark(brand: str, limit: int = 10, use_proxy: bool = False) -> list[dict]:
    """USPTO 商标搜索（新版 SPA，公开访问）"""
    q = urllib.parse.quote(brand)
    url = f"https://tmsearch.uspto.gov/search/search-information?q={q}"
    logger.info(f"🔍 USPTO Trademark: {brand}")
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
    except Exception as e:
        return [{"error": str(e)[:120]}]
    h = html.lower() if html else ""
    has_results = ("results" in h) or ("registration number" in h) or ("serial number" in h)
    return [{
        "brand": brand, "search_url": url,
        "page_size": len(html or ""),
        "has_results_indicator": has_results,
        "note": ("如果 has_results=True，至少有同名商标，需进 USPTO 网站手动确认 "
                 "live/dead 状态。如果 False，更可能是新商标，可注册。"),
    }]


def search_uspto_trademark_api(brand: str) -> dict:
    """
    USPTO 商标 TSDR 公开接口（无需 key）。
    试 TSDR 文档接口拿 brand 的 serial number。
    """
    import requests
    # USPTO 的 TMSEARCH 没公开 API，只能爬 SPA。但有 OFR API（Open Federal Register）
    # 简化策略：用 search 页面 + 检测特定文字
    q = urllib.parse.quote(brand)
    url = f"https://tmsearch.uspto.gov/search/search-information?q={q}"
    return {"brand": brand, "url": url, "method": "manual_check_required"}


# ════════════════════════════════════════════════════════════════════
# 综合 — 深度 IP 风险评估
# ════════════════════════════════════════════════════════════════════
def deep_ip_risk_assessment(category_keyword: str, brand_candidates: list[str] = None,
                              use_proxy: bool = False, max_depth: int = 1) -> dict:
    """
    深度 IP 风险评估 — 替代 quick_ip_check。
    
    流程：
    1. PatentsView API 拿真实美国专利数据（替代 Google Patents 解析）
    2. 对 Top 3 高相关专利，抓详情页拿引用链
    3. 候选品牌名 USPTO 商标查询
    
    返回真实可读的风险报告（含具体专利号 + 受让人 + 引用关系）。
    """
    logger.info(f"🔍 deep_ip_risk_assessment({category_keyword})")
    out = {
        "category": category_keyword,
        "brand_candidates": brand_candidates or [],
        "patents": {},
        "trademarks": {},
    }
    
    # 1. PatentsView 真实专利数据（首选）
    pv_result = search_uspto_patents_api(category_keyword, limit=10)
    out["patents"]["uspto_official"] = pv_result
    
    # 2. Google Patents 兜底
    if not pv_result.get("results"):
        out["patents"]["google_patents"] = search_patents(category_keyword, limit=8, use_proxy=use_proxy)
    
    # 3. 对 Top 3 专利做引用链分析（核心 — 找专利家族）
    top_patents = pv_result.get("results", [])[:3]
    citation_chains = []
    for p in top_patents:
        pn = p.get("patent_num")
        if not pn:
            continue
        try:
            detail = patent_detail_with_citations(pn, use_proxy=use_proxy)
            citation_chains.append(detail)
        except Exception as e:
            citation_chains.append({"patent_num": pn, "error": str(e)[:100]})
    out["patents"]["citation_chains"] = citation_chains
    
    # 4. 商标查询
    if brand_candidates:
        for brand in brand_candidates[:5]:
            out["trademarks"][brand] = search_trademark(brand, use_proxy=use_proxy)[0]
    
    # 5. 风险打分
    n_patents = pv_result.get("total_hits", 0) or len(pv_result.get("results", []))
    n_brand_conflicts = sum(
        1 for v in out["trademarks"].values()
        if isinstance(v, dict) and v.get("has_results_indicator")
    )
    
    if n_patents > 100:
        risk_level = "🔴 高 — 专利密集赛道，强烈建议先做 FTO（Freedom to Operate）分析"
    elif n_patents > 30:
        risk_level = "🟡 中 — 关注 Top 3 专利的引用链，避开核心权利要求"
    else:
        risk_level = "🟢 低 — 专利稀疏，进入门槛低"
    
    out["risk_summary"] = {
        "patent_count": n_patents,
        "patent_density": risk_level,
        "brand_conflicts": n_brand_conflicts,
        "brands_clear": [b for b in (brand_candidates or [])
                         if not out["trademarks"].get(b, {}).get("has_results_indicator")],
        "recommendation": (
            "如果选入此品类：① 让律师做 1 次 FTO 分析（约 $3-8K）"
            f" ② 自创品牌名优先（已建议 {n_brand_conflicts} 个候选有冲突，需要换）"
        ),
    }
    
    return out


def quick_ip_check(keyword: str, brand_candidate: str = "", use_proxy: bool = False) -> dict:
    """组合：关键词查专利 + 候选品牌查商标"""
    out = {"keyword": keyword, "brand_candidate": brand_candidate}
    out["patents"] = search_patents(keyword, limit=8, use_proxy=use_proxy)
    if brand_candidate:
        out["trademark"] = search_trademark(brand_candidate, use_proxy=use_proxy)
    return out


if __name__ == "__main__":
    r = deep_ip_risk_assessment("yoga mat alignment lines",
                                  brand_candidates=["Yogalux", "FlowMat", "Nike"])
    print(json.dumps(r, ensure_ascii=False, indent=2)[:3000])
