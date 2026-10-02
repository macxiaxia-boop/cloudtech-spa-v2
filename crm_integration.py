"""
CRM/ERP 集成层 — CRM Integration Layer
========================================
对接装修公司已有系统，打通获客→转化→施工→交付全链路

支持对接:
- 企业微信: 客户标签+跟进记录+消息互通
- 微信公众号: 粉丝→客户转化
- 通用 CRM API: 标准 REST 接口
- 飞书多维表格: 客户管理+项目管理
"""
import app_logger as _al
_log = _al.get_logger("crm_integration")

# 本地数据: 离线同步方案
# 差异化: 筷子科技没有的行业深度对接
import json, os, csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict

BASE = Path(__file__).parent
CRM_DIR = BASE / "data" / "crm"
CRM_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 统一客户数据模型
# ═══════════════════════════════════

CUSTOMER_STAGES = [
    "lead",         # 线索
    "contacted",    # 已联系
    "measured",     # 已量房
    "quoted",       # 已报价
    "negotiating",  # 谈判中
    "signed",       # 已签约
    "constructing", # 施工中
    "completed",    # 已完工
    "maintenance",  # 售后
]

CUSTOMER_SOURCES = [
    "xiaohongshu", "douyin", "shipinhao", "wechat_mp",
    "referral", "offline", "paid_ads", "geo_search", "other",
]


