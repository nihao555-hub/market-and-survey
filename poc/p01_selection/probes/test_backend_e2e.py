"""端到端测试 backend FastAPI 服务"""
import sys, io, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
import httpx

BASE = "http://127.0.0.1:8001"


async def main():
    async with httpx.AsyncClient(timeout=300) as cli:
        # 1. POST /chat
        r = await cli.post(f"{BASE}/chat", json={
            "text": "我想做蓝牙耳机品类的选品调研。",
            "model_choice": "flash",
        })
        d = r.json()
        thread_id = d["thread_id"]
        stream_id = d["stream_id"]
        print(f"创建会话 thread_id={thread_id} stream_id={stream_id}")

        # 2. SSE 订阅
        print("\n=== SSE 流式接收 ===")
        async with cli.stream("GET", f"{BASE}/events?thread_id={thread_id}",
                                timeout=600) as resp:
            count = 0
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    ev = line[6:].strip()
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    count += 1
                    if count > 80:
                        break
                    try:
                        obj = json.loads(data)
                        if isinstance(obj, dict):
                            t = obj.get("type") or obj.get("event") or "?"
                            chunk = obj.get("chunk", {})
                            if chunk.get("type") == "text-delta":
                                print(chunk.get("delta", ""), end="", flush=True)
                            elif chunk.get("type") == "tool-input-start":
                                print(f"\n🔧 [{chunk.get('name')}]({json.dumps(chunk.get('args',{}), ensure_ascii=False)[:120]})")
                            elif chunk.get("type") == "tool-output":
                                print(f"   ↳ {chunk.get('elapsed_ms')}ms {chunk.get('preview','')[:200]}")
                            elif chunk.get("type") == "step-start":
                                print(f"\n━━━ Step {chunk.get('step')} / {chunk.get('model')} ━━━")
                            elif t == "message-persisted":
                                print(f"\n✅ message-persisted")
                                break
                            elif t == "stream-error":
                                print(f"\n❌ error: {chunk}")
                                break
                    except Exception:
                        pass

        # 3. 拉会话最终状态
        print("\n\n=== 拉取会话状态 ===")
        r = await cli.get(f"{BASE}/thread/{thread_id}")
        s = r.json()
        print(f"messages: {len(s.get('messages', []))}")
        print(f"tokens: in={s['tokens']['in']} out={s['tokens']['out']}")


asyncio.run(main())
