"""
报告分级 + PDF 导出 — 替代单一 25K 字 markdown
- one_pager(): 1 页摘要（商家最关心的核心结论 + 决策矩阵）
- detail_5pages(): 5 页详情（趋势/竞品/痛点/利润/决策）
- full(): 完整 25K 字（开发者/分析师用）
- export_pdf(markdown_text, output_path): markdown → PDF
- generate_charts(metrics): 真实 matplotlib 图表（价格分布/CR4/月销/亏损概率）
"""
from __future__ import annotations
import re, base64, io, shutil
from pathlib import Path
from typing import Optional


# reports 根目录（evidence / keepa_charts 等图片资源都在这下面）
_REPORTS_ROOT = Path(__file__).resolve().parents[1] / "reports"


def _process_image(src_path: Path, dst_path: Path, max_w: int = 900,
                    is_screenshot: bool = False):
    """把图片缩放/压缩后存到 dst（控制 PDF 体积 + 保证能渲染）。
    - 宽度超过 max_w 缩放
    - 截图类（dp/search 长图）额外限制高度，避免一张图占好几页
    失败则直接复制原图。
    """
    try:
        from PIL import Image
        im = Image.open(src_path)
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        w, h = im.size
        # 截图通常是细长的整页长图 → 只保留顶部一屏（高度封顶）
        if is_screenshot and h > w * 1.6:
            im = im.crop((0, 0, w, int(w * 1.4)))
            w, h = im.size
        if w > max_w:
            nh = int(h * max_w / w)
            im = im.resize((max_w, nh), Image.LANCZOS)
        im.save(dst_path, "JPEG", quality=82, optimize=True)
        return True
    except Exception:
        try:
            shutil.copy2(src_path, dst_path)
            return True
        except Exception:
            return False


def _download_remote(url: str, dst_path: Path) -> bool:
    """下载远程图到本地（带 UA 防盗链）。"""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            "Referer": "https://www.amazon.com/",
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        tmp = dst_path.with_suffix(".tmp")
        tmp.write_bytes(data)
        ok = _process_image(tmp, dst_path, max_w=700)
        try: tmp.unlink()
        except Exception: pass
        return ok
    except Exception:
        return False


def localize_report_images(md_text: str, report_dir: str | Path) -> str:
    """
    把报告里所有图片（本地 + 远程）落地到 report_dir/assets/ 并改写为相对路径，
    让报告自包含、可移植，且 PDF 能正确渲染（远程图不下载就进不了 PDF）。

    - 本地图（evidence/keepa/绝对路径/file://）：压缩后复制到 assets/
    - 远程图（http/https，如 Amazon 主图 CDN）：下载 + 压缩到 assets/
    - 截图类长图自动裁顶部一屏，避免一张图撑满几页
    """
    report_dir = Path(report_dir)
    assets = report_dir / "assets"
    img_re = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    counter = {"n": 0}

    def _resolve_local(src: str) -> Path | None:
        s = src.strip()
        if s.startswith("http://") or s.startswith("https://"):
            return None
        if s.startswith("file:///"):
            s = s[len("file:///"):]
            try: return Path(s)
            except Exception: return None
        p = Path(s)
        if p.is_absolute():
            return p
        cand = _REPORTS_ROOT / s
        if cand.exists():
            return cand
        cand2 = report_dir / s
        if cand2.exists():
            return cand2
        # 回退：按文件名（去扩展名）在 evidence / keepa_charts 里找源图
        # 处理二次运行：md 引用已是 assets/xxx.jpg 但 assets 被清空的情况
        stem = Path(s).stem
        for d in (_REPORTS_ROOT / "evidence", _REPORTS_ROOT / "keepa_charts"):
            if not d.exists():
                continue
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                f = d / f"{stem}{ext}"
                if f.exists():
                    return f
        return None

    def _is_shot(name: str) -> bool:
        return any(k in name.lower() for k in ("_dp", "_search", "_page", "screenshot"))

    def _repl(m):
        alt, src = m.group(1), m.group(2).strip()
        assets.mkdir(parents=True, exist_ok=True)

        # 远程图 → 下载
        if src.startswith("http://") or src.startswith("https://"):
            counter["n"] += 1
            fname = f"img_{counter['n']:02d}.jpg"
            dst = assets / fname
            if _download_remote(src, dst):
                return f"![{alt}](assets/{fname})"
            return m.group(0)  # 下载失败保留原链接

        # 本地图 → 压缩复制（统一转 jpg 控体积）
        local = _resolve_local(src)
        if local is None or not local.exists():
            return m.group(0)
        stem = local.stem
        dst = assets / f"{stem}.jpg"
        if _process_image(local, dst, max_w=900, is_screenshot=_is_shot(local.name)):
            return f"![{alt}](assets/{stem}.jpg)"
        return m.group(0)

    return img_re.sub(_repl, md_text)