class CustomerManager:
    """统一客户管理 — supports both JSON (default) and SQLite (via database.py)"""

    def __init__(self, tenant_id: str = "zq-5bb59623", use_db: bool = False):
        self.tenant_id = tenant_id
        self.use_db = use_db
        self.data_file = CRM_DIR / f"customers_{tenant_id}.json"
        self._db = None

    def _init_db(self):
        """Lazy-init database connection. Returns Database or None."""
        if self._db is not None:
            return self._db
        try:
            from database import get_db
            db = get_db()
            # Quick check tables exist
            db.fetch_one("SELECT 1 FROM crm_customers LIMIT 1")
            self._db = db
            return db
        except Exception:
            self._db = False  # Mark as unavailable
            return None

    def _db_available(self):
        """Check if database is initialized and available."""
        return self.use_db and self._init_db() is not None

    def _load(self) -> List[Dict]:
        if self.data_file.exists():
            return json.loads(self.data_file.read_text(encoding="utf-8"))
        return []

    def _save(self, data: List[Dict]):
        self.data_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_customer(self, name: str, phone: str, source: str = "other",
                     city: str = "", area: float = 0, budget: float = 0,
                     style: str = "", notes: str = "", dedup: bool = True) -> dict:
        """添加客户（支持手机号去重）"""
        phone_hash = _hash_phone(phone) if phone else ""

        # Try DB first if enabled
        if self._db_available():
            db = self._db
            if dedup and phone_hash:
                dup = db.crm_dedup_check(phone_hash, self.tenant_id)
                if dup.get("exists"):
                    return {
                        "ok": False, "error": "手机号已存在",
                        "existing_customer": dup.get("existing"),
                        "hint": "使用 dedup=False 跳过去重检查",
                    }
            return db.crm_create_customer(
                self.tenant_id,
                name=name, phone=phone, phone_hash=phone_hash,
                source=source, city=city, area=area, budget=budget,
                style=style, notes=notes,
            )

        # Fall back to JSON
        customers = self._load()

        # 手机号去重
        if dedup and phone:
            existing = [c for c in customers if c.get("phone_hash") == phone_hash]
            if existing:
                return {
                    "ok": False,
                    "error": "手机号已存在",
                    "existing_customer": existing[0],
                    "hint": "使用 dedup=False 跳过去重检查",
                }

        cid = f"cust-{datetime.now().strftime('%Y%m%d')}-{len(customers)+1:04d}"

        customer = {
            "id": cid,
            "name": name,
            "phone": phone[-4:],
            "phone_hash": phone_hash,
            "source": source,
            "city": city,
            "area": area,
            "budget": budget,
            "style": style,
            "stage": "lead",
            "notes": notes,
            "created_at": datetime.now().isoformat()[:19],
            "updated_at": datetime.now().isoformat()[:19],
            "tags": [],
            "follow_ups": [],
            "project": None,
        }

        customers.append(customer)
        self._save(customers)
        return {"ok": True, "customer": customer}

    def update_stage(self, customer_id: str, new_stage: str, notes: str = "") -> dict:
        """更新客户阶段"""
        if new_stage not in CUSTOMER_STAGES:
            return {"ok": False, "error": f"无效阶段。可选: {CUSTOMER_STAGES}"}

        # Try DB first
        if self._db_available():
            result = self._db.crm_get_customer(customer_id, self.tenant_id)
            if not result.get("ok"):
                return result
            customer = result["customer"]
            old_stage = customer.get("stage")
            follow_ups = customer.get("follow_ups", [])
            follow_ups.append({
                "time": datetime.now().isoformat()[:19],
                "from_stage": old_stage,
                "to_stage": new_stage,
                "notes": notes,
            })
            update_result = self._db.crm_update_customer(
                customer_id, self.tenant_id,
                stage=new_stage, follow_ups=follow_ups,
                stage_entered_at=datetime.now().isoformat()[:19],
            )
            if update_result.get("ok"):
                return {"ok": True, "customer": update_result.get("customer"),
                        "old_stage": old_stage, "new_stage": new_stage}
            return update_result

        # Fall back to JSON
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                old_stage = c["stage"]
                c["stage"] = new_stage
                c["updated_at"] = datetime.now().isoformat()[:19]
                c["follow_ups"].append({
                    "time": datetime.now().isoformat()[:19],
                    "from_stage": old_stage,
                    "to_stage": new_stage,
                    "notes": notes,
                })
                self._save(customers)
                return {"ok": True, "customer": c, "old_stage": old_stage, "new_stage": new_stage}
        return {"ok": False, "error": "客户不存在"}

    def add_tag(self, customer_id: str, tag: str) -> dict:
        """添加客户标签"""
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                if tag not in c["tags"]:
                    c["tags"].append(tag)
                self._save(customers)
                return {"ok": True, "tags": c["tags"]}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def update_customer(self, customer_id: str, **fields) -> dict:
        """更新客户字段（name, phone, area, budget, style, notes, city）"""
        allowed = {"name", "phone", "area", "budget", "style", "notes", "city", "source"}
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields:
            return {"ok": False, "error": f"无有效字段。可选: {allowed}"}
        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                for k, v in update_fields.items():
                    c[k] = v
                c["updated_at"] = datetime.now().isoformat()[:19]
                self._save(customers)
                return {"ok": True, "customer": c, "updated_fields": list(update_fields.keys())}
        return {"ok": False, "error": "客户不存在"}

    def get_customer(self, customer_id: str) -> dict:
        """获取客户详情"""
        if self._db_available():
            return self._db.crm_get_customer(customer_id, self.tenant_id)

        customers = self._load()
        for c in customers:
            if c["id"] == customer_id:
                return {"ok": True, "customer": c}
        return {"ok": False, "error": "客户不存在"}

    def list_customers(self, stage: str = None, source: str = None, limit: int = 50,
                       offset: int = 0, keyword: str = None, tags: list = None,
                       date_from: str = None, date_to: str = None,
                       min_budget: float = None, max_budget: float = None) -> dict:
        """列出客户（增强过滤）"""
        if self._db_available():
            db_result = self._db.crm_list_customers(
                tenant_id=self.tenant_id, stage=stage, source=source,
                keyword=keyword, tags=tags, limit=limit, offset=offset,
            )
            if db_result.get("ok"):
                customers = db_result.get("customers", [])
                if date_from:
                    customers = [c for c in customers if c.get("created_at", "")[:10] >= date_from]
                if date_to:
                    customers = [c for c in customers if c.get("created_at", "")[:10] <= date_to]
                if min_budget is not None:
                    customers = [c for c in customers if c.get("budget", 0) >= min_budget]
                if max_budget is not None:
                    customers = [c for c in customers if c.get("budget", 0) <= max_budget]
                return {
                    "ok": True, "total": db_result.get("total", len(customers)),
                    "offset": offset, "count": len(customers),
                    "has_more": db_result.get("has_more", False),
                    "customers": customers,
                }

        # Fall back to JSON
        customers = self._load()
        if stage:
            customers = [c for c in customers if c["stage"] == stage]
        if source:
            customers = [c for c in customers if c["source"] == source]
        if keyword:
            kw = keyword.lower()
            customers = [
                c for c in customers
                if kw in (c.get("name", "") + c.get("phone", "") + c.get("notes", "")).lower()
            ]
        if tags:
            customers = [c for c in customers if any(t in c.get("tags", []) for t in tags)]
        if date_from:
            customers = [c for c in customers if c.get("created_at", "")[:10] >= date_from]
        if date_to:
            customers = [c for c in customers if c.get("created_at", "")[:10] <= date_to]
        if min_budget is not None:
            customers = [c for c in customers if c.get("budget", 0) >= min_budget]
        if max_budget is not None:
            customers = [c for c in customers if c.get("budget", 0) <= max_budget]
        customers = sorted(customers, key=lambda x: x["created_at"], reverse=True)
        total = len(customers)
        paged = customers[offset:offset+limit]
        return {
            "ok": True, "total": total,
            "offset": offset, "count": len(paged),
            "has_more": (offset + limit) < total,
            "customers": paged,
        }

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        if self._db_available():
            return self._db.crm_delete_customer(customer_id, self.tenant_id)

        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        if self._db_available():
            return self._db.crm_delete_customer(customer_id, self.tenant_id)

        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        if self._db_available():
            return self._db.crm_delete_customer(customer_id, self.tenant_id)

        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        if self._db_available():
            return self._db.crm_delete_customer(customer_id, self.tenant_id)

        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def get_funnel(self) -> dict:
        """销售漏斗"""
        if self._db_available():
            all_customers = self._db.crm_list_customers(
                tenant_id=self.tenant_id, limit=10000
            ).get("customers", [])
        else:
            all_customers = self._load()

        funnel = {}
        for stage in CUSTOMER_STAGES:
            count = sum(1 for c in all_customers if c.get("stage") == stage)
            funnel[stage] = {"count": count, "label": _stage_label(stage)}

        # 计算转化率
        lead_count = funnel.get("lead", {}).get("count", 0)
        signed_count = funnel.get("signed", {}).get("count", 0)
        conversion = round(signed_count / max(lead_count, 1) * 100, 1)

        return {
            "ok": True,
            "funnel": funnel,
            "total": len(all_customers),
            "conversion_rate": f"{conversion}%",
            "avg_deal_size": _calc_avg_deal(all_customers),
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def import_from_csv(self, filepath: str, source: str = "other",
                       dedup: bool = True) -> dict:
        """从CSV批量导入客户
        
        CSV格式: 姓名,电话,城市,面积,预算,风格,备注,来源
        第一行可以是表头或数据（自动判断含"姓名"则跳过）
        """
        import csv as csv_mod
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = list(csv_mod.reader(f))
        except Exception as e:
            return {"ok": False, "error": f"读取文件失败: {e}"}

        if not reader:
            return {"ok": False, "error": "空文件"}

        # 跳过表头行
        start_row = 0
        if reader[0] and reader[0][0] in ("姓名", "name", "客户姓名"):
            start_row = 1

        imported = 0
        skipped = 0
        errors = []

        for row in reader[start_row:]:
            if not row or not row[0].strip():
                continue
            try:
                name = row[0].strip() if len(row) > 0 else ""
                phone = row[1].strip() if len(row) > 1 else ""
                city = row[2].strip() if len(row) > 2 else ""
                area = float(row[3]) if len(row) > 3 and row[3].strip() else 0
                budget = float(row[4]) if len(row) > 4 and row[4].strip() else 0
                style = row[5].strip() if len(row) > 5 else ""
                notes = row[6].strip() if len(row) > 6 else ""
                row_source = row[7].strip() if len(row) > 7 and row[7].strip() else source

                result = self.add_customer(
                    name=name, phone=phone, source=row_source,
                    city=city, area=area, budget=budget,
                    style=style, notes=notes, dedup=dedup,
                )
                if result.get("ok"):
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f"{name}: {result.get('error')}")
            except Exception as e:
                skipped += 1
                errors.append(f"行{reader.index(row)+1}: {e}")

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "total_rows": len(reader) - start_row,
            "errors": errors[:10],  # 最多10条错误
        }

    def export_csv(self) -> dict:
        """导出 CSV"""
        customers = self._load()
        csv_file = CRM_DIR / f"export_{self.tenant_id}_{datetime.now().strftime('%Y%m%d')}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "姓名", "电话", "来源", "城市", "面积", "预算", "风格", "阶段", "创建时间"])
            for c in customers:
                writer.writerow([
                    c["id"], c["name"], c["phone"], c["source"],
                    c.get("city", ""), c.get("area", ""), c.get("budget", ""),
                    c.get("style", ""), c["stage"], c["created_at"],
                ])

        return {"ok": True, "file": str(csv_file), "rows": len(customers)}


