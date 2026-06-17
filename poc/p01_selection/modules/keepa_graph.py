"""
Keepa 免费价格/BSR 历史曲线（公开 graph PNG 端点，无需 API key）

实测结论（2026-06）：
- Keepa 结构化 JSON 数据走 Cloudflare Turnstile + WebSocket，scraper 拿不到（需付费 API）
- 但 Keepa 公开的「价格历史曲线图」PNG 端点 graph.keepa.com/pricehistory.png
  无需 key、无 Cloudflare 拦截、稳定返回真实 PNG（实测 3/3 成功）
- 这给我们：真实的【价格历史 + BSR/销量排名历史】趋势曲线，可嵌入报告

用途：
- 补『竞品分析』：看候选品价格是否在跌（红海信号）、BSR 趋势（销量在涨还是跌）
- 比单点价格更有信息量：能看到促销周期、价格战、季节波动

数据形式是图（不是数字），所以：
- 报告里直接嵌入图给商家看（图文并茂，商家一眼看懂趋势）
- 不会编造数字（图是 Keepa 官方真实渲染）
"""
from __future__ import annotations
import os
from pathlib import Path
from loguru import logger
import requests

from modules.scraper import DEFAULT_PROXY

# domain code（Keepa 标准）：1=com 2=co.uk 3=de 4=fr 5=co.jp 6=ca 8=it 9=es 10=in 11=com.mx
_DOMAIN_CODE = {
    "US": 1, "UK": 2, "GB": 2, "DE": 3, "FR": 4, "JP": 5, "CA": 6,
    "IT": 8, "ES": 9, "IN": 10, "MX": 11, "AU": 12,
}

_OUT_DIR = Path(__file__).resolve().parents[1] / "reports" / "keepa_charts"


def get_keepa_price_history_chart(asin: str, geo: str = "US",
                                   range_days: int = 365,
                                   use_proxy: bool = True) -> dict:
    """
    拿 Keepa 真实价格 + BSR/销量排名历史曲线（PNG，免费无 key）。
    
    返回 {ok, asin, geo, png_path, markdown, source_url, _real_data}
    range_days: 历史天数（90/180/365；越长越能看季节性和价格战）
    """
    asin = (asin or "").strip().upper()
    if not asin or len(asin) < 8:
        return {"ok": False, "error": "invalid_asin", "asin": asin}
    domain = _DOMAIN_CODE.get(geo.upper(), 1)
    # amazon=1 价格曲线 / new=1 第三方新品 / salesrank=1 BSR(销量排名)曲线
    url = (f"https://graph.keepa.com/pricehistory.png?"
           f"asin={asin}&domain={domain}&salesrank=1&amazon=1&new=1&used=0"
           f"&range={range_days}&width=720&height=300&title=1")
    logger.info(f"📈 Keepa 历史曲线 {asin} (geo={geo}, {range_days}天)")

    proxies = {"http": DEFAULT_PROXY, "https": DEFAULT_PROXY} if use_proxy else None
    try:
        r = requests.get(url, proxies=proxies, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    except Exception as e:
        return {"ok": False, "error": str(e)[:150], "asin": asin}

    if r.status_code != 200 or r.content[:8] != b"\x89PNG\r\n\x1a\n":
        return {"ok": False, "error": f"not_png_status_{r.status_code}",
                "asin": asin, "bytes": len(r.content)}
    if len(r.content) < 2000:
        # 太小通常是「无数据」占位图
        return {"ok": False, "error": "empty_or_no_data_chart",
                "asin": asin, "bytes": len(r.content)}

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = _OUT_DIR / f"keepa_{asin}_{geo}.png"
    png_path.write_bytes(r.content)

    # 像素分析把曲线还原成趋势文本（让无视觉的 DeepSeek 也能"读"图）
    chart_text = None
    try:
        from modules.keepa_chart_reader import read_keepa_chart
        cr = read_keepa_chart(str(png_path))
        if cr.get("ok"):
            chart_text = cr.get("text_summary")
    except Exception:
        pass

    # Keepa 公开页面链接（人工可点开看交互式图）
    keepa_page = f"https://keepa.com/#!product/{domain}-{asin}"
    return {
        "ok": True,
        "asin": asin, "geo": geo, "range_days": range_days,
        "png_path": str(png_path),
        "png_bytes": len(r.content),
        "source_url": keepa_page,
        "graph_url": url,
        "markdown": f"![Keepa 价格/BSR 历史曲线 {asin}](keepa_charts/{png_path.name})",
        "trend_text": chart_text,  # 像素分析得到的趋势文本（DeepSeek 可读）
        "_source": "Keepa 公开价格历史曲线（graph.keepa.com，免费无 key）",
        "_real_data": True,
        "_LLM_NOTE": ("图(PNG)给商家看；trend_text 是像素分析还原的趋势(涨跌/波动)，"
                      "LLM 分析请用 trend_text，不要凭空描述图。"
                      "绝对当前数字用 get_amazon_product_details_api。"),
        "_note": ("真实价格+第三方新品价+BSR销量排名历史曲线，供商家肉眼看趋势。"
                  "数据为 Keepa 官方渲染，非估算。"),
    }


def get_keepa_charts_batch(asins: list[str], geo: str = "US",
                           range_days: int = 365, max_charts: int = 5) -> dict:
    """批量拿候选品的 Keepa 历史曲线（免费档建议只对 3-5 个候选品调）。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    asins = [a for a in asins if a][:max_charts]
    charts, failed = [], []

    def _one(a):
        return get_keepa_price_history_chart(a, geo, range_days)

    with ThreadPoolExecutor(max_workers=min(len(asins), 4) or 1) as ex:
        futs = {ex.submit(_one, a): a for a in asins}
        for f in as_completed(futs):
            r = f.result()
            (charts if r.get("ok") else failed).append(r)

    return {
        "geo": geo, "requested": len(asins),
        "success_count": len(charts), "charts": charts,
        "failed": [{"asin": x.get("asin"), "error": x.get("error")} for x in failed],
        "_source": "Keepa 公开历史曲线（免费）",
        "_real_data": True,
    }


if __name__ == "__main__":
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    try:
        from proxy.ensure_proxy import ensure_proxy_alive
        ensure_proxy_alive(verbose=False)
    except Exception:
        pass
    r = get_keepa_price_history_chart("B0CHWRXH8B", "US")
    print(json.dumps({k: v for k, v in r.items() if k != "markdown"}, ensure_ascii=False, indent=2))
