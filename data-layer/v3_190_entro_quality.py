"""v3_190 EntroCamp · 数据质量 4 维评分引擎 · R321 实现

V3.1 P0 #2 数据质量评分 (EntroCamp) · 真实数据驱动
- 准确性 accuracy:     必填字段非空率
- 完整性 completeness:  总体字段填充率
- 时效性 timeliness:    最近 created_at 距今天数 (越近分越高)
- 一致性 consistency:   id 格式 + 时间格式 + 邮箱格式校验通过率

0-100 分 · <60 标红 · <80 黄 · >=80 绿

端点:
  GET /                           配置 + 总览
  GET /score/{dataset}           单数据集评分
  GET /batch                      全 64 数据集批量 (top 10 red)
  GET /trends                     评分趋势 (最近 7 天)
  GET /alerts                     <60 告警
"""
from __future__ import annotations
import os
import re
import json
import glob
import time
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/v3/v3_190_entro_quality", tags=["entro-quality"])

DATA_DIR = Path(r"D:\CloudTech-Portable\data")
DATA_AUDIT_DIR = DATA_DIR / "audit_logs"
NOW = datetime.now()
EPOCH_NOW = NOW.timestamp()

# 必填字段定义 (按 dataset)
REQUIRED_FIELDS = {
    "admin": ["id", "title", "start_at", "status"],
    "audit_logs": ["timestamp", "action", "service", "severity"],
    "ab_tests": ["timestamp", "test", "variant", "event"],
    "ads": ["id", "platform", "created_at"],
    "agi": ["id", "title", "created_at"],
    "bi_dashboards": ["id", "name", "created_at"],
    "commerce": ["id", "product", "price", "created_at"],
    "competitors": ["id", "name", "url"],
    "compliance_v2": ["id", "rule", "severity"],
    "content_matrix": ["id", "title", "platform", "created_at"],
    "creation_studio": ["id", "asset_type", "created_at"],
    "csm": ["id", "customer_id", "status"],
    "design": ["id", "title", "created_at"],
    "feedback": ["id", "user_id", "rating"],
    "finance": ["id", "amount", "currency"],
    "flywheel_v14": ["id", "phase"],
    "industry_config_v2": ["id", "industry"],
    "insights": ["id", "title", "created_at"],
    "invest": ["id", "name", "stage"],
    "default": ["id"],
}

# 时间字段名候选 (用于时效性)
TIME_FIELDS = ["created_at", "timestamp", "start_at", "updated_at", "time"]

# 评分等级
def grade(score: float) -> str:
    if score < 60:
        return "red"
    if score < 80:
        return "yellow"
    return "green"


def _parse_dt(value: Any) -> Optional[float]:
    """尝试解析时间为 epoch 秒."""
    if not value:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 1e9 else None
    s = str(value)
    # 兼容 ISO + 普通 datetime
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s[: len(fmt) + 5].replace("Z", "+0000"), fmt)
            return dt.timestamp()
        except Exception:
            pass
    # unix_ms (>= 1e12)
    if s.isdigit() and len(s) >= 13:
        return float(s) / 1000.0
    return None


def _id_ok(v: Any) -> bool:
    if not v:
        return False
    s = str(v)
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_:-]{1,80}$", s))


def _email_ok(v: Any) -> bool:
    if not v:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(v)))


def _phone_ok(v: Any) -> bool:
    if not v:
        return False
    return bool(re.match(r"^[\d\-\+\(\)\s]{6,20}$", str(v)))


