"""WF-G-024 企业离线导出 — 通用
=============================
输入: tenant_id, export_scope (覆盖 tenants/leads/sops/calls/contracts), format (jsonl/csv)
输出: exported_files[] (path, sha256, size), manifest (含 schema + count), integrity_check
"""
from __future__ import annotations
import hashlib
import json
import secrets
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class ExportInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    export_scope: List[str] = Field(..., min_length=1)
    format: str = Field(default="jsonl")
    records: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    workflow_id: str = Field(default="WF-G-024", pattern=r"^WF-G-\d{3}$")

    @field_validator("export_scope")
    @classmethod
    def scope_ok(cls, v):
        allowed = {"tenants", "leads", "sops", "calls", "contracts", "knowledge"}
        for s in v:
            if s not in allowed:
                raise ValueError(f"export_scope 元素必须 ∈ {allowed}")
        return v

    @field_validator("format")
    @classmethod
    def fmt_ok(cls, v):
        if v not in ("jsonl", "csv"):
            raise ValueError("format ∈ {jsonl, csv}")
        return v


class ExportedFile(BaseModel):
    scope: str
    path: str
    sha256: str
    size_bytes: int
    count: int


class ExportOutput(BaseModel):
    export_id: str
    files: List[ExportedFile]
    manifest: Dict[str, Any]
    integrity_check: str


def _to_csv(records: List[Dict[str, Any]]) -> str:
    if not records:
        return ""
    headers = sorted({k for r in records for k in r.keys()})
    lines = [",".join(headers)]
    for r in records:
        lines.append(",".join(str(r.get(h, "")).replace(",", ";").replace("\n", " ") for h in headers))
    return "\n".join(lines) + "\n"


def _to_jsonl(records: List[Dict[str, Any]]) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"


@run_workflow(workflow_id="WF-G-024", tenant_field="tenant_id")
def run_export(inp: ExportInput) -> ExportOutput:
    if not inp.export_scope:
        raise WorkflowError("WF-G024-SCOPE", "export_scope 不能为空")
    export_id = "exp-" + secrets.token_hex(6)
    base_dir = Path(__file__).resolve().parent / "_exports" / export_id
    base_dir.mkdir(parents=True, exist_ok=True)
    files: List[ExportedFile] = []
    manifest_sections: Dict[str, Any] = {}

    for scope in inp.export_scope:
        recs = inp.records.get(scope, [])
        if inp.format == "csv":
            content = _to_csv(recs)
        else:
            content = _to_jsonl(recs)
        fpath = base_dir / f"{scope}.{inp.format}"
        fpath.write_text(content, encoding="utf-8")
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        size = fpath.stat().st_size
        files.append(ExportedFile(scope=scope, path=str(fpath), sha256=sha, size_bytes=size, count=len(recs)))
        manifest_sections[scope] = {"count": len(recs), "sha256": sha, "size": size}

    manifest = {
        "export_id": export_id,
        "tenant_id": inp.tenant_id,
        "format": inp.format,
        "scope": inp.export_scope,
        "sections": manifest_sections,
    }
    manifest_path = base_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    sha_manifest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    return ExportOutput(
        export_id=export_id,
        files=files,
        manifest=manifest_sections,
        integrity_check=f"manifest sha256={sha_manifest[:16]}",
    )


validate_json = lambda s: validate_workflow_json(s, ExportInput)
validate_yaml = lambda s: validate_workflow_yaml(s, ExportInput)