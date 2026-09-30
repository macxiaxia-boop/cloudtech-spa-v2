"""V23 R395 加 5 动态路由: skills clone + billing tax-rates + campaign impressions-history + file share-revoke + auth sso/{id}/config"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_clone(skill_id: str):
    """Skill clone · 克隆 skill (R395)"""
    return {
        "status": "ok",
        "data": {
            "source_skill_id": skill_id,
            "new_skill_id":    f"{skill_id}_clone_v23",
            "new_name":        f"{skill_id} 克隆",
            "cloned_by":       "u_001",
            "cloned_at":       datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_rates():
    """Billing tax rates · 税率列表 (R395)"""
    return {
        "status": "ok",
        "data": [
            {"region": "CN",   "rate": 0.06, "type": "vat_general",   "applies_to": "all"},
            {"region": "CN",   "rate": 0.03, "type": "vat_small",     "applies_to": "small_business"},
            {"region": "CN",   "rate": 0.13, "type": "vat_old",       "applies_to": "deprecated"},
            {"region": "US",   "rate": 0.0,  "type": "sales_tax",     "applies_to": "varies_by_state"},
            {"region": "EU",   "rate": 0.20, "type": "vat",          "applies_to": "all"},
            {"region": "JP",   "rate": 0.10, "type": "consumption",   "applies_to": "all"},
        ],
        "default_region": "CN",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_impressions_history(campaign_id: str):
    """Campaigns impressions-history · 曝光历史 (R395)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "impressions": 2620},
            {"date": "2026-09-25", "impressions": 2840},
            {"date": "2026-09-26", "impressions": 2610},
            {"date": "2026-09-27", "impressions": 2920},
            {"date": "2026-09-28", "impressions": 3010},
            {"date": "2026-09-29", "impressions": 3120},
            {"date": "2026-09-30", "impressions": 3010},
        ],
        "total":        20130,
        "average":      2875,
        "trend_pct":    "+2.3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_revoke(file_id: str):
    """Files share-revoke · 撤销分享 (R395)"""
    return {
        "status": "ok",
        "data": {
            "file_id":        file_id,
            "share_revoked":  True,
            "active_links":   0,
            "revoked_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sso_config(sso_id: str):
    """Auth sso/{id}/config · SSO 配置 (R395)"""
    configs = {
        "wechat_work": {"name": "企业微信",     "client_id": "wc_v23", "scopes": ["contact:user.id"]},
        "feishu":      {"name": "飞书",         "client_id": "fs_v23", "scopes": ["contact:user.id"]},
        "dingtalk":    {"name": "钉钉",         "client_id": "dd_v23", "scopes": ["contact:user.id"]},
        "google":      {"name": "Google",       "client_id": "g_v23",  "scopes": ["openid", "email", "profile"]},
    }
    found = configs.get(sso_id)
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {"sso_id": sso_id, **found},
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R395)')
else:
    print('❌ 没找到')