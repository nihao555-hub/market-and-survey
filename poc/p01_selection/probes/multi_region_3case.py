"""
3 个并发批测：东南亚 + 俄罗斯 + 中东
注意：东南亚和中东本地平台多 blocked，必须回退到 amazon/temu/aliexpress 全球平台
"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 直接复用 multi_region_e2e 的 run_one_case
from probes.multi_region_e2e import run_one_case, REPORTS_DIR
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed


CASES = [
    {
        "case_id": "R1_SEA_kitchen",
        "markets": ["SG", "MY", "ID"],
        "category": "厨房用品",
        "category_en": "kitchen gadgets",
        "category_zh_1688": "厨房用品 不锈钢",
        "user_input": (
            "我想做厨房用品选品调研，目标东南亚（新加坡+马来+印尼）。\n\n"
            "**注意：东南亚本地平台 Shopee/Lazada/Tokopedia 都被反爬挡了**，"
            "请改用以下策略侧面调研东南亚市场：\n"
            "1. 用 Amazon US 抓东南亚相关关键词的产品作为标杆\n"
            "2. 用 Temu/AliExpress（这两个全球电商在东南亚也大量销售）调研价格\n"
            "3. 用 Amazon AU/JP 作为亚太市场对标\n"
            "4. 用 alibaba B2B 调研 1688/中国跨境供应链\n\n"
            "预算 3 万美元/月，FBA / Shopee 跨境店都接受。\n"
            "请抓 ≥ 25 件商品 + ≥ 100 条评论 + 候选品全图。"
        ),
    },
    {
        "case_id": "R2_RU_smarthome",
        "markets": ["RU"],
        "category": "智能家居小工具",
        "category_en": "smart home gadgets",
        "category_zh_1688": "智能家居 WIFI 智能",
        "user_input": (
            "我想做智能家居小工具选品调研，目标俄罗斯市场。\n\n"
            "**俄罗斯主流平台 Yandex Market 已 verified, Wildberries 间歇可抓, Ozon 反爬挡了**。\n"
            "请用 yandex_market + wildberries 抓俄罗斯本地数据，\n"
            "再用 amazon (美国市场对标) + alibaba (供应链) 拼接完整画像。\n"
            "用俄文+英文双关键词扩大覆盖。\n\n"
            "预算 3 万美元/月。请抓 ≥ 25 件商品 + ≥ 100 条评论。"
        ),
    },
    {
        "case_id": "R3_ME_beauty",
        "markets": ["AE", "SA"],
        "category": "美容个护",
        "category_en": "facial massager beauty tool",
        "category_zh_1688": "美容仪 LED 面部按摩",
        "user_input": (
            "我想做美容工具（LED 面部按摩仪）选品调研，目标中东（阿联酋+沙特）。\n\n"
            "**注意：Amazon AE 和 Noon 都被反爬挡了**，请回退用：\n"
            "1. Amazon US 抓核心评论数据（美容工具品牌主要在 Amazon US 销售）\n"
            "2. AliExpress + Temu 抓中东电商常见跨境商品\n"
            "3. Alibaba 抓供应链\n\n"
            "美容仪在中东市场需求高（伊斯兰文化重视个护）。\n"
            "预算 4 万美元/月。请抓 ≥ 25 件商品 + ≥ 100 条评论。"
        ),
    },
]


def main():
    print(f"\n{'='*70}")
    print(f"3 case 并发批测（东南亚 + 俄罗斯 + 中东）")
    print(f"{'='*70}\n")
    
    all_metrics = []
    with ProcessPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(run_one_case, tc): tc for tc in CASES}
        for fut in as_completed(futures):
            tc = futures[fut]
            try:
                m = fut.result()
                all_metrics.append(m)
                print(f"\n✅ {tc['case_id']} 完成")
            except Exception as e:
                import traceback
                print(f"\n❌ {tc['case_id']} 崩溃: {e}\n{traceback.format_exc()[:600]}")
                all_metrics.append({"case_id": tc["case_id"], "fatal_error": str(e)})
    
    # 总报告
    summary_path = REPORTS_DIR / f"summary_3regions_{datetime.now():%Y%m%d_%H%M%S}.md"
    lines = [f"# 3 区域并发批测总览（东南亚 + 俄罗斯 + 中东）\n",
              f"测试时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n"]
    lines.append("\n| 用例 | 品类 | 地区 | ASIN池 | 工具调用 | 报告字数 | 错误 |")
    lines.append("|---|---|---|---|---|---|---|")
    for m in all_metrics:
        if "fatal_error" in m:
            lines.append(f"| {m['case_id']} | — | — | — | — | — | ❌ {m['fatal_error'][:60]} |")
        else:
            lines.append(f"| {m['case_id']} | {m.get('category','')} | "
                          f"{','.join(m.get('markets', []))} | {m.get('pool_final_size',0)} | "
                          f"{m.get('total_tool_calls',0)} | {m.get('final_report_chars',0)} | "
                          f"{m.get('error_count',0)} |")
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📊 总报告：{summary_path.absolute()}")


if __name__ == "__main__":
    main()
