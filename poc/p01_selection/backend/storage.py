"""
持久化层（对应 backend steering §6）：
- Thread (activeStreamId, conversationSize, totalTokens...)
- Message (parts JSONB, role, status, turnId)
- 全局配置 key-value
PoC 用 SQLite + JSON 列；生产换 Postgres + JSONB 一行 SQL 改。
"""
from __future__ import annotations
import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime,
                         JSON, ForeignKey, Boolean, text)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

# storage 常被最先 import（早于 app 里加载 .env 的模块），这里自行加载，
# 确保 DATABASE_URL（Supabase Postgres）在 _resolve_db_url() 执行前已就位。
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

Base = declarative_base()

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "agent.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Thread(Base):
    __tablename__ = "threads"
    id = Column(String, primary_key=True)  # uuid
    tenant_id = Column(String, default="dev_tenant", index=True)  # 多租户隔离
    title = Column(String, default="")
    active_stream_id = Column(String, nullable=True)
    conversation_size = Column(Integer, default=0)
    context_window_tokens = Column(Integer, default=128000)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_input_credits = Column(Float, default=0)
    total_output_credits = Column(Float, default=0)
    kind = Column(String, default="general", index=True)  # 调研类型：market/trend/competitor/audience/opportunity/general
    is_favorite = Column(Boolean, default=False)        # 收藏夹
    deleted_at = Column(DateTime, nullable=True)        # 软删除（回收站）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)
    thread_id = Column(String, ForeignKey("threads.id"), index=True)
    role = Column(String)  # user / assistant / system / tool
    parts = Column(JSON)   # UIMessagePart[] 直接持久化
    status = Column(String, default="sent")  # queued / sent
    turn_id = Column(String, nullable=True)
    tool_call_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    thread = relationship("Thread", back_populates="messages")


class GlobalConfig(Base):
    __tablename__ = "global_config"
    key = Column(String, primary_key=True)
    value = Column(JSON)


class DataSource(Base):
    """数据源管理：调研依赖的外部数据源与连接状态。"""
    __tablename__ = "data_sources"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, default="dev_tenant", index=True)
    name = Column(String)
    description = Column(String, default="")
    kind = Column(String, default="trends")     # 用于前端选图标
    frequency = Column(String, default="每日")    # 实时 / 每日 / 每周
    connected = Column(Boolean, default=False)
    builtin = Column(Boolean, default=False)     # 预置源不可删除
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Monitor(Base):
    """监控与订阅：品类/竞品/价格的自动监控规则。"""
    __tablename__ = "monitors"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, default="dev_tenant", index=True)
    name = Column(String)
    description = Column(String, default="")
    kind = Column(String, default="trend")       # trend / competitor / price
    cadence = Column(String, default="每日")       # 实时 / 每日 / 每周
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiKey(Base):
    """API 接入：租户 API Key（仅存哈希，明文只在创建时返回一次）。"""
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, default="dev_tenant", index=True)
    name = Column(String, default="默认 Key")
    prefix = Column(String)        # 展示用前缀，如 msk_live_
    last4 = Column(String)         # 展示用后四位
    token_hash = Column(String)    # sha256(明文)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)


class DataSnapshot(Base):
    """每日定时刷新落库的真实数据快照。

    反幻觉：`status` / `real_data` 如实标注本条数据是否真抓到，拿不到不编造。
    - tier=1：免代理可得（Amazon 自动补全买家搜索词 / Google Trends / 季节性）
    - tier=2：需美国代理或付费 API（Amazon/Walmart 等商品级 BSR/价格/评论）
    """
    __tablename__ = "data_snapshots"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, default="dev_tenant", index=True)
    run_id = Column(String, index=True)            # 同一次刷新批次
    term = Column(String, index=True)              # 追踪词 / 品类
    source = Column(String, index=True)            # amazon_keywords / google_trends / seasonality / bestsellers / products
    geo = Column(String, default="US")
    tier = Column(Integer, default=1)              # 1=免代理可得 2=需代理/付费
    status = Column(String, default="ok")          # ok / empty / error / unavailable
    real_data = Column(Boolean, default=False)     # 是否真实抓到（反幻觉标记）
    summary = Column(String, default="")           # 简短人类可读摘要
    payload = Column(JSON)                          # 结构化原始结果
    captured_at = Column(DateTime, default=datetime.utcnow, index=True)


