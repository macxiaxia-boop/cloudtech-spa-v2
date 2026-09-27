"""digital_employees stub — CloudTech digital employee deployment tracker.

Original module was missing from sys.path, causing /api/v2/employees/{list,list/frontend}
to 500. This minimal stub restores expected EMPLOYEES export so live routes succeed.

Created 2026-09-25 as L1 patch (no L5 risk; no DB / no external IO).

EMPLOYEES: dict[str, dict] — mapping of employee_id → deployment metadata.
   Key matches PRESET_EMPLOYEES keys in v3_3_employees_routes.FRONTEND_EMPLOYEES /
   BACKEND_EMPLOYEES. Populated empty by default; real deployment fills it via
   POST /api/v2/employees/deploy.
"""
from __future__ import annotations

# Match keys defined in v3_3_employees_routes (8 preset digital employees)
EMPLOYEES: dict = {}

__all__ = ["EMPLOYEES"]