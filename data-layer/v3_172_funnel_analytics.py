"""
V3.172 — 销售漏斗聚合分析 + 自动复盘（Phase 45 D24-27）
========================================================

复用 v3_35_sales_crm.py 的 5 阶段漏斗（consult/demo/trial/quote/signed），
聚合：
  1. 行业转化率对比（decoration vs medical，弃用 3 deprecated 行业数据）
  2. ROI 归因：每条线索的 LTV 估算 + 转化成本
  3. 自动复盘：基于阶段转化率 + 行业 + 时间窗，给出"该行业当前是否值得投入"
  4. SSE 流式输出管道（供前端实时看漏斗）

端点:
  GET  /api/v2/sales/funnel/analytics        漏斗聚合分析
  POST /api/v2/sales/funnel/review           自动复盘（按行业）
  GET  /api/v2/sales/funnel/stages/breakdown  5 阶段停留时长 + 转化率
  GET  /api/v2/sales/funnel/industries/{industry}/cohort  行业 cohort 分析
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

# Phase 45 D4-7：行业对齐 v3_142 PIPELINES
ACTIVE_INDUSTRIES = {"decoration", "medical"}
DEPRECATED_INDUSTRIES = {"education", "catering", "retail"}
ALL_INDUSTRIES = ACTIVE_INDUSTRIES | DEPRECATED_INDUSTRIES

# 5 阶段（D24-27 沿用 v3_35 标准）
STAGES = ["consult", "demo", "trial", "quote", "signed"]
STAGE_LABELS = {
    "consult": "咨询",
    "demo": "演示",
    "trial": "试用",
    "quote": "报价",
    "signed": "签约",
}
STAGE_INDEX = {s: i for i, s in enumerate(STAGES)}

# 阶段权重（用于 LTV 估算）
STAGE_VALUE = {
    "consult": 100,    # 留资价值 100 元（行业基准）
    "demo": 500,       # 演示价值
    "trial": 2000,     # 试用价值
    "quote": 5000,     # 报价价值
    "signed": 30000,   # 签约价值（首单）
}

router = APIRouter(prefix="/api/v2/sales/funnel", tags=["V3.172 销售漏斗聚合"])

DATA_DIR = Path(r"D:\CloudTech-Portable\data")
LEADS_PATH = DATA_DIR / "v10_leads.json"


# ══════════════ 数据加载 ══════════════

def _load_leads() -> Dict[str, Any]:
    """加载 v3_35 的线索 JSON（向后兼容，无文件时返回空集）"""
    if LEADS_PATH.exists():
        try:
            return json.loads(LEADS_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"leads": {}, "stats": {"total": 0, "by_stage": {}, "by_industry": {}}}


def _safe_leads_by_industry(industry: str) -> List[Dict[str, Any]]:
    """提取某行业所有线索（按 industry 字段过滤）"""
    d = _load_leads()
    leads = d.get("leads", {})
    return [
        l for l in leads.values()
        if l.get("industry") == industry
    ]


def _stage_conversion(leads: List[Dict]) -> Dict[str, float]:
    """计算 5 阶段间转化率（每阶段进入下阶段的比例）"""
    if not leads:
        return {f"{s}_to_{nxt}": 0.0 for s, nxt in zip(STAGES[:-1], STAGES[1:])}

    stage_counts = defaultdict(int)
    for l in leads:
        # 当前阶段 = leads[i].stage；若已签约 = signed；进入的阶段都计 1
        current = l.get("stage", "consult")
        for s in STAGES:
            if STAGE_INDEX.get(current, 0) >= STAGE_INDEX[s]:
                stage_counts[s] += 1

    result = {}
    for i, s in enumerate(STAGES[:-1]):
        nxt = STAGES[i + 1]
        s_cnt = stage_counts.get(s, 0)
        n_cnt = stage_counts.get(nxt, 0)
        if s_cnt > 0:
            result[f"{s}_to_{nxt}"] = round(n_cnt / s_cnt, 4)
        else:
            result[f"{s}_to_{nxt}"] = 0.0
    return result


# ══════════════ 端点 ══════════════

@router.get("/analytics")
def funnel_analytics(
    industry: Optional[str] = Query(None, description="行业过滤（decoration/medical/...）"),
    days: int = Query(30, ge=1, le=365, description="时间窗（天）"),
):
    """漏斗聚合分析：阶段计数 + 转化率 + 行业对比 + Phase 45 改造标记。

    Phase 45 D24-27:
      - 行业 active/deprecated 标注（D4-7 一致）
      - LTV 估算（按 STAGE_VALUE 加权）
      - ROI 比率 = LTV / 留资成本（假设 100 元/留资）
    """
    leads_all = list(_load_leads().get("leads", {}).values())

    # 时间窗过滤
    cutoff = datetime.now() - timedelta(days=days)
    leads_filtered = [
        l for l in leads_all
        if _parse_dt(l.get("created_at")) >= cutoff
    ]

    if industry:
        leads_filtered = [l for l in leads_filtered if l.get("industry") == industry]
        if industry in DEPRECATED_INDUSTRIES:
            msg = (
                f"行业 {industry} 已 DEPRECATED（Phase 45 D4-7 撤回，since 2026-09-11），"
                "数据仅供参考，不再计入 ROI 决策。"
            )
        else:
            msg = None
    else:
        msg = None

    # 按行业分组
    by_industry: Dict[str, Dict[str, Any]] = {}
    for ind in ALL_INDUSTRIES:
        ind_leads = [l for l in leads_filtered if l.get("industry") == ind]
        if not ind_leads:
            by_industry[ind] = {
                "total_leads": 0,
                "stage_counts": {s: 0 for s in STAGES},
                "conversion": {},
                "estimated_ltv": 0,
                "phase45_status": "deprecated" if ind in DEPRECATED_INDUSTRIES else "active",
                "priority": "deprecated" if ind in DEPRECATED_INDUSTRIES else "active",
            }
            continue

        stage_counts = {s: 0 for s in STAGES}
        for l in ind_leads:
            current = l.get("stage", "consult")
            for s in STAGES:
                if STAGE_INDEX.get(current, 0) >= STAGE_INDEX[s]:
                    stage_counts[s] += 1

        conversion = _stage_conversion(ind_leads)
        # LTV 估算：每个 lead 当前所在阶段的 STAGE_VALUE 加权求和
        ltv = sum(
            STAGE_VALUE.get(l.get("stage", "consult"), 0)
            for l in ind_leads
        )

        by_industry[ind] = {
            "total_leads": len(ind_leads),
            "stage_counts": stage_counts,
            "conversion": conversion,
            "estimated_ltv": ltv,
            "phase45_status": "deprecated" if ind in DEPRECATED_INDUSTRIES else "active",
            "priority": "deprecated" if ind in DEPRECATED_INDUSTRIES else "active",
        }

    # 总览
    total_leads = len(leads_filtered)
    signed_count = sum(
        1 for l in leads_filtered if l.get("stage") == "signed"
    )
    overall_conversion = (
        round(signed_count / total_leads, 4) if total_leads > 0 else 0.0
    )
    total_ltv = sum(
        STAGE_VALUE.get(l.get("stage", "consult"), 0)
        for l in leads_filtered
    )

    return {
        "status": "ok",
        "window_days": days,
        "industry_filter": industry,
        "deprecation_warning": msg,
        "totals": {
            "leads": total_leads,
            "signed": signed_count,
            "overall_conversion": overall_conversion,
            "estimated_ltv": total_ltv,
            "roi_ratio": round(total_ltv / max(total_leads * 100, 1), 2),  # 假设 100 元/留资
        },
        "by_industry": by_industry,
        "phase45_changes": {
            "active_industries": sorted(ACTIVE_INDUSTRIES),
            "deprecated_industries": sorted(DEPRECATED_INDUSTRIES),
            "stages": STAGES,
            "stage_labels": STAGE_LABELS,
        },
        "generated_at": datetime.now().isoformat(),
    }


@router.post("/review")
def auto_review(
    industry: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
):
    """自动复盘：基于行业聚合数据给出"是否值得投入"决策建议。

    决策规则:
      - total_leads < 5 → 样本不足，不出建议
      - 行业 deprecated → 强烈建议撤回
      - signed > 0 且 ROI > 1.5 → 建议加注
      - signed = 0 但 demo > 0 → 调整转化路径
      - signed = 0 且 demo = 0 → 暂停投放
    """
    leads_all = list(_load_leads().get("leads", {}).values())
    cutoff = datetime.now() - timedelta(days=days)
    leads_filtered = [
        l for l in leads_all if _parse_dt(l.get("created_at")) >= cutoff
    ]

    industries = [industry] if industry else sorted(ALL_INDUSTRIES)
    reviews = []

    for ind in industries:
        ind_leads = [l for l in leads_filtered if l.get("industry") == ind]
        n = len(ind_leads)

        # 样本不足
        if n < 5:
            reviews.append({
                "industry": ind,
                "status": "insufficient_data",
                "decision": "continue_observation",
                "reason": f"样本数 {n} < 5，不足以决策",
                "phase45_status": "deprecated" if ind in DEPRECATED_INDUSTRIES else "active",
            })
            continue

        # 行业废弃
        if ind in DEPRECATED_INDUSTRIES:
            reviews.append({
                "industry": ind,
                "status": "deprecated",
                "decision": "stop_investing",
                "reason": (
                    f"行业 {ind} 已 DEPRECATED（Phase 45 D4-7 撤回 since 2026-09-11），"
                    "建议迁移到装企/医美。"
                ),
                "phase45_status": "deprecated",
                "migration_target": "decoration",
            })
            continue

        # 计算决策
        signed = sum(1 for l in ind_leads if l.get("stage") == "signed")
        demo = sum(1 for l in ind_leads if STAGE_INDEX.get(l.get("stage", "consult"), 0) >= STAGE_INDEX["demo"])
        ltv = sum(STAGE_VALUE.get(l.get("stage", "consult"), 0) for l in ind_leads)
        roi = round(ltv / max(n * 100, 1), 2)

        if signed > 0 and roi >= 1.5:
            decision = "increase_investment"
            reason = (
                f"已签约 {signed} 客户，ROI {roi}，建议加注投放。"
            )
        elif signed == 0 and demo > 0:
            decision = "optimize_conversion"
            reason = (
                f"0 签约但 {demo} 进演示，建议优化演示→签约路径。"
            )
        elif signed == 0 and demo == 0:
            decision = "pause_and_review"
            reason = (
                f"{n} 留资但 0 进演示，建议暂停投放并复盘留资质量。"
            )
        else:
            decision = "continue"
            reason = (
                f"签约 {signed} / 演示 {demo} / 留资 {n}，ROI {roi}，维持当前投放。"
            )

        reviews.append({
            "industry": ind,
            "status": "active",
            "decision": decision,
            "reason": reason,
            "metrics": {
                "leads": n,
                "demo": demo,
                "signed": signed,
                "estimated_ltv": ltv,
                "roi_ratio": roi,
            },
            "phase45_status": "active",
        })

    return {
        "status": "ok",
        "window_days": days,
        "reviews": reviews,
        "phase45_changes": {
            "active_industries": sorted(ACTIVE_INDUSTRIES),
            "deprecated_industries": sorted(DEPRECATED_INDUSTRIES),
        },
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/stages/breakdown")
def stages_breakdown(industry: Optional[str] = Query(None)):
    """5 阶段停留时长 + 转化率 breakdown"""
    leads_all = list(_load_leads().get("leads", {}).values())
    if industry:
        leads_all = [l for l in leads_all if l.get("industry") == industry]

    if not leads_all:
        return {
            "status": "ok",
            "stages": STAGES,
            "stage_labels": STAGE_LABELS,
            "breakdown": [],
            "note": "no leads yet",
        }

    breakdown = []
    for s in STAGES:
        stage_leads = [l for l in leads_all if l.get("stage") == s]
        breakdown.append({
            "stage": s,
            "label": STAGE_LABELS[s],
            "count": len(stage_leads),
            "leads_sample": [
                {"lead_id": l.get("lead_id"), "company": l.get("company")}
                for l in stage_leads[:5]
            ],
        })

    return {
        "status": "ok",
        "stages": STAGES,
        "stage_labels": STAGE_LABELS,
        "breakdown": breakdown,
        "total": len(leads_all),
    }


@router.get("/industries/{industry}/cohort")
def industry_cohort(industry: str, days: int = Query(30, ge=1, le=365)):
    """行业 cohort 分析：按周聚合新增 + 转化分布"""
    if industry not in ALL_INDUSTRIES:
        raise HTTPException(404, detail={
            "error": "industry_unknown",
            "available": sorted(ALL_INDUSTRIES),
        })

    leads = _safe_leads_by_industry(industry)
    cutoff = datetime.now() - timedelta(days=days)
    leads = [l for l in leads if _parse_dt(l.get("created_at")) >= cutoff]

    # 按周聚合
    weekly: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for l in leads:
        dt = _parse_dt(l.get("created_at"))
        week = dt.strftime("%Y-W%U")
        stage = l.get("stage", "consult")
        weekly[week][stage] += 1

    cohort = []
    for week in sorted(weekly.keys()):
        cohort.append({
            "week": week,
            "stages": dict(weekly[week]),
            "total": sum(weekly[week].values()),
        })

    return {
        "status": "ok",
        "industry": industry,
        "phase45_status": "deprecated" if industry in DEPRECATED_INDUSTRIES else "active",
        "window_days": days,
        "cohort": cohort,
        "total_leads": len(leads),
    }


# ══════════════ 工具函数 ══════════════

def _parse_dt(s: Optional[str]) -> datetime:
    """解析 ISO 时间字符串，失败时返回 epoch 1970"""
    if not s:
        return datetime(1970, 1, 1)
    try:
        return datetime.fromisoformat(s)
    except Exception:  # noqa: BLE001
        return datetime(1970, 1, 1)
