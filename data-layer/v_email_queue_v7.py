"""CloudTech 邮件队列 v7 · 2026-09-26 R291
邮件异步发送 (smoke 模式) — 真实 SMTP 由用户配置 (L5 边界)。

端点 (5):
  POST /api/email/v1/enqueue           -- 邮件入队 (异步消费)
  GET  /api/email/v1/stats             -- 队列状态 (待发/已发/失败)
  GET  /api/email/v1/template/{name}   -- 取模板渲染后的 HTML
  POST /api/email/v1/process           -- 立即处理一批 (manual trigger)
  GET  /api/email/v1/inbox/{email}     -- 模拟收件箱 (开发环境)
"""
import json, sqlite3, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_PATH = LIVE / "data" / "cloudtech.db"

router = APIRouter(prefix="/api/email/v1", tags=["email-v7"])

TEMPLATES = {
    "welcome": {
        "subject": "欢迎加入灵策智算 / LynxceAI",
        "html": """<h1>欢迎 {name}!</h1>
<p>感谢注册灵策智算 SaaS。您的账号已激活。</p>
<p>当前 plan: <b>{plan}</b></p>
<p><a href="https://lynxce.ai/dashboard">立即登录 →</a></p>""",
    },
    "password_reset": {
        "subject": "重置密码 / LynxceAI",
        "html": """<h1>密码重置</h1>
<p>您好 {name},请点击下方链接在 5 分钟内重置密码:</p>
<p><a href="{reset_url}">重置密码 →</a></p>
<p>如非本人操作,请忽略此邮件。</p>""",
    },
    "subscription_upgraded": {
        "subject": "订阅升级成功 / LynxceAI",
        "html": """<h1>升级成功 🎉</h1>
<p>{old_plan} → <b>{new_plan}</b></p>
<p>本次按剩余 {days_remaining} 天 prorated 计费: ¥{prorated_charge}</p>
<p><a href="https://lynxce.ai/billing">查看账单 →</a></p>""",
    },
    "quota_warning": {
        "subject": "用量预警 / LynxceAI",
        "html": """<h1>⚠️ 用量预警</h1>
<p>本月已用 <b>{pct}%</b> 配额 (calls {calls}/{limit_calls})。</p>
<p>建议<a href="https://lynxce.ai/pricing">升级 plan</a>避免超额。</p>""",
    },
    "referral_reward": {
        "subject": "推荐奖励到账 / LynxceAI",
        "html": """<h1>推荐成功 🎉</h1>
<p>您推荐的 <b>{referee_email}</b> 已激活订阅,您获得 <b>+{points} 积分</b>。</p>
<p>继续分享,获取更多奖励:<a href="{share_url}">{share_url}</a></p>""",
    },
    "support_reply": {
        "subject": "[工单 #{ticket_id}] 回复 / LynxceAI",
        "html": """<h1>您的工单已回复</h1>
<p><b>原问题:</b> {original_question}</p>
<p><b>回复:</b> {reply}</p>
<p><a href="https://lynxce.ai/support/{ticket_id}">查看工单 →</a></p>""",
    },
}


