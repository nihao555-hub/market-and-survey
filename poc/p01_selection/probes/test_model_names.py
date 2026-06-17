"""验证 DeepSeek 正确的模型名"""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[3] / ".env")
from openai import OpenAI

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL"))

# 先列出 API 实际支持的模型
print("=== /models 列表 ===")
try:
    for m in client.models.list().data:
        print(" -", m.id)
except Exception as e:
    print("list models error:", str(e)[:200])

# 逐个试候选名
print("\n=== 逐个测试候选模型名 ===")
candidates = ["deepseek-chat", "deepseek-reasoner",
              "deepseek-v4-flash", "deepseek-v4-pro",
              "deepseek-v4", "deepseek-flash", "deepseek-pro"]
for name in candidates:
    try:
        r = client.chat.completions.create(
            model=name,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        print(f"  ✅ {name}  -> OK ({r.model})")
    except Exception as e:
        print(f"  ❌ {name}  -> {str(e)[:100]}")
