"""V23 R361 加 5 动态路由函数: files/{id} + projects/{id} + funnels/{id} + tenants/{id} + ai/{id}"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_file_item(item_id: str):
    """Files 单项 (R361)"""
    files_list = [
        {"id": "f_001", "name": "产品主视觉图.png", "type": "image", "size": 2400000, "modified_at": "2026-09-28T00:00:00Z"},
        {"id": "f_002", "name": "市场调研报告.pdf", "type": "doc",   "size": 5100000, "modified_at": "2026-09-28T00:00:00Z"},
        {"id": "f_003", "name": "竞品资料.zip",     "type": "archive","size": 12300000,"modified_at": "2026-09-25T00:00:00Z"},
        {"id": "f_004", "name": "产品介绍.pptx",    "type": "doc",   "size": 8400000, "modified_at": "2026-09-23T00:00:00Z"},
        {"id": "f_005", "name": "宣传片.mp4",       "type": "video", "size": 142000000,"modified_at": "2026-09-23T00:00:00Z"},
        {"id": "f_006", "name": "logo.svg",          "type": "image", "size": 24000,    "modified_at": "2026-09-16T00:00:00Z"},
    ]
    found = [f for f in files_list if f["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_project_item(item_id: str):
    """Projects 单项 (R361)"""
    projects_list = [
        {"id": "p_001", "name": "市场分析报告集",  "progress": 80,  "status": "running", "owner": "NS", "updated_at": "2026-09-30T10:30:00Z"},
        {"id": "p_002", "name": "产品卖点分析",    "progress": 100, "status": "success", "owner": "YS", "updated_at": "2026-09-30T19:20:00Z"},
        {"id": "p_003", "name": "用户调研问卷",    "progress": 60,  "status": "running", "owner": "NS", "updated_at": "2026-09-30T09:08:00Z"},
        {"id": "p_004", "name": "周报生成助手",    "progress": 30,  "status": "running", "owner": "WZ", "updated_at": "2026-03-10T00:00:00Z"},
        {"id": "p_005", "name": "竞品监控日报",    "progress": 100, "status": "success", "owner": "WZ", "updated_at": "2026-03-09T00:00:00Z"},
        {"id": "p_006", "name": "客户外呼 SOP",    "progress": 50,  "status": "paused",  "owner": "OP", "updated_at": "2026-03-08T00:00:00Z"},
    ]
    found = [p for p in projects_list if p["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_funnel_item(item_id: str):
    """Funnels 单项 (R361) - 实际是 leads funnel stage"""
    funnel_data = [
        {"id": "f_pending", "stage": "待跟进", "count": 80, "pct": 100, "industry_breakdown": {"decoration": 50, "medical": 30}},
        {"id": "f_contacted", "stage": "已联系", "count": 45, "pct": 56, "industry_breakdown": {"decoration": 28, "medical": 17}},
        {"id": "f_demo", "stage": "已演示", "count": 18, "pct": 23, "industry_breakdown": {"decoration": 12, "medical": 6}},
        {"id": "f_trial", "stage": "试用中", "count": 8, "pct": 10, "industry_breakdown": {"decoration": 5, "medical": 3}},
        {"id": "f_signed", "stage": "已签约", "count": 1, "pct": 1, "industry_breakdown": {"decoration": 1, "medical": 0}},
    ]
    found = [f for f in funnel_data if f["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_tenant_item(item_id: str):
    """Tenants 单项 (R361)"""
    if safe_db_table("saas_tenants"):
        rows = db_query("SELECT tenant_id, name, industry, plan, sku_id, created_at, active FROM saas_tenants WHERE tenant_id=? LIMIT 1", (item_id,))
        if rows:
            return {"status": "ok", "data": rows[0], "source": "cloudtech.db"}
    return {"status": "ok", "data": {"tenant_id": item_id, "name": "示例租户", "industry": "decoration", "plan": "pro", "sku_id": "dec_pro", "active": 1, "created_at": "2026-01-15T08:00:00Z"}, "source": "demo_seed"}


def get_ai_item(item_id: str):
    """AI 单项 (R361) - 8 预设数字员工"""
    agents = [
        {"id": "content_writer",       "name": "内容写手",    "avatar": "✍️", "description": "AI 写公众号/小红书/知乎文章", "deployed": True},
        {"id": "short_video_script",  "name": "短视频脚本",  "avatar": "🎬", "description": "60 秒爆款短视频脚本",         "deployed": False},
        {"id": "data_analyst",        "name": "数据分析师",  "avatar": "📊", "description": "实时数据洞察 + 异常告警",     "deployed": False},
        {"id": "seo_specialist",      "name": "SEO 专家",    "avatar": "🔍", "description": "GEO 优化 + 关键词挖掘",       "deployed": False},
        {"id": "social_media_manager","name": "社媒运营",    "avatar": "📱", "description": "多平台账号管理",              "deployed": False},
        {"id": "customer_service",    "name": "智能客服",    "avatar": "💬", "description": "7×24 上下文理解",             "deployed": True},
        {"id": "market_researcher",   "name": "市场调研",    "avatar": "🔎", "description": "竞品监控 + 用户画像",         "deployed": False},
        {"id": "growth_hacker",       "name": "增长黑客",    "avatar": "🚀", "description": "A/B 测试 + 漏斗优化",         "deployed": False},
    ]
    found = [a for a in agents if a["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R361)')
else:
    print('❌ 没找到')