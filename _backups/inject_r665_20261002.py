"""
R665 治本：注入 5 端点 (skill v512 + billing v513 + campaign v534 + file v534 + quota v535)
复用 R663 R664 inject 模式
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v512(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R994_v512_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v512"}


def get_billing_payment_methods_unset_active_v513(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v513"}


def get_campaigns_audience_source_stats_v534(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R994","count":164500,"pct":78.1},
        {"source":"xhs","count":11500,"pct":28.7},
        {"source":"dy","count":100300,"pct":-124.6},
        {"source":"grp","count":3600,"pct":11.9}
    ],"total":279900,"version":"v534","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v534(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":18460,"unique_users":8665},
        {"date":"2026-10-02","downloads":18700,"unique_users":8735},
        {"date":"2026-10-03","downloads":18940,"unique_users":8805},
        {"date":"2026-10-04","downloads":19180,"unique_users":8875},
        {"date":"2026-10-05","downloads":19420,"unique_users":8945},
        {"date":"2026-10-06","downloads":19660,"unique_users":9015},
        {"date":"2026-10-07","downloads":19900,"unique_users":9085}
    ],"total":134260,"version":"v534","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v535(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":11940000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":11950000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":11960000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":11970000,"set_by":"u_001"}
    ],"count":4,"version":"v535","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v535": lambda q, id="k_001": get_auth_api_keys_quota_history_v535(id),
    "/api/v2/skills/{id}/sync-from-template-v512": lambda q, id="s_001": get_skills_sync_from_template_v512(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v513": lambda q, id="c_001": get_billing_payment_methods_unset_active_v513(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v534": lambda q, id="c001": get_campaigns_audience_source_stats_v534(id),
    "/api/v2/files/{id}/download-by-day-list-v534": lambda q, id="f_001": get_files_download_by_day_list_v534(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v533"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v533 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v533","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v533 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R665 5 endpoints (10 ROUTES + 5 defs)")