def strip_gallery_section(md_text: str) -> str:
    """删掉 LLM 自己加的『候选品图廊/图库』章节（图应嵌在对应候选品旁，不堆画廊）。"""
    pat = re.compile(
        r'(?m)^#{1,3}[^\n]*(图廊|图库|画廊|产品图集|候选品图集)[^\n]*\n.*?(?=\n#{1,3}\s|\Z)',
        re.DOTALL,
    )
    return pat.sub("", md_text)


def build_candidate_gallery(candidates: list[dict], evidence_dir: str = None,
                              geo: str = "US") -> str:
    """
    用代码强制构造「候选品图廊」章节（不依赖 LLM 自觉嵌图）。
    
    candidates: ASIN 池的 item 列表，每个含 asin/title/price/rating/image_url 等
    evidence_dir: 本地截图目录（reports/evidence），优先用本地主图（PDF 离线可渲染）
    
    图片优先级：本地 {asin}_main.jpg（相对路径，PDF 可渲染）> 远程 image_url
    """
    if not candidates:
        return ""
    
    domain_map = {"US":"com","UK":"co.uk","DE":"de","FR":"fr","JP":"co.jp",
                   "IN":"in","AU":"com.au","CA":"ca","MX":"com.mx","BR":"com.br"}
    tld = domain_map.get((geo or "US").upper(), "com")
    
    ev_path = Path(evidence_dir) if evidence_dir else None
    lines = ["\n\n---\n\n## 📸 候选品图廊（真实产品图）\n",
             "> 以下为候选品真实主图与平台截图，全部来自实时获取。\n"]
    
    shown = 0
    for c in candidates:
        asin = c.get("asin")
        if not asin:
            continue
        title = (c.get("title") or "")[:80]
        price = c.get("price")
        rating = c.get("rating")
        img_md = None
        
        # 优先本地主图（PDF 离线可渲染）
        if ev_path:
            local_main = ev_path / f"{asin}_main.jpg"
            if local_main.exists():
                # 相对 reports/ 的路径（md 和 pdf 都放 reports 子目录下）
                img_md = f"![{title}]({local_main.as_posix()})"
        # 退回远程图
        if not img_md and c.get("image_url"):
            img_md = f"![{title}]({c['image_url']})"
        
        if not img_md:
            continue
        
        meta = []
        if price: meta.append(f"${price}" if isinstance(price, (int, float)) else str(price))
        if rating: meta.append(f"★{rating}")
        meta.append(f"[{asin}](https://www.amazon.{tld}/dp/{asin})")
        
        lines.append(f"\n**{title}**  \n{' · '.join(meta)}\n\n{img_md}\n")
        shown += 1
        if shown >= 8:
            break
    
    if shown == 0:
        return ""
    return "\n".join(lines)


def _extract_section(md: str, heading_re: str, max_chars: int = 2000) -> str:
    """从 markdown 报告里提取某个章节"""
    m = re.search(heading_re, md, re.IGNORECASE)
    if not m:
        return ""
    start = m.start()
    # 找下一个同级 heading
    next_h = re.search(r"\n## ", md[start + 1:])
    end = start + 1 + next_h.start() if next_h else len(md)
    return md[start:end][:max_chars]