# ═══════════════════════════════════
# 企业微信集成
# ═══════════════════════════════════

def wecom_sync_customers(tenant_id: str = "zq-5bb59623") -> dict:
    """
    企业微信客户同步

    从企业微信「客户联系」同步客户到 CRM
    需要: 企业微信 corpid + corpsecret + 客户联系权限
    """
    import requests
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")

    corp_id = os.getenv("WECOM_CORP_ID", "")
    corp_secret = os.getenv("WECOM_CORP_SECRET", "")

    if not corp_id or not corp_secret:
        return {
            "ok": False,
            "error": "企业微信未配置",
            "hint": "在 .env 设置 WECOM_CORP_ID 和 WECOM_CORP_SECRET",
            "setup_guide": [
                "1. 登录企业微信管理后台",
                "2. 获取 Corp ID 和 Corp Secret",
                "3. 在 .env 中配置",
                "4. 确保有客户联系权限",
            ],
        }

    try:
        # 获取 access_token
        token_resp = requests.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={"corpid": corp_id, "corpsecret": corp_secret},
            timeout=10,
        ).json()
        access_token = token_resp.get("access_token")

        # 获取外部联系人列表
        contacts_resp = requests.get(
            "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/list",
            params={
                "access_token": access_token,
                "userid": token_resp.get("userid", ""),
            },
            timeout=10,
        ).json()

        external_userids = contacts_resp.get("external_userid", [])

        # 同步到 CRM
        mgr = CustomerManager(tenant_id)
        synced = 0
        for euid in external_userids[:50]:  # 限制50条防止超时
            detail = requests.get(
                "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get",
                params={"access_token": access_token, "external_userid": euid},
                timeout=10,
            ).json()

            contact = detail.get("external_contact", {})
            mgr.add_customer(
                name=contact.get("name", "未知"),
                phone=contact.get("mobile", ""),
                source="wecom",
            )
            synced += 1

        return {"ok": True, "synced": synced, "total_external": len(external_userids)}

    except Exception as e:
        return {"ok": False, "error": f"企业微信同步失败: {str(e)}"}


