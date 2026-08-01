"""
趋势层：Google Trends（pytrends）+ 关键词扩展（thefuzz）
"""
from __future__ import annotations
import os
import pandas as pd
from loguru import logger


# ════ urllib3 2.x 兼容补丁（pytrends 用了已废弃的 method_whitelist）════
def _patch_urllib3_retry():
    try:
        from urllib3.util.retry import Retry
        if hasattr(Retry, "_kw_patched"):
            return  # 只 patch 一次
        _orig_init = Retry.__init__
        import inspect
        sig = inspect.signature(_orig_init)
        has_allowed_methods = "allowed_methods" in sig.parameters
        
        def _patched_init(self, *args, **kwargs):
            # method_whitelist → allowed_methods（urllib3>=2）
            # 老版本 urllib3（无 allowed_methods）则原样保留 method_whitelist 透传
            if "method_whitelist" in kwargs:
                mw = kwargs.pop("method_whitelist")
                if has_allowed_methods:
                    if "allowed_methods" not in kwargs:
                        kwargs["allowed_methods"] = mw
                else:
                    kwargs["method_whitelist"] = mw
            return _orig_init(self, *args, **kwargs)
        
        Retry.__init__ = _patched_init
        Retry._kw_patched = True
    except Exception as e:
        logger.warning(f"urllib3 patch fail: {e}")


_patch_urllib3_retry()


# ScraperAPI 代理网关（pytrends 代理回退走这里）
_SCRAPERAPI_PROXY_HOST = "proxy-server.scraperapi.com"
_SCRAPERAPI_PROXY_PORT = 8001


def _scraperapi_proxy_reachable() -> bool:
    """
    自动探测 ScraperAPI 代理网关连通性（3 秒 TCP connect 预检）。
    沙箱/受限网络下网关不可达时快速跳过，避免 pytrends 请求级长超时挂起。

    环境变量：
    - TRENDS_PROXY_CHECK_TIMEOUT: 预检超时秒数，默认 3
    - TRENDS_PROXY_FALLBACK: 兼容旧人工开关。显式设为 0/false/off 时强制禁用回退；
      其他情况（含未设置）一律走自动探测，不再依赖人工开关。
    """
    manual = os.getenv("TRENDS_PROXY_FALLBACK", "").strip().lower()
    if manual in ("0", "false", "off", "no"):
        logger.info("TRENDS_PROXY_FALLBACK=off，人工禁用 ScraperAPI 代理回退")
        return False
    timeout = float(os.getenv("TRENDS_PROXY_CHECK_TIMEOUT", "3"))
    from modules.scraper import tcp_reachable
    ok = tcp_reachable(_SCRAPERAPI_PROXY_HOST, _SCRAPERAPI_PROXY_PORT, timeout=timeout)
    if not ok:
        logger.warning(
            f"ScraperAPI 代理网关 {_SCRAPERAPI_PROXY_HOST}:{_SCRAPERAPI_PROXY_PORT} "
            f"{timeout}s 内不可达，跳过代理回退（快速失败）")
    return ok


def _scraper_api_trends(keyword: str, geo: str = "US", timeframe: str = "today 12-m") -> pd.DataFrame:
    """ScraperAPI 代理回退：通过 ScraperAPI 代理 pytrends 请求绕过 IP 封锁。
    当 pytrends 直连失败时（如 Render 服务器 IP 被封）走此路径。
    先做 3 秒连通性预检，不通直接跳过（不再无限挂起）。"""
    key = os.getenv("SCRAPERAPI_KEY", "")
    if not key:
        return pd.DataFrame()
    if not _scraperapi_proxy_reachable():
        return pd.DataFrame()
    try:
        from pytrends.request import TrendReq
        proxy_url = f"http://scraperapi:{key}@{_SCRAPERAPI_PROXY_HOST}:{_SCRAPERAPI_PROXY_PORT}"
        py = TrendReq(
            hl="en-US", tz=360, retries=1, backoff_factor=0.3,
            timeout=(8, 15),
            requests_args={"proxies": {"http": proxy_url, "https": proxy_url}}
        )
        py.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo, gprop="")
        df = py.interest_over_time()
        if df is not None and not df.empty:
            if "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])
            logger.info(f"趋势(ScraperAPI代理) OK：{keyword} ({len(df)} 行)")
            return df
    except Exception as e:
        logger.warning(f"ScraperAPI proxy trends 失败: {str(e)[:120]}")
    return pd.DataFrame()


def get_keyword_trend(keywords: list[str], timeframe: str = "today 12-m",
                      geo: str = "US") -> pd.DataFrame:
    """近一年关键词趋势（0-100 相对热度）。直连失败时回退 ScraperAPI 抓取。"""
    # 第一步：尝试 pytrends 直连（缩短超时避免阻塞）
    try:
        from pytrends.request import TrendReq
        py = TrendReq(hl="en-US", tz=360, retries=1, backoff_factor=0.3, timeout=(5, 12))
        py.build_payload(keywords[:5], cat=0, timeframe=timeframe, geo=geo, gprop="")
        df = py.interest_over_time()
        if df is not None and not df.empty:
            if "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])
            logger.info(f"趋势 OK：{list(df.columns)} ({len(df)} 行)")
            return df
    except Exception as e:
        logger.warning(f"pytrends 直连失败: {str(e)[:100]}，尝试 ScraperAPI 回退...")

    # 第二步：回退 ScraperAPI 抓取（Render 等云服务器 IP 被 Google 封锁时）
    if keywords:
        df = _scraper_api_trends(keywords[0], geo=geo, timeframe=timeframe)
        if not df.empty:
            return df

    return pd.DataFrame()


def get_related_keywords(seed: str, candidates: list[str], top_n: int = 10) -> list[dict]:
    """用 thefuzz 模糊匹配 + 评分，从候选词里找最相关的 N 个"""
    try:
        from thefuzz import fuzz, process
        scored = process.extract(seed, candidates, scorer=fuzz.token_set_ratio, limit=top_n)
        return [{"keyword": k, "score": s} for k, s in scored]
    except Exception as e:
        logger.warning(f"thefuzz fail: {e}")
        return []


def expand_seasonal_pattern(df: pd.DataFrame) -> dict:
    """从趋势数据提取季节性高峰（哪几个月最旺）"""
    if df.empty:
        return {}
    out = {}
    for col in df.columns:
        s = df[col]
        # 按月聚合
        monthly = s.groupby(s.index.month).mean().sort_values(ascending=False)
        out[col] = {
            "peak_months": [int(m) for m in monthly.head(3).index.tolist()],
            "low_months": [int(m) for m in monthly.tail(3).index.tolist()],
            "peak_value": float(monthly.iloc[0]),
            "low_value": float(monthly.iloc[-1]),
        }
    return out


if __name__ == "__main__":
    df = get_keyword_trend(["wireless earbuds", "bluetooth headphones"])
    print(df.tail())
    print("\nseasonal:", expand_seasonal_pattern(df))
