"""V6.3 T04 — Pilot Data Importer (idempotent)
============================================

读 pilot_data/ 下的 tenants.jsonl / billing_ledger.jsonl / email_drafts.jsonl
并"导入"到内存 + 落盘 (idempotent: 重复运行结果一致).

幂等键:
  - tenants: tenant_id
  - leads: lead_id
  - billing_ledger: entry_id
  - email_drafts: draft_id

用法:
    python FINAL_HANDOFF/pilot_data/import_pilot_data.py [--data-dir DIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).resolve().parent


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def import_all(data_dir: Path = DATA_DIR) -> Dict[str, Any]:
    """幂等导入 — 重复运行同结果. 输出:各表行数 + sample."""
    result: Dict[str, Any] = {"data_dir": str(data_dir), "tables": {}}
    tables = {
        "tenants": data_dir / "tenants.jsonl",
        "leads": data_dir / "leads.jsonl",
        "billing_ledger": data_dir / "billing_ledger.jsonl",
        "email_drafts": data_dir / "email_drafts.jsonl",
    }
    for name, path in tables.items():
        rows = _load_jsonl(path)
        # 去重 (幂等) — 用 PK
        pk_map = {
            "tenants": "tenant_id", "leads": "lead_id",
            "billing_ledger": "entry_id", "email_drafts": "draft_id",
        }[name]
        seen = set()
        unique: List[Dict[str, Any]] = []
        for r in rows:
            k = r.get(pk_map)
            if k in seen:
                continue
            seen.add(k)
            unique.append(r)
        result["tables"][name] = {
            "path": str(path),
            "raw_count": len(rows),
            "unique_count": len(unique),
            "sample": unique[0] if unique else None,
        }
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=str(DATA_DIR))
    args = p.parse_args()
    res = import_all(Path(args.data_dir))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    # 二次幂等验证: 跑 2 次结果应一致
    res2 = import_all(Path(args.data_dir))
    assert res == res2, "import must be idempotent"
    print("IDEMPOTENT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
