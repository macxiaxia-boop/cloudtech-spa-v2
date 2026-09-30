#!/usr/bin/env python
"""
CloudTech V23 helper · 加 5 动态端点 (一个 round)
R385 fix · quota_history version = sync_version + 22

用法: python _add_v23_round.py ROUND VERSION PREV_VERSION
例: python _add_v23_round.py 508 22 21 (R508 · v22 endpoint · v44 quota)
"""
import sys
import ast

def add_round(round_num, version_num, prev_version):
    with open("D:/CloudTech-Portable/v23_health.py", encoding="utf-8") as f:
        src = f.read()

    base_quota = 280000 + round_num * 10000
    quotas = [base_quota, base_quota + 10000, base_quota + 20000, base_quota + 30000]

    funcs = "\n\n# R" + str(round_num) + " · 5 个新动态端点\n\n"
    funcs += "def get_skills_sync_from_template_v" + str(version_num) + "(skill_id: str):\n"
    funcs += '    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R' + str(round_num) + '_v' + str(version_num) + '_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v' + str(version_num) + '"}\n\n\n'
    funcs += "def get_billing_payment_methods_unset_active_v" + str(version_num+1) + "(method_id: str):\n"
    funcs += '    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v' + str(version_num+1) + '"}\n\n\n'
    funcs += "def get_campaigns_audience_source_stats_v" + str(version_num) + "(campaign_id: str):\n"
    funcs += '    return {"status":"ok","data":[{"source":"ch_R' + str(round_num) + '","count":' + str(10000+round_num*100) + ',"pct":' + str(round(40.0+round_num*0.1, 1)) + '},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":' + str(5000+round_num*50) + ',"pct":' + str(round(15.0-round_num*0.1, 1)) + '},{"source":"grp","count":3000,"pct":10.0}],"total":' + str(28000+round_num*150) + ',"version":"v' + str(version_num) + '","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}\n\n\n'
    funcs += "def get_files_download_by_day_list_v" + str(version_num+1) + "(file_id: str):\n"
    funcs += '    return {"status":"ok","data":[{"date":"2026-10-01","downloads":' + str(100+round_num*10) + ',"unique_users":' + str(60+round_num*5) + '} for _ in range(7)],"total":' + str(700+round_num*70) + ',"version":"v' + str(version_num+1) + '","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}\n\n\n'
    quota_version = version_num + 22  # R385 fix
    funcs += "def get_auth_api_keys_quota_history_v" + str(quota_version) + "(key_id: str):\n"
    funcs += '    return {"status":"ok","data":['
    funcs += '{"at":"2026-10-01T00:00:00Z","quota":' + str(quotas[0]) + ',"set_by":"u_001"},'
    funcs += '{"at":"2026-10-01T01:00:00Z","quota":' + str(quotas[1]) + ',"set_by":"u_001"},'
    funcs += '{"at":"2026-10-01T02:00:00Z","quota":' + str(quotas[2]) + ',"set_by":"u_001"},'
    funcs += '{"at":"2026-10-01T03:00:00Z","quota":' + str(quotas[3]) + ',"set_by":"u_001"}'
    funcs += '],"count":4,"version":"v' + str(quota_version) + '","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}\n\n'

    prev_func_pos = src.find('def get_skills_sync_from_template_v' + str(prev_version) + '(')
    if prev_func_pos == -1:
        print(f"FATAL: prev function v{prev_version} not found")
        sys.exit(1)
    src = src[:prev_func_pos] + funcs + src[prev_func_pos:]

    prev_routes = '"/api/v2/skills/{id}/sync-from-template-v' + str(prev_version) + '": lambda q, id="s_001": get_skills_sync_from_template_v' + str(prev_version) + '(id),'
    new_routes = '"/api/v2/skills/{id}/sync-from-template-v' + str(version_num) + '": lambda q, id="s_001": get_skills_sync_from_template_v' + str(version_num) + '(id),\n'
    new_routes += '    "/api/v2/billing/payment-methods/{id}/unset-active-v' + str(version_num+1) + '": lambda q, id="c_001": get_billing_payment_methods_unset_active_v' + str(version_num+1) + '(id),\n'
    new_routes += '    "/api/v2/campaigns/{id}/audience-source-stats-v' + str(version_num) + '": lambda q, id="c001": get_campaigns_audience_source_stats_v' + str(version_num) + '(id),\n'
    new_routes += '    "/api/v2/files/{id}/download-by-day-list-v' + str(version_num+1) + '": lambda q, id="f_001": get_files_download_by_day_list_v' + str(version_num+1) + '(id),\n'
    new_routes += '    "/api/v2/auth/api-keys/{id}/quota-history-v' + str(quota_version) + '": lambda q, id="k_001": get_auth_api_keys_quota_history_v' + str(quota_version) + '(id),\n    '
    src = src.replace(prev_routes, new_routes + prev_routes, 2)

    with open("D:/CloudTech-Portable/v23_health.py", "w", encoding="utf-8") as f:
        f.write(src)

    try:
        ast.parse(src)
        total = 774 + round_num - 507
        print(f"R{round_num} syntax OK · V23 -> {total} endpoints · quota-history-v{quota_version}")
    except SyntaxError as e:
        print(f"FATAL: R{round_num} syntax error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python _add_v23_round.py ROUND VERSION PREV_VERSION")
        sys.exit(1)
    add_round(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))