"""
Keepa 登录态产品页数据获取（免费账号即可）

实测结论（2026-06）：
- 未登录：botasaurus 能过 Cloudflare，但 Keepa SPA 只渲染空壳，数据 WebSocket 需登录态才推送
- 登录后：产品页的价格统计表/BSR/buybox/卖家数等**全部渲染进 DOM**，可直接抓

策略：
1. 用 botasaurus（bypass_cloudflare）登录一次 → 复用同一 driver 会话抓多个 ASIN
2. 等数据渲染（统计表出现）后抓 DOM 文本 + 解析数字
3. cookie 持久化，下次免登录

注意：
- 这是用**用户自己的免费 Keepa 账号**，合规读取页面已渲染的数据（不破解、不逆向）
- 免费账号有频率限制，建议只对候选品（3-5 个）抓，不要批量刷
- 缺账号时 available()=False，自动降级到 keepa_graph 的免费 PNG 曲线
"""
from __future__ import annotations
import os, re, json, time, threading
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

KEEPA_EMAIL = os.getenv("KEEPA_EMAIL", "").strip()
KEEPA_PASSWORD = os.getenv("KEEPA_PASSWORD", "").strip()

from modules.scraper import DEFAULT_PROXY

_DOMAIN_CODE = {"US": 1, "UK": 2, "GB": 2, "DE": 3, "FR": 4, "JP": 5, "CA": 6,
                "IT": 8, "ES": 9, "IN": 10, "MX": 11, "AU": 12}

# 单例 driver（登录一次复用，避免反复触发 CF + 登录）
_driver = None
_driver_lock = threading.Lock()
_logged_in = False
_PROFILE_DIR = Path(__file__).resolve().parents[1] / "data" / "keepa_profile"


def keepa_session_available() -> bool:
    return bool(KEEPA_EMAIL and KEEPA_PASSWORD)


def _get_logged_in_driver():
    """获取已登录的 botasaurus driver（懒加载 + 复用）。"""
    global _driver, _logged_in
    if _driver is not None and _logged_in:
        return _driver
    from botasaurus_driver import Driver
    clean = DEFAULT_PROXY.replace("http://", "").replace("https://", "")
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _driver = Driver(headless=True, proxy=clean)
    try:
        # 打开登录页
        _driver.google_get("https://keepa.com/#!registration", bypass_cloudflare=True)
        _driver.sleep(6)
        # 过 CF
        for _ in range(5):
            txt = _driver.run_js("return document.body.innerText") or ""
            if "security verification" not in txt.lower() and "ray id" not in txt.lower():
                break
            _driver.sleep(5)
        # 填登录表单（Keepa 登录字段 id: username / password）
        try:
            _driver.run_js(f"""
                var u = document.querySelector('#username') || document.querySelector('input[name="username"]') || document.querySelector('input[type="email"]');
                var p = document.querySelector('#password') || document.querySelector('input[name="password"]') || document.querySelector('input[type="password"]');
                if (u) {{ u.value = {json.dumps(KEEPA_EMAIL)}; u.dispatchEvent(new Event('input',{{bubbles:true}})); }}
                if (p) {{ p.value = {json.dumps(KEEPA_PASSWORD)}; p.dispatchEvent(new Event('input',{{bubbles:true}})); }}
            """)
            _driver.sleep(1)
            # 点登录按钮
            _driver.run_js("""
                var btn = document.querySelector('#submitLogin')
                       || Array.from(document.querySelectorAll('button,input[type=submit]'))
                            .find(b => /log\\s*in|sign\\s*in|login/i.test(b.innerText||b.value||''));
                if (btn) btn.click();
            """)
            _driver.sleep(8)
        except Exception as e:
            logger.warning(f"[keepa_session] 登录表单填写失败: {str(e)[:120]}")
        # 校验是否登录成功（页面应出现 logout/account 或不再有 login 表单）
        body = _driver.run_js("return document.body.innerText") or ""
        if "logout" in body.lower() or "log out" in body.lower() or "my account" in body.lower():
            _logged_in = True
            logger.info("[keepa_session] ✅ 登录成功")
        else:
            # 即使没检测到 logout 标记，也尝试继续（有些账号页措辞不同）
            _logged_in = True
            logger.warning("[keepa_session] ⚠ 未明确检测到登录标记，仍尝试获取")
        return _driver
    except Exception as e:
        logger.error(f"[keepa_session] driver 初始化失败: {str(e)[:160]}")
        try: _driver.close()
        except Exception: pass
        _driver = None
        _logged_in = False
        raise


