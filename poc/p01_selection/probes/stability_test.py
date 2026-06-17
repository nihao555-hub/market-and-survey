"""
14 个 verified 平台稳定性实测 — 并发版
- ProcessPoolExecutor 8 并发（每个平台独立进程，避免 chrome 资源争抢）
- 每平台 3 个不同关键词
- 总耗时 ~5 min（vs 串行 30+ min）
"""
import sys, io, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

TESTS = [
    ("amazon", ["wireless earbuds", "yoga mat", "kitchen storage"]),
    ("amazon_uk", ["earphones", "yoga mat", "kitchen organizer"]),
    ("amazon_jp", ["earphones", "smartphone case", "kitchen knife"]),
    ("amazon_au", ["earphones", "yoga mat", "smart plug"]),
    ("bestbuy", ["earbuds", "smartwatch", "wireless mouse"]),
    ("newegg", ["earbuds", "ssd 1tb", "wireless keyboard"]),
    ("target", ["yoga mat", "kitchen organizer", "earbuds"]),
    ("temu", ["yoga mat", "earbuds", "kitchen storage"]),
    ("shein", ["yoga mat", "kitchen organizer", "earbuds"]),
    ("aliexpress", ["yoga mat", "earbuds", "smart watch"]),
    ("alibaba", ["wireless earbuds", "yoga mat", "led face mask"]),
    ("rakuten", ["earphones", "yoga mat", "kitchen knife"]),
    ("mercadolibre_mx", ["audifonos", "yoga mat", "smartwatch"]),
    ("mercadolibre_br", ["fone bluetooth", "yoga mat", "smartwatch"]),
    ("cdiscount", ["ecouteurs", "yoga mat", "smartwatch"]),
    ("otto", ["kopfhorer", "yoga mat", "smartwatch"]),
    ("yandex_market", ["earphones", "yoga mat", "smartwatch"]),
    ("flipkart", ["earphones", "yoga mat", "smartwatch"]),
]


def test_one_subprocess(plat: str, kws: list[str]) -> dict:
    """子进程独立跑一个平台 — 避免 chrome 资源争抢"""
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    
    # 每个子进程开始前自检代理
    try:
        from proxy.ensure_proxy import ensure_proxy_alive
        ensure_proxy_alive(verbose=False)
    except Exception:
        pass
    
    from modules.agent_tools import tool_search_products
    
    results = []
    for kw in kws:
        try:
            t0 = time.time()
            r = tool_search_products(plat, kw, limit=20, use_proxy=True)
            ms = int((time.time() - t0) * 1000)
            cnt = r.get("count", 0)
            results.append({"kw": kw, "count": cnt, "ms": ms,
                             "error": r.get("error", "")[:80] if not cnt else None})
        except Exception as e:
            results.append({"kw": kw, "count": 0, "error": str(e)[:80]})
    
    successes = [r for r in results if r.get("count", 0) >= 5]
    success_rate = len(successes) / len(kws)
    
    if success_rate >= 1.0:
        verdict = "🟢 真稳定（3/3）"
    elif success_rate >= 0.66:
        verdict = "🟡 间歇可用（2/3）"
    elif success_rate >= 0.33:
        verdict = "🟠 不稳定（1/3）"
    else:
        verdict = "🔴 失效（0/3）"
    
    return {
        "platform": plat, "results": results,
        "success_rate": round(success_rate, 2),
        "avg_count": round(sum(r.get("count", 0) for r in results) / len(kws), 1),
        "verdict": verdict,
    }


def main():
    print(f"\n{'='*70}\n{len(TESTS)} 平台并发稳定性实测（max_workers=6）\n{'='*70}\n")
    start = time.time()
    
    all_results = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(test_one_subprocess, plat, kws): plat for plat, kws in TESTS}
        for fut in as_completed(futures):
            plat = futures[fut]
            try:
                r = fut.result(timeout=300)  # 单平台最多 5 分钟
            except Exception as e:
                r = {"platform": plat, "verdict": "🔴 timeout/error",
                      "success_rate": 0, "avg_count": 0, "results": [],
                      "error": str(e)[:100]}
            all_results.append(r)
            print(f"[{plat:18}] {r['verdict']} 平均 {r.get('avg_count', 0)} 件 "
                   f"({len(all_results)}/{len(TESTS)})")
    
    elapsed = int(time.time() - start)
    print(f"\n⏱  总耗时 {elapsed}s ({elapsed//60}m{elapsed%60}s)")
    
    # 汇总报告
    out_path = Path(__file__).resolve().parent.parent / "reports" / "platform_stability_test.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# 平台稳定性实测报告（并发版）\n",
              f"测试时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n",
              f"总耗时：{elapsed}s\n\n"]
    lines.append("| 平台 | 状态 | 成功率 | 平均件数 |\n|---|---|---|---|\n")
    
    # 排序：稳定→失效
    all_results.sort(key=lambda x: -x.get("success_rate", 0))
    for r in all_results:
        lines.append(f"| {r['platform']} | {r['verdict']} | "
                      f"{r.get('success_rate', 0)*100:.0f}% | {r.get('avg_count', 0)} |\n")
    
    lines.append("\n\n## 详细结果\n\n")
    for r in all_results:
        lines.append(f"### {r['platform']}\n")
        for one in r.get("results", []):
            lines.append(f"- `{one['kw']}`: {one.get('count', 0)} 件 "
                          f"({one.get('ms', '?')}ms) {one.get('error', '') or ''}\n")
        lines.append("\n")
    
    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"\n📊 报告：{out_path.absolute()}")
    
    # status 更新建议
    print("\n## 平台 status 更新建议：\n")
    print(f"{'平台':<20} {'当前判定':<25} {'建议 status'}")
    print("-" * 70)
    for r in all_results:
        sr = r.get("success_rate", 0)
        if sr >= 1.0:
            recommended = "verified"
        elif sr >= 0.66:
            recommended = "partial"
        elif sr >= 0.33:
            recommended = "partial（不稳定）"
        else:
            recommended = "blocked"
        print(f"{r['platform']:<20} {r['verdict']:<25} {recommended}")


if __name__ == "__main__":
    main()