def _strip_filler(md: str) -> str:
    """去掉给开发者看的水分：═══装饰线、工具调用表、重复阶段说明。"""
    lines = md.split("\n")
    out = []
    in_tool_table = False
    for ln in lines:
        if re.match(r'^\s*[#＃]*\s*[═─━]{5,}\s*$', ln):
            continue
        if re.match(r'^##\s*[═─━]+\s*$', ln):
            continue
        if re.search(r'###?\s*🛠️?\s*数据来源', ln) or re.search(r'###?\s*数据来源', ln):
            in_tool_table = True
            continue
        if in_tool_table:
            if ln.startswith("#") or (ln.strip() and not ln.lstrip().startswith("|")):
                in_tool_table = False
            else:
                continue
        out.append(ln)
    text = "\n".join(out)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def _demote_dev_sections(md: str) -> tuple[str, str]:
    """
    把"开发者向/可溯源"章节从正文剥离，单独收集（放报告最底部折叠）。
    返回 (正文, 开发者章节合集)。
    剥离对象：证据索引/证据清单、数据来源声明、待用户提供清单的工具细节等。
    """
    dev_patterns = [
        r"(?m)^#{1,3}[^\n]*(证据索引|证据清单|数据溯源|可追溯|溯源校验)[^\n]*\n.*?(?=\n#{1,2}\s|\Z)",
    ]
    collected = []
    body = md
    for pat in dev_patterns:
        for m in list(re.finditer(pat, body, re.DOTALL))[::-1]:
            collected.append(m.group(0))
            body = body[:m.start()] + body[m.end():]
    dev_block = "\n\n".join(reversed(collected))
    return body, dev_block


def build_merchant_report(full_report_md: str, loss_probability_main: float = None) -> str:
    """
    商家版报告（推荐默认产出）— 信息分层，让商家一眼看到决策：

    ┌─ 🎯 决策速览卡（做不做/主推/利润/风险）   ← 最顶，最重要
    ├─ 🏆 主推方案详情                          ← 高价值，展开
    ├─ 📈 趋势 / 🏁 竞品 / 💬 痛点 / ⚖️ IP      ← 中价值，<details> 折叠
    └─ 🔧 数据溯源 / 证据索引                    ← 开发者向，沉到最底折叠
    """
    clean = _strip_filler(full_report_md)
    # 剥离开发者向章节（证据索引/溯源），稍后沉底
    body, dev_block = _demote_dev_sections(clean)

    # 顶部：决策速览 + 主推详情（复用 one_pager 的卡片逻辑）
    head = one_pager(full_report_md, loss_probability_main=loss_probability_main)

    # 中价值章节折叠
    mid_value_patterns = [
        (r"(?m)^##[^\n]*(阶段\s*[1一]|第一阶段|stage1|趋势洞察|品类宏观)[^\n]*\n.*?(?=\n##\s|\Z)",
         "📈 趋势洞察详情"),
        (r"(?m)^##[^\n]*(阶段\s*[2二]|第二阶段|stage2|竞[争品]格局|竞争分析)[^\n]*\n.*?(?=\n##\s|\Z)",
         "🏁 竞争格局详情"),
        (r"(?m)^##[^\n]*(阶段\s*[3三]|第三阶段|stage3|痛点)[^\n]*\n.*?(?=\n##\s|\Z)",
         "💬 用户痛点 + 评论原文"),
        (r"(?m)^##[^\n]*(阶段\s*[4四]|第四阶段|stage4|候选品筛选)[^\n]*\n.*?(?=\n##\s|\Z)",
         "🛒 候选品对比 + 真实截图"),
        (r"(?m)^##[^\n]*(阶段\s*[7七]|stage7|IP\s*风险|知识产权)[^\n]*\n.*?(?=\n##\s|\Z)",
         "⚖️ IP 风险明细"),
    ]

    matches = []
    for pat, summary in mid_value_patterns:
        m = re.search(pat, body, re.DOTALL)
        if m:
            matches.append((m.start(), m.end(), summary, m.group(0)))
    matches.sort(key=lambda x: -x[0])
    for start, end, summary, section in matches:
        if not section.strip():
            continue
        wrapped = (f"<details>\n<summary><b>{summary}（点击展开）</b></summary>\n\n"
                   f"{section}\n\n</details>\n")
        body = body[:start] + wrapped + body[end:]

    parts = [head,
             "\n\n---\n\n# 📂 完整分析（按需展开）\n\n",
             "> 高价值结论已在上方决策速览。以下为支撑详情，可逐节展开核对。\n\n",
             body]

    # 开发者向 / 溯源章节沉到最底，默认折叠
    if dev_block.strip():
        parts.append("\n\n---\n\n")
        parts.append("<details>\n<summary><b>🔧 数据溯源与证据索引（开发者/审计用，点击展开）</b></summary>\n\n")
        parts.append(dev_block)
        parts.append("\n\n</details>\n")

    return "".join(parts)


def _extract_field(md: str, patterns: list[str]) -> str | None:
    """从报告里按多个正则尝试抓一个字段值（取第一个命中）。"""
    for pat in patterns:
        m = re.search(pat, md)
        if m:
            return m.group(1).strip()
    return None