def _parse_keepa_stats(text: str) -> dict:
    """从渲染后的产品页可见文本里解析关键统计数据。"""
    stats = {}
    # 价格类：Buy Box / Amazon / New 的 current / avg
    patterns = {
        "buybox_current": r'Buy Box[^$]{0,40}\$\s?([\d,]+\.\d{2})',
        "amazon_current": r'Amazon[^$]{0,40}\$\s?([\d,]+\.\d{2})',
        "new_current": r'New[^$]{0,40}\$\s?([\d,]+\.\d{2})',
        "sales_rank_current": r'Sales Rank[^\d]{0,40}([\d,]{2,})',
        "rating": r'Rating[^\d]{0,20}(\d\.\d)',
        "review_count": r'Review Count[^\d]{0,20}([\d,]{1,})',
        "offer_count_new": r'New Offer Count[^\d]{0,20}([\d,]{1,})',
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(1).replace(",", "")
            try:
                stats[key] = float(val) if "." in val else int(val)
            except Exception:
                stats[key] = m.group(1)
    # 所有出现的价格（供参考）
    stats["_all_prices"] = re.findall(r'\$\s?[\d,]+\.\d{2}', text)[:30]
    return stats


def get_keepa_product_data(asin: str, geo: str = "US") -> dict:
    """
    抓 Keepa 登录态产品页的渲染数据（价格统计/BSR/评分/卖家数）。
    缺账号 → available=False，调用方降级到 keepa_graph PNG。
    """
    asin = (asin or "").strip().upper()
    if not keepa_session_available():
        return {"available": False, "reason": "no_keepa_account",
                "_hint": "在 .env 填 KEEPA_EMAIL/PASSWORD（免费账号），或用 get_keepa_price_history 拿免费曲线图"}
    if not asin or len(asin) < 8:
        return {"available": True, "ok": False, "error": "invalid_asin"}

    domain = _DOMAIN_CODE.get(geo.upper(), 1)
    url = f"https://keepa.com/#!product/{domain}-{asin}"
    with _driver_lock:
        try:
            d = _get_logged_in_driver()
            d.get(url) if hasattr(d, "get") else d.google_get(url, bypass_cloudflare=True)
            d.sleep(8)
            # 等统计数据渲染（轮询可见文本里出现价格符号）
            text = ""
            for _ in range(6):
                text = d.run_js("return document.body.innerText") or ""
                if text.count("$") >= 2 and ("Sales Rank" in text or "Buy Box" in text):
                    break
                d.sleep(4)
            stats = _parse_keepa_stats(text)
            ok = bool(stats.get("_all_prices"))
            return {
                "available": True, "ok": ok, "asin": asin, "geo": geo,
                "source_url": url,
                "stats": stats,
                "raw_text_len": len(text),
                "_source": "Keepa 登录态产品页（用户自有免费账号，读取已渲染 DOM）",
                "_real_data": True,
                "_note": "价格/BSR/评分等为 Keepa 页面已渲染的真实数据" if ok else
                         "页面已加载但未解析到价格，可能数据加载中或该 ASIN 无历史",
            }
        except Exception as e:
            return {"available": True, "ok": False, "asin": asin, "error": str(e)[:200]}


def close_keepa_session():
    global _driver, _logged_in
    if _driver is not None:
        try: _driver.close()
        except Exception: pass
    _driver = None
    _logged_in = False


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    try:
        from proxy.ensure_proxy import ensure_proxy_alive
        ensure_proxy_alive(verbose=False)
    except Exception:
        pass
    print("available:", keepa_session_available())
    if keepa_session_available():
        r = get_keepa_product_data("B0CHWRXH8B", "US")
        print(json.dumps(r, ensure_ascii=False, indent=2))
        close_keepa_session()
