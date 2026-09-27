"""R291 v7 全谱 20 项验证脚本"""
import requests

BASE = 'http://127.0.0.1:7779'
results = []

def step(n, ok, d=''):
    s = '✅' if ok else '❌'
    print(f'{s} {n}: {d}')
    results.append((n, ok))

# 1
r = requests.post(f'{BASE}/api/referral/v1/code', headers={'x-tenant-id': 't_r291f'})
step('1️⃣ referral/code', r.ok, f'code={r.json().get("code")}')
code = r.json().get('code')

# 2
r = requests.post(f'{BASE}/api/referral/v1/redeem', json={'code': code, 'referee_tenant_id': 't_reff', 'referee_email': 'r@f.com'})
step('2️⃣ referral/redeem', r.ok, f'pts={r.json()["points"]["total_awarded"]}')

# 3
r = requests.get(f'{BASE}/api/referral/v1/stats/t_r291f')
step('3️⃣ referral/stats', r.ok, f'redeemed={r.json().get("redeemed_count")}')

# 4
r = requests.get(f'{BASE}/api/referral/v1/leaderboard')
step('4️⃣ referral/leaderboard', r.ok, f'top1={r.json()["leaderboard"][0]["points"] if r.json()["leaderboard"] else 0}')

# 5
r = requests.post(f'{BASE}/api/email/v1/enqueue', json={'to_email': 'u@f.com', 'template': 'welcome', 'variables': {'name': '张三', 'plan': 'pro'}, 'send_immediately': True})
step('5️⃣ email/welcome', r.ok, 'sent_immediately')

# 6
r = requests.post(f'{BASE}/api/email/v1/enqueue', json={'to_email': 'u@f.com', 'template': 'quota_warning', 'variables': {'pct': 85, 'calls': 850, 'limit_calls': 1000}})
step('6️⃣ email/quota_warn', r.ok, 'pct=85')

# 7
r = requests.get(f'{BASE}/api/email/v1/inbox/u@f.com')
step('7️⃣ email/inbox', r.ok, f'count={r.json()["count"]}')

# 8
r = requests.get(f'{BASE}/api/email/v1/template/welcome', params={'variables': '{"name":"张三","plan":"pro"}'})
step('8️⃣ email/render', r.ok, f'subject={r.json().get("subject","")[:20]}')

# 9
r = requests.post(f'{BASE}/api/support/v1/ticket', json={'tenant_id': 't_r291f', 'user_id': 'u1', 'subject': 'API', 'message': 'how', 'priority': 'high', 'industry': 'decoration'})
tid = r.json()['ticket_id']
step('9️⃣ support/ticket high', r.ok, f'tid={tid}')

# 10
r = requests.post(f'{BASE}/api/support/v1/ticket/{tid}/reply', json={'author_id': 'a1', 'author_role': 'agent', 'message': 'ok'})
step('🔟 support/reply', r.ok, f'new={r.json().get("new_status")}')

# 11
r = requests.post(f'{BASE}/api/quota/v1/enforce', json={'tenant_id': 't_r291f', 'operation': 'big', 'estimated_calls': 99999})
step('1️⃣1️⃣ quota → 402', r.status_code == 402, f'HTTP {r.status_code}')

# 12
r = requests.post(f'{BASE}/api/quota/v1/enforce', json={'tenant_id': 't_r291f', 'operation': 'small', 'estimated_calls': 5})
step('1️⃣2️⃣ quota ok', r.ok, f'allowed={r.json().get("allowed")}')

# 13
r = requests.get(f'{BASE}/api/quota/v1/check/t_r291f')
step('1️⃣3️⃣ quota/check', r.ok, f'plan={r.json().get("plan")}')

# 14
r = requests.get(f'{BASE}/api/analytics/v1/funnel')
step('1️⃣4️⃣ funnel', r.ok, f'{r.json().get("msg","")[:40]}')

# 15
r = requests.get(f'{BASE}/api/analytics/v1/revenue')
step('1️⃣5️⃣ revenue', r.ok, f'MRR=¥{r.json().get("mrr_yuan")} subs={r.json().get("active_subscriptions")}')

# 16
r = requests.get(f'{BASE}/api/analytics/v1/cohort', params={'weeks': 4})
step('1️⃣6️⃣ cohort', r.ok, f'weeks={r.json().get("weeks")}')

# 17
r = requests.get(f'{BASE}/api/analytics/v1/retention', params={'weeks': 4})
step('1️⃣7️⃣ retention', r.ok, f'weeks={r.json().get("weeks")}')

# 18
r = requests.post(f'{BASE}/api/recovery/v1/forgot', json={'email': 'nobody@f.com'})
step('1️⃣8️⃣ recovery 匿名', r.ok and r.json().get('status') == 'ok', f'不泄露:{r.json().get("msg","")[:20]}')

# 19
r = requests.post(f'{BASE}/api/sub/v1/upgrade', json={'tenant_id': 'no_sub', 'new_plan': 'enterprise', 'industry': 'decoration'})
step('1️⃣9️⃣ sub/upgrade', r.status_code in (200, 404), f'HTTP {r.status_code}')

# 20
r = requests.get(f'{BASE}/api/support/v1/list', params={'tenant_id': 't_r291f'})
step('2️⃣0️⃣ support/list', r.ok, f'count={r.json()["count"]}')

passed = sum(1 for _, ok in results if ok)
print(f'\n═══ {passed}/{len(results)} PASS ═══')