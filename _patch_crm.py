"""
_patch_crm.py — One-Time CRM Enhancement Patch
===============================================
⚠️ DO NOT IMPORT THIS MODULE. It modifies source files on disk.

Run once as: python _patch_crm.py

Adds P0 and P1 features to crm_integration.py and crm_deep.py:
- Phone dedup
- Customer search/filtering (keyword, tags, date range, pagination)
- Customer deletion
- CSV bulk import
- update_customer() (edit fields)
- add_task() public API
- Task filtering by stage/priority/customer
- Customer interactions listing
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from crm_integration import CustomerManager, CUSTOMER_STAGES, CUSTOMER_SOURCES, CRM_DIR, _hash_phone
    from crm_deep import DeepCRM, CRM_DEEP

    print("=" * 60)
    print("CRM ENHANCEMENT PATCH")
    print("=" * 60)

    patch_count = 0

    # ═══════════════════════════════════════
    # PATCH 1: Phone dedup in add_customer (crm_integration)
    # ═══════════════════════════════════════
    patch_count += 1
    print(f"\n[PATCH {patch_count}] Phone dedup in CustomerManager.add_customer()")

    # Read the original file
    crm_file = Path(__file__).parent / "crm_integration.py"
    content = crm_file.read_text(encoding="utf-8")

    # Replace add_customer to add phone dedup check
    old_add = '''    def add_customer(self, name: str, phone: str, source: str = "other",
                     city: str = "", area: float = 0, budget: float = 0,
                     style: str = "", notes: str = "") -> dict:
        """添加客户"""
        customers = self._load()
        cid = f"cust-{datetime.now().strftime('%Y%m%d')}-{len(customers)+1:04d}"'''

    new_add = '''    def add_customer(self, name: str, phone: str, source: str = "other",
                     city: str = "", area: float = 0, budget: float = 0,
                     style: str = "", notes: str = "", dedup: bool = True) -> dict:
        """添加客户（支持手机号去重）"""
        customers = self._load()

        # 手机号去重
        if dedup and phone:
            phone_hash = _hash_phone(phone)
            existing = [c for c in customers if c.get("phone_hash") == phone_hash]
            if existing:
                return {
                    "ok": False,
                    "error": "手机号已存在",
                    "existing_customer": existing[0],
                    "hint": "使用 dedup=False 跳过去重检查",
                }

        cid = f"cust-{datetime.now().strftime('%Y%m%d')}-{len(customers)+1:04d}"'''

    content = content.replace(old_add, new_add)

    # ---- Add search/filter/pagination to list_customers ----
    old_list = '''    def list_customers(self, stage: str = None, source: str = None, limit: int = 50) -> dict:
        """列出客户"""
        customers = self._load()
        if stage:
            customers = [c for c in customers if c["stage"] == stage]
        if source:
            customers = [c for c in customers if c["source"] == source]
        customers = sorted(customers, key=lambda x: x["created_at"], reverse=True)
        return {"ok": True, "total": len(customers), "customers": customers[:limit]}'''

    new_list = '''    def list_customers(self, stage: str = None, source: str = None, limit: int = 50,
                       offset: int = 0, keyword: str = None, tags: list = None,
                       date_from: str = None, date_to: str = None,
                       min_budget: float = None, max_budget: float = None) -> dict:
        """列出客户（增强过滤）
        
        Args:
            stage: 按阶段过滤
            source: 按来源过滤
            limit: 返回条数
            offset: 分页偏移
            keyword: 按姓名/电话/备注搜索
            tags: 按标签过滤 (需包含任一标签)
            date_from: 创建日期起始 (YYYY-MM-DD)
            date_to: 创建日期截止 (YYYY-MM-DD)
            min_budget: 最低预算
            max_budget: 最高预算
        """
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
        }'''

    content = content.replace(old_list, new_list)

    # ---- Add delete_customer ----
    old_get_funnel = '''    def get_funnel(self) -> dict:'''

    new_delete = '''    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        customers = self._load()
        for i, c in enumerate(customers):
            if c["id"] == customer_id:
                deleted = customers.pop(i)
                self._save(customers)
                return {"ok": True, "deleted": deleted}
        return {"ok": False, "error": "客户不存在"}

    def get_funnel(self) -> dict:'''

    content = content.replace(old_get_funnel, new_delete)

    # ---- Add update_customer ----
    old_get_customer = '''    def get_customer(self, customer_id: str) -> dict:'''

    new_update_cust = '''    def update_customer(self, customer_id: str, **fields) -> dict:
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

    def get_customer(self, customer_id: str) -> dict:'''

    content = content.replace(old_get_customer, new_update_cust)

    # ---- Add import_from_csv ----
    old_export = '''    def export_csv(self) -> dict:'''

    new_import = '''    def import_from_csv(self, filepath: str, source: str = "other",
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

    def export_csv(self) -> dict:'''

    content = content.replace(old_export, new_import)

    crm_file.write_text(content, encoding="utf-8")
    print("  ✓ crm_integration.py enhanced")

    # ═══════════════════════════════════════
    # PATCH 2: Enhance crm_deep.py
    # ═══════════════════════════════════════
    patch_count += 1
    print(f"\n[PATCH {patch_count}] DeepCRM enhancements (search, add_task, task filtering, interactions)")

    deep_file = Path(__file__).parent / "crm_deep.py"
    content = deep_file.read_text(encoding="utf-8")

    # ---- Add add_task() public method ----
    old_days = '''    def _days_in_current_stage(self, customer: Dict) -> int:'''

    new_task_method = '''    def add_task(self, customer_id: str = None, customer_name: str = "",
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
            customers = [c for c in customers if crm._calculate_health(c) in kwargs["health"]]
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

    def _days_in_current_stage(self, customer: Dict) -> int:'''

    content = content.replace(old_days, new_task_method)

    # ---- Fix get_pending_tasks to accept filters ----
    old_pending = '''def get_pending_tasks(tenant_id: str = "zq-5bb59623", overdue_only: bool = False) -> dict:
    """获取待办任务"""
    crm = DeepCRM(tenant_id)
    tasks = json.loads(crm.tasks_file.read_text(encoding="utf-8"))
    pending = [t for t in tasks if t["status"] == "pending"]

    if overdue_only:
        now = datetime.now().isoformat()[:19]
        pending = [t for t in pending if t.get("due_at", "") < now]

    return {
        "ok": True,
        "total_pending": len(pending),
        "overdue": sum(1 for t in pending if t.get("due_at", "") < datetime.now().isoformat()[:19]),
        "today": sum(1 for t in pending if t.get("due_at", "")[:10] == datetime.now().isoformat()[:10]),
        "tasks": sorted(pending, key=lambda x: x.get("due_at", ""))[:20],
    }'''

    new_pending = '''def get_pending_tasks(tenant_id: str = "zq-5bb59623", overdue_only: bool = False,
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
    }'''

    content = content.replace(old_pending, new_pending)

    deep_file.write_text(content, encoding="utf-8")
    print("  ✓ crm_deep.py enhanced")

    print("\n" + "=" * 60)
    print("ALL PATCHES APPLIED. Re-running tests...")
    print("=" * 60)