def _resolve_db_url() -> tuple[str, bool]:
    """选库：设了 DATABASE_URL（如 Supabase Postgres）就用它，否则回落本地 SQLite。

    返回 (sqlalchemy_url, is_sqlite)。把裸 postgres:// 归一到 psycopg(v3) 方言。
    """
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return f"sqlite:///{DB_PATH}", True
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url, url.startswith("sqlite")


DB_URL, _IS_SQLITE = _resolve_db_url()
_engine_kwargs: dict = {"future": True}
if not _IS_SQLITE:
    # 托管 Postgres（Supabase）：连接易被回收，开 pre_ping + 适度连接池。
    _engine_kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=10,
                          pool_recycle=300)
_engine = create_engine(DB_URL, **_engine_kwargs)
Base.metadata.create_all(_engine)
SessionLocal = sessionmaker(bind=_engine, future=True)

# 轻量迁移：给已存在的旧 threads 表补新增列。仅 SQLite 需要（PRAGMA/ALTER 幂等）；
# Postgres 是全新建库，create_all 已含全部列，无需补。
def _ensure_thread_columns():
    if not _IS_SQLITE:
        return
    adds = {
        "tenant_id": "ALTER TABLE threads ADD COLUMN tenant_id VARCHAR DEFAULT 'dev_tenant'",
        "is_favorite": "ALTER TABLE threads ADD COLUMN is_favorite BOOLEAN DEFAULT 0",
        "deleted_at": "ALTER TABLE threads ADD COLUMN deleted_at DATETIME",
        "kind": "ALTER TABLE threads ADD COLUMN kind VARCHAR DEFAULT 'general'",
    }
    try:
        with _engine.begin() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(threads)"))]
            for col, ddl in adds.items():
                if col not in cols:
                    conn.execute(text(ddl))
    except Exception:
        pass

_ensure_thread_columns()


def get_or_create_thread(thread_id: str, title: str = "", tenant_id: str = "dev_tenant",
                         kind: str = "general") -> Thread:
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None:
            t = Thread(id=thread_id, title=title, tenant_id=tenant_id, kind=kind or "general")
            s.add(t); s.commit(); s.refresh(t)
        elif kind and kind != "general" and (not getattr(t, "kind", None) or t.kind == "general"):
            # 已存在但未打标签：补上调研类型（不覆盖已有非默认标签）
            t.kind = kind
            s.commit(); s.refresh(t)
        return t


def assert_thread_owner(thread_id: str, tenant_id: str) -> bool:
    """多租户隔离校验：thread 是否属于该租户（不属于返回 False）。"""
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None:
            return True  # 不存在，允许创建
        owner = getattr(t, "tenant_id", None) or "dev_tenant"
        return owner == tenant_id or tenant_id == "dev_tenant"


def add_message(thread_id: str, message_id: str, role: str, parts: list,
                status: str = "sent", turn_id: str = None, tool_call_id: str = None):
    with SessionLocal() as s:
        m = Message(id=message_id, thread_id=thread_id, role=role,
                    parts=parts, status=status, turn_id=turn_id, tool_call_id=tool_call_id)
        s.add(m); s.commit()


def list_messages(thread_id: str, status: str = "sent") -> list[Message]:
    with SessionLocal() as s:
        return list(s.query(Message).filter_by(thread_id=thread_id, status=status)
                    .order_by(Message.created_at.asc()))


def set_active_stream(thread_id: str, stream_id: str | None):
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t:
            t.active_stream_id = stream_id
            s.commit()


def clear_all_active_streams():
    """启动时清理所有遗留的 active_stream_id（崩溃/中断的任务不该显示为「运行中」）。"""
    with SessionLocal() as s:
        s.execute(text("UPDATE threads SET active_stream_id = NULL WHERE active_stream_id IS NOT NULL"))
        s.commit()


