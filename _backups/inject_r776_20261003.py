"""
R1256 接续：注入 5 端点 (skill v1033 + billing v1036 + campaign v1057 + file v1057 + quota v1058)
端点累计 R1257 (R1255+2)
路径修正：/api/v2/auth-api-keys/ (连字符) 非 auth/api-keys/
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v1033(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1257_v1033_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1033"}


def get_billing_payment_methods_unset_active_v1036(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1036"}


def get_campaigns_audience_source_stats_v1057(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1257","count":275400,"pct":133.5},
        {"source":"xhs","count":66900,"pct":167.2},
        {"source":"dy","count":197600,"pct":-212.9},
        {"source":"grp","count":25800,"pct":78.5}
    ],"total":565700,"version":"v1057","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v1057(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":51900,"unique_users":24615},
        {"date":"2026-10-02","downloads":52140,"unique_users":24685},
        {"date":"2026-10-03","downloads":52380,"unique_users":24755},
        {"date":"2026-10-04","downloads":52620,"unique_users":24825},
        {"date":"2026-10-05","downloads":52860,"unique_users":24895},
        {"date":"2026-10-06","downloads":53100,"unique_users":24965},
        {"date":"2026-10-07","downloads":53340,"unique_users":25035}
    ],"total":368340,"version":"v1057","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v1058(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-03T00:45:00Z","quota":16440000,"set_by":"u_001"},
        {"at":"2026-10-03T01:00:00Z","quota":16450000,"set_by":"u_001"},
        {"at":"2026-10-03T01:15:00Z","quota":16460000,"set_by":"u_001"},
        {"at":"2026-10-03T01:30:00Z","quota":16470000,"set_by":"u_001"}
    ],"count":4,"version":"v1058","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth-api-keys/{id}/quota-history-v1058": lambda q, id="k_001": get_auth_api_keys_quota_history_v1058(id),
    "/api/v2/skills/{id}/sync-from-template-v1033": lambda q, id="s_001": get_skills_sync_from_template_v1033(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v1036": lambda q, id="c_001": get_billing_payment_methods_unset_active_v1036(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v1057": lambda q, id="c001": get_campaigns_audience_source_stats_v1057(id),
    "/api/v2/files/{id}/download-by-day-list-v1057": lambda q, id="f_001": get_files_download_by_day_list_v1057(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth-api-keys/{id}/quota-history-v1056"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v1056 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v1056","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v1056 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R1256 5 endpoints · R1257 endpoints cumulative · bug-fixed auth-api-keys path")
