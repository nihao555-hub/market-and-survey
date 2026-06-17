"""
Backend 多租户鉴权 + 简易监控（对应 backend steering 安全要求）

- API Key 鉴权：请求头 `X-API-Key`，映射到 tenant_id 做多租户隔离
- dev 模式（BACKEND_AUTH_REQUIRED=0）放行无 key 请求，归到 dev_tenant
- 生产模式（=1）强制校验，无效 key → 401
- 监控：进程内计数器（请求数/各租户用量/错误数），供 /metrics 暴露
"""
from __future__ import annotations
import os, time, threading
from collections import defaultdict
from fastapi import Header, HTTPException
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_RAW = os.getenv("BACKEND_API_KEYS", "dev-key-local:dev_tenant")
AUTH_REQUIRED = os.getenv("BACKEND_AUTH_REQUIRED", "0") == "1"

# 解析 "key:tenant,key2:tenant2"
API_KEYS: dict[str, str] = {}
for pair in _RAW.split(","):
    pair = pair.strip()
    if ":" in pair:
        k, tid = pair.split(":", 1)
        API_KEYS[k.strip()] = tid.strip()


# ───────── 进程内监控计数器（线程安全）─────────
_lock = threading.Lock()
_metrics = {
    "started_at": time.time(),
    "requests_total": 0,
    "requests_by_tenant": defaultdict(int),
    "errors_total": 0,
    "auth_failures": 0,
    "selection_jobs_started": 0,
}


def record_request(tenant_id: str):
    with _lock:
        _metrics["requests_total"] += 1
        _metrics["requests_by_tenant"][tenant_id] += 1


def record_error():
    with _lock:
        _metrics["errors_total"] += 1


def record_job_start():
    with _lock:
        _metrics["selection_jobs_started"] += 1


def get_metrics() -> dict:
    with _lock:
        uptime = int(time.time() - _metrics["started_at"])
        return {
            "uptime_sec": uptime,
            "requests_total": _metrics["requests_total"],
            "requests_by_tenant": dict(_metrics["requests_by_tenant"]),
            "errors_total": _metrics["errors_total"],
            "auth_failures": _metrics["auth_failures"],
            "selection_jobs_started": _metrics["selection_jobs_started"],
            "auth_required": AUTH_REQUIRED,
            "tenants_configured": len(API_KEYS),
        }


async def require_tenant(x_api_key: str | None = Header(default=None)) -> str:
    """
    FastAPI 依赖：校验 API Key，返回 tenant_id。
    - 有效 key → 对应 tenant_id
    - dev 模式 + 无 key → dev_tenant（放行）
    - 生产模式 + 无效/缺失 key → 401
    """
    if x_api_key and x_api_key in API_KEYS:
        tid = API_KEYS[x_api_key]
        record_request(tid)
        return tid
    if not AUTH_REQUIRED:
        record_request("dev_tenant")
        return "dev_tenant"
    with _lock:
        _metrics["auth_failures"] += 1
    raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