def delete_thread(thread_id: str, tenant_id: str = "dev_tenant") -> bool:
    """删除一个会话及其全部消息（cascade）。返回是否真的删除了。
    多租户隔离：非归属租户不可删（dev_tenant 放行）。"""
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None:
            return False
        owner = getattr(t, "tenant_id", None) or "dev_tenant"
        if owner != tenant_id and tenant_id != "dev_tenant":
            return False
        s.delete(t)  # messages 通过 cascade="all, delete-orphan" 一并删除
        s.commit()
        return True


def update_token_usage(thread_id: str, input_delta: int, output_delta: int,
                        input_credits: float = 0, output_credits: float = 0):
    """SQL 表达式自增避免读改写竞态（steering §6.1）"""
    with SessionLocal() as s:
        s.execute(text("""
            UPDATE threads SET
              total_input_tokens = total_input_tokens + :i,
              total_output_tokens = total_output_tokens + :o,
              total_input_credits = total_input_credits + :ic,
              total_output_credits = total_output_credits + :oc
            WHERE id = :tid
        """), {"i": input_delta, "o": output_delta,
                "ic": input_credits, "oc": output_credits, "tid": thread_id})
        s.commit()


# ─────────── 多租户归属辅助 ───────────
def _owned(t: Thread, tenant_id: str) -> bool:
    owner = t.tenant_id or "dev_tenant"
    return owner == tenant_id or tenant_id == "dev_tenant"


# ─────────── 线程：收藏 / 软删除（回收站） ───────────
def list_threads(tenant_id: str = "dev_tenant", *,
                 favorite: Optional[bool] = None,
                 trashed: bool = False,
                 kind: Optional[str] = None) -> list[Thread]:
    """列出线程。默认排除回收站；trashed=True 只列回收站；favorite 过滤收藏；kind 过滤调研类型。"""
    with SessionLocal() as s:
        q = s.query(Thread).filter(Thread.tenant_id == tenant_id)
        if trashed:
            q = q.filter(Thread.deleted_at.isnot(None))
        else:
            q = q.filter(Thread.deleted_at.is_(None))
        if favorite is not None:
            q = q.filter(Thread.is_favorite == favorite)
        if kind is not None:
            q = q.filter(Thread.kind == kind)
        return list(q.order_by(Thread.updated_at.desc()).all())


def toggle_favorite(thread_id: str, tenant_id: str = "dev_tenant") -> Optional[bool]:
    """切换收藏态。返回新状态；线程不存在或越权返回 None。"""
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None or not _owned(t, tenant_id):
            return None
        t.is_favorite = not bool(t.is_favorite)
        s.commit()
        return bool(t.is_favorite)


def soft_delete_thread(thread_id: str, tenant_id: str = "dev_tenant") -> bool:
    """软删除：移入回收站（保留消息，可恢复）。"""
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None or not _owned(t, tenant_id):
            return False
        t.deleted_at = datetime.utcnow()
        t.active_stream_id = None
        s.commit()
        return True


def restore_thread(thread_id: str, tenant_id: str = "dev_tenant") -> bool:
    """从回收站恢复。"""
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None or not _owned(t, tenant_id):
            return False
        t.deleted_at = None
        s.commit()
        return True


# ─────────── 数据源 ───────────
_DEFAULT_SOURCES = [
    ("Google Trends", "搜索热度与上升趋势", "trends", "实时", True),
    ("Amazon Best Sellers", "BSR 榜单与销量估算", "amazon", "实时", True),
    ("社媒声量", "TikTok / Reddit 讨论热度", "social", "实时", True),
    ("Keepa", "历史价格与 BSR 曲线", "price", "每日", True),
    ("1688 / Made-in-China", "供应链与成本实价", "sourcing", "每日", True),
    ("Semrush", "关键词搜索量与难度", "keyword", "每日", False),
    ("SimilarWeb", "站点流量与受众画像", "web", "每日", False),
]


def seed_data_sources(tenant_id: str = "dev_tenant") -> None:
    with SessionLocal() as s:
        if s.query(DataSource).filter(DataSource.tenant_id == tenant_id).count():
            return
        for name, desc, kind, freq, connected in _DEFAULT_SOURCES:
            s.add(DataSource(id=str(uuid.uuid4()), tenant_id=tenant_id, name=name,
                             description=desc, kind=kind, frequency=freq,
                             connected=connected, builtin=True))
        s.commit()


