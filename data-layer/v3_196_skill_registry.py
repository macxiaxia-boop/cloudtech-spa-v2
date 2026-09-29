"""v3_196 AIOS Skill Registry · R321 实现

用户原话: "把 AIOS 的 skill, 工作流, SOP 全部做进去"
- 工作流 = v3_192 + v3_193 (5 平台) ✅
- SOP = v3_194 (微信支付) + v3_190 + v3_145 ✅
- Skill = 本模块 (扫描 ~/.claude/skills/ 全 447 skills + 暴露为 cloudtech 端点)

端点 (6):
  GET  /                  概要 (全 skill 数 + 分类)
  GET  /list              全 skill 列表 (按分类)
  GET  /categories        分类清单 (marketing/engineering/productivity/...)
  GET  /{name}/SKILL.md   拿 skill 的 SKILL.md 内容
  POST /{name}/invoke     调用 skill (返回 SKILL.md 作为 prompt 指引)
  GET  /stats             扫描统计 (总 skills/有 SKILL.md/无 SKILL.md)
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v3/v3_196_skill_registry", tags=["skill-registry"])

SKILLS_ROOT = Path(r"C:\Users\xinzh\.claude\skills")

# 营销相关 skill 分类
CATEGORY_KEYWORDS = {
    "marketing": ["marketing", "content", "seo", "ad-", "aeo", "copywriting", "campaign", "growth", "demand"],
    "engineering": ["agent", "code", "developer", "automation", "mcp", "ops"],
    "productivity": ["brain", "thinking", "decision", "memory", "knowledge", "vault"],
    "leadership": ["ceo", "cfo", "cto", "cmo", "cro", "cso", "chro", "ciso", "coo", "cpo"],
    "creation": ["creator", "video", "audio", "image", "design", "writing"],
    "data": ["analytics", "tracking", "intel", "research"],
    "support": ["support", "office", "meeting", "compliance"],
}


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def scan_skills() -> List[Dict[str, Any]]:
    """扫 ~/.claude/skills/ 全 skill 目录 + SKILL.md 状态."""
    skills = []
    if not SKILLS_ROOT.exists():
        return []
    for entry in SKILLS_ROOT.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("@"):
            continue  # 个人目录
        skill_md = entry / "SKILL.md"
        skills.append({
            "name": entry.name,
            "path": str(entry),
            "has_skill_md": skill_md.exists(),
            "skill_md_size": skill_md.stat().st_size if skill_md.exists() else 0,
            "category": _categorize(entry.name),
        })
    return skills


def _categorize(name: str) -> str:
    n = name.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in n:
                return cat
    return "other"


@router.get("/")
async def root():
    skills = scan_skills()
    by_cat = {}
    for s in skills:
        by_cat.setdefault(s["category"], 0)
        by_cat[s["category"]] += 1
    return {
        "engine": "AIOS Skill Registry",
        "version": "1.0.0",
        "module": "v3_196_skill_registry",
        "skills_root": str(SKILLS_ROOT),
        "total_skills": len(skills),
        "with_skill_md": sum(1 for s in skills if s["has_skill_md"]),
        "by_category": by_cat,
        "categories": list(CATEGORY_KEYWORDS.keys()) + ["other"],
        "ts": _now(),
    }


@router.get("/list")
async def list_skills(category: str = None):
    skills = scan_skills()
    if category:
        skills = [s for s in skills if s["category"] == category]
    return {
        "status": "ok",
        "filter": category or "all",
        "total": len(skills),
        "items": skills,
    }


@router.get("/categories")
async def categories():
    skills = scan_skills()
    out = {}
    for s in skills:
        out.setdefault(s["category"], []).append(s["name"])
    return {
        "status": "ok",
        "categories": out,
        "total": len(skills),
    }


@router.get("/{skill_name}/SKILL.md")
async def get_skill_md(skill_name: str):
    fp = SKILLS_ROOT / skill_name / "SKILL.md"
    if not fp.exists():
        raise HTTPException(404, f"skill '{skill_name}' has no SKILL.md")
    content = fp.read_text(encoding="utf-8")
    return {
        "status": "ok",
        "skill": skill_name,
        "path": str(fp),
        "size": len(content),
        "content": content,
    }


@router.post("/{skill_name}/invoke")
async def invoke_skill(skill_name: str, body: Dict[str, Any] = None):
    """
    调用 skill (mock): 返回 SKILL.md 内容 + 调用上下文,
    真调用需要走 Claude Code task agent (L4 — 用户授权 task agent 接入)。
    """
    fp = SKILLS_ROOT / skill_name / "SKILL.md"
    if not fp.exists():
        raise HTTPException(404, f"skill '{skill_name}' not found")
    skill_md = fp.read_text(encoding="utf-8")
    body = body or {}
    return {
        "status": "ok",
        "skill": skill_name,
        "mode": "metadata_passthrough",
        "note": "实际 skill 执行需通过 Claude Code task agent 调度 (L4)",
        "skill_md_first_500_chars": skill_md[:500],
        "input": body,
        "category": _categorize(skill_name),
        "ts": _now(),
    }


@router.get("/stats")
async def stats():
    skills = scan_skills()
    by_cat = {}
    for s in skills:
        by_cat.setdefault(s["category"], 0)
        by_cat[s["category"]] += 1
    return {
        "status": "ok",
        "total": len(skills),
        "with_skill_md": sum(1 for s in skills if s["has_skill_md"]),
        "without_skill_md": sum(1 for s in skills if not s["has_skill_md"]),
        "by_category": by_cat,
    }