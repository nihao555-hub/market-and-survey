"""测试全球 37 个电商平台 — 哪些能抓哪些不能"""
import sys, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from modules.scraper import fetch, FetchFailed, is_blocked_page
from modules.platforms import PLATFORMS

# 每个平台用通用关键词测
KEYWORD_BY_REGION = {
    "RU": "smart home",  # 俄文 "умный дом" 字符可能编码出错，用英文先
    "JP": "earphones",
    "KR": "earphones",
    "TR": "kulaklik",
    "DE": "kopfhorer",
    "FR": "ecouteurs",
    "MX": "audifonos",
    "BR": "fone",
    "default": "wireless earbuds",
}


def test_one(plat_id: str) -> dict:
    p = PLATFORMS[plat_id]
    region = p.get("region", "")
    kw = KEYWORD_BY_REGION.get(region.split("/")[0] if "/" in region else region,
                                 KEYWORD_BY_REGION["default"])
    url = p["search_url"].format(kw=kw.replace(" ", "+"))
    use_proxy = bool(p.get("needs_proxy"))
    
    t0 = time.time()
    try:
        html = fetch(url, use_proxy=use_proxy, force_browser=True)
        is_block, sign = is_blocked_page(html)
        if is_block:
            return {"id": plat_id, "name": p.get("name"), "status": p["status"],
                     "result": "blocked", "sign": sign, "ms": int((time.time()-t0)*1000)}
        # 看 selector
        from scrapling.parser import Adaptor
        adp = Adaptor(html, url=url, auto_match=False)
        cards = adp.css(p["card_sel"])
        return {
            "id": plat_id, "name": p.get("name"), "status": p["status"],
            "result": "ok" if len(cards) >= 3 else "selector_invalid",
            "html_len": len(html), "cards": len(cards),
            "ms": int((time.time()-t0)*1000),
        }
    except FetchFailed as e:
        return {"id": plat_id, "name": p.get("name"), "status": p["status"],
                 "result": "fetch_failed", "error": str(e)[:120],
                 "ms": int((time.time()-t0)*1000)}
    except Exception as e:
        return {"id": plat_id, "name": p.get("name"), "status": p["status"],
                 "result": "error", "error": str(e)[:120],
                 "ms": int((time.time()-t0)*1000)}


def main():
    plat_ids = list(PLATFORMS.keys())
    print(f"测试 {len(plat_ids)} 个平台（并发 4，预计 ~10 分钟）...\n")
    
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(test_one, pid): pid for pid in plat_ids}
        for fut in as_completed(futures):
            pid = futures[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"id": pid, "result": "exception", "error": str(e)[:100]}
            results.append(r)
            icon = {"ok": "✅", "selector_invalid": "🟡",
                    "blocked": "❌", "fetch_failed": "❌",
                    "error": "⚠"}.get(r.get("result"), "?")
            print(f"  {icon} {r.get('id', pid):20} {r.get('name', ''):20} "
                   f"result={r.get('result'):20} ms={r.get('ms', '?'):>6} "
                   f"{r.get('error', '')[:50]}")
    
    # 写报告
    out = Path("reports/platform_test.md")
    lines = [f"# 全球 {len(plat_ids)} 个电商平台真抓测试报告\n",
              f"测试时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n",
              f"代理：US LA节点 108.181.6.175\n\n"]
    
    grouped = {"ok": [], "selector_invalid": [], "blocked": [], "fetch_failed": [],
                "error": [], "exception": []}
    for r in results:
        grouped.setdefault(r.get("result", "?"), []).append(r)
    
    lines.append(f"## 摘要\n\n")
    for st in ["ok", "selector_invalid", "blocked", "fetch_failed", "error"]:
        lines.append(f"- **{st}**: {len(grouped.get(st, []))} 个\n")
    
    lines.append("\n## 完整结果\n\n")
    lines.append("| 平台 ID | 名称 | 当前状态 | 测试结果 | HTML | 卡片 | 用时 | 备注 |\n")
    lines.append("|---|---|---|---|---|---|---|---|\n")
    for r in sorted(results, key=lambda x: x.get("id", "")):
        result_icon = {"ok": "✅ ok", "selector_invalid": "🟡 selector过时",
                        "blocked": "❌ blocked", "fetch_failed": "❌ failed",
                        "error": "⚠ error"}.get(r.get("result"), r.get("result"))
        lines.append(f"| {r.get('id')} | {r.get('name', '')} | {r.get('status', '')} | "
                      f"{result_icon} | {r.get('html_len', '—')} | {r.get('cards', '—')} | "
                      f"{r.get('ms', '—')}ms | {r.get('error', r.get('sign', ''))[:60]} |\n")
    
    out.write_text("".join(lines), encoding="utf-8")
    print(f"\n📊 报告已存：{out.absolute()}")
    
    # 推荐：哪些平台应该升级 status
    print("\n## 应该改 status 的平台：")
    for r in results:
        if r.get("result") == "ok" and r.get("status") != "verified":
            print(f"  → {r['id']}: {r.get('status')} → verified")
        elif r.get("result") in ("blocked", "fetch_failed") and r.get("status") not in ("blocked", "partial"):
            print(f"  → {r['id']}: {r.get('status')} → blocked")
        elif r.get("result") == "selector_invalid":
            print(f"  → {r['id']}: selector 待修（HTML 拿到了但解析不出）")


if __name__ == "__main__":
    main()