def _scan_dataset(name: str) -> Dict[str, Any]:
    """扫描单个 jsonl 数据集, 返回 4 维评分."""
    fp = DATA_DIR / f"{name}.jsonl"
    if not fp.exists():
        # audit_logs 特殊: 目录 + 按日期分文件
        if name == "audit_logs" and DATA_AUDIT_DIR.exists():
            files = sorted(DATA_AUDIT_DIR.glob("audit-*.jsonl"))
            lines = []
            for f in files:
                with f.open("r", encoding="utf-8") as fh:
                    lines.extend(fh.readlines())
        else:
            return {"error": "dataset not found", "path": str(fp)}
    else:
        with fp.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()

    total = 0
    acc_ok = 0
    fill_total = 0
    fill_count = 0
    id_ok_count = 0
    time_ok_count = 0
    email_ok_count = 0
    phone_ok_count = 0
    email_seen = 0
    phone_seen = 0
    newest_epoch = 0.0

    req_fields = REQUIRED_FIELDS.get(name, REQUIRED_FIELDS["default"])
    samples: List[Dict[str, Any]] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        # 防御: jsonl 中可能混入 list/str 行, 非 dict 跳过
        if not isinstance(rec, dict):
            continue
        total += 1
        if total <= 2:
            samples.append(rec)

        # 准确性: 必填字段非空率
        for f in req_fields:
            if rec.get(f) not in (None, "", [], {}):
                acc_ok += 1
        acc_total = len(req_fields) * total

        # 完整性: 全字段填充率
        for v in rec.values():
            fill_total += 1
            if v not in (None, "", [], {}):
                fill_count += 1

        # 一致性 (4 项分别计 0-100, 加权平均)
        if _id_ok(rec.get("id")):
            id_ok_count += 1
        # 时间字段一致性
        for tf in TIME_FIELDS:
            v = rec.get(tf)
            if v is not None:
                ep = _parse_dt(v)
                if ep is not None:
                    time_ok_count += 1
                    if ep > newest_epoch:
                        newest_epoch = ep
                break
        # 邮箱
        for k, v in rec.items():
            if "email" in k.lower() and v:
                email_seen += 1
                if _email_ok(v):
                    email_ok_count += 1
                break
        # 手机
        for k, v in rec.items():
            if "phone" in k.lower() or "mobile" in k.lower():
                if v:
                    phone_seen += 1
                    if _phone_ok(v):
                        phone_ok_count += 1
                break

    if total == 0:
        return {"dataset": name, "total": 0, "score": None, "grade": "unknown"}

    accuracy = (acc_ok / acc_total) * 100 if acc_total else 0
    completeness = (fill_count / fill_total) * 100 if fill_total else 0
    # 时效性: 最新记录距今天数 → 分数 (0天=100, 30天=0)
    if newest_epoch:
        days_old = (EPOCH_NOW - newest_epoch) / 86400.0
        timeliness = max(0.0, 100.0 - (days_old * 3.33))  # 30 天归零
    else:
        timeliness = 0
    # 一致性: 4 项分别计 0-100, 加权平均 (缺字段的项退化为 id 通过率)
    id_rate = (id_ok_count / total) * 100 if total else 0
    time_rate = (time_ok_count / total) * 100 if total else 0
    email_rate = (email_ok_count / email_seen) * 100 if email_seen else id_rate
    phone_rate = (phone_ok_count / phone_seen) * 100 if phone_seen else id_rate
    consistency = (id_rate + time_rate + email_rate + phone_rate) / 4

    overall = (accuracy + completeness + timeliness + consistency) / 4

    return {
        "dataset": name,
        "total": total,
        "score": round(overall, 1),
        "grade": grade(overall),
        "dimensions": {
            "accuracy": round(accuracy, 1),
            "completeness": round(completeness, 1),
            "timeliness": round(timeliness, 1),
            "consistency": round(consistency, 1),
        },
        "newest_epoch": newest_epoch,
        "required_fields": req_fields,
        "sample": samples[:2],
    }


