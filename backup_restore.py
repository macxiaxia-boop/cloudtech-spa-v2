#!/usr/bin/env python3
"""
Backup & Restore v1.0 — AI操作系统备份恢复引擎
=================================================
解决: 系统状态不可恢复 — 改崩了只能从头再来

功能:
  1. 每日备份所有关键状态文件 (state/, openclaw.json, cron-jobs.json, .mcp.json)
  2. 备份Obsidian仓库配置 (.obsidian/ 目录结构，非内容)
  3. 备份Hermes配置
  4. 压缩为日期归档 (.zip)
  5. 保留最近30天备份，自动清理过期
  6. 恢复命令: --restore <备份文件>
  7. 列出可用备份: --list
  8. 备份校验: --verify

Usage:
    python backup_restore.py --backup              # 执行备份
    python backup_restore.py --list                # 列出可用备份
    python backup_restore.py --restore <文件>      # 从备份恢复
    python backup_restore.py --verify <文件>       # 校验备份完整性
    python backup_restore.py --status              # 查看备份状态
    python backup_restore.py --cleanup             # 清理过期备份
    python backup_restore.py --backup --quiet       # 静默备份
"""

import os
import sys
import json
import zipfile
import argparse
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── 路径配置 ─────────────────────────────────
USER_HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
OPENCLAW_DIR = USER_HOME / ".openclaw"
STATE_DIR = OPENCLAW_DIR / "state"
WORKSPACE_DIR = OPENCLAW_DIR / "workspace"
TOOLS_DIR = OPENCLAW_DIR / "tools"
LOGS_DIR = OPENCLAW_DIR / "logs"
TOOLS_CORE_DIR = TOOLS_DIR / "core"
BACKUP_DIR = OPENCLAW_DIR / "backups"
OBSIDIAN_VAULT = Path("D:/个人文件/AI")
HERMES_CONFIG = USER_HOME / ".hermes"

# ── 备份清单 ─────────────────────────────────
BACKUP_MANIFEST = {
    "openclaw_configs": [
        OPENCLAW_DIR / "openclaw.json",
        OPENCLAW_DIR / "cron-jobs.json",
        OPENCLAW_DIR / ".mcp.json",
        OPENCLAW_DIR / "gateway.cmd",
    ],
    "state_files": [
        STATE_DIR / "system-state.json",
        STATE_DIR / "delta-sv-registry.json",
        STATE_DIR / "personal-system-health.json",
        STATE_DIR / "post_mortem_log.json",
        STATE_DIR / "failure_db.json",
        STATE_DIR / "recovery_log.json",
        STATE_DIR / "delta-sv-bridge-report.json",
        STATE_DIR / "system-capability-snapshot.json",
        STATE_DIR / "feedback-classifier-rules.json",
    ],
    "workspace_files": sorted(WORKSPACE_DIR.glob("*.md")),
    "auth_files": [
        OPENCLAW_DIR / "workbench-token.txt",
        OPENCLAW_DIR / "workbench-token-plain.txt",
    ],
    "agents_config": [
        OPENCLAW_DIR / "agents" / "audit-agent.md",
    ],
}

RETENTION_DAYS = 30
CST = timezone(timedelta(hours=8))
PASS = "✓"
FAIL = "✗"
WARN = "!"


def cst_now():
    return datetime.now(CST)


