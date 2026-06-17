"""测试 DeepSeek API 连通性（V4 Flash=deepseek-chat / Pro=deepseek-reasoner）"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
from openai import OpenAI

key = os.getenv("DEEPSEEK_API_KEY")
base = os.getenv("DEEPSEEK_BASE_URL")
print(f"key={'set' if key else 'MISSING'} base={base}")

client = OpenAI(api_key=key, base_url=base)

for label, model in [("V4 Flash", os.getenv("DEEPSEEK_MODEL_FLASH")),
                     ("Pro", os.getenv("DEEPSEEK_MODEL_PRO"))]:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "用一句话说明跨境电商选品最关键的一个指标。只回一句中文。"}],
            max_tokens=120,
            stream=False,
        )
        print(f"\n[{label} / {model}] OK")
        print("  →", resp.choices[0].message.content.strip())
        print("  tokens:", resp.usage.total_tokens)
    except Exception as e:
        print(f"\n[{label} / {model}] FAIL: {str(e)[:200]}")
