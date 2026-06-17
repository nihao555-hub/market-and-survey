"""
Wayback Machine 历史快照（archive.org 公开 API，免费、无 key、无反爬）

为什么对选品有价值：
- 看竞品在过去 1-2 年怎么演进的：标题改了什么、价格调整轨迹、评论数增长曲线
- 老品 vs 新品：从快照时间分布看上架时间
- 差异化机会：竞品改过的关键词/卖点 = 他们试错过的方向

API：
- timemap：拿某 URL 的所有历史快照时间戳（一次请求几十/几百条）
- 单快照：archive.org/web/<timestamp>/<url> 直接拿到当时的页面
"""
from __future__ import annotations
import requests, re
from datetime import datetime
from loguru import logger


def get_wayback_snapshots(url: str, limit: int = 30, from_year: int = 2020) -> dict:
    """
    拿 URL 的历史快照列表（按时间排序）。
    返回 [{timestamp, datetime, snapshot_url}]
    """
    api = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": url,
        "output": "json",
        "limit": limit,
        "from": f"{from_year}0101",
        "fl": "timestamp,statuscode,length,digest",
        "filter": "statuscode:200",
        "collapse": "digest",  # 同内容只留一个（去重）
    }
    try:
        r = requests.get(api, params=params, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return {"url": url, "error": f"http_{r.status_code}", "snapshots": []}
        rows = r.json()
        if not rows or len(rows) < 2:
            return {"url": url, "snapshots": [], "_note": "Wayback 无历史快照（可能是新品或近期上架）"}
        header, *data = rows  # 第一行是字段名
        snapshots = []
        for row in data:
            ts = row[0]
            try:
                dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            except ValueError:
                continue
            snapshots.append({
                "timestamp": ts,
                "datetime": dt.strftime("%Y-%m-%d"),
                "snapshot_url": f"https://web.archive.org/web/{ts}/{url}",
                "size": int(row[2]) if len(row) > 2 else None,
            })
        snapshots.sort(key=lambda x: x["timestamp"])
        # 计算关键指标
        first_seen = snapshots[0]["datetime"] if snapshots else None
        last_seen = snapshots[-1]["datetime"] if snapshots else None
        return {
            "url": url, "snapshot_count": len(snapshots),
            "first_seen": first_seen, "last_seen": last_seen,
            "snapshots": snapshots[-15:],  # 返回最近 15 条够用
            "_source": "Wayback Machine（archive.org，免费）",
            "_real_data": True,
            "_note": ("first_seen = Listing 最早被存档时间，可作上架时间近似；"
                      "snapshot_count 多 = 流量高/被关注多。"),
        }
    except Exception as e:
        return {"url": url, "error": str(e)[:200], "snapshots": []}


def fetch_wayback_snapshot(snapshot_url: str) -> dict:
    """抓取一个特定快照的 HTML（用于对比历史标题/价格）"""
    try:
        r = requests.get(snapshot_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return {"url": snapshot_url, "error": f"http_{r.status_code}"}
        html = r.text
        # 提取 Wayback 注入的原页面（去掉 Wayback 工具栏）
        # archive.org 会注入 <script src="//archive.org/static/..."> 等
        # 提取 title
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
        title = title_m.group(1).strip() if title_m else ""
        # 提取价格（$xx.xx 或 £/€）
        prices = re.findall(r'(?:\$|€|£|¥)\s?[\d,]+\.\d{2}', html)[:10]
        return {"url": snapshot_url, "html_len": len(html),
                "title": title[:200], "prices_found": prices,
                "_source": "Wayback 快照"}
    except Exception as e:
        return {"url": snapshot_url, "error": str(e)[:200]}


def analyze_listing_evolution(amazon_url: str, sample_size: int = 5) -> dict:
    """
    抓多个时间点的快照，对比标题/价格演变。
    给出"标题改了几次/价格变化范围/上架时间"这种实用结论。
    """
    snaps_r = get_wayback_snapshots(amazon_url, limit=30)
    if snaps_r.get("error") or not snaps_r.get("snapshots"):
        return snaps_r
    snapshots = snaps_r["snapshots"]
    # 等距取样
    step = max(1, len(snapshots) // sample_size)
    sampled = snapshots[::step][:sample_size]

    titles_seen = []
    prices_seen = []
    fetched = []
    for s in sampled:
        snap = fetch_wayback_snapshot(s["snapshot_url"])
        if snap.get("title"):
            entry = {"date": s["datetime"], "title": snap["title"][:150],
                     "prices": snap.get("prices_found", [])}
            fetched.append(entry)
            titles_seen.append(snap["title"])
            prices_seen.extend(snap.get("prices_found", []))

    # 分析变化
    unique_titles = set(t.strip() for t in titles_seen)
    return {
        "url": amazon_url,
        "first_seen": snaps_r.get("first_seen"),
        "last_seen": snaps_r.get("last_seen"),
        "total_snapshots": snaps_r.get("snapshot_count"),
        "sampled_count": len(fetched),
        "title_changes": len(unique_titles),  # 标题改过多少版
        "title_history": fetched,
        "prices_seen_history": list(dict.fromkeys(prices_seen))[:15],
        "_source": "Wayback Machine 历史演进分析",
        "_real_data": True,
        "_note": ("title_changes 多 = 卖家在试不同关键词；"
                  "prices_seen 范围 = 历史价格变动；"
                  "first_seen = Listing 上架时间近似。"),
    }


if __name__ == "__main__":
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    # 用一个老牌瑜伽垫做测试
    r = get_wayback_snapshots("https://www.amazon.com/dp/B01LP0U5X0", limit=20)
    print(json.dumps({k: v for k, v in r.items() if k != "snapshots"},
                     ensure_ascii=False, indent=2))
    print(f"快照样本(最近5个):")
    for s in r.get("snapshots", [])[-5:]:
        print(f"  {s['datetime']} | {s['snapshot_url']}")
