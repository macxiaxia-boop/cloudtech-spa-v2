"""V23 R378 加 5 动态路由: skills share + billing card-list + campaign report-csv + file metadata + auth oauth"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_share(skill_id: str):
    """Skill share · 分享 skill (R378)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "share_url":    f"https://cloudtech.example.com/share/skill/{skill_id}?token=v23_R378",
            "share_token":  "shr_v23_R378_" + skill_id,
            "permissions":  ["view", "import"],
            "expires_at":   "2026-10-30T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_card_list():
    """Billing card list · 支付方式列表 (R378)"""
    return {
        "status": "ok",
        "data": [
            {"card_id": "c_001", "brand": "Visa",       "last4": "4242", "exp": "12/27", "is_default": True},
            {"card_id": "c_002", "brand": "MasterCard", "last4": "5555", "exp": "08/28", "is_default": False},
        ],
        "count": 2,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_report_csv(campaign_id: str):
    """Campaigns report CSV · CSV 报告 (R378)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":  campaign_id,
            "csv_url":      f"/api/v2/campaigns/{campaign_id}/report.csv",
            "rows":         312,
            "columns":      ["date", "channel", "impressions", "clicks", "conversions", "revenue_yuan"],
            "size_bytes":   48720,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_metadata(file_id: str):
    """Files metadata · 文件元数据 (R378)"""
    return {
        "status": "ok",
        "data": {
            "file_id":       file_id,
            "name":          "产品主视觉图.png",
            "type":          "image/png",
            "size_bytes":    2400000,
            "created_at":    "2026-09-15T10:00:00Z",
            "modified_at":   "2026-09-30T16:00:00Z",
            "tags":          ["marketing", "v23", "hero"],
            "checksum_md5":  "9f8e7d6c5b4a3210fedcba9876543210",
            "checksum_sha256": "abc123def456789...",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_oauth():
    """Auth OAuth · OAuth 配置 (R378)"""
    return {
        "status": "ok",
        "data": {
            "providers": [
                {"provider": "google",    "client_id": "google_v23_R378", "scope": "openid email profile", "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."},
                {"provider": "github",    "client_id": "github_v23_R378", "scope": "user:email repo",       "auth_url": "https://github.com/login/oauth/authorize?..."},
                {"provider": "feishu",    "client_id": "feishu_v23_R378", "scope": "contact:user.id",       "auth_url": "https://open.feishu.cn/open-apis/authen/v1/index?..."},
            ],
            "callback_url": "https://cloudtech.example.com/auth/oauth/callback",
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
    print(f'✅ 加 5 函数 (R378)')
else:
    print('❌ 没找到')