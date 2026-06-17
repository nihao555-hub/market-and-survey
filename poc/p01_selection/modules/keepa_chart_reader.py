"""
Keepa 曲线图 → 数字趋势（像素分析，不需要多模态模型）

原理：
Keepa PNG 是【数据的确定性渲染】，曲线有固定颜色：
- 橙线 (≈240,160,0)  = Amazon 自营价格
- 蓝色 (≈120,120,200) = BSR 销量排名（Keepa 默认填充区）/ 第三方新品价
按颜色分离每条曲线的 y 轨迹 → 算出：
- 趋势方向（上升/下降/平稳）：比较前 1/3 与后 1/3 的均值
- 波动幅度：y 的标准差 / 极差
- 近期 vs 历史位置

输出的是【可被 DeepSeek 读的文本结论】，不是图。
注意：没有 y 轴刻度标定，所以给的是**相对趋势**（涨跌方向 + 波动程度），不是绝对价格。
真实绝对数字仍来自 RapidAPI（当前值）。两者互补。
"""
from __future__ import annotations
from pathlib import Path
from loguru import logger

# 各曲线颜色（RGB 中心 + 容差）
_CURVES = {
    "amazon_price": {"rgb": (240, 160, 0), "tol": 60, "label": "Amazon 自营价格"},
    "bsr_or_new": {"rgb": (120, 120, 200), "tol": 55, "label": "BSR销量排名/第三方新品价"},
    "green_line": {"rgb": (90, 170, 90), "tol": 60, "label": "绿线(BSR或评分)"},
}


def _trend_label(y_traj: list[int], img_h: int) -> dict:
    """
    给一条曲线的 y 轨迹（像素坐标，y 越小越靠上），算趋势。
    注意：图像 y 轴向下，价格/数值向上 → 像素 y 越小 = 数值越高。
    """
    import statistics
    if len(y_traj) < 10:
        return {"available": False, "reason": "too_few_points", "points": len(y_traj)}
    n = len(y_traj)
    third = max(1, n // 3)
    early = y_traj[:third]
    late = y_traj[-third:]
    early_avg = sum(early) / len(early)
    late_avg = sum(late) / len(late)
    # 像素 y 减小 = 数值上升
    delta_px = early_avg - late_avg  # 正=后期更靠上=数值上升
    span = max(y_traj) - min(y_traj)
    rel_change = delta_px / max(span, 1)
    if rel_change > 0.15:
        direction = "上升"
    elif rel_change < -0.15:
        direction = "下降"
    else:
        direction = "平稳"
    try:
        volatility = round(statistics.pstdev(y_traj) / max(img_h, 1), 3)
    except Exception:
        volatility = 0
    return {
        "available": True,
        "direction": direction,
        "relative_change": round(rel_change, 3),
        "volatility": volatility,  # 0-1，越大波动越剧烈（价格战/促销频繁）
        "data_points": n,
    }


def read_keepa_chart(png_path: str) -> dict:
    """
    从 Keepa PNG 提取各曲线趋势，输出文本结论（给 DeepSeek 读）。
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return {"ok": False, "error": "need pillow+numpy"}
    p = Path(png_path)
    if not p.exists():
        return {"ok": False, "error": "png_not_found", "path": png_path}

    try:
        im = Image.open(p).convert("RGB")
        arr = np.array(im)
        h, w, _ = arr.shape

        results = {}
        for key, spec in _CURVES.items():
            cr, cg, cb = spec["rgb"]
            tol = spec["tol"]
            # 每个 x 列，找匹配该颜色的像素的 y（取平均 y 作为该列曲线位置）
            y_traj = []
            for x in range(w):
                col = arr[:, x, :].astype(int)
                mask = ((abs(col[:, 0] - cr) < tol) &
                        (abs(col[:, 1] - cg) < tol) &
                        (abs(col[:, 2] - cb) < tol))
                ys = np.where(mask)[0]
                if len(ys) > 0:
                    y_traj.append(int(ys.mean()))
            if len(y_traj) >= 10:
                results[key] = {**_trend_label(y_traj, h), "label": spec["label"]}

        if not results:
            return {"ok": False, "error": "no_curves_detected",
                    "_note": "可能是空数据图或新品无历史"}

        # 组织成给 LLM 的文本结论
        lines = []
        for key, r in results.items():
            if r.get("available"):
                vol_desc = ("波动剧烈(促销/价格战频繁)" if r["volatility"] > 0.15 else
                            "波动温和" if r["volatility"] > 0.06 else "非常稳定")
                lines.append(f"{r['label']}: 趋势【{r['direction']}】，{vol_desc}"
                             f"（相对变化 {r['relative_change']}, 波动度 {r['volatility']}）")

        return {
            "ok": True, "png_path": png_path,
            "curves": results,
            "text_summary": "；".join(lines),
            "_source": "Keepa PNG 像素分析（曲线颜色分离，非多模态模型）",
            "_real_data": True,
            "_note": ("相对趋势（涨跌方向+波动程度），无 y 轴标定故非绝对价格；"
                      "绝对当前值请配合 get_amazon_product_details_api。"
                      "DeepSeek 可直接读 text_summary 做分析。"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "path": png_path}


if __name__ == "__main__":
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    d = Path(__file__).resolve().parents[1] / "reports" / "keepa_charts"
    for png in list(d.glob("*.png"))[:3]:
        r = read_keepa_chart(str(png))
        print(f"\n{png.name}:")
        print("  ", r.get("text_summary") or r.get("error"))
