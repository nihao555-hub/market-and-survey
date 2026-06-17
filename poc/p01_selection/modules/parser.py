"""
解析层：把 HTML 结构化为商品对象。
用 Scrapling 的 Adaptor 解析（自适应能力，未来页面改版可降低维护成本）。
当前 PoC 用 books.toscrape.com（公开练习站）演示完整链路；
真实接入 Amazon/Temu 时仅需替换选择器，代码骨架不变。
"""

from __future__ import annotations
from typing import List
from pydantic import BaseModel
from scrapling.parser import Adaptor
from loguru import logger


class Product(BaseModel):
    title: str
    price: float
    currency: str = "GBP"
    rating: float | None = None
    in_stock: bool = True
    url: str = ""
    category: str = ""


def _parse_rating(rating_class: str) -> float | None:
    """books.toscrape 用 class='star-rating Three' 表示评分"""
    mapping = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    for k, v in mapping.items():
        if k in rating_class:
            return float(v)
    return None


def parse_book_list(html: str, base_url: str = "https://books.toscrape.com/") -> List[Product]:
    """解析 books.toscrape 列表页"""
    adp = Adaptor(html, url=base_url, auto_match=True)
    products: List[Product] = []

    for item in adp.css("article.product_pod"):
        try:
            a = item.css_first("h3 a")
            title = a.attrib.get("title", "").strip()
            href = a.attrib.get("href", "")
            full_url = base_url.rstrip("/") + "/" + href.lstrip("./")

            price_text = item.css_first("p.price_color").text
            # "£51.77" 或 "Â£51.77"（编码差异） 取数字
            price = float("".join(c for c in price_text if c.isdigit() or c == "."))

            stock_node = item.css_first("p.availability")
            # books.toscrape 把状态放在 class 里：'instock availability' 表示有货
            stock_class = (stock_node.attrib.get("class", "") if stock_node else "")
            in_stock = "instock" in stock_class.lower() if stock_node else True

            rating_node = item.css_first("p.star-rating")
            rating = _parse_rating(rating_node.attrib.get("class", "")) if rating_node else None

            products.append(Product(
                title=title, price=price, rating=rating,
                in_stock=in_stock, url=full_url, category="books",
            ))
        except Exception as e:
            logger.warning(f"解析单个商品失败: {e}")
            continue

    logger.info(f"解析得到 {len(products)} 个商品")
    return products


if __name__ == "__main__":
    from scraper import fetch
    html = fetch("https://books.toscrape.com/")
    items = parse_book_list(html)
    for p in items[:3]:
        print(p.model_dump())
