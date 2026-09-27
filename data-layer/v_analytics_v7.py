"""CloudTech 数据分析 v7 · 2026-09-26 R291
SaaS 增长核心: 漏斗 / 留存 / 队列 / Cohort。

端点 (4):
  GET  /api/analytics/v1/funnel       -- 注册 → 激活 → 订阅 漏斗
  GET  /api/analytics/v1/retention    -- 周留存 (cohort 分析)
  GET  /api/analytics/v1/revenue      -- MRR + by_industry + by_plan
  GET  /api/analytics/v1/cohort       -- Cohort 留存表
"""
import sqlite3, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

from fastapi import APIRouter

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_PATH = LIVE / "data" / "cloudtech.db"

router = APIRouter(prefix="/api/analytics/v1", tags=["analytics-v7"])


def _conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


@router.get("/funnel")
async def funnel():
    """注册 → 激活 → 订阅 → 付费 漏斗。"""
    c = _conn()
    try:
        registered = c.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] or 0
        # users 表无 activated 列 → 用 last_login_at 是否存在近似
        activated = c.execute("SELECT COUNT(*) AS c FROM users WHERE last_login_at IS NOT NULL").fetchone()["c"] or 0
        subscribed = c.execute("SELECT COUNT(*) AS c FROM aios_subscription").fetchone()["c"] or 0
        paying = c.execute("SELECT COUNT(*) AS c FROM aios_subscription WHERE status='active'").fetchone()["c"] or 0
        steps = [
            {"step": "registered", "count": registered, "pct": 100},
            {"step": "activated", "count": activated, "pct": round(activated / max(registered, 1) * 100, 1)},
            {"step": "subscribed", "count": subscribed, "pct": round(subscribed / max(registered, 1) * 100, 1)},
            {"step": "paying", "count": paying, "pct": round(paying / max(registered, 1) * 100, 1)},
        ]
        return {
            "status": "ok",
            "funnel": steps,
            "conversion_overall": round(paying / max(registered, 1) * 100, 2),
            "msg": f"{paying}/{registered} = {round(paying/max(registered,1)*100,2)}% 付费转化",
        }
    finally:
        c.close()


@router.get("/retention")
async def retention(weeks: int = 8):
    """周留存 — 用户在注册 N 周后是否还有活动。"""
    c = _conn()
    try:
        # 简化版: 按用户 activated_at 分 cohort,看后续活动
        rows = c.execute("""SELECT id, created_at FROM users
                            WHERE last_login_at IS NOT NULL ORDER BY created_at DESC LIMIT 100""").fetchall()
        cohort_data = defaultdict(lambda: {"size": 0, "retained": 0})
        for r in rows:
            try:
                cohort = datetime.fromisoformat(r["created_at"]).strftime("%Y-W%W")
                cohort_data[cohort]["size"] += 1
                # 简化:有 audit 记录算 retained
                act = c.execute("""SELECT COUNT(*) AS c FROM audit_log
                                   WHERE actor_id=? AND ts > ?""",
                                (str(r["id"]), r["created_at"])).fetchone()["c"]
                if act > 0:
                    cohort_data[cohort]["retained"] += 1
            except Exception:
                pass
                cohort_data[cohort]["size"] += 1
                # 简化:有 audit 记录算 retained
                act = c.execute("""SELECT COUNT(*) AS c FROM audit_log
                                   WHERE actor_id=? AND ts > ?""",
                                (r["user_id"], r["activated_at"])).fetchone()["c"]
                if act > 0:
                    cohort_data[cohort]["retained"] += 1
            except Exception:
                pass
        cohorts = []
        for cohort, data in sorted(cohort_data.items(), reverse=True)[:weeks]:
            cohorts.append({
                "cohort": cohort,
                "size": data["size"],
                "retained": data["retained"],
                "retention_pct": round(data["retained"] / max(data["size"], 1) * 100, 1),
            })
        return {"status": "ok", "cohorts": cohorts, "weeks": weeks}
    finally:
        c.close()


@router.get("/revenue")
async def revenue():
    """MRR + by industry + by plan 拆分。"""
    c = _conn()
    try:
        by_plan = defaultdict(int)
        by_industry = defaultdict(int)
        PLAN_PRICE = {"basic": 199, "pro": 1999, "enterprise": 2999}
        rows = c.execute("""SELECT plan, industry FROM aios_subscription WHERE status='active'""").fetchall()
        for r in rows:
            by_plan[r["plan"] or "basic"] += PLAN_PRICE.get(r["plan"], 199)
            by_industry[r["industry"] or "decoration"] += PLAN_PRICE.get(r["plan"], 199)
        mrr = sum(by_plan.values())
        return {
            "status": "ok",
            "mrr_yuan": mrr,
            "mrr_formatted": f"¥{mrr:,}",
            "arr_yuan": mrr * 12,
            "arr_formatted": f"¥{mrr*12:,}",
            "by_plan": dict(by_plan),
            "by_industry": dict(by_industry),
            "active_subscriptions": len(rows),
        }
    finally:
        c.close()


@router.get("/cohort")
async def cohort(weeks: int = 8):
    """Cohort 留存表 — 周维度。"""
    c = _conn()
    try:
        rows = c.execute("""SELECT id, created_at FROM users
                            WHERE last_login_at IS NOT NULL ORDER BY created_at""").fetchall()
        cohorts = defaultdict(list)
        for r in rows:
            try:
                cohort_week = datetime.fromisoformat(r["created_at"]).strftime("%Y-W%W")
                cohorts[cohort_week].append(str(r["id"]))
            except Exception:
                pass
        # 计算每周 cohort 在 N 周后的留存
        table = []
        for cohort, users in sorted(cohorts.items())[-weeks:]:
            row = {"cohort": cohort, "size": len(users), "weeks_retained": []}
            for w in range(weeks):
                retained = 0
                week_start = datetime.now(timezone.utc) - timedelta(weeks=w+1)
                week_end = week_start + timedelta(weeks=1)
                placeholders = ",".join("?" * len(users))
                act = c.execute(f"""SELECT COUNT(DISTINCT actor_id) AS c FROM audit_log
                                    WHERE actor_id IN ({placeholders})
                                    AND ts BETWEEN ? AND ?""",
                                 users + [week_start.isoformat(), week_end.isoformat()]).fetchone()["c"]
                row["weeks_retained"].append({"week": w+1, "active": act,
                                              "pct": round(act / max(len(users), 1) * 100, 1)})
            table.append(row)
        return {"status": "ok", "weeks": weeks, "cohorts": table}
    finally:
        c.close()


@router.get("/health")
async def health():
    return {
        "status": "ok", "module": "analytics_v7",
        "endpoints": ["GET /funnel", "GET /retention", "GET /revenue", "GET /cohort"],
        "version": "v7.0 · 2026-09-26 R291",
    }


print(f"[v_analytics_v7] loaded — 漏斗 + 留存 + MRR + cohort")