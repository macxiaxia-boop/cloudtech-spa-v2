"""V23 R369 加 5 动态路由: leads convert + workflow publish + skills create + files download + auth devices"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_lead_convert(lead_id: str):
    """Lead convert · 客户签约 (R369)"""
    if not safe_db_table("leads"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    rows = db_query("SELECT id, customer_name, industry, stage FROM leads WHERE id=? LIMIT 1", (lead_id,))
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "previous_stage":  "trial",
            "updated_stage":   "signed",
            "contract_id":     f"contract_{lead_id}_v23_R369",
            "annual_revenue":  19900,
            "converted_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "cloudtech.db.leads+convert",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_workflow_publish(workflow_id: str):
    """Workflow publish · 工作流发布 (R369)"""
    return {
        "status": "ok",
        "data": {
            "workflow_id":   workflow_id,
            "previous_status": "draft",
            "updated_status":  "published",
            "version":         "v1.2.3",
            "published_at":    datetime.utcnow().isoformat() + "Z",
            "url":             f"/workflows/{workflow_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_create(skill_id: str):
    """Skill create · 创建 skill (R369)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "name":        "新创建技能 " + skill_id,
            "category":    "custom",
            "level":       "advanced",
            "use_cases":   0,
            "created_at":  datetime.utcnow().isoformat() + "Z",
            "author":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_token(file_id: str):
    """Files download token · 下载 token (R369)"""
    return {
        "status": "ok",
        "data": {
            "file_id":    file_id,
            "token":      "dl_v23_R369_" + file_id + "_" + str(hash(file_id) % 10000),
            "expires_at": "2026-09-30T19:00:00Z",
            "download_url": f"https://cloudtech.example.com/api/v2/files/{file_id}/stream?token=dl_v23_R369_{file_id}",
            "size_bytes": 2400000,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_devices():
    """Auth devices · 当前用户设备列表 (R369)"""
    return {
        "status": "ok",
        "data": [
            {"device_id": "d_001", "type": "desktop", "os": "Windows 11", "browser": "Edge",  "last_active_at": "2026-09-30T16:00:00Z", "trusted": True},
            {"device_id": "d_002", "type": "mobile",  "os": "iOS 17",    "browser": "Safari","last_active_at": "2026-09-29T20:30:00Z", "trusted": True},
            {"device_id": "d_003", "type": "desktop", "os": "macOS 14",  "browser": "Chrome","last_active_at": "2026-09-28T15:00:00Z", "trusted": False},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R369)')
else:
    print('❌ 没找到')