"""
趋势层：Google Trends（pytrends）+ 关键词扩展（thefuzz）
"""
from __future__ import annotations
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
            # method_whitelist → allowed_methods
            if "method_whitelist" in kwargs:
                mw = kwargs.pop("method_whitelist")
                if has_allowed_methods and "allowed_methods" not in kwargs:
                    kwargs["allowed_methods"] = mw
            return _orig_init(self, *args, **kwargs)
        
        Retry.__init__ = _patched_init
        Retry._kw_patched = True
    except Exception as e:
        logger.warning(f"urllib3 patch fail: {e}")


_patch_urllib3_retry()


def get_keyword_trend(keywords: list[str], timeframe: str = "today 12-m",
                      geo: str = "US") -> pd.DataFrame:
    """近一年关键词趋势（0-100 相对热度）"""
    try:
        from pytrends.request import TrendReq
        py = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=0.5)
        py.build_payload(keywords[:5], cat=0, timeframe=timeframe, geo=geo, gprop="")
        df = py.interest_over_time()
        if df is None or df.empty:
            return pd.DataFrame()
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])
        logger.info(f"趋势 OK：{list(df.columns)} ({len(df)} 行)")
        return df
    except Exception as e:
        logger.warning(f"pytrends 失败: {str(e)[:120]}")
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
