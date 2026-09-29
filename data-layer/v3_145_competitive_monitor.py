"""v3_145 Competitive Monitor · 竞品对比雷达 v1.0 · R321 升级

V3.1 P0 #4 竞品对比雷达
- 输入: data/competitors.jsonl (30 竞品 × 5 行业)
- 4 维雷达: 功能完整度 / 价格竞争力 / AI 能力 / 生态成熟度
- 对比: 多竞品叠加 + 差距分析 + AI 总结

端点:
  GET /                                  配置 + 总览
  GET /competitors                       全部 30 竞品
  GET /competitors/{industry}            按行业 (decoration/education/medical/catering/retail)
  GET /compare?names=甲,乙,丙            多竞品对比
  GET /radar/{industry}                  行业 4 维雷达
  GET /insights?industry=装修            AI 总结对比建议
  GET /gaps?industry=装修                cloudtech 自身差距分析
"""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/v3/v3_145_competitive_monitor", tags=["competitive-monitor"])

DATA_FILE = Path(r"D:\CloudTech-Portable\data\competitors_fixed.jsonl")

INDUSTRY_LABEL = {
    "decoration": "装修",
    "education":  "教育",
    "medical":    "医美",
    "catering":   "餐饮",
    "retail":     "零售",
}

FUNDING_SCORE = {
    "种子轮": 30, "天使轮": 30,
    "Pre-A": 50, "A 轮": 60,
    "A+": 65, "B 轮": 75, "B+": 78,
    "C 轮": 85, "C+": 88, "D 轮": 92, "D+": 95, "上市": 100,
    "未融资": 25,
}

PRICE_SCORE = {"low": 100, "mid": 75, "high": 50}  # 反向 (越低越有竞争力)


