"""
Core API Integration Tests — CloudTech v2.1
覆盖: Auth / Content Creation / Repurpose / Zhuangqi / GEO / System / Validation / Security
"""
import pytest, json, sys, secrets
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from admin_dashboard import app

@pytest.fixture
def seed_admin():
    from auth import AuthManager; from database import get_db
    from auth import AuthManager as _AM
    db = get_db()
    existing_t = db.fetch_one("SELECT id FROM tenants WHERE id = ?", ('tenant-test',))
    if not existing_t:
        db.insert('tenants', {'id': 'tenant-test', 'name': 'Test Tenant', 'email': 'tenant-test@cloudtech.com', 'api_key': 'key-test-123', 'api_key_hash': 'hash-test-abc'})
    existing = db.fetch_one("SELECT id FROM users WHERE email = ?", ("admin@cloudtech.com",))
    if not existing:
        a = _AM()
        a.create_user(tenant_id='tenant-test', email='admin@cloudtech.com', password='admin123', name='Test Admin', role='admin')
    return True

@pytest.fixture
def client(seed_admin):
    app.config['TESTING'] = True
    return app.test_client()

@pytest.fixture
def admin_token(client):
    r = client.post('/api/auth/login', json={'email': 'admin@cloudtech.com', 'password': 'admin123'})
    try:
        d = json.loads(r.data)
        return d.get('token', d.get('access_token', ''))
    except Exception:
        return ''

def _h(token):
    return {'X-Admin-Token': token, 'Content-Type': 'application/json'}

# ═══════════════════ System ═══════════════════
class TestSystem:
    def test_health(self, client):
        r = client.get('/health')
        assert r.status_code == 200
        assert json.loads(r.data)['status'] == 'ok'

    def test_system_status(self, client, admin_token):
        r = client.get('/api/system/status', headers=_h(admin_token))
        assert r.status_code == 200
        d = json.loads(r.data)
        assert 'services' in d

    def test_landing(self, client):
        assert client.get('/').status_code == 200

    def test_admin_page(self, client):
        assert client.get('/admin').status_code == 200

# ═══════════════════ Auth ═══════════════════
class TestAuth:
    def test_login_empty_422(self, client):
        assert client.post('/api/auth/login', json={}).status_code == 422

    def test_login_bad_email_422(self, client):
        assert client.post('/api/auth/login', json={'email': 'bad', 'password': '123456'}).status_code == 422

    def test_login_short_pw_422(self, client):
        assert client.post('/api/auth/login', json={'email': 'a@b.com', 'password': '12345'}).status_code == 422

    def test_login_wrong_creds_401(self, client):
        assert client.post('/api/auth/login', json={'email': 'no@test.com', 'password': 'wrongpas'}).status_code == 401

    def test_login_ok_200(self, client):
        r = client.post('/api/auth/login', json={'email': 'admin@cloudtech.com', 'password': 'admin123'})
        assert r.status_code == 200
        assert 'token' in json.loads(r.data)

    def test_register_empty_422(self, client):
        assert client.post('/api/auth/register', json={}).status_code == 422

    def test_register_ok(self, client):
        email = f'test-{secrets.token_hex(4)}@test.com'
        r = client.post('/api/auth/register', json={'email': email, 'password': 'test1234', 'name': 'Test'})
        assert r.status_code in (200, 400)

# ═══════════════════ Admin Guard ═══════════════════
class TestAdminGuard:
    def test_dashboard_401_no_token(self, client):
        assert client.get('/api/admin/dashboard').status_code == 401

    def test_dashboard_401_bad_token(self, client):
        assert client.get('/api/admin/dashboard', headers=_h('bad')).status_code == 401

    def test_dashboard_200_ok(self, client, admin_token):
        r = client.get('/api/admin/dashboard', headers=_h(admin_token))
        assert r.status_code == 200
        assert json.loads(r.data)['status'] == 'ok'

    def test_users_401(self, client):
        assert client.get('/api/admin/users').status_code == 401

    def test_users_200(self, client, admin_token):
        assert client.get('/api/admin/users', headers=_h(admin_token)).status_code == 200

    def test_apikeys_401(self, client):
        assert client.get('/api/admin/api-keys').status_code == 401

    def test_backup_401(self, client):
        assert client.get('/api/admin/backup/status').status_code == 401

