"""
CRM 深度引擎 v2 — Full Sales Pipeline Automation
===================================================
全生命周期客户管理 + 自动化跟进 + 数据看板

能力:
- 智能客户评分 (Lead Scoring)
- 自动跟进提醒 (基于阶段+时间)
- 流失预警 (静默客户检测)
- 成交概率预测 (基于历史数据)
- 客户健康度仪表盘
- 转介绍追踪
- 工地进度同步
"""
import json, os
import app_logger as _al
_log = _al.get_logger("crm_deep")
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import defaultdict

BASE = Path(__file__).parent
CRM_DEEP = BASE / "data" / "crm_deep"
CRM_DEEP.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 一、智能客户评分
# ═══════════════════════════════════

LEAD_SCORE_RULES = {
    "source": {
        "referral": 30,     # 转介绍最高
        "geo_search": 25,    # AI搜索来的意向强
        "xiaohongshu": 20,
        "douyin": 15,
        "wechat_mp": 15,
        "paid_ads": 10,
        "other": 5,
    },
    "budget": {
        "high": 25,    # >20万
        "mid": 20,     # 10-20万
        "low": 10,     # <10万
        "unknown": 5,
    },
    "urgency": {
        "immediate": 30,    # 马上开工
        "1_month": 25,      # 1个月内
        "3_months": 15,     # 3个月内
        "exploring": 5,     # 随便看看
    },
    "interaction": {
        "called_3plus": 20,    # 通话3次以上
        "called": 15,
        "measured": 25,        # 已量房
        "visited_office": 20,   # 已到店
        "no_response": -10,
    },
}

STAGE_TIMELINE = {
    "lead": {"max_days": 2, "action": "首次联系"},
    "contacted": {"max_days": 3, "action": "预约量房"},
    "measured": {"max_days": 5, "action": "出方案报价"},
    "quoted": {"max_days": 7, "action": "跟进谈判"},
    "negotiating": {"max_days": 14, "action": "促成签约"},
    "signed": {"max_days": 0, "action": "开工准备"},
    "constructing": {"max_days": 90, "action": "施工跟进"},
    "completed": {"max_days": 365, "action": "售后回访"},
    "maintenance": {"max_days": 30, "action": "转介绍邀请"},
}


