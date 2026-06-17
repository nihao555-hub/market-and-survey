"""
完整端到端 Agent 测试 — 通过 backend FastAPI 跑
所有输出 UTF-8 写文件（避免 PowerShell 乱码）
"""
import sys, io, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
import httpx
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "reports" / "full_e2e_transcript.md"
BASE = "http://127.0.0.1:8001"


async def main():
    transcript: list[str] = []
    def w(line: str = ""):
        transcript.append(line)
        print(line)

    async with httpx.AsyncClient(timeout=600) as cli:
        # 1) 创建会话
        prompt = ("我想做蓝牙耳机品类的选品调研。\n"
                   "目标市场美国，平台 Amazon FBA，月度预算 5 万美元，"
                   "MOQ 500-1000，定位自有品牌中端精品，避开 Apple/Sony 专利。")
        r = await cli.post(f"{BASE}/chat", json={"text": prompt})
        d = r.json()
        thread_id = d["thread_id"]
        w(f"# 完整端到端 Agent 调研 — 真实运行")
        w(f"\n- 会话 ID: `{thread_id}`")
        w(f"- 用户输入：{prompt}\n")
        w(f"- 启动时间：{httpx.get(f'{BASE}/').json()}\n")

        # 2) 订阅 SSE
        w(f"\n## SSE 实时流（接收 backend 流式 chunk）\n")
        async with cli.stream("GET", f"{BASE}/events?thread_id={thread_id}",
                                timeout=900) as resp:
            count = 0
            current_text = ""
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if not line.startswith("data:"):
                    continue
                count += 1
                if count > 500:
                    break
                data = line[5:].strip()
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    t = obj.get("type") or "?"
                    chunk = obj.get("chunk") or {}
                    ct = chunk.get("type")
                    if ct == "text-delta":
                        current_text += chunk.get("delta", "")
                    elif ct == "text-end":
                        if current_text.strip():
                            w(f"💭 {current_text}\n")
                        current_text = ""
                    elif ct == "tool-input-start":
                        args_str = json.dumps(chunk.get('args', {}), ensure_ascii=False)[:140]
                        w(f"🔧 [{chunk.get('name')}]({args_str})")
                    elif ct == "tool-output":
                        w(f"   ↳ {chunk.get('elapsed_ms')}ms {chunk.get('preview','')[:240]}")
                    elif ct == "step-start":
                        w(f"\n━━━ Step {chunk.get('step')} / {chunk.get('model')} ━━━")
                    elif ct == "finish":
                        w(f"\n[stream finished]")
                    elif t == "message-persisted":
                        w(f"\n✅ message-persisted")
                        break
                    elif t == "stream-error":
                        w(f"\n❌ stream-error: {chunk}")
                        break

        # 3) 最终拉会话状态 + 持久化的消息
        w(f"\n\n## 最终会话状态（持久化）\n")
        r = await cli.get(f"{BASE}/thread/{thread_id}")
        s = r.json()
        w(f"- 消息数：{len(s.get('messages', []))}")
        w(f"- token：input={s['tokens']['in']} output={s['tokens']['out']}")
        w(f"- 费用 credits：input={s['tokens']['in_credits']:.4f} output={s['tokens']['out_credits']:.4f}")

        for m in s.get("messages", []):
            w(f"\n### Message [{m['role']}] {m['id'][:8]}...")
            for p in m.get("parts", []):
                if p.get("type") == "text":
                    w(p.get("text", ""))
                else:
                    w(f"[{p.get('type')}]")

    # 写 transcript 到文件
    OUT.write_text("\n".join(transcript), encoding="utf-8")
    print(f"\n✅ 完整 transcript 已写入：{OUT} ({OUT.stat().st_size} bytes)")


asyncio.run(main())
