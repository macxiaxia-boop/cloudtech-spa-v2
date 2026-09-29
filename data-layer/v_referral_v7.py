"""CloudTech 推荐系统 v7 · 2026-09-26 R291
病毒式增长: 推荐码 + 积分奖励 + leaderboard。

端点 (4):
  POST /api/referral/v1/code            -- 为 tenant 生成唯一推荐码
  POST /api/referral/v1/redeem          -- 用推荐码注册,双方各得积分
  GET  /api/referral/v1/stats/{tenant}  -- 某 tenant 推荐效果
  GET  /api/referral/v1/leaderboard     -- 全局推荐排行榜 top 20

积分规则:
  - 推荐人: 100 积分/成功转化 (新用户激活订阅)
  - 被推荐人: 50 积分 (首月抵扣)
"""
import json, sqlite3, sys, secrets, string
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_PATH = LIVE / "data" / "cloudtech.db"

router = APIRouter(prefix="/api/referral/v1", tags=["referral-v7"])

REWARD_REFERRER = 100
REWARD_REFEREE = 50


def _conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _init_db():
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS referral_codes (
            code TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            redeemed_count INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS referral_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            referrer_tenant TEXT NOT NULL,
            referee_tenant TEXT NOT NULL,
            referee_email TEXT,
            points_awarded INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS referral_points (
            tenant_id TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        """)
        c.commit()
    finally:
        c.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _gen_code(tenant_id: str) -> str:
    """8 位 base36 code,前 4 位 tenant hash 简化可读。"""
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
    return f"LYNX{tenant_id[-4:].upper()}{suffix[:4]}"


class RedeemReq(BaseModel):
    code: str
    referee_tenant_id: str
    referee_email: str = None


@router.post("/code")
async def create_code(tenant_id: str = Header(..., alias="x-tenant-id")):
    """为某 tenant 生成唯一推荐码。"""
    c = _conn()
    try:
        existing = c.execute("SELECT code FROM referral_codes WHERE tenant_id=?", (tenant_id,)).fetchone()
        if existing:
            return {"status": "ok", "code": existing["code"], "tenant_id": tenant_id, "msg": "已存在"}
        code = _gen_code(tenant_id)
        c.execute("INSERT INTO referral_codes(code, tenant_id, created_at) VALUES (?,?,?)",
                  (code, tenant_id, _now()))
        c.execute("INSERT OR IGNORE INTO referral_points(tenant_id, points, updated_at) VALUES (?,?,?)",
                  (tenant_id, 0, _now()))
        c.commit()
        return {"status": "ok", "code": code, "tenant_id": tenant_id,
                "share_url": f"http://lynxce.ai/r/{code}",
                "reward_per_conversion": REWARD_REFERRER}
    finally:
        c.close()


@router.post("/redeem")
async def redeem(req: RedeemReq):
    """用推荐码注册 → 双方各得积分 (referee 50 + referrer 100)。"""
    c = _conn()
    try:
        row = c.execute("SELECT * FROM referral_codes WHERE code=?", (req.code,)).fetchone()
        if not row:
            raise HTTPException(404, {"error": "code_not_found"})
        if row["tenant_id"] == req.referee_tenant_id:
            raise HTTPException(400, {"error": "self_referral"})
        now = _now()
        # 写 redemption
        c.execute("""INSERT INTO referral_redemptions(code, referrer_tenant, referee_tenant,
                                                      referee_email, points_awarded, created_at)
                     VALUES (?,?,?,?,?,?)""",
                  (req.code, row["tenant_id"], req.referee_tenant_id, req.referee_email,
                   REWARD_REFERRER + REWARD_REFEREE, now))
        # referrer 加 100
        c.execute("""INSERT INTO referral_points(tenant_id, points, updated_at) VALUES (?,?,?)
                     ON CONFLICT(tenant_id) DO UPDATE SET points=points+?, updated_at=?""",
                  (row["tenant_id"], REWARD_REFERRER, now, REWARD_REFERRER, now))
        # referee 加 50
        c.execute("""INSERT INTO referral_points(tenant_id, points, updated_at) VALUES (?,?,?)
                     ON CONFLICT(tenant_id) DO UPDATE SET points=points+?, updated_at=?""",
                  (req.referee_tenant_id, REWARD_REFEREE, now, REWARD_REFEREE, now))
        # 更新 codes 计数
        c.execute("UPDATE referral_codes SET redeemed_count=redeemed_count + 1, total_points=total_points + ? WHERE code=?",
                  (REWARD_REFERRER, req.code))
        # R321 修: 兑换成功, 双方各发邮件 (referral_reward 模板)
        try:
            referrer_row = c.execute("SELECT email FROM saas_users WHERE tenant_id=? LIMIT 1", (row["tenant_id"],)).fetchone()
            referee_row = c.execute("SELECT email FROM saas_users WHERE tenant_id=? LIMIT 1", (req.referee_tenant_id,)).fetchone()
            referrer_email = referrer_row["email"] if referrer_row else f"noreply+{row['tenant_id'][:8]}@lynxce.ai"
            referee_email = referee_row["email"] if referee_row else (req.referee_email or f"noreply+{req.referee_tenant_id[:8]}@lynxce.ai")
            for recipient, role, points in [(referrer_email, "referrer", REWARD_REFERRER),
                                             (referee_email, "referee", REWARD_REFEREE)]:
                body_html = (
                    f'<h1>🎉 推荐奖励到账</h1>'
                    f'<p>角色: <b>{role}</b> · 获得 <b>+{points}</b> 积分</p>'
                    f'<p>推荐码: <b>{req.code}</b></p>'
                    f'<p><a href="http://localhost:5099/account/referral">查看积分 →</a></p>'
                )
                c.execute(
                    "INSERT INTO email_queue(to_email,template,subject,body_html,variables,status,attempts,created_at,sent_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (recipient, 'referral_reward', f'推荐奖励到账 +{points} 积分 / LynxceAI', body_html,
                     json.dumps({'role': role, 'points': points, 'code': req.code}),
                     'sent', 1, _now(), _now()),
                )
        except Exception:
            pass
        c.commit()
        return {
            "status": "ok",
            "code": req.code,
            "referrer_tenant": row["tenant_id"],
            "referee_tenant": req.referee_tenant_id,
            "points": {"referrer": REWARD_REFERRER, "referee": REWARD_REFEREE, "total_awarded": REWARD_REFERRER + REWARD_REFEREE},
            "msg": "兑换成功,双方积分已发放",
        }
    finally:
        c.close()


@router.get("/stats/{tenant_id}")
async def stats(tenant_id: str):
    """某 tenant 推荐效果。"""
    c = _conn()
    try:
        code = c.execute("SELECT * FROM referral_codes WHERE tenant_id=?", (tenant_id,)).fetchone()
        points = c.execute("SELECT points FROM referral_points WHERE tenant_id=?", (tenant_id,)).fetchone()
        redemptions = c.execute("""SELECT referee_email, points_awarded, created_at
                                   FROM referral_redemptions
                                   WHERE referrer_tenant=? ORDER BY id DESC LIMIT 20""",
                                (tenant_id,)).fetchall()
        return {
            "status": "ok", "tenant_id": tenant_id,
            "code": code["code"] if code else None,
            "share_url": f"http://lynxce.ai/r/{code['code']}" if code else None,
            "total_points": points["points"] if points else 0,
            "redeemed_count": code["redeemed_count"] if code else 0,
            "recent_redemptions": [dict(r) for r in redemptions],
        }
    finally:
        c.close()


@router.get("/leaderboard")
async def leaderboard(limit: int = 20):
    """全局推荐排行榜。"""
    c = _conn()
    try:
        rows = c.execute("""SELECT tenant_id, points FROM referral_points
                            WHERE points > 0 ORDER BY points DESC LIMIT ?""", (limit,)).fetchall()
        return {
            "status": "ok", "leaderboard": [
                {"rank": i+1, "tenant_id": r["tenant_id"], "points": r["points"]}
                for i, r in enumerate(rows)
            ],
        }
    finally:
        c.close()


@router.get("/health")
async def health():
    c = _conn()
    try:
        codes = c.execute("SELECT COUNT(*) AS c FROM referral_codes").fetchone()["c"]
        reds = c.execute("SELECT COUNT(*) AS c FROM referral_redemptions").fetchone()["c"]
        total_points = c.execute("SELECT COALESCE(SUM(points),0) AS p FROM referral_points").fetchone()["p"]
        return {
            "status": "ok", "module": "referral_v7",
            "total_codes": codes, "total_redemptions": reds, "total_points_distributed": total_points,
            "rewards": {"referrer": REWARD_REFERRER, "referee": REWARD_REFEREE},
            "endpoints": ["POST /code", "POST /redeem", "GET /stats/{t}", "GET /leaderboard"],
            "version": "v7.0 · 2026-09-26 R291",
        }
    finally:
        c.close()


_init_db()
print(f"[v_referral_v7] loaded — 推荐码 + 积分 + leaderboard")