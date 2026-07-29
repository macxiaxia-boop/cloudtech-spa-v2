"""
Tenant Data Isolation Middleware
Every query automatically scoped to tenant — prevents cross-tenant data leaks.
"""
import functools
from flask import request, jsonify, g
from database import get_db


def get_current_tenant_id():
    """Extract tenant_id from JWT token in request"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.args.get("token", "")
    if not token:
        return None

    try:
        import jwt as pyjwt
        from auth import JWT_SECRET
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("tenant_id")
    except Exception:
        return None


def require_tenant(f):
    """Decorator: require valid tenant auth"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({"error": "未登录或登录已过期"}), 401
        g.tenant_id = tenant_id
        return f(*args, **kwargs)
    return wrapper


class TenantScopedDB:
    """Database wrapper that auto-filters by tenant_id"""

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.db = get_db()

    def _add_tenant_filter(self, sql, params):
        """Inject tenant_id into WHERE clause"""
        sql_lower = sql.strip().lower()
        if "where" in sql_lower:
            sql = sql.rstrip(";") + " AND tenant_id = ?"
        else:
            # Find the right place to add WHERE
            keywords = ["group by", "order by", "limit", "having"]
            insert_pos = len(sql)
            for kw in keywords:
                idx = sql_lower.find(kw)
                if idx > 0 and idx < insert_pos:
                    insert_pos = idx
            sql = sql[:insert_pos] + " WHERE tenant_id = ?" + sql[insert_pos:]

        if params is None:
            params = [self.tenant_id]
        elif isinstance(params, list):
            params.append(self.tenant_id)
        elif isinstance(params, tuple):
            params = tuple(list(params) + [self.tenant_id])
        return sql, params

    def fetch_one(self, sql, params=None):
        sql, params = self._add_tenant_filter(sql, params)
        return self.db.fetch_one(sql, params)

    def fetch_all(self, sql, params=None):
        sql, params = self._add_tenant_filter(sql, params)
        return self.db.fetch_all(sql, params)

    def insert(self, table, data):
        data["tenant_id"] = self.tenant_id
        return self.db.insert(table, data)

    def update(self, table, data, where, where_params=None):
        if "tenant_id" not in where.lower():
            where = f"tenant_id = ? AND ({where})"
            if where_params is None:
                where_params = [self.tenant_id]
            elif isinstance(where_params, list):
                where_params.insert(0, self.tenant_id)
        return self.db.update(table, data, where, where_params)

    def execute(self, sql, params=None):
        sql, params = self._add_tenant_filter(sql, params)
        return self.db.execute(sql, params)


# Per-request tenant DB accessor
def get_tenant_db():
    if not hasattr(g, "tenant_id"):
        raise RuntimeError("No tenant in context. Use @require_tenant decorator.")
    if not hasattr(g, "_tenant_db"):
        g._tenant_db = TenantScopedDB(g.tenant_id)
    return g._tenant_db
