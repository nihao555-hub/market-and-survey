"""
存储层：用 SQLite 跑 PoC（生产换成 PostgreSQL 同一行 SQLAlchemy URL）。
含商品主表 + 历史快照表（替代 Keepa 的"价格/BSR 历史"思路）。
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from loguru import logger

Base = declarative_base()


class ProductRow(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, index=True)
    url = Column(String, unique=True, index=True)
    category = Column(String, index=True)
    currency = Column(String, default="GBP")
    last_seen = Column(DateTime, default=datetime.utcnow)
    snapshots = relationship("PriceSnapshot", back_populates="product", cascade="all, delete-orphan")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    price = Column(Float)
    rating = Column(Float, nullable=True)
    in_stock = Column(Boolean, default=True)
    captured_at = Column(DateTime, default=datetime.utcnow, index=True)
    product = relationship("ProductRow", back_populates="snapshots")


def get_engine(db_path: str = None):
    db_path = db_path or str(Path(__file__).parent.parent / "data" / "selection.sqlite")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(eng)
    return eng


def upsert_products(products: List[dict], engine=None) -> int:
    """商品主表 upsert + 当前快照入历史表"""
    engine = engine or get_engine()
    Session = sessionmaker(bind=engine, future=True)
    saved = 0
    with Session() as s:
        for p in products:
            row = s.query(ProductRow).filter_by(url=p["url"]).one_or_none()
            if row is None:
                row = ProductRow(
                    title=p["title"], url=p["url"],
                    category=p.get("category", ""), currency=p.get("currency", "GBP"),
                )
                s.add(row)
                s.flush()
            row.last_seen = datetime.utcnow()

            snap = PriceSnapshot(
                product_id=row.id,
                price=p["price"],
                rating=p.get("rating"),
                in_stock=p.get("in_stock", True),
            )
            s.add(snap)
            saved += 1
        s.commit()
    logger.info(f"入库完成：{saved} 条快照")
    return saved


if __name__ == "__main__":
    eng = get_engine()
    print("DB ready:", eng.url)
