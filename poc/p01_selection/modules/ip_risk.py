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
import os, re, time, urllib.parse, json
from loguru import logger

from modules.scraper import fetch, proxy_reachable


# ════ 重试 / 代理自动探测（国内网络三接口常全灭，给 1 次指数退避重试）════
_IP_RISK_RETRIES = int(os.getenv("IP_RISK_RETRIES", "1"))          # 每接口重试次数
_IP_RISK_BACKOFF = [float(x) for x in os.getenv("IP_RISK_BACKOFF", "2,5").split(",") if x.strip()]
_IP_RISK_HTTP_TIMEOUT = float(os.getenv("IP_RISK_HTTP_TIMEOUT", "15"))


def _with_retry(fn, retries: int = None, backoff: list = None):
    """指数退避重试（默认 1 次重试，等待 2s/5s，环境变量可调）。"""
    retries = _IP_RISK_RETRIES if retries is None else retries
    backoff = _IP_RISK_BACKOFF if backoff is None else backoff
    last = None
    for attempt in range(retries + 1):
        if attempt > 0:
            wait = backoff[min(attempt - 1, len(backoff) - 1)]
            logger.info(f"🔄 IP 接口重试 第 {attempt}/{retries} 次（退避 {wait}s）")
            time.sleep(wait)
        try:
            return fn()
        except Exception as e:
            last = e
            logger.warning(f"IP 接口第 {attempt + 1} 次尝试失败: {str(e)[:120]}")
    raise last


def us_proxy_auto() -> bool:
    """探测 US_PROXY：配置了且 3 秒 TCP 预检通过才自动走代理。"""
    px = os.getenv("US_PROXY", "").strip()
    if not px:
        return False
    timeout = float(os.getenv("IP_RISK_PROXY_CHECK_TIMEOUT", "3"))
    ok = proxy_reachable(px, timeout=timeout)
    if ok:
        logger.info(f"US_PROXY 探测可用（{timeout}s 预检通过），IP 查询自动走代理")
    else:
        logger.warning(f"US_PROXY 已配置但 {timeout}s 内不可达，IP 查询走直连")
    return ok


def _adaptor(*args, **kwargs):
    """延迟导入 scrapling（可选爬虫依赖；仅在真正获取/解析时才需要）。
    未安装时给出清晰提示，而不是在 import 阶段就让整个后端起不来。"""
    from scrapling.parser import Adaptor  # noqa: PLC0415
    return Adaptor(*args, **kwargs)


def _css1(node, sel: str):
    """scrapling css_first 兼容：css() 返回列表，取第一个或 None。"""
    results = node.css(sel)
    return results[0] if results else None


# ════════════════════════════════════════════════════════════════════
# 1. Google Patents — 关键词 + 引用链
# ════════════════════════════════════════════════════════════════════
def search_patents(keyword: str, limit: int = 10, use_proxy: bool = False) -> list[dict]:
    """Google Patents 搜索（公开页面）。返回 Top 命中的标题/号/日期/受让人。
    带 1 次指数退避重试（IP_RISK_RETRIES/IP_RISK_BACKOFF 可调）。"""
    q = urllib.parse.quote(keyword)
    url = f"https://patents.google.com/?q={q}&oq={q}"
    logger.info(f"🔍 Google Patents: {keyword}")
    try:
        html = _with_retry(lambda: fetch(url, use_proxy=use_proxy, force_browser=True))
    except Exception as e:
        return [{"error": f"fetch failed after retries: {e}"}]
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
        n = _css1(adp, sel)
        if n and n.text:
            out["title"] = n.text.strip()[:300]
            break
    
    # 受让人 / 发明人
    for sel in ["dd[itemprop='assigneeOriginal']", "[itemprop='assignee']"]:
        n = _css1(adp, sel)
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
# PatentsView 端点按顺序尝试（不可达时自动切下一个），环境变量可覆盖/追加备用端点
_PATENTSVIEW_ENDPOINTS = [u.strip() for u in os.getenv(
    "PATENTSVIEW_ENDPOINTS",
    "https://search.patentsview.org/api/v1/patent/",
).split(",") if u.strip()]


def search_uspto_patents_api(keyword: str, limit: int = 10) -> dict:
    """
    用 PatentsView API（官方免费）查美国专利 — 比 Google Patents 解析更可靠。
    API 文档：https://api.patentsview.org/
    多端点顺序尝试 + 每端点 1 次指数退避重试；全部失败返回结构化 attempts。
    """
    import requests
    payload = {
        "q": {"_text_phrase": {"patent_title": keyword}},
        "f": ["patent_id", "patent_title", "patent_date", "patent_abstract",
               "assignees.assignee_organization"],
        "o": {"size": limit},
    }
    logger.info(f"🔍 PatentsView API: {keyword}")
    attempts = []
    for url in _PATENTSVIEW_ENDPOINTS:
        def _do(url=url):
            r = requests.post(url, json=payload, timeout=_IP_RISK_HTTP_TIMEOUT)
            if r.status_code != 200:
                raise RuntimeError(f"http_{r.status_code}: {r.text[:120]}")
            return r.json()
        try:
            data = _with_retry(_do)
        except Exception as e:
            attempts.append({"endpoint": url, "error": str(e)[:200]})
            continue
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
            "_endpoint": url,
            "_attempts": attempts,  # 成功前失败过的端点记录
        }
    return {"error": "all_endpoints_failed", "attempts": attempts}