# ═══════════════════ Content Creation ═══════════════════
class TestContentCreation:
    def test_styles_200(self, client):
        d = json.loads(client.get('/api/create/styles').data)
        assert d['status'] == 'ok'
        assert len(d['styles']) == 5

    def test_forms_200(self, client):
        d = json.loads(client.get('/api/create/forms').data)
        assert len(d['forms']) == 7
        assert len(d['hook_types']) == 6
        assert len(d['story_formulas']) == 4

    def test_topic_discovery_422(self, client):
        assert client.post('/api/create/topic-discovery', json={}).status_code == 422

    def test_generate_v2_empty_422(self, client):
        assert client.post('/api/create/generate-v2', json={}).status_code == 422

    def test_generate_v2_bad_enum_422(self, client):
        r = client.post('/api/create/generate-v2', json={
            'topic': 'test', 'content_form': 'xyz', 'creator': 'zhinan', 'platform': 'douyin'
        })
        assert r.status_code == 422

    def test_style_clone_short_422(self, client):
        assert client.post('/api/create/style-clone', json={'text': 'hi'}).status_code == 422

    def test_deai_short_422(self, client):
        assert client.post('/api/create/deai-check', json={'text': 'hi'}).status_code == 422

    def test_multi_platform_empty_422(self, client):
        assert client.post('/api/create/multi-platform', json={}).status_code == 422

# ═══════════════════ Repurpose ═══════════════════
class TestRepurpose:
    def test_extract_no_url_422(self, client):
        assert client.post('/api/repurpose/extract', json={}).status_code == 422

    def test_extract_bad_url_422(self, client):
        assert client.post('/api/repurpose/extract', json={'url': 'not-a-url'}).status_code == 422

    def test_extract_ftp_422(self, client):
        assert client.post('/api/repurpose/extract', json={'url': 'ftp://x.com'}).status_code == 422

    def test_rewrite_no_text_422(self, client):
        assert client.post('/api/repurpose/rewrite', json={}).status_code == 422

    def test_rewrite_too_short_422(self, client):
        assert client.post('/api/repurpose/rewrite', json={'text': 'x'}).status_code == 422

    def test_repurpose_page_200(self, client):
        assert client.get('/repurpose').status_code == 200

# ═══════════════════ Zhuangqi ═══════════════════
class TestZhuangqi:
    def test_formats_200(self, client):
        assert client.get('/api/zhuangqi/formats').status_code == 200

    def test_scenes_200(self, client):
        assert client.get('/api/zhuangqi/scenes').status_code == 200

    def test_cookies_200(self, client):
        assert client.get('/api/zhuangqi/cookies/status').status_code == 200

    def test_evolve_200(self, client):
        assert client.get('/api/zhuangqi/evolve/status').status_code == 200

# ═══════════════════ GEO ═══════════════════
class TestGEO:
    def test_keyword_empty_422(self, client):
        assert client.post('/api/geo/keyword-research', json={}).status_code == 422

    def test_rank_empty_422(self, client):
        assert client.post('/api/geo/rank-check', json={}).status_code == 422

    def test_content_empty_422(self, client):
        assert client.post('/api/geo/content-generate', json={}).status_code == 422

# ═══════════════════ Prompts ═══════════════════
class TestPrompts:
    def test_list_200(self, client):
        assert client.get('/api/prompts/list').status_code == 200

    def test_templates_200(self, client):
        assert client.get('/api/prompts/templates').status_code == 200

    def test_create_empty_422(self, client):
        assert client.post('/api/prompts/create', json={}).status_code == 422

    def test_generate_empty_422(self, client):
        assert client.post('/api/prompts/generate', json={}).status_code == 422

# ═══════════════════ Security ═══════════════════
class TestSecurity:
    def test_cors_header(self, client):
        r = client.get('/health', headers={'Origin': 'http://localhost:5099'})
        assert 'Access-Control-Allow-Origin' in r.headers

    def test_security_headers(self, client):
        r = client.get('/health')
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'
        assert r.headers.get('X-Frame-Options') == 'SAMEORIGIN'

    def test_no_hardcoded_keys(self):
        for f in ['admin_dashboard.py', 'repurpose_pipeline.py']:
            content = (Path(__file__).parent.parent / f).read_text(encoding='utf-8')
            assert 'sk-23002d' not in content, f"Hardcoded key found in {f}"

# ═══════════════════ Edge Cases ═══════════════════
class TestEdgeCases:

    def test_empty_json_body(self, client):
        r = client.post('/api/auth/login', data='', content_type='application/json')
        assert r.status_code == 422

    def test_xss_in_topic(self, client):
        r = client.post('/api/create/topic-discovery', json={
            'domain': '<script>alert(1)</script>', 'creators': ['zhinan'], 'count': 1
        })
        assert r.status_code != 500  # Should not crash

    def test_sql_injection_attempt(self, client):
        r = client.get('/api/admin/users?search=\' OR 1=1 --')
        assert r.status_code == 401  # Should be auth-blocked, not crashed

    def test_unicode_input(self, client):
        r = client.post('/api/create/topic-discovery', json={
            'domain': '装修设计🏠日本語한국어', 'creators': ['zhinan'], 'count': 1
        })
        assert r.status_code != 500
