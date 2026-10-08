"""CloudTech Workflows Base — 共享 RunHistoryTracker + 错误/状态/校验

设计要点:
  * RunHistoryTracker: start/cancel/get_status — 所有 24 workflow 共享
  * 状态机: pending → running → success/failed/cancelled
  * 数据落盘: workflow_runs.jsonl (JSONL append-only)
  * 校验器: validate_workflow_yaml / validate_workflow_json
  * 不依赖任何外部 API; mock-only
"""
from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ════════════════════════════════════════════════════════
# 状态机
# ════════════════════════════════════════════════════════

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowError(Exception):
    """Workflow 运行错误 (output 字段用)"""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}


# ════════════════════════════════════════════════════════
# Run Record
# ════════════════════════════════════════════════════════

@dataclass
class RunRecord:
    run_id: str
    workflow_id: str
    status: WorkflowStatus
    tenant_id: str
    input_summary: Dict[str, Any]
    started_at: str
    finished_at: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value if isinstance(self.status, WorkflowStatus) else self.status,
            "tenant_id": self.tenant_id,
            "input_summary": self.input_summary,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "output": self.output,
            "error": self.error,
        }


# ════════════════════════════════════════════════════════
# RunHistoryTracker — 线程安全单例
# ════════════════════════════════════════════════════════

