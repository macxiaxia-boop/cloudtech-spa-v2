"""V23 R414 加 5 动态路由: skills apply-template + billing payment-methods/{id}/set-active + campaign audience-grade + file download-by-hour-chart + auth api-keys/{id}/throttle-rate"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_apply_template(skill_id: str):
    """Skill apply-template · 应用模板 (R414)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "applied_at":  datetime.utcnow().isoformat() + "Z",
            "applied_by":  "u_001",
            "template_id": f"tpl_v23_R414_{skill_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_active(method_id: str):
    """Billing payment-methods/{id}/set-active · 激活支付 (R414)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_grade(campaign_id: str):
    """Campaigns audience-grade · 受众等级 (R414)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7},
            {"grade": "B 良好", "count": 6240, "pct": 33.9},
            {"grade": "C 普通", "count": 5240, "pct": 28.4},
            {"grade": "D 低质", "count": 2760, "pct": 15.0},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_hour_chart(file_id: str):
    """Files download-by-hour-chart · 按小时下载 chart (R414)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["00", "04", "08", "12", "16", "20", "23"],
            "datasets": [
                {"label": "下载", "data": [3,  1,  10, 56, 42, 16,  0], "type": "bar"},
                {"label": "唯一", "data": [2,  1,   8, 42, 28,  8,  0], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_rate(key_id: str):
    """Auth api-keys/{id}/throttle-rate · 限流率 (R414)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "throttle_rate":   "100 req/min",
            "current_rate":   "42 req/min",
            "headroom":       58,
            "throttled":      False,
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
    print(f'✅ 加 5 函数 (R414)')
else:
    print('❌ 没找到')