# ════════════════════════════════════════════════════════════════════
# 3. USPTO TMSearch 商标查询
# ════════════════════════════════════════════════════════════════════
def search_trademark(brand: str, limit: int = 10, use_proxy: bool = False) -> list[dict]:
    """USPTO 商标搜索（新版 SPA，公开访问）"""
    q = urllib.parse.quote(brand)
    url = f"https://tmsearch.uspto.gov/search/search-information?q={q}"
    logger.info(f"🔍 USPTO Trademark: {brand}")
    try:
        html = _with_retry(lambda: fetch(url, use_proxy=use_proxy, force_browser=True))
    except Exception as e:
        return [{"error": f"fetch failed after retries: {str(e)[:120]}"}]
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
                              use_proxy: bool = None, max_depth: int = 1) -> dict:
    """
    深度 IP 风险评估 — 替代 quick_ip_check。

    流程：
    1. PatentsView API 拿真实美国专利数据（替代 Google Patents 解析）
    2. 对 Top 3 高相关专利，抓详情页拿引用链
    3. 候选品牌名 USPTO 商标查询

    use_proxy=None（默认）时自动探测 US_PROXY：配置了且 3 秒 TCP 预检通过才走代理。
    全部接口失败时输出 failure_diagnosis（结构化原因 + 「配置 US_PROXY 后重试」补救提示）。

    返回真实可读的风险报告（含具体专利号 + 受让人 + 引用关系）。
    """
    logger.info(f"🔍 deep_ip_risk_assessment({category_keyword})")
    eff_proxy = us_proxy_auto() if use_proxy is None else use_proxy
    out = {
        "category": category_keyword,
        "brand_candidates": brand_candidates or [],
        "patents": {},
        "trademarks": {},
        "us_proxy": {
            "configured": bool(os.getenv("US_PROXY", "").strip()),
            "used": eff_proxy,
        },
    }
    iface_errors: dict[str, str] = {}  # 接口名 → 结构化错误原因

    # 1. PatentsView 真实专利数据（首选）
    pv_result = search_uspto_patents_api(category_keyword, limit=10)
    out["patents"]["uspto_official"] = pv_result
    if not pv_result.get("results"):
        iface_errors["patentsview"] = json.dumps(
            pv_result.get("attempts") or pv_result.get("error"), ensure_ascii=False)[:300]

    # 2. Google Patents 兜底
    if not pv_result.get("results"):
        gp = search_patents(category_keyword, limit=8, use_proxy=eff_proxy)
        out["patents"]["google_patents"] = gp
        gp_err = [x.get("error") for x in gp if isinstance(x, dict) and x.get("error")]
        if gp_err or not gp:
            iface_errors["google_patents"] = (gp_err[0] if gp_err else "no_results")[:300]
    
    # 3. 对 Top 3 专利做引用链分析（核心 — 找专利家族）
    top_patents = pv_result.get("results", [])[:3]
    citation_chains = []
    for p in top_patents:
        pn = p.get("patent_num")
        if not pn:
            continue
        try:
            detail = patent_detail_with_citations(pn, use_proxy=eff_proxy)
            citation_chains.append(detail)
        except Exception as e:
            citation_chains.append({"patent_num": pn, "error": str(e)[:100]})
    out["patents"]["citation_chains"] = citation_chains

    # 4. 商标查询
    if brand_candidates:
        tm_errs = []
        for brand in brand_candidates[:5]:
            tm = search_trademark(brand, use_proxy=eff_proxy)[0]
            out["trademarks"][brand] = tm
            if tm.get("error"):
                tm_errs.append(tm["error"])
        if tm_errs and len(tm_errs) == len(out["trademarks"]):
            iface_errors["uspto_tmsearch"] = tm_errs[0][:300]

    # 5. 全灭诊断：专利两接口都没拿到数据 且 商标接口也全失败
    patents_dead = (not pv_result.get("results")) and "google_patents" in iface_errors
    tm_dead = (not brand_candidates) or ("uspto_tmsearch" in iface_errors)
    if patents_dead and tm_dead:
        out["failure_diagnosis"] = {
            "reason": "all_ip_interfaces_unreachable",
            "interfaces": iface_errors,
            "us_proxy": out["us_proxy"],
            "remedy": (
                "PatentsView / Google Patents / USPTO 三接口在当前网络均不可达。"
                "请配置 US_PROXY 环境变量（美国出口代理，如 "
                "http://user:pass@host:port）后重试本阶段——检测到 US_PROXY 可用时会自动优先走代理；"
                "或稍后重试（已内置 1 次指数退避重试 2s/5s，可用 IP_RISK_RETRIES 调增）。"
                "**禁止在报告中编造专利/商标结论**，如实标注'IP 风险未核查'。"
            ),
        }
    
    # 5. 风险打分
    n_patents = pv_result.get("total_hits", 0) or len(pv_result.get("results", []))
    n_brand_conflicts = sum(
        1 for v in out["trademarks"].values()
        if isinstance(v, dict) and v.get("has_results_indicator")
    )
    
    if out.get("failure_diagnosis"):
        risk_level = "⚪ 未知 — IP 接口全部不可达，未核查（禁止据此判断低风险）"
    elif n_patents > 100:
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


def quick_ip_check(keyword: str, brand_candidate: str = "", use_proxy: bool = None) -> dict:
    """组合：关键词查专利 + 候选品牌查商标。use_proxy=None 时自动探测 US_PROXY。"""
    eff_proxy = us_proxy_auto() if use_proxy is None else use_proxy
    out = {"keyword": keyword, "brand_candidate": brand_candidate}
    out["patents"] = search_patents(keyword, limit=8, use_proxy=eff_proxy)
    if brand_candidate:
        out["trademark"] = search_trademark(brand_candidate, use_proxy=eff_proxy)
    return out


if __name__ == "__main__":
    r = deep_ip_risk_assessment("yoga mat alignment lines",
                                  brand_candidates=["Yogalux", "FlowMat", "Nike"])
    print(json.dumps(r, ensure_ascii=False, indent=2)[:3000])
