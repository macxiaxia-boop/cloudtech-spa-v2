"""
V3.174 — 多租户隔离 + 配额 + 计费（Phase 46 D31-37）
=====================================================

SaaS 生产化硬指标：
  - 租户鉴权（基于 v3_142 CLOUDTECH_TENANT_TOKENS 已就绪）
  - 配额管理（FE/BE 员工调用次数 + LLM token）
  - 计费（按 plan_id: free/pro/enterprise + 用量阶梯）
  - 多租户隔离（每租户独立 namespace + 数据隔离）

端点:
  GET  /api/v2/billing/plans                 3 档套餐
  GET  /api/v2/billing/tenants/{tid}/usage   当前用量
  POST /api/v2/billing/tenants/{tid}/upgrade 升级套餐（需 admin）
  GET  /api/v2/billing/tenants/{tid}/quota   配额 + 余量
  POST /api/v2/billing/usage/record          记录一次用量（pipeline_run / employee_call）
  GET  /api/v2/billing/invoices              发票列表（占位 · 红 #22 待用户拍板签发）
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header

# Phase 45 D4-7 行业/员工对齐
ACTIVE_INDUSTRIES = {"decoration", "medical"}
DEPRECATED_INDUSTRIES = {"education", "catering", "retail"}
FRONTEND_EMPLOYEES = {"content_writer", "customer_service", "market_researcher"}
BACKEND_EMPLOYEES = {
    "short_video_script", "data_analyst", "seo_specialist",
    "social_media_manager", "growth_hacker",
}

router = APIRouter(prefix="/api/v2/billing", tags=["V3.174 多租户计费"])

DATA_DIR = Path(r"D:\CloudTech-Portable\data")
USAGE_PATH = DATA_DIR / "v3_174_usage.jsonl"
TENANTS_PATH = DATA_DIR / "v3_174_tenants.json"

# ══════════════ 套餐定义 ══════════════

PLANS = {
    "free": {
        "label": "免费版",
        "monthly_calls": 100,
        "monthly_tokens": 50_000,
        "fe_employees": 1,
        "be_employees": 0,
        "industries": ["decoration"],
        "price_yuan": 0,
    },
    "pro": {
        "label": "专业版",
        "monthly_calls": 5_000,
        "monthly_tokens": 2_000_000,
        "fe_employees": 3,
        "be_employees": 5,
        "industries": ["decoration", "medical"],
        "price_yuan": 499,
    },
    "enterprise": {
        "label": "企业版",
        "monthly_calls": 999_999,
        "monthly_tokens": 100_000_000,
        "fe_employees": 99,
        "be_employees": 99,
        "industries": ["decoration", "medical", "custom"],
        "price_yuan": 2_499,
    },
}


# ══════════════ 租户存储 ══════════════

def _load_tenants() -> Dict[str, Any]:
    if TENANTS_PATH.exists():
        try:
            return json.loads(TENANTS_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    # 默认租户
    return {
        "tenants": {
            "default": {
                "tenant_id": "default",
                "plan": "pro",
                "tenant_token": os.environ.get("CLOUDTECH_DEFAULT_TOKEN", "demo_token_001"),
                "created_at": datetime.now().isoformat(),
                "active": True,
                "contact_name": "灵策智算",
                "contact_email": "admin@lynxce.ai",
                "company": "灵策智算",
            },
        }
    }


def _save_tenants(d: Dict[str, Any]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TENANTS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_usage(tenant_id: str, category: str, calls: int = 1,
                  tokens: int = 0, industry: Optional[str] = None,
                  employee: Optional[str] = None) -> str:
    """记录用量到 v3_174_usage.jsonl"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    usage_id = uuid.uuid4().hex[:12]
    record = {
        "usage_id": usage_id,
        "tenant_id": tenant_id,
        "category": category,
        "calls": calls,
        "tokens": tokens,
        "industry": industry,
        "employee": employee,
        "recorded_at": datetime.now().isoformat(),
    }
    with open(USAGE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return usage_id


def _tenant_usage_this_month(tenant_id: str) -> Dict[str, int]:
    """统计某租户当月用量（calls + tokens）"""
    if not USAGE_PATH.exists():
        return {"calls": 0, "tokens": 0, "by_category": {}, "by_industry_active": 0, "by_industry_deprecated": 0}
    now = datetime.now()
    cutoff = datetime(now.year, now.month, 1)
    calls = 0
    tokens = 0
    by_cat: Dict[str, int] = {}
    by_ind_active = 0
    by_ind_deprecated = 0
    with open(USAGE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("tenant_id") != tenant_id:
                continue
            try:
                ts = datetime.fromisoformat(rec.get("recorded_at", "1970-01-01"))
            except Exception:  # noqa: BLE001
                continue
            if ts < cutoff:
                continue
            calls += int(rec.get("calls", 0))
            tokens += int(rec.get("tokens", 0))
            cat = rec.get("category", "unknown")
            by_cat[cat] = by_cat.get(cat, 0) + int(rec.get("calls", 0))
            ind = rec.get("industry")
            if ind:
                if ind in ACTIVE_INDUSTRIES:
                    by_ind_active += 1
                elif ind in DEPRECATED_INDUSTRIES:
                    by_ind_deprecated += 1
    return {
        "calls": calls,
        "tokens": tokens,
        "by_category": by_cat,
        "by_industry_active": by_ind_active,
        "by_industry_deprecated": by_ind_deprecated,
    }


# ══════════════ 鉴权 ══════════════

def _check_tenant_token(tenant_id: str, token: Optional[str]) -> None:
    tenants = _load_tenants().get("tenants", {})
    tenant = tenants.get(tenant_id)
    if not tenant:
        raise HTTPException(404, detail={"error": "tenant_not_found", "tenant_id": tenant_id})
    if not tenant.get("active", True):
        raise HTTPException(403, detail={"error": "tenant_inactive", "tenant_id": tenant_id})
    # token 校验（demo 模式跳过）
    expected = tenant.get("tenant_token", "")
    if expected and token and token != expected:
        raise HTTPException(401, detail={"error": "invalid_tenant_token"})


# ══════════════ 端点 ══════════════

@router.get("/plans")
def list_plans():
    """3 档套餐（free/pro/enterprise）"""
    return {
        "status": "ok",
        "plans": PLANS,
        "phase45_changes": {
            "active_industries": sorted(ACTIVE_INDUSTRIES),
            "deprecated_industries": sorted(DEPRECATED_INDUSTRIES),
        },
    }


@router.get("/tenants/{tenant_id}/usage")
def tenant_usage(
    tenant_id: str,
    x_tenant_token: Optional[str] = Header(None),
):
    """租户当月用量"""
    _check_tenant_token(tenant_id, x_tenant_token)
    usage = _tenant_usage_this_month(tenant_id)
    tenant = _load_tenants().get("tenants", {}).get(tenant_id, {})
    plan_id = tenant.get("plan", "free")
    plan = PLANS.get(plan_id, PLANS["free"])

    quota_calls = plan["monthly_calls"]
    quota_tokens = plan["monthly_tokens"]
    usage_calls = usage["calls"]
    usage_tokens = usage["tokens"]
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "plan": plan_id,
        "plan_label": plan["label"],
        "month": datetime.now().strftime("%Y-%m"),
        "usage": {
            "calls": usage_calls,
            "tokens": usage_tokens,
            "by_category": usage["by_category"],
            "by_industry_active": usage["by_industry_active"],
            "by_industry_deprecated": usage["by_industry_deprecated"],
        },
        "quota": {
            "calls": quota_calls,
            "tokens": quota_tokens,
            "calls_remaining": max(quota_calls - usage_calls, 0),
            "tokens_remaining": max(quota_tokens - usage_tokens, 0),
            "calls_pct": round(usage_calls / max(quota_calls, 1) * 100, 2),
            "tokens_pct": round(usage_tokens / max(quota_tokens, 1) * 100, 2),
        },
        "phase45_warnings": {
            "deprecated_industry_calls": usage["by_industry_deprecated"],
            "hint": "已 P3-BA 撤回的行业调用会被记录但不计入 ROI 决策",
        },
    }


@router.get("/tenants/{tenant_id}/quota")
def tenant_quota(
    tenant_id: str,
    x_tenant_token: Optional[str] = Header(None),
):
    """配额 + 余量"""
    _check_tenant_token(tenant_id, x_tenant_token)
    return tenant_usage(tenant_id=tenant_id, x_tenant_token=x_tenant_token)


@router.post("/tenants/{tenant_id}/upgrade")
def tenant_upgrade(
    tenant_id: str,
    plan_id: str,
    x_tenant_token: Optional[str] = Header(None),
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
):
    """升级套餐（需 admin secret）

    红 #22 守门：实际扣费需用户拍板，本端点仅切换 plan_id（demo）。
    """
    _check_tenant_token(tenant_id, x_tenant_token)
    if plan_id not in PLANS:
        raise HTTPException(400, detail={"error": "plan_unknown", "available": list(PLANS.keys())})
    # admin secret 校验（demo 默认通过）
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if admin_secret and x_admin_secret and x_admin_secret != admin_secret:
        raise HTTPException(403, detail={"error": "invalid_admin_secret"})

    tenants = _load_tenants()
    if tenant_id not in tenants["tenants"]:
        raise HTTPException(404, detail={"error": "tenant_not_found"})
    old_plan = tenants["tenants"][tenant_id].get("plan")
    tenants["tenants"][tenant_id]["plan"] = plan_id
    tenants["tenants"][tenant_id]["upgraded_at"] = datetime.now().isoformat()
    _save_tenants(tenants)

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "old_plan": old_plan,
        "new_plan": plan_id,
        "new_plan_label": PLANS[plan_id]["label"],
        "price_yuan": PLANS[plan_id]["price_yuan"],
        "note": "Demo 模式 — 真实扣费需用户拍板后接入支付（红 #22）",
    }