class DeepCRM:
    """深度客户关系管理"""

    def __init__(self, tenant_id: str = "zq-5bb59623", use_db: bool = False):
        self.tid = tenant_id
        self.use_db = use_db
        self.data_file = CRM_DEEP / f"customers_{tenant_id}.json"
        self.tasks_file = CRM_DEEP / f"tasks_{tenant_id}.json"
        self._db = None
        self._init_files()

    def _init_db(self):
        """Lazy-init database connection. Returns Database or None."""
        if self._db is not None:
            return self._db
        try:
            from database import get_db
            db = get_db()
            db.fetch_one("SELECT 1 FROM crm_customers LIMIT 1")
            self._db = db
            return db
        except Exception:
            self._db = False
            return None

    def _db_available(self):
        """Check if database is initialized and available."""
        return self.use_db and self._init_db() is not None

    def _init_files(self):
        if not self.data_file.exists():
            self.data_file.write_text("[]", encoding="utf-8")
        if not self.tasks_file.exists():
            self.tasks_file.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict]:
        if self._db_available():
            import json as _json
            result = self._db.crm_list_customers(tenant_id=self.tid, limit=10000)
            if result.get("ok"):
                customers = result.get("customers", [])
                for c in customers:
                    for field in ("tags", "interactions", "follow_ups", "project"):
                        val = c.get(field)
                        if isinstance(val, str):
                            try:
                                c[field] = _json.loads(val)
                            except Exception:
                                pass
                return customers
        return json.loads(self.data_file.read_text(encoding="utf-8"))

    def _save(self, data: List[Dict]):
        if self._db_available():
            import json as _json
            for c in data:
                existing = self._db.crm_get_customer(c["id"], self.tid)
                if existing.get("ok"):
                    update = {}
                    for k, v in c.items():
                        if k in ("tags", "interactions", "follow_ups", "project"):
                            update[k] = v
                        elif k in ("name", "phone", "source", "stage", "budget", "city",
                                   "community", "area", "style", "urgency", "notes",
                                   "score", "health", "stage_entered_at"):
                            update[k] = v
                    update["updated_at"] = datetime.now().isoformat()[:19]
                    self._db.crm_update_customer(c["id"], self.tid, **update)
                else:
                    self._db.crm_create_customer(self.tid, **c)
            return
        self.data_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 客户操作 ──

    def add_customer(self, **kwargs) -> dict:
        """添加客户（含智能评分）"""
        phone = kwargs.get("phone", "")

        # Try DB first if enabled
        if self._db_available():
            import json as _json
            now = datetime.now().isoformat()[:19]
            customer_data = {
                "name": kwargs.get("name", ""),
                "phone": phone,
                "source": kwargs.get("source", "other"),
                "city": kwargs.get("city", ""),
                "community": kwargs.get("community", ""),
                "area": kwargs.get("area", 0),
                "budget": kwargs.get("budget", 0),
                "style": kwargs.get("style", ""),
                "urgency": kwargs.get("urgency", "unknown"),
                "notes": kwargs.get("notes", ""),
                "stage": "lead",
                "stage_entered_at": now,
                "created_at": now,
                "updated_at": now,
                "tags": [],
                "interactions": [],
                "follow_ups": [],
                "score": 0,
                "health": "neutral",
                "project": {
                    "start_date": None, "end_date": None,
                    "current_phase": None, "manager": None,
                    "budget_actual": 0, "issues": [], "progress_pct": 0,
                },
            }
            result = self._db.crm_create_customer(self.tid, **customer_data)
            if result.get("ok"):
                customer = result["customer"]
                customer["score"] = self._calculate_score(customer)
                self._db.crm_update_customer(customer["id"], self.tid, score=customer["score"])
                self._auto_create_task(customer, "首次联系")
                return {"ok": True, "customer": customer}
            return result

        # Fall back to JSON
        customers = self._load()
        cid = f"crm-{datetime.now().strftime('%Y%m%d')}-{len(customers)+1:04d}"

        customer = {
            "id": cid,
            "name": kwargs.get("name", ""),
            "phone": phone[-4:],
            "source": kwargs.get("source", "other"),
            "city": kwargs.get("city", ""),
            "community": kwargs.get("community", ""),
            "area": kwargs.get("area", 0),
            "budget": kwargs.get("budget", 0),
            "style": kwargs.get("style", ""),
            "urgency": kwargs.get("urgency", "unknown"),
            "stage": "lead",
            "stage_entered_at": datetime.now().isoformat()[:19],
            "created_at": datetime.now().isoformat()[:19],
            "updated_at": datetime.now().isoformat()[:19],
            "tags": [],
            "notes": kwargs.get("notes", ""),
            "interactions": [],    # 互动记录
            "follow_ups": [],      # 跟进记录
            "score": 0,            # 客户评分
            "health": "neutral",   # 健康度
            "lost_risk": False,    # 流失风险
            "project": {
                "start_date": None,
                "end_date": None,
                "current_phase": None,
                "manager": None,
                "budget_actual": 0,
                "issues": [],
                "progress_pct": 0,
            },
        }

        # 初始评分
        customer["score"] = self._calculate_score(customer)
        customers.append(customer)
        self._save(customers)

        # 自动创建首个跟进任务
        self._auto_create_task(customer, "首次联系")

        return {"ok": True, "customer": customer}

    def update_stage(self, customer_id: str, new_stage: str, notes: str = "") -> dict:
        """更新阶段（含自动化操作）"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                old_stage = c["stage"]
                c["stage"] = new_stage
                c["stage_entered_at"] = datetime.now().isoformat()[:19]
                c["updated_at"] = datetime.now().isoformat()[:19]

                c["follow_ups"].append({
                    "time": datetime.now().isoformat()[:19],
                    "action": f"阶段变更: {old_stage} → {new_stage}",
                    "notes": notes,
                })

                # 自动操作
                auto_actions = self._auto_actions_on_stage_change(c, old_stage, new_stage)
                c["score"] = self._calculate_score(c)

                self._save(customers)
                return {"ok": True, "customer": c, "old_stage": old_stage, "auto_actions": auto_actions}

        return {"ok": False, "error": "客户不存在"}

    def add_interaction(self, customer_id: str, int_type: str, notes: str = "", outcome: str = "") -> dict:
        """记录互动"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                c["interactions"].append({
                    "time": datetime.now().isoformat()[:19],
                    "type": int_type,    # call/wechat/visit/measure/quote/contract
                    "notes": notes,
                    "outcome": outcome,   # positive/neutral/negative
                })
                c["updated_at"] = datetime.now().isoformat()[:19]
                c["score"] = self._calculate_score(c)
                c["health"] = self._calculate_health(c)
                self._save(customers)
                return {"ok": True, "interaction": c["interactions"][-1]}
        return {"ok": False, "error": "客户不存在"}

    # ── 智能评分 ──

    def _calculate_score(self, customer: Dict) -> int:
        """计算客户质量评分 (0-100)"""
        score = 0

        # 来源评分
        score += LEAD_SCORE_RULES["source"].get(customer.get("source", "other"), 5)

        # 预算评分
        budget = customer.get("budget", 0)
        if budget >= 20:
            score += LEAD_SCORE_RULES["budget"]["high"]
        elif budget >= 10:
            score += LEAD_SCORE_RULES["budget"]["mid"]
        elif budget > 0:
            score += LEAD_SCORE_RULES["budget"]["low"]
        else:
            score += LEAD_SCORE_RULES["budget"]["unknown"]

        # 互动评分 (handle both list and JSON string from DB)
        interactions = customer.get("interactions", [])
        if isinstance(interactions, str):
            import json as _json
            try:
                interactions = _json.loads(interactions)
            except Exception:
                interactions = []
        call_count = sum(1 for i in interactions if i.get("type") == "call")
        if call_count >= 3:
            score += LEAD_SCORE_RULES["interaction"]["called_3plus"]
        elif call_count >= 1:
            score += LEAD_SCORE_RULES["interaction"]["called"]
        if any(i.get("type") == "measure" for i in interactions):
            score += LEAD_SCORE_RULES["interaction"]["measured"]
        if any(i.get("type") == "visit" for i in interactions):
            score += LEAD_SCORE_RULES["interaction"]["visited_office"]

        # 阶段加分
        stage_scores = {
            "lead": 0, "contacted": 5, "measured": 15,
            "quoted": 20, "negotiating": 25, "signed": 30,
        }
        score += stage_scores.get(customer.get("stage", "lead"), 0)

        # 时效扣分
        days_in_stage = self._days_in_current_stage(customer)
        timeline = STAGE_TIMELINE.get(customer.get("stage", "lead"), {})
        max_days = timeline.get("max_days", 30)
        if days_in_stage > max_days and max_days > 0:
            score -= min(20, (days_in_stage - max_days) * 2)

        return max(0, min(100, score))

    def _calculate_health(self, customer: Dict) -> str:
        """计算客户健康度"""
        days = self._days_in_current_stage(customer)
        stage = customer.get("stage", "lead")
        timeline = STAGE_TIMELINE.get(stage, {})
        max_days = timeline.get("max_days", 30)

        if max_days == 0:
            return "healthy"

        ratio = days / max_days
        if ratio < 0.5:
            return "healthy"
        elif ratio < 1.0:
            return "warning"
        elif ratio < 2.0:
            return "danger"
        else:
            return "critical"

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if self._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def add_task(self, customer_id: str = None, customer_name: str = "",
                name: str = "", stage: str = "lead",
                due_days: int = 1, priority: str = "normal") -> dict:
        """手动创建跟进任务"""
        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer_id or "",
            "customer_name": customer_name,
            "name": name,
            "stage": stage,
            "created_at": datetime.now().isoformat()[:19],
            "due_at": (datetime.now() + timedelta(days=due_days)).isoformat()[:19],
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "task": task}

    def list_customers(self, **kwargs) -> dict:
        """列出深度CRM客户（支持搜索过滤）"""
        customers = self._load()
        if kwargs.get("stage"):
            customers = [c for c in customers if c["stage"] == kwargs["stage"]]
        if kwargs.get("source"):
            customers = [c for c in customers if c["source"] == kwargs["source"]]
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("community", "") + c.get("notes", "")).lower()
            ]
        if kwargs.get("tags"):
            customers = [c for c in customers if any(t in c.get("tags", []) for t in kwargs["tags"])]
        if kwargs.get("min_score") is not None:
            customers = [c for c in customers if c.get("score", 0) >= kwargs["min_score"]]
        if kwargs.get("health"):
            customers = [c for c in customers if DeepCRM()._calculate_health(c) in kwargs["health"]]
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        customers = sorted(customers, key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(customers)
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(customers[offset:offset+limit]),
            "customers": customers[offset:offset+limit],
        }

    def get_interactions(self, customer_id: str) -> dict:
        """获取客户互动时间线"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {
                    "ok": True,
                    "customer_name": c["name"],
                    "total_interactions": len(c.get("interactions", [])),
                    "total_follow_ups": len(c.get("follow_ups", [])),
                    "interactions": c.get("interactions", []),
                    "follow_ups": c.get("follow_ups", []),
                }
        return {"ok": False, "error": "客户不存在"}

    def _days_in_current_stage(self, customer: Dict) -> int:
        """在当前阶段停留天数"""
        entered = customer.get("stage_entered_at", customer.get("created_at", ""))
        if not entered:
            return 0
        try:
            dt = datetime.fromisoformat(entered)
            return (datetime.now() - dt).days
        except Exception:
            return 0

    def _auto_actions_on_stage_change(self, customer: Dict, old_stage: str, new_stage: str) -> List[str]:
        """阶段变更自动操作"""
        actions = []

        # 签约→施工: 创建项目
        if new_stage == "signed" and old_stage != "signed":
            customer["project"] = {
                "start_date": None,
                "end_date": None,
                "current_phase": "preparation",
                "manager": None,
                "budget_actual": 0,
                "issues": [],
                "progress_pct": 0,
            }
            actions.append("创建施工项目")

        # 完工→售后: 设置回访提醒
        if new_stage == "completed":
            self._auto_create_task(customer, "30天回访", due_days=30)
            self._auto_create_task(customer, "邀请转介绍", due_days=45)
            actions.append("设置售后回访+转介绍提醒")

        # 自动创建下一阶段任务
        next_action = STAGE_TIMELINE.get(new_stage, {}).get("action")
        if next_action:
            max_days = STAGE_TIMELINE.get(new_stage, {}).get("max_days", 3)
            self._auto_create_task(customer, next_action, due_days=max(1, max_days // 2))
            actions.append(f"创建任务: {next_action}")

        return actions

    def _auto_create_task(self, customer: Dict, task_name: str, due_days: int = 1):
        """自动创建跟进任务"""
        now = datetime.now()
        due_at = (now + timedelta(days=due_days)).isoformat()[:19]
        priority = "high" if customer.get("score", 0) >= 60 else "normal"

        if self._db_available():
            self._db.crm_create_task(
                self.tid,
                customer_id=customer["id"],
                customer_name=customer.get("name", ""),
                name=task_name,
                stage=customer.get("stage", "lead"),
                due_at=due_at,
                priority=priority,
            )
            return

        tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        task = {
            "id": f"task-{len(tasks)+1:04d}",
            "customer_id": customer["id"],
            "customer_name": customer["name"],
            "name": task_name,
            "stage": customer["stage"],
            "created_at": now.isoformat()[:19],
            "due_at": due_at,
            "status": "pending",
            "priority": priority,
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 流失预警 ──

    def detect_at_risk_customers(self) -> dict:
        """检测流失风险客户"""
        customers = self._load()
        at_risk = []

        for c in customers:
            if c.get("stage") in ("signed", "constructing", "completed", "maintenance"):
                continue  # 已签约的不算流失

            health = self._calculate_health(c)
            if health in ("danger", "critical"):
                days = self._days_in_current_stage(c)
                last_interaction = c["interactions"][-1] if c.get("interactions") else None
                days_since_contact = 0
                if last_interaction:
                    dt = datetime.fromisoformat(last_interaction["time"])
                    days_since_contact = (datetime.now() - dt).days

                at_risk.append({
                    "id": c["id"],
                    "name": c["name"],
                    "stage": c["stage"],
                    "days_in_stage": days,
                    "days_since_contact": days_since_contact,
                    "score": c.get("score", 0),
                    "health": health,
                    "recommended_action": _get_rescue_action(c),
                    "urgency": "immediate" if days_since_contact > 7 else "soon",
                })

        return {
            "ok": True,
            "at_risk_count": len(at_risk),
            "immediate_action": len([r for r in at_risk if r["urgency"] == "immediate"]),
            "customers": at_risk,
        }


def _get_rescue_action(customer: Dict) -> str:
    """流失挽回建议"""
    stage = customer.get("stage", "lead")
    actions = {
        "lead": "立即电话联系，了解真实需求",
        "contacted": "发送3套同户型案例+优惠方案",
        "measured": "24h内出方案，强调差异化设计",
        "quoted": "主动降价5%或赠送软装方案",
        "negotiating": "老板亲自出面，给最终底价",
    }
    return actions.get(stage, "主动联系了解原因")


# ═══════════════════════════════════
# 二、销售漏斗深度分析
# ═══════════════════════════════════

def deep_funnel_analysis(tenant_id: str = "zq-5bb59623") -> dict:
    """深度漏斗分析"""
    crm = DeepCRM(tenant_id)
    customers = crm._load()

    # 阶段分布
    stage_dist = defaultdict(lambda: {"count": 0, "total_budget": 0, "customers": []})
    for c in customers:
        stage = c.get("stage", "lead")
        stage_dist[stage]["count"] += 1
        stage_dist[stage]["total_budget"] += c.get("budget", 0)
        stage_dist[stage]["customers"].append(c["id"])

    # 转化率
    lead_count = stage_dist.get("lead", {}).get("count", 0)
    signed_count = stage_dist.get("signed", {}).get("count", 0)
    completed_count = stage_dist.get("completed", {}).get("count", 0)

    # 平均成交周期
    signed_customers = [c for c in customers if c.get("stage") in ("signed", "constructing", "completed")]
    avg_cycle = 0
    if signed_customers:
        cycles = []
        for c in signed_customers:
            try:
                created = datetime.fromisoformat(c["created_at"])
                signed_at = None
                for f in c.get("follow_ups", []):
                    if "签约" in f.get("action", "") or f.get("to_stage") == "signed":
                        signed_at = datetime.fromisoformat(f["time"])
                        break
                if signed_at:
                    cycles.append((signed_at - created).days)
            except Exception:
                pass
        avg_cycle = round(sum(cycles) / len(cycles)) if cycles else 0

    # 来源归因（按签约）
    source_roi = defaultdict(lambda: {"leads": 0, "signed": 0, "revenue": 0})
    for c in customers:
        src = c.get("source", "other")
        source_roi[src]["leads"] += 1
        if c.get("stage") in ("signed", "constructing", "completed"):
            source_roi[src]["signed"] += 1
            source_roi[src]["revenue"] += c.get("budget", 0)

    # 各来源转化率
    for src in source_roi:
        s = source_roi[src]
        s["conversion"] = f"{round(s['signed']/max(s['leads'],1)*100)}%"
        s["avg_revenue"] = f"{round(s['revenue']/max(s['signed'],1), 1)}万"

    # 流失分析
    lost_stages = ["lead", "contacted", "measured", "quoted"]
    loss_points = {}
    for i in range(len(lost_stages) - 1):
        curr = lost_stages[i]
        next_stage = lost_stages[i + 1]
        curr_count = stage_dist.get(curr, {}).get("count", 0)
        next_count = stage_dist.get(next_stage, {}).get("count", 0)
        loss_pct = round((1 - next_count / max(curr_count, 1)) * 100)
        loss_points[f"{curr}→{next_stage}"] = {
            "from_count": curr_count,
            "to_count": next_count,
            "loss_rate": f"{loss_pct}%",
            "action": _get_loss_action(curr, loss_pct),
        }

    return {
        "ok": True,
        "total_customers": len(customers),
        "funnel": {k: v["count"] for k, v in stage_dist.items()},
        "conversion_rate": f"{round(signed_count/max(lead_count,1)*100)}%",
        "avg_deal_cycle_days": avg_cycle,
        "total_pipeline_value": sum(c.get("budget", 0) for c in customers if c.get("stage") not in ("completed", "maintenance")),
        "source_roi": dict(source_roi),
        "loss_points": loss_points,
        "health_summary": {
            "healthy": sum(1 for c in customers if DeepCRM()._calculate_health(c) == "healthy"),
            "warning": sum(1 for c in customers if DeepCRM()._calculate_health(c) == "warning"),
            "danger": sum(1 for c in customers if DeepCRM()._calculate_health(c) in ("danger", "critical")),
        },
    }


def _get_loss_action(stage: str, loss_pct: int) -> str:
    if loss_pct > 50:
        return f"⚠️ 高流失! 检查{stage}阶段话术和响应速度"
    if loss_pct > 30:
        return f"📉 建议: 优化{stage}阶段的案例展示和报价速度"
    return "✅ 正常"


# ═══════════════════════════════════
# 三、待办任务管理
# ═══════════════════════════════════

def get_pending_tasks(tenant_id: str = "zq-5bb59623", overdue_only: bool = False,
                     stage: str = None, priority: str = None,
                     customer_name: str = None, limit: int = 50) -> dict:
    """获取待办任务（增强过滤）
    
    Args:
        overdue_only: 仅显示逾期任务
        stage: 按客户阶段过滤
        priority: 按优先级过滤 (high/normal)
        customer_name: 按客户姓名搜索
        limit: 返回条数
    """
    crm = DeepCRM(tenant_id)
    tasks = json.loads(crm.tasks_file.read_text(encoding="utf-8"))
    pending = [t for t in tasks if t["status"] == "pending"]

    if overdue_only:
        now = datetime.now().isoformat()[:19]
        pending = [t for t in pending if t.get("due_at", "") < now]
    if stage:
        pending = [t for t in pending if t.get("stage") == stage]
    if priority:
        pending = [t for t in pending if t.get("priority") == priority]
    if customer_name:
        kw = customer_name.lower()
        pending = [t for t in pending if kw in t.get("customer_name", "").lower()]

    return {
        "ok": True,
        "total_pending": len(pending),
        "overdue": sum(1 for t in pending if t.get("due_at", "") < datetime.now().isoformat()[:19]),
        "today": sum(1 for t in pending if t.get("due_at", "")[:10] == datetime.now().isoformat()[:10]),
        "high_priority": sum(1 for t in pending if t.get("priority") == "high"),
        "tasks": sorted(pending, key=lambda x: x.get("due_at", ""))[:limit],
    }


def complete_task(task_id: str, tenant_id: str = "zq-5bb59623") -> dict:
    """完成任务"""
    crm = DeepCRM(tenant_id)
    tasks = json.loads(crm.tasks_file.read_text(encoding="utf-8"))
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "completed"
            t["completed_at"] = datetime.now().isoformat()[:19]
            crm.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "task": t}
    return {"ok": False, "error": "任务不存在"}


# ═══════════════════════════════════
# 四、今日工作看板
# ═══════════════════════════════════

def daily_dashboard(tenant_id: str = "zq-5bb59623") -> dict:
    """今日工作看板"""
    crm = DeepCRM(tenant_id)
    funnel = deep_funnel_analysis(tenant_id)
    at_risk = crm.detect_at_risk_customers()
    tasks = get_pending_tasks(tenant_id)

    return {
        "ok": True,
        "date": datetime.now().isoformat()[:10],
        "kpi": {
            "total_customers": funnel["total_customers"],
            "pipeline_value": f"{funnel['total_pipeline_value']}万",
            "conversion_rate": funnel["conversion_rate"],
            "avg_cycle_days": funnel["avg_deal_cycle_days"],
        },
        "today_tasks": tasks["today"],
        "overdue_tasks": tasks["overdue"],
        "at_risk_customers": at_risk["at_risk_count"],
        "immediate_action": at_risk["immediate_action"],
        "health": funnel["health_summary"],
        "top_priority": _get_top_priority(tasks, at_risk),
    }


def _get_top_priority(tasks: dict, at_risk: dict) -> List[str]:
    priorities = []
    if at_risk.get("immediate_action", 0) > 0:
        priorities.append(f"🚨 {at_risk['immediate_action']}个客户需立即挽回")
    if tasks.get("overdue", 0) > 0:
        priorities.append(f"⏰ {tasks['overdue']}个任务已逾期")
    if tasks.get("today", 0) > 0:
        priorities.append(f"📋 {tasks['today']}个任务今日到期")
    if not priorities:
        priorities.append("✅ 今日一切正常")
    return priorities


# ═══════════════════════════════════
# CLI测试
# ═══════════════════════════════════

if __name__ == "__main__":
    crm = DeepCRM()

    # 添加测试客户
    r = crm.add_customer(
        name="李先生", phone="138xxxx8888", source="geo_search",
        city="漳州", community="碧湖万达", area=120, budget=18,
        style="现代简约", urgency="1_month",
    )
    _log.info(f"添加客户: {r['customer']['id']} (评分: {r['customer']['score']})")

    # 模拟跟进
    crm.add_interaction(r["customer"]["id"], "call", "电话了解需求，计划周末量房", "positive")

    # 看板
    dash = daily_dashboard()
    _log.info(f"\n今日看板:")
    _log.info(f"  客户总数: {dash['kpi']['total_customers']}")
    _log.info(f"  管道价值: {dash['kpi']['pipeline_value']}")
    _log.info(f"  优先事项: {dash['top_priority']}")

    # 漏斗
    funnel = deep_funnel_analysis()
    _log.info(f"\n漏斗: 转化率={funnel['conversion_rate']}")
