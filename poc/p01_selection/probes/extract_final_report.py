"""从 Agent 日志里抽出最终决策报告 + 阶段统计 → 直接写文件"""
import re
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

log = Path("poc/01-选品/reports/agent_run_v3.log").read_text(encoding="utf-8")

OUT = Path("poc/01-选品/reports/final_report_extracted.txt")
buf: list[str] = []

# 统计
steps = re.findall(r"Step (\d+) / model=(\S+)", log)
buf.append("=" * 80)
buf.append("Agent 运行统计")
buf.append("=" * 80)
buf.append(f"  总步数: {len(steps)}")
buf.append(f"  Flash 步数: {sum(1 for _, m in steps if m == 'deepseek-v4-flash')}")
buf.append(f"  Pro 步数:   {sum(1 for _, m in steps if m == 'deepseek-v4-pro')}")
tool_count = {}
for m in re.finditer(r"\[(load_skill|get_trend|get_bestsellers|get_movers_shakers|search_products|analyze_market_structure|get_reviews|analyze_reviews|full_cost_breakdown|stress_test|quick_ip_check)\]\(", log):
    tool_count[m.group(1)] = tool_count.get(m.group(1), 0) + 1
buf.append(f"\n  工具调用统计:")
for k, v in sorted(tool_count.items(), key=lambda x: -x[1]):
    buf.append(f"    {k:<30} {v}")

# 找最后一次"[Agent]"输出
last_agent = log.rfind("[Agent]")
buf.append("\n" + "=" * 80)
buf.append("最终决策报告（Agent 最后一次产出）")
buf.append("=" * 80)
if last_agent > 0:
    snippet = log[last_agent:]
    # 去掉日志噪声行
    cleaned = []
    for line in snippet.splitlines():
        if line.startswith(("12:", "13:", "14:", "15:")) and "|" in line:
            continue  # 时间戳日志
        if line.startswith("[20"):
            continue  # scrapy log
        cleaned.append(line)
    buf.append("\n".join(cleaned))

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"已写入 {OUT} ({OUT.stat().st_size} bytes)")
print(f"\n[Top 30 lines preview]")
for line in (OUT.read_text(encoding="utf-8").splitlines())[:30]:
    print(line)
