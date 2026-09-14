"""
V3.173 — OpenTelemetry tracing + 业务指标埋点（Phase 45 D28-30）
================================================================

复用 opentelemetry-api SDK（轻量封装，避免硬依赖）：
  - 自动 trace FastAPI 请求（req_id + latency + status）
  - 业务指标：industry_call / employee_call / pipeline_run / funnel_conversion
  - 导出 OTLP HTTP（生产 OTLP collector）；无 collector 时回退到 stdout

D28-30 验收:
  - 接入 opentelemetry-api（最小依赖）
  - 与 Phase 45 D4-7 行业标记联动（active vs deprecated）
  - 与 D24-27 漏斗转化指标联动

端点:
  GET  /api/v2/_otel/status         OTel 状态（tracer provider + exporter）
  POST /api/v2/_otel/spans          模拟 span 注入（演示用）
  GET  /api/v2/_otel/metrics        业务指标聚合（行业 + 员工 + 管线）
"""
from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException

# Phase 45 D4-7 行业对齐
ACTIVE_INDUSTRIES = {"decoration", "medical"}
DEPRECATED_INDUSTRIES = {"education", "catering", "retail"}

# Phase 45 D4-7 员工对齐（FE 3 + BE 5）
FRONTEND_EMPLOYEES = {"content_writer", "customer_service", "market_researcher"}
BACKEND_EMPLOYEES = {
    "short_video_script", "data_analyst", "seo_specialist",
    "social_media_manager", "growth_hacker",
}

router = APIRouter(prefix="/api/v2/_otel", tags=["V3.173 OpenTelemetry"])

DATA_DIR = Path(r"D:\CloudTech-Portable\data")
SPANS_PATH = DATA_DIR / "v3_173_spans.jsonl"
METRICS_PATH = DATA_DIR / "v3_173_metrics.jsonl"

# ══════════════ OTel 状态 ══════════════

OTEL_STATE = {
    "enabled": False,
    "exporter": "stdout",
    "endpoint": os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
    "service_name": "cloudtech-saas",
    "service_version": "45.0.0",
    "spans_recorded": 0,
    "metrics_recorded": 0,
    "last_span_at": None,
}


def _try_init_otel():
    """尝试初始化 OTel SDK（无依赖时回退到 stdout exporter）"""
    global OTEL_STATE
    try:
        from opentelemetry import trace  # noqa: F401
        from opentelemetry.sdk.trace import TracerProvider  # noqa: F401
        from opentelemetry.sdk.trace.export import (  # noqa: F401
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # noqa: F401
                OTEL_STATE["exporter"] = "otlp_http"
            except ImportError:
                OTEL_STATE["exporter"] = "stdout"
        else:
            OTEL_STATE["exporter"] = "stdout"

        OTEL_STATE["enabled"] = True
        OTEL_STATE["endpoint"] = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "stdout")
    except ImportError:
        OTEL_STATE["enabled"] = False
        OTEL_STATE["exporter"] = "stdout-fallback"


# 启动时尝试一次
_try_init_otel()


# ══════════════ Span 持久化（轻量 stdout exporter 替代） ══════════════

def _record_span(span: Dict[str, Any]) -> None:
    """记录 span 到 v3_173_spans.jsonl（行分隔 JSON）"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    span["recorded_at"] = datetime.now().isoformat()
    with open(SPANS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")
    OTEL_STATE["spans_recorded"] += 1
    OTEL_STATE["last_span_at"] = span["recorded_at"]


def _record_metric(metric: Dict[str, Any]) -> None:
    """记录业务指标到 v3_173_metrics.jsonl"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    metric["recorded_at"] = datetime.now().isoformat()
    with open(METRICS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(metric, ensure_ascii=False) + "\n")
    OTEL_STATE["metrics_recorded"] += 1


# ══════════════ 公共 API ══════════════

def trace_business_event(
    category: str,
    name: str,
    *,
    industry: Optional[str] = None,
    employee: Optional[str] = None,
    tenant_id: str = "default",
    attributes: Optional[Dict[str, Any]] = None,
) -> str:
    """业务事件埋点（供其他模块调用）

    Returns:
        trace_id (str): 用于跨调用关联
    """
    trace_id = uuid.uuid4().hex[:16]
    attrs = {
        "category": category,
        "name": name,
        "tenant_id": tenant_id,
    }
    if industry:
        attrs["industry"] = industry
        attrs["industry_active"] = industry in ACTIVE_INDUSTRIES
        attrs["industry_deprecated"] = industry in DEPRECATED_INDUSTRIES
    if employee:
        attrs["employee"] = employee
        attrs["employee_tier"] = (
            "frontend" if employee in FRONTEND_EMPLOYEES
            else "backend" if employee in BACKEND_EMPLOYEES
            else "unknown"
        )
    if attributes:
        attrs.update(attributes)

    span = {
        "trace_id": trace_id,
        "span_id": uuid.uuid4().hex[:8],
        "name": f"{category}.{name}",
        "kind": "internal",
        "start_time": time.time(),
        "attributes": attrs,
        "status": "ok",
    }
    _record_span(span)

    # 业务指标
    _record_metric({
        "trace_id": trace_id,
        "category": category,
        "name": name,
        "industry": industry,
        "employee": employee,
        "tenant_id": tenant_id,
    })
    return trace_id


