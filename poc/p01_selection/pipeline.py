"""
第一环节·市场调研/选品 — 端到端 PoC 主流程
流程：采集 → 解析 → 入库(+历史快照) → 趋势 → 分析 → 报告

PoC 阶段使用 books.toscrape.com（公开练习站）演示完整链路。
真实接入 Amazon/Temu 时仅需替换 URL 与 parser 选择器，骨架不变。
"""

from __future__ import annotations
import sys
from pathlib import Path

# 让 modules 可被导入
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from loguru import logger
from sqlalchemy.orm import sessionmaker

from modules.scraper import fetch
from modules.parser import parse_book_list
from modules.storage import get_engine, upsert_products, ProductRow, PriceSnapshot
from modules.trends import get_keyword_trend
from modules.analysis import score_opportunity, suggest_decisions
from modules.report import make_report

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

# ---- PoC 抓取目标（公开练习站，无反爬，演示链路）----
TARGET_URLS = [
    "https://books.toscrape.com/",
    "https://books.toscrape.com/catalogue/page-2.html",
    "https://books.toscrape.com/catalogue/page-3.html",
]

# 趋势关键词（演示用）
TREND_KEYWORDS = ["dropshipping", "amazon fba", "tiktok shop"]


def step_collect_and_parse():
    logger.info("=== Step 1: 采集 + 解析 ===")
    all_products: list[dict] = []
    for url in TARGET_URLS:
        try:
            html = fetch(url)
            items = parse_book_list(html, base_url=url if url.endswith("/") else "https://books.toscrape.com/")
            all_products.extend([p.model_dump() for p in items])
        except Exception as e:
            logger.error(f"抓取失败 {url}：{e}")
    logger.success(f"共采集 {len(all_products)} 件商品")
    return all_products


def step_store(products: list[dict]):
    logger.info("=== Step 2: 入库 + 历史快照 ===")
    engine = get_engine()
    upsert_products(products, engine=engine)
    return engine


def step_load_latest_df(engine) -> pd.DataFrame:
    """从 DB 取每个商品最新一条快照，作为本轮分析输入"""
    Session = sessionmaker(bind=engine, future=True)
    rows = []
    with Session() as s:
        for prod in s.query(ProductRow).all():
            snap = (
                s.query(PriceSnapshot)
                .filter_by(product_id=prod.id)
                .order_by(PriceSnapshot.captured_at.desc())
                .first()
            )
            if snap:
                rows.append({
                    "title": prod.title,
                    "url": prod.url,
                    "category": prod.category,
                    "price": snap.price,
                    "rating": snap.rating,
                    "in_stock": snap.in_stock,
                })
    df = pd.DataFrame(rows)
    logger.info(f"DB 中现有 {len(df)} 件商品（最新快照）")
    return df


def step_trends():
    logger.info("=== Step 3: Google Trends 趋势 ===")
    return get_keyword_trend(TREND_KEYWORDS)


def step_analyze(df: pd.DataFrame):
    logger.info("=== Step 4: 机会评分 + 选品建议 ===")
    scored = score_opportunity(df)
    suggestions = suggest_decisions(scored, top_n=10)
    logger.success(f"产出 {len(suggestions)} 条选品建议")
    return scored, suggestions


def step_report(df: pd.DataFrame, trend_df, suggestions):
    logger.info("=== Step 5: 生成报告 ===")
    return make_report(df, trend_df, suggestions, REPORT_DIR)


def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}")

    products = step_collect_and_parse()
    if not products:
        logger.error("采集为空，流程终止")
        sys.exit(1)

    engine = step_store(products)
    df = step_load_latest_df(engine)
    trend_df = step_trends()
    scored, suggestions = step_analyze(df)
    report_path = step_report(scored, trend_df, suggestions)

    print("\n" + "=" * 60)
    print(f"✅ 流程完成")
    print(f"📦 采集 {len(products)} 条 → 入库 {len(df)} 件")
    print(f"💡 选品建议 {len(suggestions)} 条")
    print(f"📊 报告：{report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
