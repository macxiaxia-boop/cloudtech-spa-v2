"""
R663 治本：注入 5 端点 (skill v508 + billing v509 + campaign v530 + file v530 + quota v531)
1. ROUTES chunk 1 (line 24455 前): +5 routes v530/v508/v509/v529/v529
2. ROUTES chunk 2 (line 24680 前): +5 routes same
4. 函数定义 (line 29849 后空行前): +5 defs
5. AST 验证
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

# R663 5 函数定义（插入到 line 29849 后空行 29850 之前 → 实际是 29851 空行前）
func_defs = '''
def get_skills_sync_from_template_v508(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R992_v508_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v508"}


def get_billing_payment_methods_unset_active_v509(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v509"}


def get_campaigns_audience_source_stats_v530(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R992","count":162500,"pct":77.1},
        {"source":"xhs","count":10500,"pct":26.3},
        {"source":"dy","count":98540,"pct":-123.0},
        {"source":"grp","count":3200,"pct":10.7}
    ],"total":274740,"version":"v530","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v530(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":17880,"unique_users":8385},
        {"date":"2026-10-02","downloads":18120,"unique_users":8455},
        {"date":"2026-10-03","downloads":18360,"unique_users":8525},
        {"date":"2026-10-04","downloads":18600,"unique_users":8595},
        {"date":"2026-10-05","downloads":18840,"unique_users":8665},
        {"date":"2026-10-06","downloads":19080,"unique_users":8735},
        {"date":"2026-10-07","downloads":19320,"unique_users":8805}
    ],"total":130200,"version":"v530","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v531(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":11860000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":11870000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":11880000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":11890000,"set_by":"u_001"}
    ],"count":4,"version":"v531","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

# ROUTES 注册（chunk 1 和 chunk 2 内容相同）
route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v531": lambda q, id="k_001": get_auth_api_keys_quota_history_v531(id),
    "/api/v2/skills/{id}/sync-from-template-v508": lambda q, id="s_001": get_skills_sync_from_template_v508(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v509": lambda q, id="c_001": get_billing_payment_methods_unset_active_v509(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v530": lambda q, id="c001": get_campaigns_audience_source_stats_v530(id),
    "/api/v2/files/{id}/download-by-day-list-v530": lambda q, id="f_001": get_files_download_by_day_list_v530(file_id),
'''

# 1. 注入 ROUTES chunk 1 (line 24455 前)
# line 24455 = "/api/v2/auth/api-keys/{id}/quota-history-v529"
# 实际是 ROUTES dict 内 line 24455-24459 = R661 chunk 1
# 等等！让我看 — 之前看到 line 24452+ = R661 + R662 chunk
# 现在 line 24455-24459 = R661 chunk · line 24460-24464 = R662 chunk
# 我要在 R661 chunk (line 24455) 之前注入 R663 chunk

# 找首个 "/api/v2/auth/api-keys/{id}/quota-history-v529" 行
target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v529"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of quota-history-v529 routes, got {len(target_lines)}")

# 在两个位置前都插入 route_block
# 从后往前插，避免行号错位
new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

# 2. 注入函数定义 (在最后一个 R661 quota-history-v529 函数末尾 line 29849 + 空行后)
# 找 line 29849 (实际 0-index = 29848) — 但因为前面插了 10 行 ROUTES (5+5)，行号偏移 +10
# 找内容而不是行号
fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v529","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i  # 这就是 line 29849 在新行号中

if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v529 quota-history function end")

# 找到空行后的 class Handler
class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

# 在 class_line 前插入函数定义（保留一个空行间隔）
new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]

src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R663 5 endpoints (10 ROUTES + 5 defs)")