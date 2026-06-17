"""
DeepSeek LLM 客户端封装（OpenAI 兼容协议）——全项目模型名唯一来源。
- Flash = deepseek-v4-flash（快，默认，编排/工具调用）
- Pro   = deepseek-v4-pro（最强，用于最终决策）
模型名以 DeepSeek 官方文档为准（https://api-docs.deepseek.com/quick_start/pricing）：
deepseek-v4-flash / deepseek-v4-pro。旧别名 deepseek-chat / deepseek-reasoner
将于 2026-07-24 下线，不再作为默认。
backend.selection_job / backend.stream_job / agent.py 均从本模块 import，
避免模型名在多处 drift。
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_KEY = os.getenv("DEEPSEEK_API_KEY")
_BASE = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_FLASH = os.getenv("DEEPSEEK_MODEL_FLASH", "deepseek-v4-flash")
MODEL_PRO = os.getenv("DEEPSEEK_MODEL_PRO", "deepseek-v4-pro")

# 客户端延迟构造：import 阶段不强制要求 DEEPSEEK_API_KEY，
# 这样新克隆/单测/纯函数工具无需密钥也能 import；真正发起 API 调用时才需要密钥。
_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not _KEY:
            logger.warning("DEEPSEEK_API_KEY 未设置——LLM 调用会失败；纯函数/工具仍可用。")
        _client = OpenAI(api_key=_KEY or "MISSING_DEEPSEEK_API_KEY", base_url=_BASE)
    return _client


def resolve_model(choice: str = "flash") -> str:
    """choice: 'flash' | 'pro'"""
    return MODEL_PRO if choice == "pro" else MODEL_FLASH


def chat(messages: list[dict], model_choice: str = "flash", **kw) -> str:
    """简单一问一答（无工具）"""
    resp = get_client().chat.completions.create(
        model=resolve_model(model_choice),
        messages=messages,
        **kw,
    )
    return resp.choices[0].message.content or ""