def list_data_sources(tenant_id: str = "dev_tenant") -> list[DataSource]:
    seed_data_sources(tenant_id)
    with SessionLocal() as s:
        return list(s.query(DataSource).filter(DataSource.tenant_id == tenant_id)
                    .order_by(DataSource.created_at.asc()).all())


def create_data_source(tenant_id: str, name: str, description: str = "",
                       kind: str = "trends", frequency: str = "每日") -> DataSource:
    with SessionLocal() as s:
        ds = DataSource(id=str(uuid.uuid4()), tenant_id=tenant_id, name=name,
                        description=description, kind=kind, frequency=frequency,
                        connected=True, builtin=False)
        s.add(ds); s.commit(); s.refresh(ds)
        return ds


def set_data_source_connected(source_id: str, connected: bool,
                              tenant_id: str = "dev_tenant") -> Optional[bool]:
    with SessionLocal() as s:
        ds = s.get(DataSource, source_id)
        if ds is None or (ds.tenant_id != tenant_id and tenant_id != "dev_tenant"):
            return None
        ds.connected = connected
        s.commit()
        return bool(ds.connected)


# ─────────── 监控规则 ───────────
_DEFAULT_MONITORS = [
    ("趋势异动提醒", "关注品类搜索热度周环比 > 20% 时通知", "trend", "每日", True),
    ("竞品上新监控", "Top 竞品新增 listing 时推送", "competitor", "实时", True),
    ("价格波动订阅", "目标 ASIN 价格变动 > 10% 时提醒", "price", "每日", False),
]


def seed_monitors(tenant_id: str = "dev_tenant") -> None:
    with SessionLocal() as s:
        if s.query(Monitor).filter(Monitor.tenant_id == tenant_id).count():
            return
        for name, desc, kind, cadence, enabled in _DEFAULT_MONITORS:
            s.add(Monitor(id=str(uuid.uuid4()), tenant_id=tenant_id, name=name,
                          description=desc, kind=kind, cadence=cadence, enabled=enabled))
        s.commit()


def list_monitors(tenant_id: str = "dev_tenant") -> list[Monitor]:
    seed_monitors(tenant_id)
    with SessionLocal() as s:
        return list(s.query(Monitor).filter(Monitor.tenant_id == tenant_id)
                    .order_by(Monitor.created_at.asc()).all())


def create_monitor(tenant_id: str, name: str, description: str = "",
                   kind: str = "trend", cadence: str = "每日") -> Monitor:
    with SessionLocal() as s:
        m = Monitor(id=str(uuid.uuid4()), tenant_id=tenant_id, name=name,
                    description=description, kind=kind, cadence=cadence, enabled=True)
        s.add(m); s.commit(); s.refresh(m)
        return m


def set_monitor_enabled(monitor_id: str, enabled: bool,
                        tenant_id: str = "dev_tenant") -> Optional[bool]:
    with SessionLocal() as s:
        m = s.get(Monitor, monitor_id)
        if m is None or (m.tenant_id != tenant_id and tenant_id != "dev_tenant"):
            return None
        m.enabled = enabled
        s.commit()
        return bool(m.enabled)


def delete_monitor(monitor_id: str, tenant_id: str = "dev_tenant") -> bool:
    with SessionLocal() as s:
        m = s.get(Monitor, monitor_id)
        if m is None or (m.tenant_id != tenant_id and tenant_id != "dev_tenant"):
            return False
        s.delete(m); s.commit()
        return True


# ─────────── API Key ───────────
def list_api_keys(tenant_id: str = "dev_tenant") -> list[ApiKey]:
    with SessionLocal() as s:
        return list(s.query(ApiKey).filter(ApiKey.tenant_id == tenant_id)
                    .order_by(ApiKey.created_at.desc()).all())