def _load_all() -> List[Dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    return [json.loads(l) for l in DATA_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]


def _flat() -> List[Dict[str, Any]]:
    """30 个竞品平铺."""
    out = []
    for rec in _load_all():
        out.extend(rec.get("competitors", []))
    return out


def _score_product_count(products: List[str]) -> float:
    """功能完整度: 产品数 × 20, 上限 100."""
    return min(100.0, len(products) * 20)


def _score_price(price_range: str) -> float:
    return PRICE_SCORE.get(price_range, 60)


def _score_ai(products: List[str], name: str = "") -> float:
    """AI 能力启发式: 含 AI / 智能 / 数字员工 / 智慧关键词高分."""
    text = " ".join(products + [name]).lower()
    score = 40  # 基础分
    if any(k in text for k in ["ai", "智能", "数字员工", "智慧", "agent"]):
        score += 35
    if "erp" in text or "中台" in text:
        score += 15
    return min(100.0, score)


def _score_eco(funding: str) -> float:
    return FUNDING_SCORE.get(funding, 50)


def _radar(comp: Dict[str, Any]) -> Dict[str, float]:
    return {
        "feature":     round(_score_product_count(comp.get("products", [])), 1),
        "price":       round(_score_price(comp.get("price_range", "mid")), 1),
        "ai":          round(_score_ai(comp.get("products", []), comp.get("name", "")), 1),
        "ecosystem":   round(_score_eco(comp.get("funding", "")), 1),
    }


def _overall(r: Dict[str, float]) -> float:
    return round(sum(r.values()) / 4, 1)


@router.get("/")
async def root():
    all = _flat()
    industries = sorted({c.get("industry") for c in all})
    return {
        "engine": "Competitive Monitor",
        "version": "1.0.0",
        "module": "v3_145_competitive_monitor",
        "data_source": str(DATA_FILE),
        "scoring_dimensions": ["feature", "price", "ai", "ecosystem"],
        "total_competitors": len(all),
        "industries": industries,
        "endpoints": ["/", "/competitors", "/competitors/{industry}",
                       "/compare", "/radar/{industry}", "/insights", "/gaps"],
    }


@router.get("/competitors")
async def list_all():
    return {
        "total": len(_flat()),
        "data": _flat(),
    }


@router.get("/competitors/{industry}")
async def list_by_industry(industry: str):
    items = [c for c in _flat() if c.get("industry") == industry]
    return {
        "industry": industry,
        "label": INDUSTRY_LABEL.get(industry, industry),
        "total": len(items),
        "data": items,
    }


@router.get("/compare")
async def compare(names: str):
    """多竞品对比 (URL ?names=酷家乐,土巴兔,齐家网)."""
    target = [n.strip() for n in names.split(",") if n.strip()]
    items = [c for c in _flat() if c.get("name") in target]
    if not items:
        raise HTTPException(404, f"未找到竞品: {target}")
    radar_data = []
    for c in items:
        r = _radar(c)
        radar_data.append({
            "name": c.get("name"),
            "industry": c.get("industry"),
            "overall": _overall(r),
            "radar": r,
            "strengths": c.get("strengths", []),
            "weaknesses": c.get("weaknesses", []),
        })
    return {
        "names": target,
        "found": len(items),
        "compare": radar_data,
    }


@router.get("/radar/{industry}")
async def radar(industry: str):
    """行业 4 维雷达."""
    items = [c for c in _flat() if c.get("industry") == industry]
    if not items:
        raise HTTPException(404, f"无 {industry} 行业竞品数据")
    radar_data = []
    for c in items:
        r = _radar(c)
        radar_data.append({
            "name": c.get("name"),
            "overall": _overall(r),
            "radar": r,
        })
    radar_data.sort(key=lambda x: x["overall"], reverse=True)
    avg = {
        dim: round(sum(d["radar"][dim] for d in radar_data) / len(radar_data), 1)
        for dim in ("feature", "price", "ai", "ecosystem")
    }
    return {
        "industry": industry,
        "label": INDUSTRY_LABEL.get(industry, industry),
        "total": len(radar_data),
        "ranking": radar_data,
        "industry_avg": avg,
    }


@router.get("/insights")
async def insights(industry: str):
    """AI 总结对比建议."""
    items = [c for c in _flat() if c.get("industry") == industry]
    if not items:
        raise HTTPException(404, f"无 {industry} 行业竞品数据")
    # 最高分/最低分
    radar_data = [(c, _radar(c), _overall(_radar(c))) for c in items]
    radar_data.sort(key=lambda x: x[2], reverse=True)
    top = radar_data[0]
    bottom = radar_data[-1]
    label = INDUSTRY_LABEL.get(industry, industry)

    # 维度差距分析
    avg = {
        dim: sum(d[1][dim] for d in radar_data) / len(radar_data)
        for dim in ("feature", "price", "ai", "ecosystem")
    }

    # 启发式建议 (基于真实 strengths/weaknesses 关键词)
    all_strong_kws = []
    all_weak_kws = []
    for c, _, _ in radar_data:
        all_strong_kws.extend(c.get("strengths", []))
        all_weak_kws.extend(c.get("weaknesses", []))

    recommendations = []
    if avg["ai"] < 60:
        recommendations.append("AI 能力是该行业普遍短板 → cloudtech 的 AI 数字员工是显著差异化")
    if avg["feature"] < 60:
        recommendations.append("行业产品功能平均分偏低 → cloudtech 158 项技能有覆盖优势")
    if avg["price"] > 70:
        recommendations.append("价格普遍亲民 → cloudtech 中高端 SKU 需做差异化 (如 7 天 trial)")
    if avg["ecosystem"] < 70:
        recommendations.append("生态成熟度分布广 → 中小竞品生态弱, cloudtech 通用中台优势大")

    return {
        "industry": industry,
        "label": label,
        "top_competitor": {"name": top[0]["name"], "score": top[2]},
        "bottom_competitor": {"name": bottom[0]["name"], "score": bottom[2]},
        "industry_avg": avg,
        "competitor_count": len(radar_data),
        "recommendations": recommendations,
        "common_strengths": all_strong_kws[:5],
        "common_weaknesses": all_weak_kws[:5],
        "cloudtech_positioning": f"cloudtech 灵策智算 · 158 技能 · 38 数字员工 · {label} 行业 SaaS",
    }


@router.get("/gaps")
async def gaps(industry: str):
    """cloudtech 自身差距分析 (vs 行业竞品)."""
    items = [c for c in _flat() if c.get("industry") == industry]
    if not items:
        raise HTTPException(404, f"无 {industry} 行业竞品数据")
    radar_data = [(_radar(c), c) for c in items]
    industry_avg = {
        dim: sum(r[dim] for r, _ in radar_data) / len(radar_data)
        for dim in ("feature", "price", "ai", "ecosystem")
    }
    # cloudtech 自评 (基于真实能力数字)
    cloudtech = {
        "feature":   95.0,  # 158 技能
        "price":     75.0,  # ¥199-999/月 (mid)
        "ai":        92.0,  # 38 数字员工 + 灵策智算
        "ecosystem": 80.0,  # 500+ 企业客户 (估算)
    }
    gaps = {
        dim: round(cloudtech[dim] - industry_avg[dim], 1)
        for dim in ("feature", "price", "ai", "ecosystem")
    }
    return {
        "industry": industry,
        "label": INDUSTRY_LABEL.get(industry, industry),
        "cloudtech_score": cloudtech,
        "industry_avg": {k: round(v, 1) for k, v in industry_avg.items()},
        "gap": gaps,
        "interpretation": [
            ("领先" if v > 10 else ("持平" if v > -10 else "落后")) + f" · {dim} (cloudtech {cloudtech[dim]:.1f} vs 行业 {industry_avg[dim]:.1f})"
            for dim, v in gaps.items()
        ],
    }