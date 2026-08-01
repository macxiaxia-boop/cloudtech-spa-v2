"""
合规自动化 — Automated Compliance Pipeline
对标筷子: 商业级版权合规授信·侵权源头切断·AI授权授信流程
"""
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
COMPLIANCE_DIR = Path("D:/个人文件/AI/云数科技/compliance")
COMPLIANCE_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 合规规则库
# ═══════════════════════════════════
COMPLIANCE_RULES = {
    "content_publish": [
        {"id": "cp-1", "name": "肖像授权检查", "check": "portrait_check", "severity": "blocker"},
        {"id": "cp-2", "name": "音乐版权检查", "check": "music_check", "severity": "blocker"},
        {"id": "cp-3", "name": "AI生成声明", "check": "ai_disclosure", "severity": "warning"},
        {"id": "cp-4", "name": "虚假宣传检测", "check": "false_claim_check", "severity": "blocker"},
        {"id": "cp-5", "name": "敏感词过滤", "check": "sensitive_words", "severity": "blocker"},
        {"id": "cp-6", "name": "竞品诋毁检测", "check": "competitor_defamation", "severity": "warning"},
    ],
}

SENSITIVE_WORDS = ["第一", "唯一", "最好", "最低价", "全网最", "国家级", "绝对", "100%保证", "永不", "永久免费"]
BANNED_CLAIMS = ["治愈", "根治", "包治", "特效", "神效", "立竿见影", "药到病除", "永不复发"]


def run_compliance_check(content: dict, content_type: str = "article") -> dict:
    """
    发布前合规自动检查
    对标筷子: 商业级版权合规授信 — 从源头切断侵权风险
    """
    text = content.get("text", content.get("body", ""))
    title = content.get("title", "")
    full = f"{title}\n{text}"
    issues = []
    warnings = []

    # CP-1: 肖像授权检查
    from digital_rights import list_assets
    portraits = list_assets("portrait", "active", 100)
    if content_type in ("voiceover", "persona", "video") and not portraits:
        warnings.append({"rule": "cp-1", "msg": "未找到已授权肖像资产·建议注册"})

    # CP-2: 音乐版权
    music = list_assets("music", "active", 10)
    if content_type == "video" and not music:
        warnings.append({"rule": "cp-2", "msg": "未找到已授权音乐资产"})

    # CP-3: AI生成声明
    if "AI" in full or "ai" in full.lower():
        warnings.append({"rule": "cp-3", "msg": "建议添加AI生成内容声明"})

    # CP-4: 虚假宣传
    for claim in BANNED_CLAIMS:
        if claim in full:
            issues.append({"rule": "cp-4", "msg": f"可能涉及虚假宣传: '{claim}'"})

    # CP-5: 敏感词
    for word in SENSITIVE_WORDS:
        if word in full:
            warnings.append({"rule": "cp-5", "msg": f"敏感词: '{word}'"})

    # CP-6: 竞品诋毁
    competitors = content.get("competitors", [])
    for comp in competitors:
        if comp in full and any(w in full for w in ["垃圾", "骗", "坑", "黑心"]):
            warnings.append({"rule": "cp-6", "msg": f"可能涉及竞品诋毁: '{comp}'"})

    passed = len(issues) == 0
    result = {
        "passed": passed, "status": "PASS" if passed else "FAIL",
        "issues": issues, "warnings": warnings,
        "rules_checked": len(COMPLIANCE_RULES["content_publish"]),
        "checked_at": datetime.now().isoformat()[:19],
        "risk_level": "high" if issues else "medium" if warnings else "low",
    }

    # 记录合规日志
    log_file = COMPLIANCE_DIR / f"check-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    log_file.write_text(json.dumps({"result": result, "content_preview": full[:200]}, ensure_ascii=False, indent=2), encoding="utf-8")

    return result


def get_compliance_stats(tid: str = "") -> dict:
    """合规统计"""
    total, passed, failed = 0, 0, 0
    for f in COMPLIANCE_DIR.glob("check-*.json"):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
            total += 1
            if c["result"]["passed"]: passed += 1
            else: failed += 1
        except Exception: pass
    return {"total_checks": total, "passed": passed, "failed": failed, "pass_rate": round(passed / max(total, 1) * 100)}