# ═══════════════════════════════════
# 飞书多维表格集成
# ═══════════════════════════════════

def feishu_sync_projects(tenant_id: str = "zq-5bb59623") -> dict:
    """
    飞书多维表格项目同步

    将客户+项目数据同步到飞书多维表格
    需要: 飞书 App ID + App Secret
    """
    return {
        "ok": False,
        "mode": "ready_for_config",
        "message": "飞书多维表格集成已就绪",
        "setup": [
            "1. 飞书开放平台创建应用",
            "2. 获取 app_id 和 app_secret",
            "3. 在 .env 配置 FEISHU_APP_ID / FEISHU_APP_SECRET",
            "4. 创建客户管理多维表格",
            "5. 配置表结构: 姓名/电话/来源/阶段/面积/预算/风格",
            "6. 自动同步: 每次客户更新 → 飞书自动更新",
        ],
        "table_schema": {
            "fields": [
                {"name": "客户姓名", "type": "text"},
                {"name": "电话", "type": "phone"},
                {"name": "获客来源", "type": "select", "options": CUSTOMER_SOURCES},
                {"name": "客户阶段", "type": "select", "options": CUSTOMER_STAGES},
                {"name": "面积(平)", "type": "number"},
                {"name": "预算(万)", "type": "number"},
                {"name": "风格", "type": "text"},
                {"name": "创建时间", "type": "datetime"},
                {"name": "最近跟进", "type": "datetime"},
            ],
        },
    }


# ═══════════════════════════════════
# 通用 CRM API
# ═══════════════════════════════════

