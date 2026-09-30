"""V23 R363 加 5 函数: auth refresh/logout + files download + campaigns report + email_queue resend"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_auth_refresh():
    """Auth refresh · 刷新 token (R363)"""
    return {
        "status": "ok",
        "data": {
            "user_id":   "u_001",
            "tenant_id": "t_3a59592b7619",
            "token":     "demo_refreshed_jwt_token_v23_R363",
            "role":      "owner",
            "expires_in": 86400,
            "refreshed_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_logout():
    """Auth logout · 注销 (R363)"""
    return {
        "status": "ok",
        "data": {
            "logged_out": True,
            "user_id": "u_001",
            "sessions_revoked": 1,
            "logged_out_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_file_download(file_id: str):
    """Files download · 文件下载 (R363)"""
    files_meta = {
        "f_001": {"name": "产品主视觉图.png", "size_bytes": 2400000, "mime": "image/png"},
        "f_002": {"name": "市场调研报告.pdf", "size_bytes": 5100000, "mime": "application/pdf"},
        "f_003": {"name": "竞品资料.zip",     "size_bytes": 12300000, "mime": "application/zip"},
        "f_004": {"name": "产品介绍.pptx",    "size_bytes": 8400000, "mime": "application/vnd.ms-powerpoint"},
        "f_005": {"name": "宣传片.mp4",       "size_bytes": 142000000, "mime": "video/mp4"},
        "f_006": {"name": "logo.svg",          "size_bytes": 24000,    "mime": "image/svg+xml"},
    }
    meta = files_meta.get(file_id)
    if not meta:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            "file_id":    file_id,
            "name":       meta["name"],
            "size_bytes": meta["size_bytes"],
            "mime":       meta["mime"],
            "download_url": f"/api/v2/files/{file_id}/download?token=demo_v23_R363",
            "expires_at":  "2026-09-30T18:00:00Z",
            "md5":         "9f8e7d6c5b4a3210fedcba9876543210",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_report(campaign_id: str):
    """Campaigns 单项 report · 营销活动报告 (R363)"""
    campaigns_meta = {
        "c001": {"name": "新客 7 天试用",     "channel": "邮件",   "leads": 142, "conversions": 18},
        "c002": {"name": "老客推荐激励",     "channel": "微信",   "leads": 87,  "conversions": 24},
        "c003": {"name": "小红书 KOL 投放",   "channel": "小红书", "leads": 256, "conversions": 31},
        "c004": {"name": "抖音矩阵投放",     "channel": "抖音",   "leads": 312, "conversions": 42},
        "c005": {"name": "公众号长文推送",   "channel": "公众号", "leads": 89,  "conversions": 12},
        "c006": {"name": "微信社群裂变",     "channel": "微信群", "leads": 0,   "conversions": 0},
        "c007": {"name": "抖音直播切片",     "channel": "抖音",   "leads": 178, "conversions": 19},
        "c008": {"name": "百度 SEM 投放",    "channel": "百度",   "leads": 198, "conversions": 15},
    }
    meta = campaigns_meta.get(campaign_id)
    if not meta:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **meta,
            "campaign_id":   campaign_id,
            "report_url":    f"/api/v2/campaigns/{campaign_id}/report.pdf",
            "insights": [
                "前 3 天转化率最高 (47%)",
                "周末转化率下降 23%",
                "A/B 测试 B 组转化率比 A 组高 12%",
            ],
            "next_actions": [
                "扩大 B 组预算 30%",
                "针对流失用户发二次营销邮件",
                "准备下一轮素材 (3 个新文案)",
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_resend(item_id: str):
    """Email queue resend · 邮件重发 (R363)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    try:
        item_id_int = int(item_id)
        rows = db_query("SELECT id, to_email, template, subject, status, attempts FROM email_queue WHERE id=? LIMIT 1", (item_id_int,))
    except (ValueError, TypeError):
        rows = []
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    # 模拟重发：attempts+1
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "resent":       True,
            "resent_at":    datetime.utcnow().isoformat() + "Z",
            "new_attempts":  rows[0].get("attempts", 0) + 1,
        },
        "source": "cloudtech.db.email_queue+resend",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R363)')
else:
    print('❌ 没找到')