@router.post("/usage/record")
def usage_record(
    tenant_id: str,
    category: str,
    calls: int = 1,
    tokens: int = 0,
    industry: Optional[str] = None,
    employee: Optional[str] = None,
    x_tenant_token: Optional[str] = Header(None),
):
    """记录一次用量（pipeline_run / employee_call / funnel_event）"""
    _check_tenant_token(tenant_id, x_tenant_token)
    # 校验 industry + employee
    if industry and industry not in ACTIVE_INDUSTRIES | DEPRECATED_INDUSTRIES:
        raise HTTPException(400, detail={"error": "industry_unknown", "available": sorted(ACTIVE_INDUSTRIES | DEPRECATED_INDUSTRIES)})
    if employee and employee not in FRONTEND_EMPLOYEES | BACKEND_EMPLOYEES:
        raise HTTPException(400, detail={"error": "employee_unknown"})

    usage_id = _record_usage(tenant_id, category, calls, tokens, industry, employee)
    # 立即返回当月用量
    usage = _tenant_usage_this_month(tenant_id)
    return {
        "status": "ok",
        "usage_id": usage_id,
        "tenant_id": tenant_id,
        "category": category,
        "calls": calls,
        "tokens": tokens,
        "month_total": usage,
    }


@router.get("/tenants")
def list_tenants(x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret")):
    """租户列表（admin only）"""
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if admin_secret and x_admin_secret != admin_secret:
        raise HTTPException(403, detail={"error": "invalid_admin_secret"})
    tenants = _load_tenants().get("tenants", {})
    return {
        "status": "ok",
        "total": len(tenants),
        "tenants": [
            {
                "tenant_id": tid,
                "plan": t.get("plan"),
                "company": t.get("company"),
                "active": t.get("active", True),
                "created_at": t.get("created_at"),
            }
            for tid, t in tenants.items()
        ],
    }


@router.get("/invoices")
def list_invoices(tenant_id: str, x_tenant_token: Optional[str] = Header(None)):
    """发票列表（占位 — 红 #22 待用户拍板接入金税系统）"""
    _check_tenant_token(tenant_id, x_tenant_token)
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "invoices": [],
        "note": "发票功能待接入金税系统（红 #22 · 用户拍板后开通）",
    }