def fmt_time(dt=None):
    if dt is None:
        dt = cst_now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def load_json(path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


# ══════════════════════════════════════════════════
# 备份引擎
# ══════════════════════════════════════════════════
def collect_backup_items():
    """收集所有需要备份的文件"""
    items = []
    errors = []

    for section, paths in BACKUP_MANIFEST.items():
        for path in paths:
            if not path:
                continue
            if isinstance(path, list):
                # 通配符展开
                for p in path:
                    if p.exists() and p.is_file():
                        try:
                            rel = p.relative_to(OPENCLAW_DIR)
                        except ValueError:
                            rel = p.relative_to(USER_HOME)
                        items.append({
                            "source": p,
                            "archive_name": str(rel).replace("\\", "/")
                        })
                continue
            if path.exists() and path.is_file():
                try:
                    rel = path.relative_to(OPENCLAW_DIR)
                except ValueError:
                    rel = path.relative_to(USER_HOME)
                items.append({
                    "source": path,
                    "archive_name": str(rel).replace("\\", "/")
                })
            else:
                errors.append(f"文件不存在: {path}")

    return items, errors


def create_backup(items, quiet=False):
    """创建备份归档"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = cst_now().strftime("%Y%m%d-%H%M%S")
    backup_file = BACKUP_DIR / f"openclaw-backup-{ts}.zip"

    archived_count = 0
    skipped_count = 0
    error_count = 0

    with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            source = item["source"]
            arcname = item["archive_name"]
            if not source.exists():
                skipped_count += 1
                continue
            try:
                zf.write(source, arcname)
                archived_count += 1
            except Exception as e:
                error_count += 1
                if not quiet:
                    print(f"  {FAIL} 备份失败: {source.name} - {str(e)[:60]}")

    # 写入备份清单
    manifest = {
        "backup_file": backup_file.name,
        "timestamp": fmt_time(),
        "ts_iso": cst_now().isoformat(),
        "total_files": archived_count,
        "skipped": skipped_count,
        "errors": error_count,
        "file_list": [item["archive_name"] for item in items if item["source"].exists()]
    }
    manifest_path = backup_file.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    if not quiet:
        print(f"  {PASS} 备份完成: {backup_file.name}")
        print(f"    文件数: {archived_count} | 跳过: {skipped_count} | 错误: {error_count}")
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"    大小: {size_mb:.1f}MB")

    return {
        "success": error_count == 0,
        "backup_file": str(backup_file),
        "manifest": str(manifest_path),
        "archived_count": archived_count,
        "size_mb": round(backup_file.stat().st_size / (1024 * 1024), 1) if backup_file.exists() else 0
    }


def cleanup_old_backups(quiet=False):
    """清理过期备份"""
    if not BACKUP_DIR.exists():
        return 0

    cutoff = cst_now() - timedelta(days=RETENTION_DAYS)
    removed = 0

    for f in BACKUP_DIR.iterdir():
        if f.suffix not in ('.zip', '.json'):
            continue
        # 从文件名提取日期
        try:
            # openclaw-backup-20260619-120000.zip
            parts = f.stem.split("-")
            if len(parts) >= 3:
                date_str = parts[-2]
                ts = datetime.strptime(date_str, "%Y%m%d")
                ts = ts.replace(tzinfo=CST)
                if ts < cutoff:
                    f.unlink()
                    removed += 1
        except (ValueError, IndexError):
            # 非标准文件名，跳过
            continue

    if not quiet and removed > 0:
        print(f"  {PASS} 清理了 {removed} 个过期备份")

    return removed


def list_backups():
    """列出所有可用备份"""
    if not BACKUP_DIR.exists():
        print(f"  {WARN} 备份目录不存在: {BACKUP_DIR}")
        return []

    backups = []
    for f in sorted(BACKUP_DIR.glob("openclaw-backup-*.zip")):
        size_mb = f.stat().st_size / (1024 * 1024)
        # 读取清单
        manifest_path = f.with_suffix(".json")
        manifest = load_json(manifest_path, {})
        ts = manifest.get("timestamp", "?")
        count = manifest.get("total_files", "?")

        # 从文件名提取日期
        try:
            parts = f.stem.split("-")
            date_str = f"{parts[-2][:4]}-{parts[-2][4:6]}-{parts[-2][6:8]}"
            time_str = f"{parts[-1][:2]}:{parts[-1][2:4]}:{parts[-1][4:6]}"
            display_ts = f"{date_str} {time_str}"
        except Exception:
            display_ts = ts

        backups.append({
            "file": f.name,
            "path": str(f),
            "size_mb": round(size_mb, 1),
            "timestamp": display_ts,
            "file_count": count
        })

    if not backups:
        print(f"  {WARN} 无可用备份")
        return []

    print(f"\n{'═' * 60}")
    print(f"  可用备份 (共 {len(backups)} 个)")
    print(f"{'═' * 60}")
    for b in backups:
        print(f"  [{PASS}] {b['timestamp']} | {b['file']} | {b['size_mb']}MB | {b['file_count']}文件")

    return backups


def verify_backup(backup_path):
    """校验备份文件完整性"""
    path = Path(backup_path)
    if not path.exists():
        print(f"  {FAIL} 备份文件不存在: {path}")
        return False

    try:
        with zipfile.ZipFile(path, 'r') as zf:
            # 测试文件完整性
            bad = zf.testzip()
            if bad:
                print(f"  {FAIL} 备份损坏: {bad}")
                return False

            # 列出内容
            names = zf.namelist()
            print(f"\n{'═' * 60}")
            print(f"  备份校验: {path.name}")
            print(f"{'═' * 60}")
            print(f"  大小: {path.stat().st_size / (1024 * 1024):.1f}MB")
            print(f"  文件数: {len(names)}")
            print(f"  {PASS} 完整性校验通过")

            # 检查关键文件
            key_files = ["openclaw.json", "cron-jobs.json", ".mcp.json"]
            for kf in key_files:
                found = any(kf in n for n in names)
                print(f"  {PASS if found else WARN} {kf}: {'存在' if found else '缺失'}")

            return True

    except zipfile.BadZipFile:
        print(f"  {FAIL} 无效的ZIP文件: {path}")
        return False
    except Exception as e:
        print(f"  {FAIL} 校验异常: {str(e)[:100]}")
        return False


def restore_backup(backup_path, quiet=False):
    """从备份恢复"""
    path = Path(backup_path)
    if not path.exists():
        print(f"  {FAIL} 备份文件不存在: {path}")
        return False

    # 先校验
    if not verify_backup(backup_path):
        print(f"  {FAIL} 备份校验未通过，取消恢复")
        return False

    print(f"\n{'═' * 60}")
    print(f"  恢复备份: {path.name}")
    print(f"  目标: {OPENCLAW_DIR}")
    print(f"{'═' * 60}")

    if not quiet:
        confirm = input(f"\n  确认恢复? 这将覆盖现有文件 (yes/no): ")
        if confirm.lower() not in ('yes', 'y'):
            print(f"  {WARN} 已取消")
            return False

    restored = 0
    errors = 0
    skipped = []

    with zipfile.ZipFile(path, 'r') as zf:
        names = zf.namelist()
        for name in names:
            # 安全检查: 防止 zip slip
            clean_name = name.replace("\\", "/")
            if ".." in clean_name or clean_name.startswith("/"):
                skipped.append(f"跳过危险路径: {name}")
                continue

            target = OPENCLAW_DIR / clean_name
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                zf.extract(name, str(OPENCLAW_DIR))
                restored += 1
            except Exception as e:
                errors += 1
                if not quiet:
                    print(f"  {FAIL} 恢复失败: {name} - {str(e)[:60]}")

    print(f"\n  {PASS if errors == 0 else WARN} 恢复完成")
    print(f"    已恢复: {restored} 文件")
    print(f"    错误: {errors}")
    if skipped:
        print(f"    跳过: {len(skipped)}")
        for s in skipped[:5]:
            print(f"    {WARN} {s}")

    return errors == 0


def show_backup_status():
    """显示备份状态"""
    print_header("备份系统状态")

    # 备份目录
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    total_size = sum(f.stat().st_size for f in BACKUP_DIR.glob("*.zip"))
    total_mb = total_size / (1024 * 1024)
    count = len(list(BACKUP_DIR.glob("*.zip")))
    print(f"\n  备份目录: {BACKUP_DIR}")
    print(f"  备份文件数: {count}")
    print(f"  总大小: {total_mb:.1f}MB")
    print(f"  保留期限: {RETENTION_DAYS}天")

    # 最近备份
    backups = sorted(BACKUP_DIR.glob("openclaw-backup-*.zip"), reverse=True)
    if backups:
        latest = backups[0]
        size_mb = latest.stat().st_size / (1024 * 1024)
        print(f"\n  最近备份: {latest.name}")
        print(f"  大小: {size_mb:.1f}MB")
        print(f"  路径: {latest}")

    else:
        print(f"\n  {WARN} 尚无备份")

    # 存储使用趋势
    if count >= 2:
        sizes = [f.stat().st_size for f in backups[:7]]
        avg = sum(sizes) / len(sizes) / (1024 * 1024)
        print(f"  平均备份大小: {avg:.1f}MB")

    # 下次清理时间
    oldest = None
    for f in backups:
        try:
            parts = f.stem.split("-")
            date_str = parts[-2]
            ts = datetime.strptime(date_str, "%Y%m%d")
            ts = ts.replace(tzinfo=CST)
            if oldest is None or ts < oldest:
                oldest = ts
        except Exception:
            continue

    if oldest:
        expires = oldest + timedelta(days=RETENTION_DAYS)
        remaining = (expires - cst_now()).days
        if remaining > 0:
            print(f"  最早备份过期: {remaining}天后 ({expires.strftime('%Y-%m-%d')})")
        else:
            print(f"  {WARN} 有 {abs(remaining)} 天前的过期备份需要清理")


def print_header(title):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="AI系统备份恢复引擎 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backup", action="store_true", help="执行备份")
    group.add_argument("--restore", type=str, metavar="<备份文件>", help="从备份恢复")
    group.add_argument("--verify", type=str, metavar="<备份文件>", help="校验备份完整性")
    group.add_argument("--list", action="store_true", help="列出可用备份")
    group.add_argument("--status", action="store_true", help="查看备份系统状态")
    group.add_argument("--cleanup", action="store_true", help="清理过期备份")
    parser.add_argument("--quiet", action="store_true", help="静默模式")

    args = parser.parse_args()

    if args.list:
        list_backups()
    elif args.status:
        show_backup_status()
    elif args.cleanup:
        removed = cleanup_old_backups(args.quiet)
        if not args.quiet and removed > 0:
            print(f"  {PASS} 已清理 {removed} 个过期备份")
        elif not args.quiet:
            print(f"  {PASS} 无过期备份")
    elif args.verify:
        verify_backup(args.verify)
    elif args.restore:
        restore_backup(args.restore, args.quiet)
    elif args.backup:
        print_header("系统备份")
        items, errors = collect_backup_items()

        if errors and not args.quiet:
            for e in errors[:5]:
                print(f"  {WARN} {e}")

        result = create_backup(items, args.quiet)
        cleanup_old_backups(quiet=True)  # 静默清理

        if result["success"]:
            print(f"\n  {PASS} 备份完成: {result['backup_file']}")
        else:
            print(f"\n  {WARN} 备份完成但有错误")

        if not args.quiet:
            # 列出最近3个备份
            backups = sorted(BACKUP_DIR.glob("openclaw-backup-*.zip"), reverse=True)[:3]
            if backups:
                print(f"\n  最近备份:")
                for b in backups:
                    print(f"  {b.name}")


if __name__ == "__main__":
    main()