def export_for_crm(tenant_id: str = "zq-5bb59623", format: str = "json") -> dict:
    """
    导出为标准格式，供第三方 CRM 导入

    支持: 销售易/纷享销客/EC/探迹 等
    """
    mgr = CustomerManager(tenant_id)
    result = mgr.list_customers(limit=1000)

    export_data = {
        "export_time": datetime.now().isoformat()[:19],
        "tenant_id": tenant_id,
        "format_version": "1.0",
        "customers": [],
    }

    for c in result.get("customers", []):
        export_data["customers"].append({
            "external_id": c["id"],
            "name": c["name"],
            "phone": c["phone"],
            "source": c["source"],
            "stage": c["stage"],
            "city": c.get("city", ""),
            "area": c.get("area", 0),
            "budget": c.get("budget", 0),
            "style": c.get("style", ""),
            "tags": c.get("tags", []),
            "created_at": c.get("created_at", ""),
            "updated_at": c.get("updated_at", c.get("created_at", "")),
        })

    if format == "json":
        export_file = CRM_DIR / f"crm_export_{tenant_id}_{datetime.now().strftime('%Y%m%d')}.json"
        export_file.write_text(json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif format == "csv":
        return mgr.export_csv()

    return {"ok": True, "file": str(export_file), "customers": len(export_data["customers"])}


# ═══════════════════════════════════
# 获客归因分析
# ═══════════════════════════════════

def source_attribution(tenant_id: str = "zq-5bb59623") -> dict:
    """获客来源归因分析"""
    mgr = CustomerManager(tenant_id)
    customers = mgr._load()

    by_source = {}
    by_source_signed = {}

    for c in customers:
        src = c.get("source", "other")
        by_source[src] = by_source.get(src, 0) + 1
        if c.get("stage") in ("signed", "constructing", "completed", "maintenance"):
            by_source_signed[src] = by_source_signed.get(src, 0) + 1

    # 计算各来源签约率
    attribution = {}
    for src in CUSTOMER_SOURCES:
        total = by_source.get(src, 0)
        signed = by_source_signed.get(src, 0)
        attribution[src] = {
            "leads": total,
            "signed": signed,
            "conversion": f"{round(signed / max(total, 1) * 100, 1)}%",
        }

    return {
        "ok": True,
        "total_customers": len(customers),
        "total_signed": sum(by_source_signed.values()),
        "by_source": attribution,
        "best_channel": max(attribution.items(), key=lambda x: x[1]["signed"])[0] if by_source_signed else "暂无数据",
    }


# ═══════════════════════════════════
# 辅助函数
# ═══════════════════════════════════

def _hash_phone(phone: str) -> str:
    """手机号哈希（不可逆，用于去重）"""
    import hashlib
    return hashlib.sha256(phone.encode()).hexdigest()[:16]


def _stage_label(stage: str) -> str:
    label_map = {
        "lead": "线索", "contacted": "已联系", "measured": "已量房",
        "quoted": "已报价", "negotiating": "谈判中", "signed": "已签约",
        "constructing": "施工中", "completed": "已完工", "maintenance": "售后",
    }
    return label_map.get(stage, stage)


def _calc_avg_deal(customers: list) -> str:
    signed = [c for c in customers if c.get("stage") in ("signed", "constructing", "completed")]
    if not signed:
        return "暂无"
    budgets = [c.get("budget", 0) for c in signed if c.get("budget", 0) > 0]
    if not budgets:
        return "暂无"
    return f"{sum(budgets) / len(budgets):.1f}万"


# ═══════════════════════════════════
# 快捷函数
# ═══════════════════════════════════

def get_crm_dashboard(tenant_id: str = "zq-5bb59623") -> dict:
    """CRM 仪表盘数据"""
    mgr = CustomerManager(tenant_id)
    funnel = mgr.get_funnel()
    attribution = source_attribution(tenant_id)

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "funnel": funnel.get("funnel", {}),
        "conversion_rate": funnel.get("conversion_rate", "0%"),
        "avg_deal_size": funnel.get("avg_deal_size", "暂无"),
        "best_channel": attribution.get("best_channel", "暂无"),
        "total_customers": attribution.get("total_customers", 0),
        "integrations": {
            "wecom": "已配置" if os.getenv("WECOM_CORP_ID") else "未配置",
            "feishu": "已配置" if os.getenv("FEISHU_APP_ID") else "未配置",
            "local_crm": "运行中",
        },
    }


# ═══════════════════════════════════
# CLI 测试
# ═══════════════════════════════════

if __name__ == "__main__":
    mgr = CustomerManager()
    # 添加测试客户
    r = mgr.add_customer("张先生", "138xxxx8888", "xiaohongshu", "漳州", 100, 15, "奶油风")
    _log.info(f"添加客户: {r['customer']['id']}")

    r2 = mgr.update_stage(r["customer"]["id"], "contacted", "已电话联系")
    _log.info(f"更新阶段: {r2['old_stage']} → {r2['new_stage']}")

    funnel = mgr.get_funnel()
    _log.info(f"漏斗: {json.dumps(funnel, ensure_ascii=False, indent=2)[:300]}")

    attr = source_attribution()
    _log.info(f"归因: 最佳渠道={attr['best_channel']}")
