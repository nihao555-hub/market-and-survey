"""
最终决策报告生成器（带证据 + 截图 + 可追溯工具调用链）
输出：HTML（含图）+ Markdown（含本地图链接）
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json


def build_final_report(thread_id: str, query: str,
                        agent_steps: list[dict],
                        candidates: list[dict],
                        evidence: dict,
                        cost_results: list[dict],
                        ip_check_results: list[dict],
                        out_dir: Path) -> dict:
    """
    生成 markdown + html 报告
    candidates: [{asin, title, price, rating, ..., real_data: bool, source_url}]
    evidence:   {asin -> {detail_page: {screenshot_path, url}, ...}}
    cost_results: [{asin, sale_price, breakdown, verdict, data_provenance}]
    ip_check_results: [{keyword, brand_candidate, patents, trademark}]
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"final_{ts}.md"

    md = []
    md.append(f"# 选品决策报告（含证据）\n")
    md.append(f"- **会话 ID**: `{thread_id}`")
    md.append(f"- **生成时间**: {datetime.now():%Y-%m-%d %H:%M:%S}")
    md.append(f"- **原始需求**: {query}\n")

    # ─── 候选品列表（带证据）───
    md.append("## 一、候选品决策（来自真实 ASIN 池）\n")
    if not candidates:
        md.append("> ⚠️ 无候选品。需要先扩充 ASIN 池。\n")
    else:
        md.append("| ASIN | 标题 | 售价 | 评分 | 评论数 | BSR | 月销区间 | 决策 | 证据 |")
        md.append("|------|------|------|------|--------|-----|----------|------|------|")
        for c in candidates:
            ev = evidence.get(c["asin"], {})
            dp = ev.get("detail_page", {})
            screenshot = dp.get("screenshot_path", "")
            screenshot_md = f"[页面]({c.get('source_url') or '#'})"
            if screenshot:
                # 相对路径方便 markdown 渲染
                rel = Path(screenshot).resolve().relative_to(out_dir.parent.resolve()) if Path(screenshot).exists() else screenshot
                screenshot_md = f"[截图](../{rel}) [页面]({c.get('source_url') or '#'})"
            sales = c.get("estimated_monthly_sales", {})
            sales_str = (f"{sales.get('estimated_monthly_sales_low', '?')}-"
                          f"{sales.get('estimated_monthly_sales_high', '?')}")
            md.append(f"| {c['asin']} | {(c.get('title') or '')[:40]} | "
                       f"${c.get('price', '?')} | {c.get('rating', '?')}★ | "
                       f"{c.get('review_count', '?')} | "
                       f"#{c.get('rank', '?')} | {sales_str} | "
                       f"{c.get('decision', '观察')} | {screenshot_md} |")

    # ─── 证据截图区 ───
    if evidence:
        md.append("\n## 二、证据截图（每个候选品）\n")
        for asin, ev in evidence.items():
            md.append(f"### {asin}")
            for kind, data in ev.items():
                if kind == "asin":
                    continue
                if isinstance(data, dict) and data.get("screenshot_path"):
                    rel = Path(data["screenshot_path"]).resolve()
                    try:
                        rel = rel.relative_to(out_dir.parent.resolve())
                    except Exception:
                        pass
                    md.append(f"**{kind}**：[原页面]({data.get('url')})")
                    md.append(f"![{kind}](../{rel})")
                    md.append("")

    # ─── 成本与利润测算（数据溯源）───
    if cost_results:
        md.append("## 三、成本与利润测算（数据溯源）\n")
        for r in cost_results:
            md.append(f"### {r.get('asin', '?')} @ ${r.get('sale_price', '?')}")
            md.append(f"- 净利：${r.get('net_profit', '?')} / 毛利率：{r.get('margin', 0)*100:.2f}%")
            md.append(f"- 决策：{r.get('verdict', '?')}")
            prov = r.get("data_provenance", {})
            if prov:
                md.append(f"- 数据来源：")
                meta = prov.get("real_cost_metadata", {})
                if meta:
                    md.append(f"  - 关税：HS {meta.get('hs_code')} → {meta.get('duty_rate', 0)*100:.2f}% （USITC）")
                    md.append(f"  - FBA Fee：${meta.get('fba_fulfillment_fee', '?')} （Amazon 2026 standard）")
                    md.append(f"  - 佣金：{meta.get('amazon_referral_rate', 0)*100:.1f}% （Amazon 2026 referral fee）")
                    md.append(f"  - 实时汇率：1USD = {meta.get('fx_rate_usd_cny')} CNY")
                if prov.get("asin_real_data"):
                    a = prov["asin_real_data"]
                    md.append(f"  - ASIN 来源：{a.get('source_url', '?')}")
            md.append("")

    # ─── IP 风险扫描 ───
    if ip_check_results:
        md.append("## 四、专利 / 商标风险\n")
        for r in ip_check_results:
            md.append(f"- 关键词：{r.get('keyword')} / 候选品牌：{r.get('brand_candidate')}")
            md.append(f"  - 专利搜索：{r.get('patents', [])}")
            md.append(f"  - 商标搜索：{r.get('trademark', [])}")

    # ─── 工具调用链（可追溯过程）───
    md.append("\n## 五、Agent 工具调用链（完整可追溯）\n")
    for i, s in enumerate(agent_steps, 1):
        md.append(f"### Step {i} ({s.get('model', '?')})")
        if s.get("text"):
            md.append(f"💭 {s['text'][:300]}")
        for tc in s.get("tool_calls", []):
            md.append(f"- 🔧 `{tc.get('name')}` → {str(tc.get('result_preview', ''))[:200]}")

    md_path.write_text("\n".join(md), encoding="utf-8")
    return {"md_path": str(md_path), "ts": ts}