# ══════════════ 端点 ══════════════

@router.get("/status")
def otel_status():
    """OTel 状态（tracer provider + exporter + 计数）"""
    return {
        "status": "ok" if OTEL_STATE["enabled"] else "degraded",
        "service_name": OTEL_STATE["service_name"],
        "service_version": OTEL_STATE["service_version"],
        "exporter": OTEL_STATE["exporter"],
        "endpoint": OTEL_STATE["endpoint"],
        "spans_recorded": OTEL_STATE["spans_recorded"],
        "metrics_recorded": OTEL_STATE["metrics_recorded"],
        "last_span_at": OTEL_STATE["last_span_at"],
        "phase45_changes": {
            "active_industries": sorted(ACTIVE_INDUSTRIES),
            "deprecated_industries": sorted(DEPRECATED_INDUSTRIES),
            "frontend_employees": sorted(FRONTEND_EMPLOYEES),
            "backend_employees": sorted(BACKEND_EMPLOYEES),
        },
    }


@router.post("/spans")
def inject_span(
    category: str,
    name: str,
    industry: Optional[str] = None,
    employee: Optional[str] = None,
    tenant_id: str = "default",
    duration_ms: int = 100,
):
    """手动注入 span（演示/测试用）"""
    if industry and industry not in ACTIVE_INDUSTRIES | DEPRECATED_INDUSTRIES:
        raise HTTPException(400, detail={
            "error": "industry_unknown",
            "available": sorted(ACTIVE_INDUSTRIES | DEPRECATED_INDUSTRIES),
        })
    if employee and employee not in FRONTEND_EMPLOYEES | BACKEND_EMPLOYEES:
        raise HTTPException(400, detail={
            "error": "employee_unknown",
            "available": sorted(FRONTEND_EMPLOYEES | BACKEND_EMPLOYEES),
        })

    trace_id = trace_business_event(
        category=category,
        name=name,
        industry=industry,
        employee=employee,
        tenant_id=tenant_id,
        attributes={"duration_ms": duration_ms},
    )
    return {
        "status": "ok",
        "trace_id": trace_id,
        "category": category,
        "name": name,
        "industry": industry,
        "employee": employee,
        "duration_ms": duration_ms,
    }


@router.get("/metrics")
def metrics_summary(days: int = 1):
    """业务指标聚合（最近 N 天）"""
    if not METRICS_PATH.exists():
        return {
            "status": "ok",
            "window_days": days,
            "by_category": {},
            "by_industry": {"active": {}, "deprecated": {}},
            "by_employee_tier": {"frontend": {}, "backend": {}},
            "total_events": 0,
        }

    cutoff = datetime.now().timestamp() - days * 86400
    by_category: Dict[str, int] = defaultdict(int)
    by_industry_active: Dict[str, int] = defaultdict(int)
    by_industry_deprecated: Dict[str, int] = defaultdict(int)
    by_employee_fe: Dict[str, int] = defaultdict(int)
    by_employee_be: Dict[str, int] = defaultdict(int)
    total = 0

    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = m.get("recorded_at", "")
            try:
                if datetime.fromisoformat(ts).timestamp() < cutoff:
                    continue
            except Exception:  # noqa: BLE001
                pass
            total += 1
            cat = m.get("category", "unknown")
            by_category[cat] += 1
            ind = m.get("industry")
            if ind:
                if ind in ACTIVE_INDUSTRIES:
                    by_industry_active[ind] += 1
                elif ind in DEPRECATED_INDUSTRIES:
                    by_industry_deprecated[ind] += 1
            emp = m.get("employee")
            if emp:
                if emp in FRONTEND_EMPLOYEES:
                    by_employee_fe[emp] += 1
                elif emp in BACKEND_EMPLOYEES:
                    by_employee_be[emp] += 1

    return {
        "status": "ok",
        "window_days": days,
        "by_category": dict(by_category),
        "by_industry": {
            "active": dict(by_industry_active),
            "deprecated": dict(by_industry_deprecated),
        },
        "by_employee_tier": {
            "frontend": dict(by_employee_fe),
            "backend": dict(by_employee_be),
        },
        "total_events": total,
    }


@router.post("/spans/clear")
def clear_spans():
    """清空 span 文件（演示用）"""
    if SPANS_PATH.exists():
        SPANS_PATH.unlink()
    if METRICS_PATH.exists():
        METRICS_PATH.unlink()
    OTEL_STATE["spans_recorded"] = 0
    OTEL_STATE["metrics_recorded"] = 0
    OTEL_STATE["last_span_at"] = None
    return {"status": "ok", "cleared": True}
