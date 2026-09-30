"""V23 R392 加 5 动态路由: skills auto-train + billing coupon-validate + campaign abtest-stop + file comments/{id} + auth sessions/cleanup"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_auto_train(skill_id: str):
    """Skill auto-train · 自动训练 (R392)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "auto_train":     True,
            "epochs":         20,
            "started_at":     datetime.utcnow().isoformat() + "Z",
            "estimated_done": "2026-10-01T08:00:00Z",
            "gpu":            "auto",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_coupon_validate(coupon_code: str):
    """Billing coupon validate · 验证优惠券 (R392)"""
    coupons = {
        "V23_R392":     {"discount_pct": 50, "valid": True,  "applies_to": "all"},
        "EARLY_BIRD":  {"discount_pct": 30, "valid": False, "reason": "expired"},
        "INVALID":     {"valid":        False, "reason": "unknown_code"},
    }
    found = coupons.get(coupon_code)
    if not found:
        return {"status": "ok", "data": {"coupon_code": coupon_code, "valid": False, "reason": "unknown_code"}, "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {"coupon_code": coupon_code, **found},
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_abtest_stop(campaign_id: str):
    """Campaigns abtest-stop · 停止 A/B 测试 (R392)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "abtest_status": "stopped",
            "winner":        "B",
            "stopped_at":    datetime.utcnow().isoformat() + "Z",
            "winner_promoted_to_full": True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_item(comment_id: str):
    """Files comments/{id} · 评论单项 (R392)"""
    comments = {
        "c_001": {"user_id": "u_001", "name": "心之所向便是光", "content": "请更新 logo 颜色", "created_at": "2026-09-29T10:00:00Z", "replies": 2},
        "c_002": {"user_id": "u_002", "name": "运维",          "content": "已上传 v2 版本",  "created_at": "2026-09-30T14:00:00Z", "replies": 0},
        "c_003": {"user_id": "u_003", "name": "销售",          "content": "请改成中文版",    "created_at": "2026-09-30T15:00:00Z", "replies": 1},
    }
    found = comments.get(comment_id)
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {"comment_id": comment_id, **found},
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_cleanup():
    """Auth sessions cleanup · 清理过期 session (R392)"""
    return {
        "status": "ok",
        "data": {
            "cleaned_count":  12,
            "remaining_count": 4,
            "cleaned_at":      datetime.utcnow().isoformat() + "Z",
            "kept_session_ids": ["s_001", "s_002", "s_003", "s_004"],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R392)')
else:
    print('❌ 没找到')