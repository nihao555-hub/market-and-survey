"""
SPA 平台 selector 深度诊断 — 用 patchright 等 JS 渲染完再分析
针对 9 个 selector 待修平台。
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TO_FIX = [
    ("shopee_my", "https://shopee.com.my/search?keyword=earphones"),
    ("lazada_sg", "https://www.lazada.sg/catalog/?q=earphones"),
    ("tokopedia", "https://www.tokopedia.com/search?q=earphones"),
    ("tiktok_shop", "https://www.tiktok.com/shop/s/earbuds"),
    ("trendyol", "https://www.trendyol.com/sr?q=kulaklik"),
    ("flipkart", "https://www.flipkart.com/search?q=earphones"),
    ("amazon_ae", "https://www.amazon.ae/s?k=earphones"),
    ("noon", "https://www.noon.com/uae-en/search/?q=earphones"),
    ("target", "https://www.target.com/s?searchTerm=wireless+earbuds"),
]


def diag_with_render(plat_id: str, url: str) -> dict:
    """用 patchright 完整渲染 + 滚动 + 等待，然后 dump 整个 DOM"""
    from patchright.sync_api import sync_playwright
    
    PROXY = {"server": "http://127.0.0.1:10808"}
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, proxy=PROXY)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            browser.close()
            return {"plat_id": plat_id, "error": f"goto fail: {str(e)[:120]}"}
        
        # 滚动 5 次让懒加载触发
        for _ in range(5):
            try:
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(800)
            except Exception:
                break
        
        # 等更多内容
        page.wait_for_timeout(3000)
        
        # 注入 JS 找所有可能的商品卡片
        candidates_js = """
        () => {
          const found = [];
          const seen = new Set();
          
          // 策略：找所有含 $ 或 价格符号 的元素，向上找父级，记录唯一选择器
          const priceRegex = /\\$|€|£|¥|₹|₺|₽|RM|\\bRp\\b|S\\$/;
          const elements = document.querySelectorAll('*');
          let priceCount = 0;
          
          for (const el of elements) {
            if (priceCount >= 50) break;
            const text = el.textContent || '';
            if (text.length < 3 || text.length > 200) continue;
            if (!priceRegex.test(text)) continue;
            // 过滤掉容器（应该是叶子或近叶子）
            if (el.children.length > 5) continue;
            priceCount++;
            
            // 向上找 4 层父级，每层记录 tag + class
            let cur = el.parentElement;
            for (let depth = 0; depth < 4 && cur; depth++) {
              const tag = cur.tagName.toLowerCase();
              const cls = (cur.className || '').toString().split(/\\s+/).filter(c => c.length > 2).slice(0, 2).join('.');
              const dataAttrs = [...cur.attributes].filter(a => a.name.startsWith('data-')).map(a => a.name).slice(0, 2).join(',');
              const sig = tag + (cls ? '.' + cls : '') + (dataAttrs ? '[' + dataAttrs + ']' : '');
              if (!seen.has(sig)) {
                seen.add(sig);
                found.push({sig, depth, tag, hasClass: cls, dataAttrs, sample: text.slice(0, 80)});
              }
              cur = cur.parentElement;
            }
          }
          return {priceCount, candidates: found.slice(0, 30), title: document.title, url: location.href};
        }
        """
        try:
            result = page.evaluate(candidates_js)
        except Exception as e:
            result = {"error": str(e)[:200]}
        
        # 也截图存档
        screenshot_path = f"d:/new 项目/poc/p01_selection/reports/spa_diag/{plat_id}.png"
        Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            page.screenshot(path=screenshot_path, full_page=False)
        except Exception:
            pass
        
        # 也存 HTML
        html_path = f"d:/new 项目/poc/p01_selection/reports/spa_diag/{plat_id}.html"
        try:
            html = page.content()
            Path(html_path).write_text(html[:1500000], encoding="utf-8")
        except Exception:
            html = ""
        
        browser.close()
        return {"plat_id": plat_id, "html_len": len(html), "result": result,
                 "html_path": html_path, "screenshot": screenshot_path}


def main():
    print(f"诊断 {len(TO_FIX)} 个 SPA 平台\n" + "="*60)
    out_lines = ["# SPA 平台 selector 深度诊断（含截图）\n"]
    
    for plat_id, url in TO_FIX:
        print(f"\n--- {plat_id} ---")
        try:
            r = diag_with_render(plat_id, url)
        except Exception as e:
            print(f"  ❌ 整体失败: {e}")
            continue
        
        if r.get("error"):
            print(f"  ❌ {r['error']}")
            out_lines.append(f"\n## {plat_id}\n\n❌ {r['error']}\n")
            continue
        
        result = r.get("result", {})
        print(f"  HTML: {r.get('html_len')} chars, 含价格元素: {result.get('priceCount', 0)}")
        print(f"  page title: {result.get('title', '?')[:80]}")
        out_lines.append(f"\n## {plat_id}\n\n")
        out_lines.append(f"- HTML: {r.get('html_len')} chars\n")
        out_lines.append(f"- 含价格符号的元素: {result.get('priceCount', 0)}\n")
        out_lines.append(f"- title: {result.get('title', '')[:120]}\n")
        out_lines.append(f"- 截图: `{r.get('screenshot')}`\n\n")
        out_lines.append("候选父级 selector：\n\n")
        
        # 按 depth=2/3 优先（通常商品卡是价格父级 2-3 层）
        candidates = result.get("candidates", [])
        for c in candidates[:15]:
            out_lines.append(f"- depth={c.get('depth')}  `{c.get('sig')}` — {c.get('sample', '')[:60]}\n")
            print(f"    depth={c.get('depth')}  {c.get('sig')[:60]}")
    
    out_path = Path("reports/spa_selector_diag.md")
    out_path.write_text("".join(out_lines), encoding="utf-8")
    print(f"\n📊 详情：{out_path.absolute()}")


if __name__ == "__main__":
    main()
