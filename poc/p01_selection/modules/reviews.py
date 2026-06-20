"""
Amazon 评论数据获取（适配 2026 反爬政策）

事实：
- /product-reviews/<ASIN> 全量评论页 → 强制登录态，无登录跳 Sign-In 页
- /dp/<ASIN> 详情页 → 公开可抓，底部嵌入 8 条 top reviews + Customers say 摘要 + 关键词云

策略（不靠登录）：
1. 单 ASIN 详情页抓 8 条公开评论 + Customers say 摘要
2. 多 ASIN 横向覆盖（5-10 个竞品 × 8 条 = 40-80 条评论） → 给 LLM 做痛点聚类够用
3. 关键词云：抓"Customers say"区域的 popular topics（这是 Amazon AI 自动提炼的痛点关键词）

DOM 适配 2026 新版：data-hook="reviewTitle"/"reviewText"（驼峰命名）
"""
from __future__ import annotations
from typing import Optional
import os, re
from loguru import logger
from bs4 import BeautifulSoup

from modules.scraper import fetch, DEFAULT_PROXY


def _fetch_dp_with_review_loaded(asin: str, use_proxy: bool = True,
                                  max_retries: int = 2) -> Optional[str]:
    """
    专用：抓详情页 + 滚动到评论区触发懒加载。
    
    速度优化（v2）：
    - 完整性阈值从 600KB 降到 350KB（评论区其实 250-400KB 就够提取 8 条公开评论 + Customers say）
    - 重试 3→2 次，滚动点位精简，每次 sleep 缩短
    - 单 ASIN 从 ~40s 降到 ~18s
    """
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            from botasaurus_driver import Driver
            kw = {"headless": True, "block_images": True}
            if use_proxy:
                kw["proxy"] = DEFAULT_PROXY
            driver = Driver(**kw)
            try:
                driver.google_get(f"https://www.amazon.com/dp/{asin}", bypass_cloudflare=True)
                driver.sleep(2.5)
                # 精简滚动点位（4 个足够触发评论懒加载）
                for y in [4000, 8000, 13000, 17000]:
                    driver.run_js(f"window.scrollTo(0, {y})")
                    driver.sleep(1.0)
                # 强制等待评论区出现
                try:
                    driver.run_js("""
                      const el = document.querySelector('#reviewsMedley')
                              || document.querySelector('[data-hook=\"top-customer-reviews-widget\"]')
                              || document.querySelector('#cr-summarization-container');
                      if (el) el.scrollIntoView({behavior:'instant', block:'start'});
                    """)
                    driver.sleep(1.5)
                except Exception:
                    pass
                html = driver.page_html
                size = len(html or "")
                # 完整性校验（降到 350KB；且只要含评论 DOM 标记就接受）
                has_review_dom = html and ("data-hook=\"review\"" in html
                                            or "cr-summarization" in html
                                            or "aspect-summary" in html)
                if size < 350000 and not has_review_dom:
                    last_err = f"page_too_small_{size}_attempt{attempt}"
                    logger.warning(f"  ASIN={asin} attempt {attempt}: {last_err}, retrying...")
                    continue
                logger.info(f"  ASIN={asin} OK ({size} chars)")
                return html
            finally:
                try: driver.close()
                except Exception: pass
        except Exception as e:
            last_err = str(e)[:160]
            logger.warning(f"  ASIN={asin} attempt {attempt} fail: {last_err}")
    logger.warning(f"_fetch_dp giving up after {max_retries}: {last_err}")
    return None