@router.get("/")
async def root():
    """配置 + 总览."""
    all_datasets = [p.stem for p in DATA_DIR.glob("*.jsonl")]
    all_datasets.append("audit_logs")
    return {
        "engine": "EntroCamp",
        "version": "1.0.0",
        "module": "v3_190_entro_quality",
        "scoring_dimensions": ["accuracy", "completeness", "timeliness", "consistency"],
        "score_range": "0-100",
        "grade_thresholds": {"red": "<60", "yellow": "60-79", "green": ">=80"},
        "data_dir": str(DATA_DIR),
        "audit_dir": str(DATA_AUDIT_DIR),
        "datasets_count": len(all_datasets),
        "datasets": sorted(all_datasets),
        "endpoints": ["/", "/score/{dataset}", "/batch", "/trends", "/alerts"],
        "ts": NOW.isoformat(timespec="seconds"),
    }


@router.get("/score/{dataset}")
async def score(dataset: str):
    """单数据集评分."""
    return _scan_dataset(dataset)


@router.get("/batch")
async def batch():
    """全 64 数据集批量评分."""
    datasets = sorted({p.stem for p in DATA_DIR.glob("*.jsonl")} | {"audit_logs"})
    results = []
    for name in datasets:
        r = _scan_dataset(name)
        if r.get("error"):
            continue
        results.append(r)
    results.sort(key=lambda x: (x.get("score") or 0))
    return {
        "status": "ok",
        "total": len(results),
        "red_count": sum(1 for r in results if r["grade"] == "red"),
        "yellow_count": sum(1 for r in results if r["grade"] == "yellow"),
        "green_count": sum(1 for r in results if r["grade"] == "green"),
        "top10_worst": [
            {
                "dataset": r.get("dataset"),
                "score": r.get("score") if r.get("score") is not None else "N/A",
                "grade": r.get("grade"),
                "dimensions": r.get("dimensions"),
            }
            for r in results[:10]
        ],
        "all": results,
        "ts": NOW.isoformat(timespec="seconds"),
    }


@router.get("/trends")
async def trends(days: int = 7):
    """评分趋势 (基于 audit_logs 时间分布)."""
    bucket = {}
    if DATA_AUDIT_DIR.exists():
        for f in sorted(DATA_AUDIT_DIR.glob("audit-*.jsonl"))[-days:]:
            day = f.stem.replace("audit-", "")
            try:
                with f.open("r", encoding="utf-8") as fh:
                    lines = fh.readlines()
                bucket[day] = {
                    "count": len(lines),
                    "score": min(100.0, 50.0 + len(lines) / 10),
                }
            except Exception:
                pass
    return {
        "status": "ok",
        "window_days": days,
        "source": "audit_logs/audit-*.jsonl",
        "buckets": bucket,
    }


@router.get("/alerts")
async def alerts(threshold: float = 60.0):
    """<60 告警."""
    datasets = sorted({p.stem for p in DATA_DIR.glob("*.jsonl")} | {"audit_logs"})
    red = []
    for name in datasets:
        r = _scan_dataset(name)
        if r.get("error"):
            continue
        if r.get("score") is not None and r["score"] < threshold:
            red.append({
                "dataset": r["dataset"],
                "score": r["score"],
                "grade": r["grade"],
                "dimensions": r["dimensions"],
                "recommendation": _recommend(r),
            })
    return {
        "status": "ok" if not red else "alert",
        "threshold": threshold,
        "alerts": red,
        "ts": NOW.isoformat(timespec="seconds"),
    }


def _recommend(score_obj: Dict[str, Any]) -> str:
    """最低维度给出修复建议."""
    dims = score_obj.get("dimensions", {})
    if not dims:
        return "无可用建议"
    worst = min(dims, key=dims.get)
    advice = {
        "accuracy":     "补齐必填字段 (id/title/...)",
        "completeness": "清理空值字段, 提升字段填充率",
        "timeliness":   "补充最近 30 天内的新数据",
        "consistency":  "统一 id 时间 邮箱 号码格式",
    }
    return f"最低维度={worst}({dims[worst]}) · {advice.get(worst, '需人工审查')}"