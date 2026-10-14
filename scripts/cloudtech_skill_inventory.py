"""Inventory existing CloudTech skills without publishing raw contents.

Run locally on the Windows CloudTech workspace; by default prints only counts.
If requested, writes a metadata-only JSON report to a chosen local path.
This does not copy SKILL.md files to any repository or server.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone


def inventory(root: Path) -> dict:
    root = root.expanduser().resolve()
    report = {
        "root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED",
        "file_count": 0,
        "operation_groups": {},
        "entries": [],
    }
    if not root.is_dir():
        report["error"] = "SKILL_ROOT_UNAVAILABLE"
        return report
    kinds = Counter()
    entries = []
    for path in sorted(root.rglob("SKILL.md")):
        if len(entries) >= 5000:
            report["error"] = "SKILL_COUNT_LIMIT_EXCEEDED"
            return report
        real = path.resolve()
        if root not in real.parents:
            report["error"] = "SKILL_PATH_ESCAPES_ALLOWED_ROOT"
            return report
        relative = real.relative_to(root).as_posix()
        source = real.read_bytes()
        folder = real.parent.name
        # The report contains metadata only. Never save document text.
        entries.append({
            "relative_path": relative,
            "sha256": hashlib.sha256(source).hexdigest(),
            "size_bytes": len(source),
            "operation_id_candidate": folder.lower().replace("-", "."),
        })
        kind = folder.split("-", 1)[0].lower()
        kinds[kind] += 1
    report["file_count"] = len(entries)
    report["operation_groups"] = dict(sorted(kinds.items()))
    report["entries"] = entries
    report["status"] = "INDEXED" if entries else "BLOCKED"
    if not entries:
        report["error"] = "NO_SKILL_FILES"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root",
        default=os.environ.get(
            "CLOUDTECH_SKILL_ROOT",
            r"D:\CloudTech-Portable\data\skill_orchestrator",
        ))
    parser.add_argument("--output", help="Optional LOCAL metadata JSON output path")
    parser.add_argument("--minimum", type=int, default=100)
    options = parser.parse_args()
    report = inventory(Path(options.root))
    print(json.dumps({
        "status": report["status"],
        "file_count": report["file_count"],
        "required_minimum": options.minimum,
        "operation_groups": report["operation_groups"],
        "error": report.get("error"),
    }, ensure_ascii=False, indent=2))
    if options.output:
        dest = Path(options.output).expanduser().resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    if report["status"] != "INDEXED" or report["file_count"] < options.minimum:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