def _extract_customers_say_keywords(soup: BeautifulSoup) -> list[dict]:
    """
    提取详情页 Customers say 的方面关键词云（含提及次数 + 情感）。
    2026 版 Amazon 用 data-testid，不是老的 data-hook。
    每个 aspect 是 'Sound quality(3.6K)' 这种格式 + 情感图标。
    """
    out = []
    aspect_summaries = soup.select('[data-testid="aspect-summary"]')
    for aspect_node in aspect_summaries:
        # label 含名字 + 提及数
        label_node = aspect_node.select_one('[data-testid="aspect-label"]')
        if not label_node:
            continue
        label_text = label_node.get_text(" ", strip=True)
        # "Sound quality(3.6K)" → 拆出名字 + 次数
        import re
        m = re.match(r'^(.+?)\s*\(([\d.]+[KMk]?)\)\s*$', label_text)
        if m:
            aspect = m.group(1).strip()
            mentions_raw = m.group(2)
            # 转数字（3.6K → 3600）
            mult = 1
            if mentions_raw.endswith(("K", "k")):
                mult = 1000
                mentions_raw = mentions_raw[:-1]
            elif mentions_raw.endswith(("M", "m")):
                mult = 1_000_000
                mentions_raw = mentions_raw[:-1]
            try:
                mentions = int(float(mentions_raw) * mult)
            except Exception:
                mentions = None
        else:
            aspect = label_text
            mentions = None

        # 情感（positive / negative / mixed）
        sentiment = "neutral"
        if aspect_node.select_one('[data-testid="aspect-icon-positive"]'):
            sentiment = "positive"
        elif aspect_node.select_one('[data-testid="aspect-icon-negative"]'):
            sentiment = "negative"
        elif aspect_node.select_one('[data-testid="aspect-icon-mixed"]'):
            sentiment = "mixed"

        out.append({"aspect": aspect, "mentions": mentions, "sentiment": sentiment})
    return out


def _extract_ai_summary(soup: BeautifulSoup) -> str:
    """提取 AI Customers Say 段落摘要（2026 版用 data-testid='overall-summary'）"""
    el = soup.select_one('[data-testid="overall-summary"]')
    if el:
        # overall-summary 里可能含很多嵌套，取第一段干净文字
        for child in el.descendants:
            if hasattr(child, "get_text"):
                continue
            text = str(child).strip()
            if 50 < len(text) < 2000:
                return text
        # 兜底：拿全文，截断到第一段句号后
        text = el.get_text(" ", strip=True)
        if text:
            # 切掉后面 aspect list 等噪声
            for stop in [" AI Generated", " Select to learn", " Customers like",
                          " Customers find these"]:
                pass  # 不切开头
            # 找第一段（句号结束）
            sentences = re.split(r'(?<=[.!?])\s+', text)
            collected = []
            total = 0
            for s in sentences:
                if "AI Generated" in s or "Select to" in s or "Read more" in s:
                    break
                collected.append(s)
                total += len(s)
                if total > 800:
                    break
            return " ".join(collected)
    # 兜底：找 Customers say 的兄弟段落
    h = soup.find("h3", string=lambda s: s and "Customers say" in s)
    if h and h.parent:
        text = h.parent.get_text(" ", strip=True)
        if text.startswith("Customers say"):
            text = text[len("Customers say"):].strip(" |")
        sentences = re.split(r'(?<=[.!?])\s+', text)
        out = []
        for s in sentences:
            if any(stop in s for stop in ["AI Generated", "Select to", "Read more"]):
                break
            out.append(s)
            if sum(len(x) for x in out) > 600:
                break
        return " ".join(out).strip()
    return ""


def _extract_reviews(soup: BeautifulSoup) -> list[dict]:
    """从详情页提取 review 卡片"""
    samples = []
    for c in soup.select("[data-hook='review']"):
        body_node = (c.select_one("[data-hook='reviewText']")
                     or c.select_one("[data-hook='review-body']")
                     or c.select_one("[data-hook='reviewTextContainer']"))
        title_node = (c.select_one("[data-hook='reviewTitle']")
                      or c.select_one("[data-hook='review-title']")
                      or c.select_one("h5"))
        rating_node = (c.select_one("i[data-hook='review-star-rating'] span")
                       or c.select_one("span.a-icon-alt"))
        date_node = c.select_one("[data-hook='review-date']")
        if not body_node:
            continue
        rating = None
        if rating_node:
            try:
                rating = float(rating_node.get_text(strip=True).split()[0])
            except Exception:
                pass
        body = body_node.get_text(" ", strip=True)
        for noise in ["Brief content visible, double tap to read full content.",
                      "Full content visible, double tap to read brief content."]:
            body = body.replace(noise, "").strip()
        samples.append({
            "rating": rating,
            "title": title_node.get_text(" ", strip=True) if title_node else "",
            "body": body[:600],
            "date": date_node.get_text(strip=True) if date_node else "",
        })
    return samples