class RunHistoryTracker:
    """所有 24 workflow 共用的运行历史追踪器 (start / cancel / get_status / list)."""

    _instance: Optional["RunHistoryTracker"] = None
    _lock = threading.Lock()

    def __init__(self, log_path: Optional[Path] = None):
        self._runs: Dict[str, RunRecord] = {}
        self._mtx = threading.Lock()
        if log_path is None:
            base = Path(__file__).parent
            log_path = base / "_runtime.jsonl"
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.reset()  # 测试隔离

    @classmethod
    def instance(cls) -> "RunHistoryTracker":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def reset(self) -> None:
        """清空当前 tracker 内存中的运行记录 (测试用)"""
        with self._mtx:
            self._runs.clear()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _persist(self, rec: RunRecord) -> None:
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def start(self, workflow_id: str, tenant_id: str, input_summary: Dict[str, Any]) -> RunRecord:
        run_id = "run_" + secrets.token_hex(8)
        rec = RunRecord(
            run_id=run_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            tenant_id=tenant_id,
            input_summary=input_summary,
            started_at=self._now(),
        )
        with self._mtx:
            self._runs[run_id] = rec
        return rec

    def mark_running(self, run_id: str) -> None:
        with self._mtx:
            rec = self._runs.get(run_id)
            if rec is None:
                return
            rec.status = WorkflowStatus.RUNNING

    def mark_success(self, run_id: str, output: Dict[str, Any]) -> None:
        with self._mtx:
            rec = self._runs.get(run_id)
            if rec is None:
                return
            rec.status = WorkflowStatus.SUCCESS
            rec.finished_at = self._now()
            rec.output = output
        self._persist(rec)

    def mark_failed(self, run_id: str, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        with self._mtx:
            rec = self._runs.get(run_id)
            if rec is None:
                return
            rec.status = WorkflowStatus.FAILED
            rec.finished_at = self._now()
            rec.error = {"code": code, "message": message, "details": details or {}}
        self._persist(rec)

    def cancel(self, run_id: str) -> bool:
        with self._mtx:
            rec = self._runs.get(run_id)
            if rec is None:
                return False
            if rec.status in (WorkflowStatus.SUCCESS, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
                return False
            rec.status = WorkflowStatus.CANCELLED
            rec.finished_at = self._now()
        self._persist(rec)
        return True

    def get_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._mtx:
            rec = self._runs.get(run_id)
            if rec is None:
                return None
            return rec.to_dict()

    def list_runs(
        self,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        with self._mtx:
            items = list(self._runs.values())
        if workflow_id:
            items = [r for r in items if r.workflow_id == workflow_id]
        if tenant_id:
            items = [r for r in items if r.tenant_id == tenant_id]
        items.sort(key=lambda r: r.started_at, reverse=True)
        return [r.to_dict() for r in items[:limit]]


# ════════════════════════════════════════════════════════
# run_workflow 装饰器
# ════════════════════════════════════════════════════════

def run_workflow(workflow_id: str, tenant_field: str = "tenant_id"):
    """装饰器: sync run 函数 → 统一返回 {run_id, status, output|error}"""
    def deco(fn: Callable[..., Any]):
        def call(*args, **kwargs):
            if args and hasattr(args[0], tenant_field):
                tenant_id = getattr(args[0], tenant_field)
                input_obj = args[0]
            elif "input" in kwargs and hasattr(kwargs["input"], tenant_field):
                tenant_id = getattr(kwargs["input"], tenant_field)
                input_obj = kwargs["input"]
            else:
                raise WorkflowError("WF-001", "缺少 tenant_id 字段")

            tracker = RunHistoryTracker.instance()
            summary = _safe_summary(input_obj)
            rec = tracker.start(workflow_id, tenant_id, summary)
            run_id = rec.run_id

            tracker.mark_running(run_id)

            try:
                out = fn(input_obj, **kwargs)
            except WorkflowError as e:
                tracker.mark_failed(run_id, e.code, e.message, e.details)
                return {"run_id": run_id, "status": "failed",
                        "error": {"code": e.code, "message": e.message, "details": e.details}}
            except Exception as e:
                tracker.mark_failed(run_id, "WF-EXCEPTION", str(e))
                return {"run_id": run_id, "status": "failed",
                        "error": {"code": "WF-EXCEPTION", "message": str(e)}}

            current = tracker.get_status(run_id)
            if current and current["status"] == "cancelled":
                return {"run_id": run_id, "status": "cancelled", "output": None}

            if hasattr(out, "model_dump"):
                output = out.model_dump()
            elif isinstance(out, dict):
                output = dict(out)
            else:
                output = {"data": out}
            output["run_id"] = run_id
            tracker.mark_success(run_id, output)
            return {"run_id": run_id, "status": "success", "output": output}
        return call
    return deco


def _safe_summary(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        d = obj.model_dump()
    elif isinstance(obj, dict):
        d = obj
    else:
        d = {"_repr": repr(obj)[:200]}
    for k, v in list(d.items()):
        if isinstance(v, str) and len(v) > 120:
            d[k] = v[:120] + "..."
        elif isinstance(v, list) and len(v) > 8:
            d[k] = f"<list len={len(v)}>"
    return d


# ════════════════════════════════════════════════════════
# YAML/JSON 校验器 (Pydantic-based)
# ════════════════════════════════════════════════════════

def _coerce_yaml_value(v: str) -> Any:
    """YAML scalar 简单类型推断"""
    s = v.strip()
    if not s:
        return s
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    if s.lower() in ("null", "~", "none"):
        return None
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_coerce_yaml_value(x) for x in inner.split(",")]
    return s


def validate_workflow_yaml(yaml_text: str, schema_model: Any) -> Dict[str, Any]:
    """极简 YAML 校验: 用 line-based key:value 解析 + pydantic schema 校验."""
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        return {"ok": False, "errors": [{"code": "WF-YAML-EMPTY", "msg": "YAML 文本为空"}]}
    lines = [l for l in yaml_text.splitlines() if l.strip() and not l.strip().startswith("#")]
    parsed: Dict[str, Any] = {}
    for line in lines:
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        parsed[k.strip()] = _coerce_yaml_value(v.strip())
    try:
        schema_model(**parsed)
    except Exception as e:
        return {"ok": False, "errors": [{"code": "WF-YAML-SCHEMA", "msg": str(e)}]}
    return {"ok": True, "parsed": parsed}


def validate_workflow_json(json_text: str, schema_model: Any) -> Dict[str, Any]:
    if not isinstance(json_text, str) or not json_text.strip():
        return {"ok": False, "errors": [{"code": "WF-JSON-EMPTY", "msg": "JSON 文本为空"}]}
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        return {"ok": False, "errors": [{"code": "WF-JSON-PARSE", "msg": str(e)}]}
    if not isinstance(data, dict):
        return {"ok": False, "errors": [{"code": "WF-JSON-NOT-OBJ", "msg": "必须是 JSON 对象"}]}
    try:
        schema_model(**data)
    except Exception as e:
        return {"ok": False, "errors": [{"code": "WF-JSON-SCHEMA", "msg": str(e)}]}
    return {"ok": True, "parsed": data}


# ════════════════════════════════════════════════════════
# 通用常量
# ════════════════════════════════════════════════════════

INDUSTRIES = ("decoration", "medical", "education", "catering", "retail")
PLANS = ("free", "starter", "pro", "enterprise")
DECORATION_CITIES = ("厦门", "泉州", "福州", "漳州", "莆田", "龙岩", "三明", "南平", "宁德")
PLATFORMS_T = ("douyin", "xiaohongshu", "wechat", "shipinhao", "kuaishou", "bilibili")