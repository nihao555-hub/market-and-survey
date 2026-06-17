"""
端到端测试 backend /selection/start 接口
- POST 启动选品 Agent
- SSE 订阅事件流，实时打印每个工具调用 / 文本输出
- 等终态后 GET /thread/{id} 拿持久化消息
"""
import sys, io, json, time, uuid
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
import requests

BACKEND = "http://127.0.0.1:8001"

# 用瑜伽垫 case，因为 MIC 已确认能拿到采购成本
USER_INPUT = (
    "我想做瑜伽垫选品调研，目标美国市场，FBA 自有品牌中端定位，"
    "预算 5 万美元/月，避开大牌 Lululemon/Manduka。"
    "请抓 ≥ 25 件商品 + ≥ 100 条评论 + 必须跑通 stage5 利润测算（用 Made-in-China 备用源）。"
)

# 1) 启动
print("→ POST /selection/start")
r = requests.post(f"{BACKEND}/selection/start", json={
    "user_text": USER_INPUT, "model_choice": "flash"
})
data = r.json()
thread_id = data["thread_id"]
stream_id = data["stream_id"]
print(f"  thread_id: {thread_id}")
print(f"  stream_id: {stream_id}")

# 2) 用 requests stream 订阅 SSE
print(f"\n→ GET /events?thread_id={thread_id} (SSE)")
print("=" * 70)

# requests SSE 简易解析
events_received = 0
tool_calls_received = 0
text_chunks_received = 0
start_t = time.time()
LIMIT_SEC = 1200  # 20 min max

with requests.get(f"{BACKEND}/events?thread_id={thread_id}",
                   stream=True, timeout=(10, LIMIT_SEC)) as resp:
    buf = ""
    cur_event = None
    for raw in resp.iter_lines(decode_unicode=True):
        if time.time() - start_t > LIMIT_SEC:
            print(f"\n⏰ 超时 {LIMIT_SEC}s，停止订阅")
            break
        
        if raw is None:
            continue
        if raw == "":
            # 一条 event 结束
            cur_event = None
            continue
        if raw.startswith("event:"):
            cur_event = raw[6:].strip()
            continue
        if raw.startswith("data:"):
            data_str = raw[5:].strip()
            try:
                data = json.loads(data_str)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            
            events_received += 1
            
            # 解析事件 — 主要看 chunk 类型
            chunk = data.get("chunk", {}) if isinstance(data, dict) else {}
            ctype = chunk.get("type") if isinstance(chunk, dict) else None
            
            etype = data.get("type") or cur_event
            
            if etype == "ping":
                continue
            
            if ctype == "step-start":
                print(f"\n━━ Step {chunk.get('step')}/{chunk.get('max_steps','?')} | {chunk.get('model')} ━━")
            elif ctype == "tool-input-start":
                tool_calls_received += 1
                args_preview = json.dumps(chunk.get('args', {}), ensure_ascii=False)[:120]
                print(f"  🔧 {chunk.get('name')}({args_preview})")
            elif ctype == "tool-output":
                preview = chunk.get('preview', '')[:200]
                print(f"  ↳ [{chunk.get('elapsed_ms')}ms] {preview}")
            elif ctype == "text-delta":
                text_chunks_received += 1
                delta = chunk.get('delta', '')[:200]
                if delta.strip():
                    print(f"  💭 {delta}")
            elif ctype == "dsml-detected":
                print(f"  ⚠️ DSML 误输出，已重试")
            elif ctype == "final-stage-starting":
                print(f"\n━━ FINAL / {chunk.get('model')} 综合报告生成中 ━━")
            elif ctype == "final-report":
                print(f"\n📊 报告产出: {chunk.get('content', '')[:200]}")
            elif ctype == "finish":
                print(f"\n✅ Agent 流程结束")
            elif data.get("type") == "message-persisted":
                print(f"\n💾 消息已持久化 — message_id={data.get('messageId')} "
                       f"report_chars={data.get('report_chars', '?')}")
                break  # 收到 persisted = 终态
            elif data.get("type") == "stream-error":
                print(f"\n❌ {chunk.get('reason')}")
                break

print("=" * 70)
print(f"\n📈 统计：")
print(f"  事件总数: {events_received}")
print(f"  工具调用: {tool_calls_received}")
print(f"  文本 delta: {text_chunks_received}")
print(f"  耗时: {int(time.time() - start_t)}s")

# 3) 拿持久化的报告
print(f"\n→ GET /thread/{thread_id}")
r = requests.get(f"{BACKEND}/thread/{thread_id}", timeout=15)
state = r.json()
print(f"  active_stream: {state.get('active_stream_id')}")
print(f"  tokens (in/out): {state.get('tokens', {}).get('in')}/{state.get('tokens', {}).get('out')}")
print(f"  credits (in/out): ${state.get('tokens', {}).get('in_credits'):.4f}/${state.get('tokens', {}).get('out_credits'):.4f}")
print(f"  messages: {len(state.get('messages', []))}")

# 把最终报告存到文件
asst = [m for m in state.get('messages', []) if m['role'] == 'assistant']
if asst:
    last = asst[-1]
    final_text = ""
    for p in (last.get('parts') or []):
        if isinstance(p, dict) and p.get('type') == 'text':
            final_text += p.get('text', '')
    
    from pathlib import Path
    out = Path(f"reports/backend_test_{thread_id[:8]}.md")
    out.write_text(f"# Backend Test — thread {thread_id}\n\n{final_text}\n", encoding="utf-8")
    print(f"\n📄 最终报告已存：{out.absolute()}")
    print(f"   字数：{len(final_text)}")
