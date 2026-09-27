"""R293 SaaS 用户门 + PWA bug 治本 全谱验证脚本"""
import urllib.request, json, sys

BASE = 'http://127.0.0.1:7790'
results = []

def step(n, ok, d=''):
    s = '✅' if ok else '❌'
    print(f'{s} {n}: {d}')
    results.append((n, ok))

def http(method, path, body=None):
    data = json.dumps(body).encode('utf-8') if body else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                  headers={'Content-Type':'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        raw = r.read().decode()
        try: return r.status, json.loads(raw)
        except: return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except: return e.code, raw

# ========== SaaS 用户门 8 项 ==========
status, d = http('GET', '/api/saas/v1/info')
step('1️⃣ saas/info',         status == 200, f"brand={d.get('brand')} skus={d.get('sku_count')}")

status, d = http('POST', '/api/saas/v1/register',
                 {'email':'r293unique@lynxce.ai','password':'lynxce2026','tenant_name':'测试装企R293','industry':'decoration','sku_id':'dec_pro'})
ok = status == 200 and 'token' in d
step('2️⃣ saas/register',      ok, f"uid={d.get('user_id','?')[:14]}... tid={d.get('tenant_id','?')[:14]}... plan={d.get('plan')}")

status, d = http('POST', '/api/saas/v1/login',
                 {'email':'r293unique@lynxce.ai','password':'lynxce2026'})
ok = status == 200 and 'token' in d
step('3️⃣ saas/login',         ok, f"token={d.get('token','?')[:24]}...")

status, d = http('POST', '/api/saas/v1/login',
                 {'email':'r293unique@lynxce.ai','password':'WRONG'})
step('4️⃣ saas/wrong-cred',    status == 401, f"HTTP {status} err={d.get('detail',{}).get('error','?')}")

# 重复注册 → 409
status, d = http('POST', '/api/saas/v1/register',
                 {'email':'r293unique@lynxce.ai','password':'lynxce2026'})
step('5️⃣ saas/dup-register',  status == 409, f"HTTP {status}")

# 落地页 HTML
status, d = http('GET', '/api/saas/v1/landing')
ok = status == 200 and isinstance(d, str) and '灵策智算' in d
step('6️⃣ saas/landing',       ok, f"HTTP {status} bytes={len(d) if isinstance(d,str) else 0}")

# 短密码校验
status, d = http('POST', '/api/saas/v1/register',
                 {'email':'x@y.com','password':'123'})
step('7️⃣ saas/short-pwd',     status == 400, f"HTTP {status}")

# SaaS banner 在 PWA index.html
r = urllib.request.urlopen(BASE + '/', timeout=5)
html = r.read().decode('utf-8', errors='replace')
step('8️⃣ PWA/banner',         'saas-gate-banner' in html and '灵策智算' in html, f"banner present + brand name in HTML")

# ========== 2 个 PWA bug 治本 4 项 ==========
# ws.map 治本: chat stub 返空数组 wrapper
status, d = http('GET', '/api/v2/chat/spaces')
ok = status == 200 and d.get('data') == []
step('🔟 ws.map fix (spaces)', ok, f"data={d.get('data')}  type={type(d.get('data')).__name__}")

status, d = http('GET', '/api/v2/chat/skills')
ok = status == 200 and d.get('data') == []
step('1️⃣1️⃣ ws.map fix (skills)', ok, f"data={d.get('data')}  type={type(d.get('data')).__name__}")

# web-vitals 405 治本
req = urllib.request.Request(BASE + '/api/v3/monitoring/web-vitals', data=b'{}', method='POST',
                              headers={'Content-Type':'application/json'})
status, _ = (lambda: (lambda r: (r.status, r.read()))(urllib.request.urlopen(req, timeout=5)))()
step('1️⃣2️⃣ web-vitals POST',   status == 200, f"HTTP {status}")

req = urllib.request.Request(BASE + '/api/v3/monitoring/web-vitals', method='GET')
status, _ = (lambda: (lambda r: (r.status, r.read()))(urllib.request.urlopen(req, timeout=5)))()
step('1️⃣3️⃣ web-vitals GET',    status == 200, f"HTTP {status}")

# Manifest rebrand
r = urllib.request.urlopen(BASE + '/manifest.json', timeout=5)
m = json.loads(r.read().decode())
step('1️⃣4️⃣ manifest rebrand',  m.get('name','').startswith('灵策智算'), f"name={m.get('name')[:30]}")

# Index.html title rebrand
r = urllib.request.urlopen(BASE + '/', timeout=5)
html = r.read().decode('utf-8', errors='replace')
ok = '<title>灵策智算' in html and 'CloudTech · AI 数字员工中台</title>' not in html
step('1️⃣5️⃣ title rebrand',     ok, f"title in HTML, old CloudTech removed")

passed = sum(1 for _, ok in results if ok)
print(f'\n═══ {passed}/{len(results)} PASS ═══')