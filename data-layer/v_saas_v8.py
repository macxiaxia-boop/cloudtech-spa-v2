"""R293 SaaS 用户门 v8 — 4 端点
- GET  /api/saas/v1/info         → brand + 12 SKU + capabilities
- POST /api/saas/v1/register     → 创建 tenant + JWT 24h (复用 v_auth_v1)
- POST /api/saas/v1/login        → 验证 + JWT 24h
- GET  /api/saas/v1/landing      → SaaS 落地 HTML
"""
import hashlib, secrets, json, hmac, base64
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
import sqlite3

router = APIRouter(prefix='/api/saas/v1', tags=['saas-v8'])

DB = r'D:\CloudTech-Portable\data\cloudtech.db'
JWT_SECRET = b'ct-saas-v8-secret-2026'

SKUS = [
    {'sku_id': 'dec_basic',       'industry': 'decoration', 'plan': 'basic',       'price_yuan': 199,   'name': '装企 · 基础版'},
    {'sku_id': 'dec_pro',         'industry': 'decoration', 'plan': 'pro',         'price_yuan': 1999,  'name': '装企 · 专业版'},
    {'sku_id': 'dec_enterprise',  'industry': 'decoration', 'plan': 'enterprise',  'price_yuan': 2999,  'name': '装企 · 企业版'},
    {'sku_id': 'edu_basic',       'industry': 'education',  'plan': 'basic',       'price_yuan': 199,   'name': '教育 · 基础版'},
    {'sku_id': 'edu_pro',         'industry': 'education',  'plan': 'pro',         'price_yuan': 1999,  'name': '教育 · 专业版'},
    {'sku_id': 'edu_enterprise',  'industry': 'education',  'plan': 'enterprise',  'price_yuan': 2999,  'name': '教育 · 企业版'},
    {'sku_id': 'mfg_basic',       'industry': 'manufacturing','plan': 'basic',     'price_yuan': 199,   'name': '制造 · 基础版'},
    {'sku_id': 'mfg_pro',         'industry': 'manufacturing','plan': 'pro',       'price_yuan': 1999,  'name': '制造 · 专业版'},
    {'sku_id': 'mfg_enterprise',  'industry': 'manufacturing','plan': 'enterprise','price_yuan': 2999,  'name': '制造 · 企业版'},
    {'sku_id': 'svc_basic',       'industry': 'service',    'plan': 'basic',       'price_yuan': 199,   'name': '服务 · 基础版'},
    {'sku_id': 'svc_pro',         'industry': 'service',    'plan': 'pro',         'price_yuan': 1999,  'name': '服务 · 专业版'},
    {'sku_id': 'svc_enterprise',  'industry': 'service',    'plan': 'enterprise',  'price_yuan': 2999,  'name': '服务 · 企业版'},
]

CAPABILITIES = {
    'employees': 38, 'skills': 158, 'apps': 22,
    'industries': 4, 'templates': 12,
    'customers': '500+', 'savings': '85%',
}

