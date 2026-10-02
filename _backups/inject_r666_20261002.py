"""
R666 治本：注入 5 端点 (skill v514 + billing v516 + campaign v536 + file v536 + quota v537)
复用 R663 R664 R665 inject 模式
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v514(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R995_v514_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v514"}


def get_billing_payment_methods_unset_active_v516(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v516"}


def get_campaigns_audience_source_stats_v536(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R995","count":165500,"pct":78.6},
        {"source":"xhs","count":12000,"pct":30.0},
        {"source":"dy","count":101180,"pct":-125.4},
        {"source":"grp","count":3800,"pct":12.5}
    ],"total":282480,"version":"v536","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v536(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":18750,"unique_users":8805},
        {"date":"2026-10-02","downloads":18990,"unique_users":8875},
        {"date":"2026-10-03","downloads":19230,"unique_users":8945},
        {"date":"2026-10-04","downloads":19470,"unique_users":9015},
        {"date":"2026-10-05","downloads":19710,"unique_users":9085},
        {"date":"2026-10-06","downloads":19950,"unique_users":9155},
        {"date":"2026-10-07","downloads":20190,"unique_users":9225}
    ],"total":136290,"version":"v536","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v537(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":11980000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":11990000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12000000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12010000,"set_by":"u_001"}
    ],"count":4,"version":"v537","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v537": lambda q, id="k_001": get_auth_api_keys_quota_history_v537(id),
    "/api/v2/skills/{id}/sync-from-template-v514": lambda q, id="s_001": get_skills_sync_from_template_v514(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v516": lambda q, id="c_001": get_billing_payment_methods_unset_active_v516(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v536": lambda q, id="c001": get_campaigns_audience_source_stats_v536(id),
    "/api/v2/files/{id}/download-by-day-list-v536": lambda q, id="f_001": get_files_download_by_day_list_v536(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v535"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v535 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v535","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v535 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R666 5 endpoints (10 ROUTES + 5 defs)")