def _build_decision_card(full_report_md: str) -> str:
    """
    从完整报告里智能提取关键决策数字，拼成顶部「决策速览卡」。
    商家 10 秒看到：做不做 / 主推什么 / 售价 / 净利 / 盈亏点 / 风险。
    抓不到的字段留空不编造。
    """
    md = full_report_md

    # 主推产品名（优先从"主推方案/产品定义"标题抓，避开决策表单元格）
    main_pick = _extract_field(md, [
        r'产品定义[：:]\s*[「"]([^」\n]{4,60})',
        r'(?m)^#+[^\n]*主推方案[^\n]*\n(?:[^\n]*\n)??[^\n]*产品定义[：:]\s*[「"]?([^」\n]{4,60})',
        r'(?m)^#+\s*🥇?\s*主推方案[^\n]*\n+[#>\s]*([^\n]{4,60})',
        r'主推[：:]\s*[「"]?([^」\n，。]{4,50})',
    ])
    # 决策表里标「🟢 主推/✅ 上架」的那一行，抓产品名（第 2 列）
    if not main_pick:
        m = re.search(r'(?m)^\|[^\n|]*\|\s*([^|]{3,40})\s*\|[^\n]*(?:🟢\s*\*?\*?主推|✅\s*\*?\*?上架)',
                       md)
        if not m:
            m = re.search(r'(?m)^\|[^\n]*?\|\s*([^|]{3,40})\s*\|[^\n]*(主推|上架)\s*\*?\*?\s*\|',
                           md)
        if m:
            main_pick = m.group(1)
    if main_pick:
        main_pick = main_pick.strip("「」\"' #*").strip()
        # 去掉行尾残留的英寸引号造成的截断符
        main_pick = main_pick.rstrip('"」').strip()

    # 售价（优先"升价目标/稳定期售价"，避开首发亏损价）
    price = _extract_field(md, [
        r'升价目标[^\n|]*?\|\s*\*?\*?(\$[\d,.]+)',
        r'稳定期[^\n|]*?\|\s*\*?\*?(\$[\d,.]+)',
        r'(?:建议定价|目标售价|主推售价)[：:\s]*\*?\*?(\$[\d,.]+)',
    ])

    # 健康期净利（优先"升价目标"行的净利，体现可达的健康利润）
    margin = _extract_field(md, [
        r'升价目标[^\n]*?([+\-]?\$[\d.]+（[\d.]+%）)',
        r'升价目标[^\n|]*\|[^\n|]*\|[^\n|]*\|\s*\*?\*?([+\-]?\$[\d.]+[^\n|]{0,10})',
        r'稳定期[^\n|]*\|[^\n|]*\|[^\n|]*\|\s*\*?\*?([+\-]?\$[\d.]+[^\n|]{0,10})',
    ])

    # 盈亏点（必须明确带"件"，且数值有效，避免抓到预算等无关数字）
    breakeven = _extract_field(md, [
        r'盈亏(?:平衡)?点[：:\s/月]*\*?\*?(\d[\d,]{1,5}\s*件)',
        r'盈亏(?:平衡)?点[^\n]{0,12}?(\d[\d,]{1,5})\s*件',
    ])
    if breakeven:
        # 去掉千分位逗号校验是否为有效正整数
        digits = re.sub(r'[^\d]', '', breakeven)
        if not digits or int(digits) == 0:
            breakeven = None
        elif "件" not in breakeven:
            breakeven = breakeven.strip() + " 件/月"

    # 整体风险：优先"风险清单"里的新品期亏损概率（蒙特卡洛整体结论）
    loss_p = _extract_field(md, [
        r'新品期?亏损概率\s*([\d.]+%)',
        r'新品亏[损率率]\s*([\d.]+%)',
        r'蒙特卡洛[^\n]*?新品[^\n]*?([\d.]+%)',
    ])

    # 市场规模 / GMV
    market = _extract_field(md, [
        r'(?:月\s*GMV|月度\s*GMV)[：:\s~约]*\*?\*?(\$[\d,.]+\s*[KkMm万]?)',
        r'市场规模[^\n]*?(\$[\d,.]+\s*[KkMm万]?)',
        r'GMV[^\n]*?(\$[\d,.]+\s*[KkMm万]?)',
    ])

    # 总体决策判断（综合主推是否存在 + 稳定期能否盈利 + 是否待用户补数据）
    has_stable_profit = bool(re.search(r'稳定期[^\n]*?\+\$[\d.]+', md)) or \
                        bool(re.search(r'升价目标[^\n]*?\+\$[\d.]+', md))
    profit_pending = bool(re.search(r'(待用户提供|待确认|n/a\(俄\)|阶段\s*5[^\n]*?(partial|跳过|待))', md))
    if main_pick and has_stable_profit:
        verdict = "🟡 谨慎进入（差异化可盈利，新品期需扛广告投入）"
    elif main_pick and profit_pending:
        verdict = "🟡 有机会（已选主推方向，利润待补采购/物流数据后定）"
    elif main_pick:
        verdict = "🟡 谨慎进入（需优化成本结构）"
    else:
        verdict = "🔴 暂不建议（未找到可盈利方案）"

    rows = [f"| 🎯 **是否进入** | **{verdict}** |"]
    if main_pick:  rows.append(f"| 🏆 主推产品 | {main_pick} |")
    if price:      rows.append(f"| 💲 健康期售价 | {price} |")
    if margin:     rows.append(f"| 💰 健康期净利 | {margin} |")
    if breakeven:  rows.append(f"| ⚖️ 盈亏平衡点 | {breakeven} |")
    if market:     rows.append(f"| 📊 市场规模 | {market} |")
    if loss_p:     rows.append(f"| ⚠️ 新品期亏损概率 | {loss_p}（需广告预算扛过） |")

    card = ["## 🎯 决策速览\n",
            "> 30 秒看懂：做不做、主推什么、能赚多少、风险多大。\n",
            "| 决策维度 | 结论 |",
            "|:--|:--|"]
    card.extend(rows)
    return "\n".join(card) + "\n"


