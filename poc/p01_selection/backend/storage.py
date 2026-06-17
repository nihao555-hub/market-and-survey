"""
持久化层（对应 backend steering §6）：
- Thread (activeStreamId, conversationSize, totalTokens...)
- Message (parts JSONB, role, status, turnId)
- 全局配置 key-value
PoC 用 SQLite + JSON 列；生产换 Postgres + JSONB 一行 SQL 改。
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime,
                         JSON, ForeignKey, Boolean, text)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

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


_engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
Base.metadata.create_all(_engine)
SessionLocal = sessionmaker(bind=_engine, future=True)

# 轻量迁移：给已存在的旧 threads 表补 tenant_id 列（SQLite ALTER 幂等处理）
def _ensure_tenant_column():
    try:
        with _engine.begin() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(threads)"))]
            if "tenant_id" not in cols:
                conn.execute(text("ALTER TABLE threads ADD COLUMN tenant_id VARCHAR DEFAULT 'dev_tenant'"))
    except Exception:
        pass

_ensure_tenant_column()


def get_or_create_thread(thread_id: str, title: str = "", tenant_id: str = "dev_tenant") -> Thread:
    with SessionLocal() as s:
        t = s.get(Thread, thread_id)
        if t is None:
            t = Thread(id=thread_id, title=title, tenant_id=tenant_id)
            s.add(t); s.commit(); s.refresh(t)
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
