"""
辅助模块 — 让所有 vendor 项目都参与，作为可选增强：
- crawl4ai     : 网页 → LLM-ready markdown（清洗对手页面）
- markitdown   : PDF/Office/HTML → markdown（处理供应商资料/认证文档）
- ScrapeGraphAI: LLM 驱动的结构化抽取（页面结构特殊时兜底）
- apscheduler  : 定时任务（生产环境定时刷 BSR/价格）
- tenacity     : 重试装饰器（已在 scraper 用）
- prefect      : 复杂 DAG 编排（多环节合并时启用）
"""
from __future__ import annotations
from loguru import logger

from modules.llm import MODEL_FLASH  # 模型名单一来源

# ScrapeGraphAI 用 "provider/model" 形式；provider=openai（OpenAI 兼容协议）
_SCRAPEGRAPH_MODEL = f"openai/{MODEL_FLASH}"


# ─────────── crawl4ai：网页清洗成 LLM 友好 markdown ───────────
async def webpage_to_markdown(url: str) -> str:
    """用 crawl4ai 获取并转成干净 markdown"""
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
            return result.markdown or ""
    except Exception as e:
        logger.warning(f"crawl4ai fail: {e}")
        return ""


def webpage_to_markdown_sync(url: str) -> str:
    import asyncio
    try:
        return asyncio.run(webpage_to_markdown(url))
    except Exception as e:
        logger.warning(f"crawl4ai sync fail: {e}")
        return ""


# ─────────── markitdown：文档/PDF → markdown ───────────
def file_to_markdown(file_path: str) -> str:
    """供应商 PDF 报价 / 专利 PDF / 认证文档转 markdown 给 LLM 读"""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(file_path)
        return result.text_content or ""
    except Exception as e:
        logger.warning(f"markitdown fail: {e}")
        return ""


# ─────────── ScrapeGraphAI：LLM 驱动结构化抽取（SPA 平台的又一层兜底）───────────
def scrapegraph_extract_products(html_or_url: str, max_items: int = 20) -> list[dict]:
    """
    用 ScrapeGraphAI 的 SmartScraperGraph 从页面抽结构化商品列表。
    作为 selector + extract_products_with_llm 之后的【再一层】兜底（多层回退、万一成功了呢）。

    入参可以是已抓到的 HTML 文本，也可以是 URL（让它自己渲染）。
    返回标准化商品列表 [{title, price, rating, url}]，失败返回 []。
    """
    try:
        import os
        from scrapegraphai.graphs import SmartScraperGraph
        graph_config = {
            "llm": {
                "model": _SCRAPEGRAPH_MODEL,
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            },
            "verbose": False, "headless": True,
        }
        prompt = (
            f"Extract up to {max_items} real products from this e-commerce search page. "
            "Return JSON: {\"products\": [{\"title\": str, \"price\": str, "
            "\"rating\": str_or_null, \"url\": str_or_null}]}. "
            "Only real products actually on the page; ignore ads/UI text/banners."
        )
        graph = SmartScraperGraph(prompt=prompt, source=html_or_url, config=graph_config)
        result = graph.run() or {}
        products = result.get("products", []) if isinstance(result, dict) else []
        # 归一化
        out = []
        for p in products[:max_items]:
            if not isinstance(p, dict):
                continue
            title = (p.get("title") or "").strip()
            if not title:
                continue
            out.append({"title": title[:120], "price": p.get("price"),
                        "rating": p.get("rating"), "url": p.get("url")})
        return out
    except Exception as e:
        logger.warning(f"ScrapeGraphAI extract fail: {str(e)[:160]}")
        return []


def llm_extract(html: str, prompt: str, openai_api_key: str = None) -> dict:
    """（保留）通用 LLM 结构化抽取。"""
    try:
        import os
        from scrapegraphai.graphs import SmartScraperGraph
        graph_config = {
            "llm": {
                "model": _SCRAPEGRAPH_MODEL,
                "api_key": openai_api_key or os.getenv("DEEPSEEK_API_KEY"),
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            },
            "verbose": False, "headless": True,
        }
        graph = SmartScraperGraph(prompt=prompt, source=html, config=graph_config)
        return graph.run() or {}
    except Exception as e:
        logger.warning(f"ScrapeGraphAI fail: {e}")
        return {"error": str(e)[:200]}


# ─────────── APScheduler：定时刷新 ───────────
def make_scheduler():
    """创建定时任务调度器（背景线程）。生产环境用来定时刷 BSR/价格历史快照。"""
    from apscheduler.schedulers.background import BackgroundScheduler
    return BackgroundScheduler(timezone="UTC")


# ─────────── Prefect：DAG 编排（仅在多环节合并时启用） ───────────
def has_prefect() -> bool:
    try:
        import prefect  # noqa
        return True
    except ImportError:
        return False
