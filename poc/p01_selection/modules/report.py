"""
展示层（PoC 版）：用 plotly 出 HTML 报告 + 控制台总结。
后续接入 Superset/Metabase 时，只需把 SQLite 改 Postgres 即可。
"""

from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
from loguru import logger


def make_report(
    products_df: pd.DataFrame,
    trend_df: pd.DataFrame,
    suggestions: list[dict],
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = out_dir / f"report_{ts}.html"

    parts: list[str] = ["<html><head><meta charset='utf-8'><title>选品报告</title>",
                        "<style>body{font-family:Arial,Helvetica,sans-serif;margin:24px;max-width:1100px;}",
                        "table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ddd;padding:8px;font-size:14px;}",
                        "th{background:#f5f5f5;text-align:left;}h1{color:#333;}h2{color:#666;border-bottom:1px solid #eee;padding-bottom:6px;}",
                        ".badge{display:inline-block;padding:3px 10px;border-radius:10px;font-size:12px;}",
                        ".green{background:#dcfce7;color:#166534;}.gray{background:#f3f4f6;color:#374151;}</style></head><body>"]

    parts.append(f"<h1>① 市场调研 / 选品 — 自动报告</h1>")
    parts.append(f"<p>生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}　|　样本数：{len(products_df)} 件</p>")

    # 价格分布图
    if not products_df.empty:
        fig1 = px.histogram(products_df, x="price", nbins=20, title="价格分布")
        parts.append("<h2>价格分布</h2>")
        parts.append(fig1.to_html(full_html=False, include_plotlyjs="cdn"))

        # 评分 vs 价格
        if products_df["rating"].notna().any():
            fig2 = px.scatter(products_df.dropna(subset=["rating"]),
                              x="rating", y="price", hover_data=["title"],
                              title="评分 vs 价格")
            parts.append("<h2>评分 vs 价格</h2>")
            parts.append(fig2.to_html(full_html=False, include_plotlyjs=False))

    # Google Trends
    if not trend_df.empty:
        fig3 = px.line(trend_df, title="Google Trends — 关键词热度（近12月）")
        parts.append("<h2>趋势热度</h2>")
        parts.append(fig3.to_html(full_html=False, include_plotlyjs=False))
    else:
        parts.append("<h2>趋势热度</h2><p style='color:#999'>pytrends 未取到数据（Google 限频/网络），跳过。</p>")

    # 选品建议
    parts.append("<h2>选品建议（Top）</h2>")
    if suggestions:
        parts.append("<table><tr><th>商品</th><th>售价</th><th>评分</th><th>预估利润</th><th>毛利率</th><th>建议</th></tr>")
        for s in suggestions:
            badge = "green" if s["decision"] == "上架" else "gray"
            parts.append(
                f"<tr><td>{s['title'][:60]}</td><td>{s['price']:.2f}</td>"
                f"<td>{s['rating'] if s['rating'] else '-'}</td>"
                f"<td>{s['estimated_profit']:.2f}</td>"
                f"<td>{s['estimated_margin']*100:.1f}%</td>"
                f"<td><span class='badge {badge}'>{s['decision']}</span> {s['reason']}</td></tr>"
            )
        parts.append("</table>")
    else:
        parts.append("<p>暂无候选。</p>")

    parts.append("</body></html>")
    html_path.write_text("\n".join(parts), encoding="utf-8")

    # 同时输出 JSON 便于后续接管线
    json_path = out_dir / f"report_{ts}.json"
    json_path.write_text(json.dumps({
        "timestamp": ts, "n_products": len(products_df),
        "suggestions": suggestions,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"报告已生成：{html_path}")
    return html_path
