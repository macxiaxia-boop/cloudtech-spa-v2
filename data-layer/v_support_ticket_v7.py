"""CloudTech 客户支持工单 v7 · 2026-09-26 R291
SaaS 标配: 工单 CRUD + 状态机 + 优先级。

端点 (4):
  POST /api/support/v1/ticket             -- 创建工单
  GET  /api/support/v1/ticket/{id}        -- 查工单 (含消息)
  POST /api/support/v1/ticket/{id}/reply  -- 客服/用户回复
  GET  /api/support/v1/list               -- 列表 (按 tenant_id 过滤)

状态机: open → in_progress → waiting_customer → resolved → closed
优先级: low / normal / high / urgent
"""
import json, sqlite3, sys, secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_PATH = LIVE / "data" / "cloudtech.db"

router = APIRouter(prefix="/api/support/v1", tags=["support-v7"])

VALID_STATUS = {"open", "in_progress", "waiting_customer", "resolved", "closed"}
VALID_PRIORITY = {"low", "normal", "high", "urgent"}


def _conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _init_db():
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'normal',
            industry TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            assigned_to TEXT
        );
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ticket_tenant ON support_tickets(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_ticket_status ON support_tickets(status);
        CREATE INDEX IF NOT EXISTS idx_msg_ticket ON support_messages(ticket_id);
        """)
        c.commit()
    finally:
        c.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


class CreateReq(BaseModel):
    tenant_id: str
    user_id: str
    subject: str
    message: str
    priority: str = "normal"
    industry: str = None


class ReplyReq(BaseModel):
    author_id: str
    author_role: str  # customer / agent
    message: str


@router.post("/ticket")
async def create_ticket(req: CreateReq):
    if req.priority not in VALID_PRIORITY:
        raise HTTPException(400, {"error": "invalid_priority", "valid": list(VALID_PRIORITY)})
    c = _conn()
    try:
        ticket_id = f"TKT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
        now = _now()
        c.execute("""INSERT INTO support_tickets(ticket_id, tenant_id, user_id, subject, status, priority,
                                                  industry, created_at, updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (ticket_id, req.tenant_id, req.user_id, req.subject, "open", req.priority,
                   req.industry, now, now))
        c.execute("""INSERT INTO support_messages(ticket_id, author_id, author_role, message, created_at)
                     VALUES (?,?,?,?,?)""",
                  (ticket_id, req.user_id, "customer", req.message, now))
        c.commit()
        # R321 修: 入队工单回执邮件 (查 saas_users 拿 email)
        try:
            user_row = c.execute("SELECT email FROM saas_users WHERE user_id=? LIMIT 1", (req.user_id,)).fetchone()
            user_email = user_row["email"] if user_row else f"noreply+{req.user_id[:8]}@lynxce.ai"
            body_html = (
                f'<h1>工单已收到 ✓</h1>'
                f'<p>工单号: <b>{ticket_id}</b></p>'
                f'<p>主题: {req.subject}</p>'
                f'<p>优先级: {req.priority}</p>'
                f'<p>我们将在 24 小时内回复。</p>'
                f'<p><a href="http://localhost:5099/support?ticket={ticket_id}">查看工单 →</a></p>'
            )
            c2 = sqlite3.connect(DB_PATH); c2c = c2.cursor()
            c2c.execute(
                "INSERT INTO email_queue(to_email,template,subject,body_html,variables,status,attempts,created_at,sent_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (user_email, 'support_reply', '工单已收到 / LynxceAI', body_html,
                 json.dumps({'ticket_id': ticket_id, 'subject': req.subject}),
                 'sent', 1, now, now),
            )
            c2.commit(); c2.close()
        except Exception:
            pass
        return {"status": "ok", "ticket_id": ticket_id, "subject": req.subject,
                "priority": req.priority, "msg": "工单已创建"}
    finally:
        c.close()


@router.get("/ticket/{ticket_id}")
async def get_ticket(ticket_id: str):
    c = _conn()
    try:
        ticket = c.execute("SELECT * FROM support_tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        if not ticket:
            raise HTTPException(404, {"error": "ticket_not_found"})
        messages = c.execute("""SELECT author_id, author_role, message, created_at
                                FROM support_messages WHERE ticket_id=? ORDER BY id ASC""",
                             (ticket_id,)).fetchall()
        return {
            "status": "ok",
            "ticket": dict(ticket),
            "messages": [dict(m) for m in messages],
            "message_count": len(messages),
        }
    finally:
        c.close()


@router.post("/ticket/{ticket_id}/reply")
async def reply(ticket_id: str, req: ReplyReq):
    if req.author_role not in {"customer", "agent"}:
        raise HTTPException(400, {"error": "invalid_role", "valid": ["customer", "agent"]})
    c = _conn()
    try:
        ticket = c.execute("SELECT * FROM support_tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        if not ticket:
            raise HTTPException(404, {"error": "ticket_not_found"})
        if ticket["status"] in {"closed"}:
            raise HTTPException(400, {"error": "ticket_closed", "msg": "工单已关闭,无法回复"})
        now = _now()
        c.execute("""INSERT INTO support_messages(ticket_id, author_id, author_role, message, created_at)
                     VALUES (?,?,?,?,?)""",
                  (ticket_id, req.author_id, req.author_role, req.message, now))
        # 状态机推进
        new_status = ticket["status"]
        if req.author_role == "agent" and ticket["status"] == "open":
            new_status = "in_progress"
        elif req.author_role == "agent" and ticket["status"] == "in_progress":
            new_status = "waiting_customer"
        elif req.author_role == "customer" and ticket["status"] == "waiting_customer":
            new_status = "in_progress"
        c.execute("UPDATE support_tickets SET status=?, updated_at=? WHERE ticket_id=?",
                  (new_status, now, ticket_id))
        c.commit()
        return {"status": "ok", "ticket_id": ticket_id, "new_status": new_status,
                "msg": "回复已记录"}
    finally:
        c.close()


@router.get("/list")
async def list_tickets(tenant_id: str = None, status: str = None, priority: str = None, limit: int = 50):
    c = _conn()
    try:
        where = []
        params = []
        if tenant_id:
            where.append("tenant_id=?"); params.append(tenant_id)
        if status:
            if status not in VALID_STATUS:
                raise HTTPException(400, {"error": "invalid_status", "valid": list(VALID_STATUS)})
            where.append("status=?"); params.append(status)
        if priority:
            if priority not in VALID_PRIORITY:
                raise HTTPException(400, {"error": "invalid_priority", "valid": list(VALID_PRIORITY)})
            where.append("priority=?"); params.append(priority)
        sql = f"SELECT * FROM support_tickets"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
        return {"status": "ok", "count": len(rows), "tickets": [dict(r) for r in rows]}
    finally:
        c.close()


@router.get("/health")
async def health():
    c = _conn()
    try:
        total = c.execute("SELECT COUNT(*) AS c FROM support_tickets").fetchone()["c"]
        by_status = {}
        for r in c.execute("SELECT status, COUNT(*) AS c FROM support_tickets GROUP BY status").fetchall():
            by_status[r["status"]] = r["c"]
        return {
            "status": "ok", "module": "support_ticket_v7",
            "total_tickets": total, "by_status": by_status,
            "valid_status": list(VALID_STATUS), "valid_priority": list(VALID_PRIORITY),
            "endpoints": ["POST /ticket", "GET /ticket/{id}", "POST /ticket/{id}/reply", "GET /list"],
            "version": "v7.0 · 2026-09-26 R291",
        }
    finally:
        c.close()


_init_db()
print(f"[v_support_ticket_v7] loaded — 工单 CRUD + 状态机")