def create_api_key(tenant_id: str, name: str = "默认 Key") -> tuple[ApiKey, str]:
    """生成新 Key，返回 (记录, 明文)。明文仅此一次可见。"""
    token = "msk_live_" + secrets.token_hex(20)
    rec = ApiKey(id=str(uuid.uuid4()), tenant_id=tenant_id, name=name,
                 prefix="msk_live_", last4=token[-4:],
                 token_hash=hashlib.sha256(token.encode()).hexdigest())
    with SessionLocal() as s:
        s.add(rec); s.commit(); s.refresh(rec)
    return rec, token


def revoke_api_key(key_id: str, tenant_id: str = "dev_tenant") -> bool:
    with SessionLocal() as s:
        k = s.get(ApiKey, key_id)
        if k is None or (k.tenant_id != tenant_id and tenant_id != "dev_tenant"):
            return False
        k.revoked = True
        s.commit()
        return True


# ─────────── 租户设置 ───────────
_DEFAULT_SETTINGS = {
    "displayName": "产品经理",
    "email": "pm@marketagent.ai",
    "plan": "专业版 Pro",
    "defaultModel": "flash",
    "defaultMarket": "US",
    "defaultPositioning": "中端",
    "notifyEmail": True,
    "notifyInApp": False,
}


def _settings_key(tenant_id: str) -> str:
    return f"settings:{tenant_id}"


def get_settings(tenant_id: str = "dev_tenant") -> dict:
    with SessionLocal() as s:
        row = s.get(GlobalConfig, _settings_key(tenant_id))
        stored = dict(row.value) if row and isinstance(row.value, dict) else {}
    return {**_DEFAULT_SETTINGS, **stored}


def update_settings(tenant_id: str, patch: dict) -> dict:
    merged = {**get_settings(tenant_id), **{k: v for k, v in patch.items() if v is not None}}
    with SessionLocal() as s:
        key = _settings_key(tenant_id)
        row = s.get(GlobalConfig, key)
        if row is None:
            s.add(GlobalConfig(key=key, value=merged))
        else:
            row.value = merged
        s.commit()
    return merged


# ─────────── 全局 KV（每日刷新状态等）───────────
def get_config(key: str, default=None):
    with SessionLocal() as s:
        row = s.get(GlobalConfig, key)
        return row.value if row is not None else default


def set_config(key: str, value) -> None:
    with SessionLocal() as s:
        row = s.get(GlobalConfig, key)
        if row is None:
            s.add(GlobalConfig(key=key, value=value))
        else:
            row.value = value
        s.commit()


# ─────────── 数据快照（每日定时刷新落库）───────────
def save_snapshot(*, tenant_id: str, run_id: str, term: str, source: str,
                  geo: str = "US", tier: int = 1, status: str = "ok",
                  real_data: bool = False, summary: str = "", payload=None) -> str:
    """落一条数据快照，返回快照 id。"""
    sid = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(DataSnapshot(
            id=sid, tenant_id=tenant_id, run_id=run_id, term=term, source=source,
            geo=geo, tier=tier, status=status, real_data=bool(real_data),
            summary=summary or "", payload=payload if payload is not None else {},
        ))
        s.commit()
    return sid


def latest_run_id(tenant_id: str = "dev_tenant") -> Optional[str]:
    """该租户最近一次刷新批次的 run_id。"""
    with SessionLocal() as s:
        row = (s.query(DataSnapshot)
               .filter(DataSnapshot.tenant_id == tenant_id)
               .order_by(DataSnapshot.captured_at.desc())
               .first())
        return row.run_id if row else None


def list_latest_snapshots(tenant_id: str = "dev_tenant", *,
                          term: Optional[str] = None,
                          source: Optional[str] = None,
                          run_id: Optional[str] = None,
                          limit: int = 200) -> list[DataSnapshot]:
    """列出最近一次刷新批次的快照（或指定 run_id），可按 term/source 过滤。"""
    rid = run_id or latest_run_id(tenant_id)
    if not rid:
        return []
    with SessionLocal() as s:
        q = (s.query(DataSnapshot)
             .filter(DataSnapshot.tenant_id == tenant_id, DataSnapshot.run_id == rid))
        if term:
            q = q.filter(DataSnapshot.term == term)
        if source:
            q = q.filter(DataSnapshot.source == source)
        return list(q.order_by(DataSnapshot.captured_at.asc()).limit(limit).all())
