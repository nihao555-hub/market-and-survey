"""快速验证新增工具已正确注册"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.agent_tools import TOOLS_SCHEMA, TOOL_IMPL

names = [t["function"]["name"] for t in TOOLS_SCHEMA]
print(f"schema_count = {len(names)}")
print(f"impl_count   = {len(TOOL_IMPL)}")

new = ["provide_procurement_cost", "get_provided_costs",
       "record_stage_status", "stage_status_summary"]
print(f"\n新工具检查：")
for n in new:
    in_s = "✅" if n in names else "❌"
    in_i = "✅" if n in TOOL_IMPL else "❌"
    print(f"  {n:30}  schema={in_s}  impl={in_i}")

# 找重复定义
from collections import Counter
dup = [k for k, v in Counter(names).items() if v > 1]
print(f"\n重复 schema 名: {dup or '无'}")

# 试调一下新工具
print("\n--- 试调 record_stage_status ---")
r = TOOL_IMPL["record_stage_status"](
    stage_id="stage5_profit", status="skipped",
    reason="1688 反爬触发，无真实采购成本",
    needs_user_action="提供 1688 商品 URL 或工厂报价"
)
print(r)

print("\n--- 试调 provide_procurement_cost ---")
r = TOOL_IMPL["provide_procurement_cost"](
    procurement_cost_usd=8.5,
    source_label="user-input: PingPong 2026-05 报价单 #ABC123",
    asin="B0CRTR3PMF", category_keyword="蓝牙耳机 真无线"
)
print(r)

print("\n--- 试调 stage_status_summary ---")
r = TOOL_IMPL["stage_status_summary"]()
print("warning:", r["warning"])
print("\nmarkdown 表:\n" + r["markdown"])