def get_product_review_summary(asin: str, use_proxy: bool = True) -> dict:
    """单 ASIN 完整评论 + 摘要"""
    if not asin:
        return {"error": "no asin"}
    logger.info(f"📝 详情页评论 ASIN={asin}")
    html = _fetch_dp_with_review_loaded(asin, use_proxy=use_proxy)
    if not html or len(html) < 250000:
        return {"asin": asin, "error": f"page incomplete ({len(html or '')} bytes)",
                "source_url": f"https://www.amazon.com/dp/{asin}"}

    soup = BeautifulSoup(html, "lxml")
    out = {"asin": asin, "source_url": f"https://www.amazon.com/dp/{asin}",
           "fetched_chars": len(html)}

    t = soup.select_one("#productTitle")
    if t:
        out["title"] = t.get_text(" ", strip=True)[:120]

    # 评分 / 评论总数
    r = soup.select_one("span[data-hook='rating-out-of-text']") or soup.select_one("span.a-icon-alt")
    if r:
        try:
            out["rating"] = float(r.get_text(strip=True).split()[0])
        except Exception:
            pass

    rc = soup.select_one("a[data-hook='see-all-reviews-link-foot']") \
         or soup.select_one("#acrCustomerReviewText")
    if rc:
        txt = rc.get_text(strip=True)
        digits = "".join(c for c in txt if c.isdigit())
        if digits:
            out["total_reviews"] = int(digits)

    out["ai_summary"] = _extract_ai_summary(soup)
    out["aspects"] = _extract_customers_say_keywords(soup)
    out["sample_reviews"] = _extract_reviews(soup)
    out["sample_count"] = len(out["sample_reviews"])

    # 兼容老字段
    out["keywords"] = [{"keyword": a["aspect"], "sentiment": a["sentiment"]}
                        for a in out["aspects"]]

    logger.info(f"  ASIN={asin} reviews={out['sample_count']} aspects={len(out['aspects'])} "
                f"summary={'有' if out['ai_summary'] else '无'}")
    return out


