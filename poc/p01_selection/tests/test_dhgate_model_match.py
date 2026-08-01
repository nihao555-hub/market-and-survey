"""DHgate 型号级兜底匹配的最小单测（离线，不触网）。"""
import pytest

from modules import sourcing_1688 as s


ATTRS = {"material": "stainless steel", "capacity": "3L"}


def test_build_model_query():
    q = s.build_model_query("pet water fountain", ATTRS)
    assert q == "stainless steel pet water fountain 3L"
    # 无属性时退化为类目词
    assert s.build_model_query("pet water fountain", None) == "pet water fountain"
    # 自定义型号词去重拼接
    q2 = s.build_model_query("pet water fountain",
                             {"capacity": "7L", "model_terms": ["automatic", "7L"]})
    assert q2 == "pet water fountain 7L automatic"


def test_model_match_items_model_level():
    items = [
        {"title": "Stainless Steel Pet Water Fountain 3L Automatic Cat Dispenser",
         "price_usd": 8.5},
        {"title": "Stainless Steel Cat Water Fountain 3.0L with Filter",  # 3.0L ≠ 3L，但材质命中
         "price_usd": 7.8},
        {"title": "Pet Supplies Wholesale Hot Sale Chew Toy",  # 泛品类，无规格词
         "price_usd": 1.2},
        {"title": "Automatic Pet Water Fountain 7L Large Capacity",  # 类目命中但规格全不命中
         "price_usd": 9.9},
    ]
    matched, info = s.model_match_items(items, "pet water fountain", ATTRS)
    assert len(matched) == 2
    assert info["match_level"] == "model"
    assert info["usable_for_cost_calc"] is True
    assert "stainless steel" in info["matched_keywords"]
    assert all(it["match_level"] == "model" and it["matched_keywords"] for it in matched)


def test_model_match_items_generic_rejected():
    """只有泛品类命中（无规格词）→ match_level=none，禁止进入测算"""
    items = [
        {"title": "Pet Supplies Wholesale Hot Sale", "price_usd": 7.53},
        {"title": "Pet Water Fountain Automatic", "price_usd": 6.0},  # 类目命中，规格不命中
    ]
    matched, info = s.model_match_items(items, "pet water fountain", ATTRS)
    assert matched == []
    assert info["match_level"] == "none"
    assert info["usable_for_cost_calc"] is False


def test_capacity_compact_match():
    """容量做去空格匹配：'3 L' / '3L' 等价"""
    items = [{"title": "Stainless Steel Pet Water Fountain 3 L Dispenser", "price_usd": 8.0}]
    matched, _ = s.model_match_items(items, "pet water fountain", ATTRS)
    assert len(matched) == 1


def _patch_all_sources_fail(monkeypatch, dhgate_items):
    """1688 / MIC 失败，DHgate 返回给定商品；汇率固定（避免触网）"""
    monkeypatch.setattr(s, "search_1688",
                        lambda *a, **k: {"error": "blocked_by_alibaba_cloud_ip_bl", "items": []})
    monkeypatch.setattr(s, "search_made_in_china",
                        lambda *a, **k: {"error": "no_items", "items": []})
    monkeypatch.setattr(s, "search_dhgate",
                        lambda kw, **k: {"keyword": kw, "url": "https://www.dhgate.com/x",
                                         "count": len(dhgate_items), "items": dhgate_items})
    monkeypatch.setattr(s, "search_globalsources",
                        lambda *a, **k: {"error": "no_items", "items": []})
    monkeypatch.setattr(s, "get_usd_cny_rate", lambda: 7.2)


def test_procurement_cost_model_level_usable(monkeypatch):
    """型号级匹配命中 → match_level=model 且 usable_for_cost_calc=True，允许进测算"""
    _patch_all_sources_fail(monkeypatch, [
        {"title": "Stainless Steel Pet Water Fountain 3L Automatic", "price_usd": 8.5},
        {"title": "Pet Supplies Generic Toy", "price_usd": 1.0},
    ])
    r = s.get_real_procurement_cost("宠物饮水机", product_attrs=ATTRS)
    assert r["real_data"] is True
    assert r["source"] == "dhgate.com"
    assert r["match_level"] == "model"
    assert r["usable_for_cost_calc"] is True
    assert r["search_keyword_en"] == "stainless steel pet water fountain 3L"
    assert "stainless steel" in r["matched_keywords"]
    assert 0 < r["confidence"] <= 1
    assert r["median_usd"] == 8.5  # 只剩型号级匹配样本


def test_procurement_cost_generic_rejected(monkeypatch):
    """型号级无匹配退回泛品类 → usable_for_cost_calc=False + 铁律警告"""
    _patch_all_sources_fail(monkeypatch, [
        {"title": "Pet Water Fountain Automatic Dispenser", "price_usd": 7.53},
    ])
    r = s.get_real_procurement_cost("宠物饮水机", product_attrs=ATTRS)
    assert r["real_data"] is True
    assert r["match_level"] == "category"
    assert r["usable_for_cost_calc"] is False
    assert "_strict_warning" in r and "禁止进入 full_cost_breakdown" in r["_strict_warning"]