def one_pager(full_report_md: str, candidates: list = None,
               loss_probability_main: float = None) -> str:
    """
    1 页摘要 — 商家 1 分钟内能读完的核心决策。
    布局：决策速览卡（最重要）→ 主推建议 → 阶段汇总（折叠）。
    """
    decision_card = _build_decision_card(full_report_md)
    decision = _extract_section(full_report_md, r"##.*?(决策|阶段 *8|最终建议)", 2200)
    summary_table = _extract_section(full_report_md, r"##\s*(📋|📊).*?(执行汇总|阶段执行)", 1500)

    out = []
    out.append("# 📌 选品决策 · 一页速览\n")
    out.append(f"> 生成于报告系统 · 数据全部实时获取、可溯源\n\n")

    # 1) 决策速览卡（最顶，最重要）
    out.append(decision_card)
    out.append("\n")

    # 2) 主推决策详情
    if decision:
        out.append("## 🏆 主推方案详情\n")
        out.append(decision[:1800])
        out.append("\n\n")

    # 3) 阶段汇总（折叠，次要）
    if summary_table:
        out.append("<details>\n<summary><b>📋 8 阶段执行状态（点击展开）</b></summary>\n\n")
        out.append(summary_table)
        out.append("\n\n</details>\n\n")

    out.append("---\n")
    out.append("> 📂 完整分析（趋势 / 竞品 / 痛点 / 利润 / IP）见商家版报告或完整版。\n")
    return "\n".join(out)


def detail_5pages(full_report_md: str) -> str:
    """5 页详情 — 含 5 大阶段核心结论 + 候选品对比表 + 数据来源声明"""
    sections_to_keep = [
        r"##\s*(📋|📊).*?(执行汇总|阶段执行)",
        r"##.*?(数据来源|数据采集|平台可用)",
        r"##.*?阶段\s*1",
        r"##.*?阶段\s*2",
        r"##.*?阶段\s*3",
        r"##.*?阶段\s*4",
        r"##.*?阶段\s*5",
        r"##.*?阶段\s*8",
    ]
    out = ["# 选品决策详情（5 页版）\n\n"]
    for pattern in sections_to_keep:
        section = _extract_section(full_report_md, pattern, 4000)
        if section:
            out.append(section)
            out.append("\n\n---\n\n")
    return "".join(out)


