"""V23 R394 加 5 动态路由: skills optimize + billing payment-methods + campaign ctr-history + file comments/{id}/delete + auth devices/{id}/forget"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_optimize(skill_id: str):
    """Skill optimize · 优化 skill (R394)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":          skill_id,
            "optimized":         True,
            "latency_improvement":"-32%",
            "cost_improvement":  "-18%",
            "optimized_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods():
    """Billing payment methods · 支付方式 (R394)"""
    return {
        "status": "ok",
        "data": [
            {"method": "wechat_pay", "name": "微信支付",   "fee_pct": 0.6,  "min_yuan": 0.01, "max":     50000},
            {"method": "alipay",      "name": "支付宝",     "fee_pct": 0.6,  "min_yuan": 0.01, "max":     50000},
            {"method": "union_pay",    "name": "银联支付",   "fee_pct": 0.7,  "min_yuan": 0.01, "max":     100000},
            {"method": "bank_card",    "name": "银行卡",     "fee_pct": 1.0,  "min_yuan": 1.00, "max":     200000},
        ],
        "default_method": "wechat_pay",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_ctr_history(campaign_id: str):
    """Campaigns ctr-history · CTR 历史 (R394)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "impressions": 2620, "clicks": 132, "ctr": "5.0%"},
            {"date": "2026-09-25", "impressions": 2840, "clicks": 145, "ctr": "5.1%"},
            {"date": "2026-09-26", "impressions": 2610, "clicks": 128, "ctr": "4.9%"},
            {"date": "2026-09-27", "impressions": 2920, "clicks": 156, "ctr": "5.3%"},
            {"date": "2026-09-28", "impressions": 3010, "clicks": 162, "ctr": "5.4%"},
            {"date": "2026-09-29", "impressions": 3120, "clicks": 178, "ctr": "5.7%"},
            {"date": "2026-09-30", "impressions": 3010, "clicks": 187, "ctr": "6.2%"},
        ],
        "average_ctr": "5.4%",
        "trend": "+1.0%",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_delete(comment_id: str):
    """Files comments/{id}/delete · 删除评论 (R394)"""
    return {
        "status": "ok",
        "data": {
            "comment_id":   comment_id,
            "deleted":      True,
            "deleted_at":   datetime.utcnow().isoformat() + "Z",
            "deleted_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_devices_forget(device_id: str):
    """Auth devices/{id}/forget · 忘记设备 (R394)"""
    return {
        "status": "ok",
        "data": {
            "device_id":   device_id,
            "forgot":      True,
            "forgot_at":   datetime.utcnow().isoformat() + "Z",
            "trusted_until":None,
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
    print(f'✅ 加 5 函数 (R394)')
else:
    print('❌ 没找到')