"""
DeepSeek LLM 客户端封装（OpenAI 兼容协议）
- V4 Flash = deepseek-chat（快，默认，支持 function calling）
- Pro      = deepseek-reasoner（深度推理，用于最终决策）
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_KEY = os.getenv("DEEPSEEK_API_KEY")
_BASE = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_FLASH = os.getenv("DEEPSEEK_MODEL_FLASH", "deepseek-chat")
MODEL_PRO = os.getenv("DEEPSEEK_MODEL_PRO", "deepseek-reasoner")

_client = OpenAI(api_key=_KEY, base_url=_BASE)


def get_client() -> OpenAI:
    return _client


def resolve_model(choice: str = "flash") -> str:
    """choice: 'flash' | 'pro'"""
    return MODEL_PRO if choice == "pro" else MODEL_FLASH


def chat(messages: list[dict], model_choice: str = "flash", **kw) -> str:
    """简单一问一答（无工具）"""
    resp = _client.chat.completions.create(
        model=resolve_model(model_choice),
        messages=messages,
        **kw,
    )
    return resp.choices[0].message.content or ""