def export_pdf(md_text: str, output_path: str, title: str = "选品决策报告") -> dict:
    """
    用 markdown_pdf 把 markdown 转 PDF（纯 Python，无需 GTK）。
    简洁排版：克制的配色、清晰的层级、易读的表格。
    """
    try:
        from markdown_pdf import MarkdownPdf, Section
        import os
        out = Path(output_path)
        # markdown_pdf 解析图片相对路径基于 CWD，切到 PDF 所在目录确保 assets/ 能被找到
        prev_cwd = os.getcwd()
        if out.parent.exists():
            os.chdir(out.parent)
        try:
            pdf = MarkdownPdf(toc_level=2)
            css = """
            body {
                font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 10.5pt; line-height: 1.65; color: #222;
            }
            h1 { font-size: 19pt; color: #111; margin: 0.8em 0 0.5em;
                 border-bottom: 2px solid #333; padding-bottom: 6px; }
            h2 { font-size: 14pt; color: #1a1a1a; margin: 1.4em 0 0.4em;
                 padding-bottom: 3px; border-bottom: 1px solid #ddd; }
            h3 { font-size: 12pt; color: #333; margin: 1em 0 0.3em; }
            h4 { font-size: 11pt; color: #444; margin: 0.8em 0 0.3em; }
            p { margin: 0.5em 0; }
            table { border-collapse: collapse; width: 100%; margin: 0.9em 0; font-size: 9.5pt; }
            th, td { border: 1px solid #ccc; padding: 6px 9px; text-align: left; }
            th { background: #f2f2f2; font-weight: 600; }
            tr:nth-child(even) { background: #fafafa; }
            code { background: #f4f4f4; padding: 1px 4px; border-radius: 3px;
                   font-family: Consolas, monospace; font-size: 9pt; }
            pre { background: #f7f7f7; padding: 10px; border-radius: 4px;
                  border: 1px solid #eee; overflow-x: auto; font-size: 9pt; }
            blockquote { border-left: 3px solid #bbb; padding: 2px 12px;
                         color: #555; margin: 0.6em 0; }
            img { max-width: 60%; margin: 8px 0; border: 1px solid #eee; }
            details summary { cursor: pointer; color: #1a5fb4; font-weight: 600; margin: 6px 0; }
            hr { border: none; border-top: 1px solid #e0e0e0; margin: 1.2em 0; }
            a { color: #1a5fb4; text-decoration: none; }
            strong { color: #111; }
            """
            pdf.add_section(Section(md_text, toc=False), user_css=css)
            pdf.meta["title"] = title
            pdf.save(out.name if out.parent.exists() else output_path)
        finally:
            os.chdir(prev_cwd)
        return {"ok": True, "path": output_path,
                 "size_bytes": Path(output_path).stat().st_size}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def generate_price_distribution_chart(price_bands: dict, output_path: str) -> dict:
    """生成价格分布柱状图"""
    try:
        import matplotlib
        matplotlib.use("Agg")  # 无 GUI
        import matplotlib.pyplot as plt
        
        bands = list(price_bands.keys())
        counts = list(price_bands.values())
        
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(bands, counts, color="#3498db", edgecolor="#2c3e50")
        ax.set_xlabel("Price Band (USD)")
        ax.set_ylabel("Product Count")
        ax.set_title("Price Distribution Histogram")
        plt.xticks(rotation=30, ha="right")
        # 数值标签
        for b, c in zip(bars, counts):
            ax.text(b.get_x() + b.get_width()/2, c + 0.3, str(c), ha="center", fontsize=9)
        plt.tight_layout()
        plt.savefig(output_path, dpi=120)
        plt.close()
        return {"ok": True, "path": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def generate_monte_carlo_chart(profits: list, output_path: str) -> dict:
    """生成蒙特卡洛净利分布直方图"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        
        arr = np.array(profits)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(arr, bins=50, color="#3498db", edgecolor="white", alpha=0.8)
        ax.axvline(0, color="red", linestyle="--", label="Break-even ($0)")
        ax.axvline(arr.mean(), color="green", linestyle="-",
                    label=f"Mean (${arr.mean():.2f})")
        var_95 = np.percentile(arr, 5)
        ax.axvline(var_95, color="orange", linestyle=":",
                    label=f"VaR 95% (${var_95:.2f})")
        
        ax.set_xlabel("Net Profit per Unit (USD)")
        ax.set_ylabel("Frequency")
        ax.set_title(f"Monte Carlo Profit Distribution (n={len(arr)})")
        ax.legend()
        plt.tight_layout()
        plt.savefig(output_path, dpi=120)
        plt.close()
        return {"ok": True, "path": output_path,
                 "p_loss": float((arr < 0).mean())}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


if __name__ == "__main__":
    # 自测
    import json
    sample = "## 📋 执行汇总\n| 阶段 | 状态 |\n|---|---|\n| 1 | OK |\n\n## 阶段 8\n主推 X"
    print(one_pager(sample, loss_probability_main=0.15))