def _conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _init_db():
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            to_email TEXT NOT NULL,
            template TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_html TEXT NOT NULL,
            variables TEXT,
            status TEXT DEFAULT 'pending',
            attempts INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            sent_at TEXT,
            last_error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_email_status ON email_queue(status);
        CREATE INDEX IF NOT EXISTS idx_email_to ON email_queue(to_email);
        """)
        c.commit()
    finally:
        c.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _render_template(name: str, variables: dict) -> dict:
    if name not in TEMPLATES:
        return None
    t = TEMPLATES[name]
    body = t["html"]
    for k, v in variables.items():
        body = body.replace("{" + k + "}", str(v))
    subject = t["subject"]
    for k, v in variables.items():
        subject = subject.replace("{" + k + "}", str(v))
    return {"subject": subject, "body_html": body}


class EnqueueReq(BaseModel):
    to_email: str
    template: str
    variables: dict = {}
    send_immediately: bool = False


@router.post("/enqueue")
async def enqueue(req: EnqueueReq):
    """邮件入队。send_immediately=True 立即处理;否则后台批量消费。"""
    rendered = _render_template(req.template, req.variables)
    if not rendered:
        raise HTTPException(400, {"error": "template_not_found", "valid": list(TEMPLATES)})
    c = _conn()
    try:
        c.execute("""INSERT INTO email_queue(to_email, template, subject, body_html, variables, created_at)
                     VALUES (?,?,?,?,?,?)""",
                  (req.to_email, req.template, rendered["subject"], rendered["body_html"],
                   json.dumps(req.variables), _now()))
        c.commit()
        # 模拟消费
        if req.send_immediately:
            c.execute("""UPDATE email_queue SET status='sent', sent_at=? WHERE id=(SELECT MAX(id) FROM email_queue)""",
                      (_now(),))
            c.commit()
        return {"status": "ok", "template": req.template, "to": req.to_email,
                "sent_immediately": req.send_immediately}
    finally:
        c.close()


@router.get("/stats")
async def stats():
    c = _conn()
    try:
        rows = c.execute("""SELECT status, COUNT(*) AS c FROM email_queue GROUP BY status""").fetchall()
        by_status = {r["status"]: r["c"] for r in rows}
        return {
            "status": "ok",
            "total": sum(by_status.values()),
            "by_status": by_status,
            "templates_available": list(TEMPLATES.keys()),
            "smtp_configured": False,  # L5 边界 — 用户配 SMTP
        }
    finally:
        c.close()


@router.get("/template/{name}")
async def template(name: str, variables: str = "{}"):
    try:
        vars = json.loads(variables)
    except Exception:
        vars = {}
    rendered = _render_template(name, vars)
    if not rendered:
        raise HTTPException(404, {"error": "template_not_found", "valid": list(TEMPLATES)})
    return {"status": "ok", "name": name, "subject": rendered["subject"], "body_html": rendered["body_html"]}


@router.post("/process")
async def process(batch_size: int = 50):
    """手动触发 — 模拟消费一批 pending 邮件 (开发环境,真实场景接 SMTP)。"""
    c = _conn()
    try:
        cur = c.execute("""SELECT id FROM email_queue WHERE status='pending' LIMIT ?""", (batch_size,))
        ids = [r["id"] for r in cur.fetchall()]
        if ids:
            placeholders = ",".join("?" * len(ids))
            c.execute(f"""UPDATE email_queue SET status='sent', sent_at=?, attempts=attempts+1
                          WHERE id IN ({placeholders})""", [_now()] + ids)
            c.commit()
        return {"status": "ok", "processed_count": len(ids), "batch_size": batch_size}
    finally:
        c.close()


@router.get("/inbox/{email}")
async def inbox(email: str, limit: int = 20):
    """模拟收件箱 — 列出某邮箱收到的所有邮件。"""
    c = _conn()
    try:
        rows = c.execute("""SELECT id, subject, body_html, status, created_at, sent_at
                            FROM email_queue WHERE to_email=? ORDER BY id DESC LIMIT ?""",
                         (email, limit)).fetchall()
        return {"status": "ok", "email": email, "count": len(rows),
                "messages": [dict(r) for r in rows]}
    finally:
        c.close()


@router.get("/health")
async def health():
    return {
        "status": "ok", "module": "email_queue_v7",
        "templates": list(TEMPLATES.keys()),
        "endpoints": ["POST /enqueue", "GET /stats", "GET /template/{name}",
                      "POST /process", "GET /inbox/{email}"],
        "version": "v7.0 · 2026-09-26 R291",
        "smtp_status": "smoke mode (L5 边界: 需 SMTP 配置)",
    }


_init_db()
print(f"[v_email_queue_v7] loaded — {len(TEMPLATES)} 模板")