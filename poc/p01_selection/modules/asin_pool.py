"""
ASIN 候选池：所有从真实获取拿到的 ASIN 都自动进池子
LLM 提候选品时必须从这个池里选，禁止凭空创造。
"""
from __future__ import annotations
from typing import Optional


class ASINPool:
    """会话级别的候选 ASIN 池（含真实抓到的字段）"""

    def __init__(self):
        self._items: dict[str, dict] = {}

    def add(self, asin: str, **fields):
        if not asin or len(asin) < 5:
            return
        cur = self._items.setdefault(asin, {"asin": asin})
        # 只覆盖非空字段
        for k, v in fields.items():
            if v is not None and v != "":
                cur[k] = v

    def add_batch(self, items: list[dict]):
        for it in items:
            asin = it.get("asin")
            if not asin:
                continue
            self.add(asin, **{k: v for k, v in it.items() if k != "asin"})

    def get(self, asin: str) -> Optional[dict]:
        return self._items.get(asin)

    def all(self) -> list[dict]:
        return list(self._items.values())

    def size(self) -> int:
        return len(self._items)

    def summary_for_llm(self) -> str:
        """生成给 LLM 的池子简介，提候选品前必看"""
        if not self._items:
            return "（ASIN 池为空，请先调用 get_bestsellers / search_products / get_movers_shakers）"
        lines = [f"## 当前 ASIN 池（共 {self.size()} 个真实商品，候选品必须从此选择）"]
        for it in list(self._items.values())[:50]:
            line = (f"- {it['asin']}  "
                    f"${it.get('price','?')}  "
                    f"★{it.get('rating','?')}  "
                    f"reviews={it.get('review_count','?')}  "
                    f"BSR={it.get('rank','?')}  "
                    f"{(it.get('title','') or '')[:60]}")
            lines.append(line)
        return "\n".join(lines)


# 全局会话池（单进程）。生产环境会改成按 thread_id family
POOL = ASINPool()