def get_reviews_batch(asins: list[str], use_proxy: bool = True,
                      max_total: int = 260, concurrency: int = 8) -> dict:
    """
    多 ASIN 横向批量获取（并发，绕过登录限制的合法方式）。
    返回聚合结果：所有评论 + 关键词云聚合 + 每个 ASIN 概览。
    
    并发获取大幅提速：20 个 ASIN 串行需 ~14 分钟，并发 6 个只需 ~3 分钟。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    all_reviews: list[dict] = []
    # aspect 真实诉求聚合：保留 Amazon 官方的真实提及次数（不是简单计数），并按销量加权
    aspect_agg: dict[str, dict] = {}   # aspect → {mentions(真实加权), products, sentiments}
    per_asin: list[dict] = []
    
    def _fetch_one(asin: str):
        try:
            s = get_product_review_summary(asin, use_proxy=use_proxy)
            return asin, s, None
        except Exception as e:
            return asin, None, str(e)[:200]

    # 销量权重映射（调用方在 asins 同序传 weights 时按销量加权；否则等权=1）
    weight_map = {}
    if isinstance(asins, list) and asins and isinstance(asins[0], dict):
        # 支持传 [{asin, weight}] 形式
        weight_map = {a["asin"]: a.get("weight", 1) for a in asins if a.get("asin")}
        asin_list = [a["asin"] for a in asins if a.get("asin")]
    else:
        asin_list = list(asins)
    
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(_fetch_one, a): a for a in asin_list}
        for fut in as_completed(futures):
            if len(all_reviews) >= max_total:
                for f in futures:
                    if not f.done():
                        f.cancel()
                break
            asin, s, err = fut.result()
            if err or (s and s.get("error")):
                per_asin.append({"asin": asin, "error": err or s.get("error")})
                continue
            total_rev = s.get("total_reviews") or 0
            per_asin.append({
                "asin": asin, "title": s.get("title", "")[:80],
                "rating": s.get("rating"), "total_reviews": total_rev,
                "samples": s.get("sample_count", 0),
            })
            for r in s.get("sample_reviews", []):
                r["from_asin"] = asin
                all_reviews.append(r)
            # ── 关键：聚合 aspect 的真实提及次数（Amazon 跨全部评论的官方汇总）──
            # 权重 = 该商品评论总数（评论越多的商品，其诉求越能代表大众；无则按 1）
            w = weight_map.get(asin) or (total_rev if total_rev else 1)
            for a in s.get("aspects", []):
                name = (a.get("aspect") or "").strip().lower()
                if not name:
                    continue
                m = a.get("mentions")  # Amazon 官方真实提及次数
                slot = aspect_agg.setdefault(name, {
                    "aspect": a.get("aspect"), "real_mentions": 0,
                    "weighted_mentions": 0.0, "product_count": 0,
                    "positive": 0, "negative": 0, "mixed": 0, "neutral": 0,
                    "has_real_count": False,
                })
                slot["product_count"] += 1
                if isinstance(m, int) and m > 0:
                    slot["real_mentions"] += m          # 真实提及次数累加
                    slot["weighted_mentions"] += m      # 真实次数本身已是权重
                    slot["has_real_count"] = True
                else:
                    slot["weighted_mentions"] += w      # 无真实次数时用销量/评论数代理
                sent = a.get("sentiment", "neutral")
                slot[sent] = slot.get(sent, 0) + 1
    
    # 按"真实加权提及"排序的诉求云（代表性远好于简单计数）
    demand_cloud = sorted(aspect_agg.values(), key=lambda x: -x["weighted_mentions"])
    for d in demand_cloud:
        d["weighted_mentions"] = round(d["weighted_mentions"], 1)

    # ── 代表性自检：覆盖了多少商品、多少评论体量，够不够代表该品类 ──
    ok_asins = [p for p in per_asin if not p.get("error")]
    total_reviews_covered = sum(p.get("total_reviews") or 0 for p in ok_asins)
    real_count_aspects = sum(1 for d in demand_cloud if d["has_real_count"])
    representativeness = {
        "products_covered": len(ok_asins),
        "products_requested": len(asin_list),
        "total_reviews_behind_aspects": total_reviews_covered,  # 这些 aspect 背后的真实评论体量
        "sample_reviews_collected": len(all_reviews),
        "aspects_with_real_counts": real_count_aspects,
        "verdict": (
            f"✅ 覆盖 {len(ok_asins)} 个商品、背后约 {total_reviews_covered} 条真实评论的官方诉求汇总，"
            "代表性较好" if len(ok_asins) >= 10 and total_reviews_covered >= 1000 else
            f"⚠️ 仅覆盖 {len(ok_asins)} 个商品 / {total_reviews_covered} 条评论体量，"
            "代表性偏弱——建议扩到 Top 15-20 个商品、评论体量≥1000 再下结论"
        ),
    }

    # 关键词云（兼容旧字段，保留简单计数）
    simple_kw: dict[str, int] = {}
    for d in demand_cloud:
        simple_kw[d["aspect"]] = d["product_count"]

    return {
        "asins_count": len(asin_list),
        "total_reviews": len(all_reviews),
        "per_asin": per_asin,
        "reviews": all_reviews[:max_total],
        "demand_cloud": demand_cloud[:30],   # 真实加权的用户诉求云（新，主用）
        "keyword_cloud": [{"word": k, "freq": v} for k, v in
                          sorted(simple_kw.items(), key=lambda x: -x[1])[:30]],  # 兼容旧
        "representativeness": representativeness,
        "_note": ("demand_cloud 按 Amazon 官方真实提及次数(或销量/评论体量)加权排序，"
                  "代表该品类大众诉求；representativeness 给出样本覆盖度自检。"),
    }


def reviews_to_text_list(items, max_chars_each: int = 400) -> list[str]:
    """转纯文本列表给 LLM 用"""
    out = []
    if isinstance(items, dict):
        if items.get("ai_summary"):
            out.append(f"[AI Summary] {items['ai_summary'][:max_chars_each]}")
        for r in items.get("sample_reviews", items.get("reviews", [])):
            t = (r.get("title", "") + " - " + r.get("body", "")).strip(" -")
            if not t:
                continue
            if len(t) > max_chars_each:
                t = t[:max_chars_each] + "..."
            if r.get("rating"):
                t = f"[{r['rating']}★] {t}"
            out.append(t)
    elif isinstance(items, list):
        for r in items:
            t = (r.get("title", "") + " - " + r.get("body", "")).strip(" -")
            if t:
                if len(t) > max_chars_each:
                    t = t[:max_chars_each] + "..."
                if r.get("rating"):
                    t = f"[{r['rating']}★] {t}"
                out.append(t)
    return out


# 兼容旧调用
def get_reviews(asin: str, n_pages: int = 1, star_filter: Optional[str] = None,
                use_proxy: bool = True) -> list[dict]:
    return [get_product_review_summary(asin, use_proxy=use_proxy)]