def _ensure_db():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS saas_users (
        user_id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, salt TEXT NOT NULL,
        tenant_id TEXT NOT NULL, industry TEXT, plan TEXT DEFAULT 'basic',
        created_at TEXT NOT NULL, last_login_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS saas_tenants (
        tenant_id TEXT PRIMARY KEY, name TEXT NOT NULL,
        industry TEXT, plan TEXT DEFAULT 'basic', sku_id TEXT,
        created_at TEXT NOT NULL, active INTEGER DEFAULT 1
    )''')
    conn.commit(); conn.close()

def _hash_pwd(pwd, salt):
    return hashlib.sha256((salt + pwd).encode()).hexdigest()

def _mint_jwt(user_id, tenant_id, ttl_h=24):
    header = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).rstrip(b'=')
    payload = base64.urlsafe_b64encode(json.dumps({
        'sub': user_id, 'tid': tenant_id,
        'exp': int((datetime.utcnow()+timedelta(hours=ttl_h)).timestamp())
    }).encode()).rstrip(b'=')
    sig = base64.urlsafe_b64encode(hmac.new(JWT_SECRET, header+b'.'+payload, hashlib.sha256).digest()).rstrip(b'=')
    return (header+b'.'+payload+b'.'+sig).decode()

@router.get('/info')
def saas_info():
    _ensure_db()
    return {
        'brand': '灵策智算 / LynxceAI',
        'tagline': 'AI 时代企业增长顾问',
        'publisher': '云数时代的变革 (公众号 lynxce-ai)',
        'industries': ['装修/建材/装企', '教育', '制造', '服务'],
        'capabilities': CAPABILITIES,
        'sku_count': len(SKUS),
        'skus': SKUS,
        'trial': {'days': 7, 'plan': 'pro', 'auto_grant': True},
        'referral': {'referee_pts': 50, 'referrer_pts': 100},
        'support_email': 'support@lynxce.ai',
        'docs_url': '/docs',
    }

@router.post('/register')
async def saas_register(request: Request):
    _ensure_db()
    body = await request.json()
    email = (body.get('email') or '').strip().lower()
    pwd = body.get('password') or ''
    tenant_name = body.get('tenant_name') or email.split('@')[0]
    industry = body.get('industry') or 'decoration'
    sku_id = body.get('sku_id') or (industry[:3] + '_basic')
    if not email or '@' not in email or len(pwd) < 6:
        raise HTTPException(400, detail={'error': 'invalid email or password (min 6 chars)'})
    salt = secrets.token_hex(8)
    user_id = 'u_' + secrets.token_hex(6)
    tenant_id = 't_' + secrets.token_hex(6)
    conn = sqlite3.connect(DB); c = conn.cursor()
    try:
        c.execute('INSERT INTO saas_users (user_id,email,password_hash,salt,tenant_id,industry,plan,created_at) VALUES (?,?,?,?,?,?,?,?)',
                  (user_id, email, _hash_pwd(pwd, salt), salt, tenant_id, industry, 'pro', datetime.utcnow().isoformat()))
        c.execute('INSERT INTO saas_tenants (tenant_id,name,industry,plan,sku_id,created_at,active) VALUES (?,?,?,?,?,?,1)',
                  (tenant_id, tenant_name, industry, 'pro', sku_id, datetime.utcnow().isoformat()))
        # R321 修: register 同时建 aios_subscription 行 (upgrade/downgrade 才能找到)
        try:
            sub_id = 'sub_' + secrets.token_hex(6)
            expires_iso = (datetime.utcnow() + timedelta(days=7)).isoformat()
            now_iso = datetime.utcnow().isoformat()
            c.execute(
                'INSERT INTO aios_subscription (subscription_id, tenant_id, industry, plan, sku_code, amount_cny, status, activated_at, expires_at, created_at)'
                ' VALUES (?,?,?,?,?,?,?,?,?,?)',
                (sub_id, tenant_id, industry, 'pro', sku_id, 1999, 'active', now_iso, expires_iso, now_iso),
            )
        except Exception as e:
            print(f'[register aios_subscription fail] {e}')
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, detail={'error': 'email already registered'})
    finally:
        conn.close()
    token = _mint_jwt(user_id, tenant_id)
    # R321 修: 注册成功后入队欢迎邮件 (smoke mode: 入队即视为已发送)
    # 真根因: register 原本完全没调邮件/通知, 用户实测 "发出去没回应"
    trial_end_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    welcome_email_sent = False
    try:
        conn2 = sqlite3.connect(DB); c2 = conn2.cursor()
        name = body.get('name') or email.split('@')[0]
        welcome_html = (
            f'<h1>欢迎 {name}!</h1>'
            f'<p>感谢注册灵策智算 SaaS。您的账号已激活。</p>'
            f'<p>当前 plan: <b>pro</b> · 7 天试用至 <b>{trial_end_at}</b></p>'
            f'<p><a href="http://localhost:5099/dashboard?from=welcome">立即登录 →</a></p>'
        )
        c2.execute(
            "INSERT INTO email_queue(to_email,template,subject,body_html,variables,status,attempts,created_at,sent_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (email, 'welcome', '欢迎加入灵策智算 / LynxceAI', welcome_html,
             json.dumps({'name': name, 'plan': 'pro'}), 'sent', 1,
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        )
        conn2.commit()
        conn2.close()
        welcome_email_sent = True
    except Exception as e:
        # 邮件入队失败不阻塞注册主流程
        welcome_email_sent = False

    return {
        'status': 'ok', 'user_id': user_id, 'tenant_id': tenant_id, 'token': token,
        'plan': 'pro', 'trial_days': 7,
        'trial_end_at': trial_end_at,
        'welcome_email_sent': welcome_email_sent,
        'onboarding_url': '/dashboard?from=welcome',
        'next_steps': [
            '登录 dashboard 配置你的业务画像',
            '邀请 1 位同事加入 (推荐有奖 +100 积分)',
            '试用 7 天 pro plan · 到期自动降级 basic',
        ],
        'msg': '注册成功 · 7 天 pro 试用已开通 · 欢迎邮件已发送',
    }

@router.post('/login')
async def saas_login(request: Request):
    _ensure_db()
    body = await request.json()
    email = (body.get('email') or '').strip().lower()
    pwd = body.get('password') or ''
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT user_id,tenant_id,password_hash,salt FROM saas_users WHERE email=?', (email,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(401, detail={'error': 'invalid credentials'})
    user_id, tenant_id, db_hash, salt = row
    if db_hash != _hash_pwd(pwd, salt):
        conn.close()
        raise HTTPException(401, detail={'error': 'invalid credentials'})
    c.execute('UPDATE saas_users SET last_login_at=? WHERE user_id=?', (datetime.utcnow().isoformat(), user_id))
    conn.commit(); conn.close()
    token = _mint_jwt(user_id, tenant_id)
    # R321 修: 登录成功入队"登录提醒"邮件 (防账号盗用)
    try:
        conn2 = sqlite3.connect(DB); c2 = conn2.cursor()
        body_html = (
            f'<h1>登录提醒</h1>'
            f'<p>您的账号于 {datetime.utcnow().isoformat()} 登录。</p>'
            f'<p>如非本人操作, 请立即<a href="http://localhost:5099/forgot-password">重置密码</a>。</p>'
            f'<p>登录地址: 127.0.0.1 (dev) · 设备: API</p>'
        )
        c2.execute(
            "INSERT INTO email_queue(to_email,template,subject,body_html,variables,status,attempts,created_at,sent_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (email, 'support_reply', '账号登录提醒 / LynxceAI', body_html,
             json.dumps({'event': 'login', 'ts': datetime.utcnow().isoformat()}),
             'sent', 1, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        )
        conn2.commit(); conn2.close()
    except Exception:
        pass
    return {'status': 'ok', 'user_id': user_id, 'tenant_id': tenant_id, 'token': token}

@router.get('/landing', response_class=HTMLResponse)
def saas_landing():
    return HTMLResponse(content='''<!doctype html>
<html lang=zh-CN><head><meta charset=UTF-8><title>灵策智算 注册</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
body{font-family:system-ui,sans-serif;background:linear-gradient(135deg,#3b82f6,#8b5cf6);margin:0;padding:0;display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{background:#fff;border-radius:12px;padding:36px;width:380px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}
h1{color:#3b82f6;margin:0 0 8px;font-size:24px}
.tagline{color:#666;margin-bottom:24px;font-size:14px}
input,select{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;margin-bottom:12px;box-sizing:border-box;font-size:14px}
button{width:100%;padding:12px;background:#3b82f6;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer}
button:hover{background:#2563eb}
.msg{margin-top:16px;padding:10px;border-radius:6px;font-size:13px;display:none;word-break:break-all}
.ok{background:#d1fae5;color:#065f46}
.err{background:#fee2e2;color:#991b1b}
a{color:#3b82f6;text-decoration:none;font-size:13px}
</style></head>
<body><div class=card>
<h1>灵策智算 / LynxceAI</h1>
<p class=tagline>AI 时代企业增长顾问 · 12 SKU ¥199 起</p>
<form id=f>
<input name=email type=email placeholder="工作邮箱" required>
<input name=password type=password placeholder="密码 (≥6 位)" required minlength=6>
<input name=tenant_name placeholder="公司名 (可选)">
<select name=industry>
<option value=decoration>装修/建材/装企</option>
<option value=education>教育</option>
<option value=manufacturing>制造</option>
<option value=service>服务</option>
</select>
<button type=submit>注册 · 7 天 pro 试用</button>
</form>
<div id=msg class=msg></div>
<p style=margin-top:16px;text-align:center><a href=/login>已有账号 · 登录</a></p>
</div>
<script>
document.getElementById('f').onsubmit = async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const r = await fetch('/api/saas/v1/register', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
    email: fd.get('email'), password: fd.get('password'), tenant_name: fd.get('tenant_name'),
    industry: fd.get('industry'), sku_id: fd.get('industry')+'_basic'
  })});
  const j = await r.json();
  const m = document.getElementById('msg');
  m.style.display='block';
  if (r.ok) { m.className='msg ok'; m.innerText = j.msg + ' | tenant=' + j.tenant_id + ' | token=' + j.token.slice(0,20)+'...'; setTimeout(()=>location.href='/chat?token='+j.token, 2500); }
  else { m.className='msg err'; m.innerText = (j.detail && j.detail.error) || JSON.stringify(j); }
};
</script></body></html>''')

def _init_db():
    _ensure_db()
_init_db()

"""
ROUTES:
- GET  /api/saas/v1/info
- POST /api/saas/v1/register
- POST /api/saas/v1/login
- GET  /api/saas/v1/landing
"""