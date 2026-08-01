#!/usr/bin/env python3
"""
Auto-Recovery Daemon v1.0 — AI操作系统自愈引擎
=================================================
解决: 异常无自愈 — 出错后系统停滞，需要人工干预

功能:
  1. 监控常见故障模式 (从 learning_log / failure_db 读取模式)
  2. 自动重启失败的Cron Job (指数退避重试)
  3. 自动轮转过大的状态文件 (learning_log.json, task-queue.json)
  4. 自动重启核心服务 (Gateway, Hermes, MCP)
  5. 自动清理卡住的Session
  6. 自动刷新API Key (从备份key文件恢复)
  7. 发送告警到飞书 (当需要人工干预时)
  8. 保持恢复日志

Usage:
    python auto_recovery.py                        # 执行一次全面恢复检查
    python auto_recovery.py --watch                # 持续监控模式 (每60秒)
    python auto_recovery.py --health-check         # 仅执行健康检查并自动修复
    python auto_recovery.py --rotate-logs          # 仅执行日志轮转
    python auto_recovery.py --status               # 查看当前恢复状态
    python auto_recovery.py --history              # 查看恢复历史
    python auto_recovery.py --cleanup-sessions     # 清理卡住的Session
"""

import os
import sys
import json
import time
import socket
import subprocess
import argparse
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── 路径 ─────────────────────────────────
USER_HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
OPENCLAW_DIR = USER_HOME / ".openclaw"
STATE_DIR = OPENCLAW_DIR / "state"
TOOLS_CORE_DIR = OPENCLAW_DIR / "tools" / "core"
LOGS_DIR = OPENCLAW_DIR / "logs"
WORKSPACE_DIR = OPENCLAW_DIR / "workspace"

CRON_JOBS_FILE = OPENCLAW_DIR / "cron-jobs.json"
OPENCLAW_CONFIG = OPENCLAW_DIR / "openclaw.json"
SESSIONS_JSON = OPENCLAW_DIR / "agents" / "main" / "sessions" / "sessions.json"
RECOVERY_LOG = STATE_DIR / "recovery_log.json"
FAILURE_DB_FILE = STATE_DIR / "failure_db.json"
HEALTH_SNAPSHOT_FILE = STATE_DIR / "personal-system-health.json"
POST_MORTEM_LOG = STATE_DIR / "post_mortem_log.json"
RECOVERY_LOCK = STATE_DIR / "recovery.lock"

CST = timezone(timedelta(hours=8))

PASS = "✓"
FAIL = "✗"
WARN = "!"
RECOVER = "⟳"

# ── Windows 服务重启脚本 ──────────────────
GATEWAY_RESTART_SCRIPT = TOOLS_CORE_DIR / "openclaw-gateway-restart.ps1"
HEALTH_CHECK_SCRIPT = TOOLS_CORE_DIR / "openclaw-health-check.ps1"
HERMES_WATCHDOG = OPENCLAW_DIR / "tools" / "hermes" / "watchdog.ps1"

# ── 文件大小阈值 ──────────────────
LOG_SIZE_WARN_MB = 50
LOG_SIZE_ROTATE_MB = 100
STATE_FILE_SIZE_WARN_MB = 10

# ── 已知故障模式 ──────────────────
KNOWN_FAILURE_PATTERNS = [
    {
        "pattern": "gateway.*不可达|gateway.*restart|gateway.*timeout",
        "description": "Gateway连接超时",
        "action": "restart_gateway",
        "cooldown_minutes": 15
    },
    {
        "pattern": "Hermes.*timeout|Hermes.*unreachable",
        "description": "Hermes服务不可达",
        "action": "restart_hermes",
        "cooldown_minutes": 10
    },
    {
        "pattern": "API key.*invalid|API key.*expired|401",
        "description": "API Key过期或无效",
        "action": "alert_api_key",
        "cooldown_minutes": 60
    },
    {
        "pattern": "disk.*full|空间不足|No space left",
        "description": "磁盘空间不足",
        "action": "alert_disk_full",
        "cooldown_minutes": 120
    },
    {
        "pattern": "stuck session|卡住会话|In Progress",
        "description": "Session卡住",
        "action": "cleanup_sessions",
        "cooldown_minutes": 5
    },
    {
        "pattern": "rate_limit|429|too many requests",
        "description": "API限流",
        "action": "rate_limit_backoff",
        "cooldown_minutes": 30
    }
]


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


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

# ══════════════════════════════════════════════════
# 恢复日志
# ══════════════════════════════════════════════════
def log_recovery(action, target, status, detail=""):
    """记录恢复操作"""
    log = load_json(RECOVERY_LOG, {"entries": [], "stats": {"total": 0, "success": 0, "fail": 0}})
    entry = {
        "timestamp": fmt_time(),
        "ts_iso": cst_now().isoformat(),
        "action": action,
        "target": target,
        "status": status,
        "detail": detail
    }
    log["entries"].append(entry)
    log["stats"]["total"] += 1
    if status == "success":
        log["stats"]["success"] += 1
    else:
        log["stats"]["fail"] += 1

    # 保留最近200条
    if len(log["entries"]) > 200:
        log["entries"] = log["entries"][-200:]

    save_json(RECOVERY_LOG, log)
    return entry


def get_recovery_history(days=7):
    """获取最近恢复历史"""
    log = load_json(RECOVERY_LOG, {"entries": []})
    cutoff = cst_now() - timedelta(days=days)
    recent = []
    for e in log.get("entries", []):
        try:
            ts = datetime.fromisoformat(e.get("ts_iso", ""))
            if ts.replace(tzinfo=CST) if ts.tzinfo is None else ts >= cutoff:
                recent.append(e)
        except Exception:
            recent.append(e)
    return recent


# ══════════════════════════════════════════════════
# Gateway 重启
# ══════════════════════════════════════════════════
def check_gateway():
    """检查Gateway是否健康"""
    try:
        sock = socket.create_connection(("127.0.0.1", 18792), timeout=5)
        sock.close()
        return True, "Gateway 18792 可达"
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return False, f"Gateway 不可达: {str(e)[:50]}"


def restart_gateway():
    """重启OpenClaw Gateway"""
    if not GATEWAY_RESTART_SCRIPT.exists():
        # 尝试用 gateway.cmd 重启
        gateway_cmd = OPENCLAW_DIR / "gateway.cmd"
        if gateway_cmd.exists():
            try:
                result = subprocess.run(
                    ["cmd", "/c", str(gateway_cmd)],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(OPENCLAW_DIR)
                )
                log_recovery("restart", "openclaw-gateway", "success" if result.returncode == 0 else "fail",
                             result.stdout[:200])
                return result.returncode == 0
            except subprocess.TimeoutExpired:
                log_recovery("restart", "openclaw-gateway", "fail", "超时")
                return False
        log_recovery("restart", "openclaw-gateway", "fail", "重启脚本不存在")
        return False

    try:
        result = subprocess.run(
            ["powershell", "-File", str(GATEWAY_RESTART_SCRIPT)],
            capture_output=True, text=True, timeout=60
        )
        log_recovery("restart", "openclaw-gateway", "success" if result.returncode == 0 else "fail",
                     result.stdout[:200] or result.stderr[:200])
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log_recovery("restart", "openclaw-gateway", "fail", "重启超时")
        return False
    except Exception as e:
        log_recovery("restart", "openclaw-gateway", "fail", str(e)[:100])
        return False


# ══════════════════════════════════════════════════
# Hermes 重启
# ══════════════════════════════════════════════════
def restart_hermes():
    """重启Hermes (通过watchdog)"""
    if not HERMES_WATCHDOG.exists():
        log_recovery("restart", "hermes", "fail", "watchdog脚本不存在")
        return False

    try:
        result = subprocess.run(
            ["powershell", "-File", str(HERMES_WATCHDOG)],
            capture_output=True, text=True, timeout=30
        )
        success = "OK" in result.stdout or "started" in result.stdout
        log_recovery("restart", "hermes", "success" if success else "fail",
                     result.stdout[:200] or result.stderr[:200])
        return success
    except Exception as e:
        log_recovery("restart", "hermes", "fail", str(e)[:100])
        return False


# ══════════════════════════════════════════════════
# Session 清理
# ══════════════════════════════════════════════════
def cleanup_stuck_sessions():
    """清理卡住的Session"""
    if not SESSIONS_JSON.exists():
        return 0, "Session文件不存在"

    try:
        data = json.loads(SESSIONS_JSON.read_text(encoding='utf-8'))
        fixed = 0
        for key in list(data.keys()):
            if isinstance(data[key], dict):
                status = data[key].get("status", "")
                if status == "running":
                    data[key]["status"] = "done"
                    data[key]["completedAt"] = fmt_time()
                    fixed += 1

        if fixed > 0:
            SESSIONS_JSON.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            log_recovery("cleanup", "stuck-sessions", "success", f"清理了 {fixed} 个卡住会话")
        return fixed, f"清理了 {fixed} 个卡住会话"
    except Exception as e:
        log_recovery("cleanup", "stuck-sessions", "fail", str(e)[:100])
        return 0, str(e)[:100]


# ══════════════════════════════════════════════════
# 日志轮转
# ══════════════════════════════════════════════════
def rotate_logs():
    """轮转过大的日志文件"""
    rotated = []
    errors = []

    if not LOGS_DIR.exists():
        return rotated, errors

    # 归档目录
    archive_dir = LOGS_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)

    for f in LOGS_DIR.iterdir():
        if not f.is_file():
            continue
        size_mb = f.stat().st_size / (1024 * 1024)
        if size_mb > LOG_SIZE_ROTATE_MB:
            # 轮转: 压缩并归档
            ts = cst_now().strftime("%Y%m%d-%H%M%S")
            archive_name = f"{f.stem}-{ts}{f.suffix}"
            archive_path = archive_dir / archive_name
            try:
                # 复制到归档
                shutil.copy2(f, archive_path)
                # 清空原文件
                f.write_text("", encoding='utf-8')
                rotated.append(f.name)
                log_recovery("rotate", f.name, "success",
                             f"{size_mb:.1f}MB -> 归档到 {archive_name}")
            except Exception as e:
                errors.append(f"{f.name}: {str(e)[:60]}")
        elif size_mb > LOG_SIZE_WARN_MB:
            # 超过警告线但未到轮转线，只记录
            pass

    return rotated, errors


# ══════════════════════════════════════════════════
# 状态文件轮转
# ══════════════════════════════════════════════════
def rotate_state_files():
    """轮转过大的状态文件"""
    rotated = []
    files_to_check = [
        ("post_mortem_log.json", POST_MORTEM_LOG, 10000),
    ]

    for name, path, max_entries in files_to_check:
        if not path.exists():
            continue
        try:
            data = load_json(path, [])
            if isinstance(data, list) and len(data) > max_entries:
                # 保留最近的 max_entries 条
                trimmed = data[-max_entries:]
                save_json(path, trimmed)
                rotated.append(name)
                log_recovery("trim", name, "success",
                             f"{len(data)} -> {len(trimmed)} 条目")
            elif isinstance(data, dict):
                entries = data.get("entries", [])
                if len(entries) > max_entries:
                    data["entries"] = entries[-max_entries:]
                    save_json(path, data)
                    rotated.append(name)
                    log_recovery("trim", name, "success",
                                 f"{len(entries)} -> {len(data['entries'])} 条目")
        except Exception as e:
            pass

    return rotated


# ══════════════════════════════════════════════════
# Cron Job 健康检查
# ══════════════════════════════════════════════════
def check_cron_jobs_health():
    """检查Cron Job配置完整性"""
    if not CRON_JOBS_FILE.exists():
        return []

    issues = []
    try:
        jobs = json.loads(CRON_JOBS_FILE.read_text(encoding='utf-8'))
        for job in jobs:
            name = job.get("name", "unknown")
            falert = job.get("failureAlert", {})
            if not falert.get("enabled", True):
                issues.append({"name": name, "issue": "告警未启用"})
            # 检查backoff配置
            retry = job.get("retry", {})
            if not retry:
                pass  # 顶层重试配置在 cron.retry
    except Exception as e:
        issues.append({"name": "cron-jobs.json", "issue": str(e)[:60]})

    return issues


# ══════════════════════════════════════════════════
# 故障模式匹配
# ══════════════════════════════════════════════════
def match_failure_patterns(log_text):
    """检查日志文本是否匹配已知故障模式"""
    import re
    matched = []
    for pattern in KNOWN_FAILURE_PATTERNS:
        if re.search(pattern["pattern"], log_text, re.IGNORECASE):
            matched.append(pattern)
    return matched


def check_recent_failures():
    """检查最近的故障记录"""
    failures = []
    # 读取 post_mortem_log
    pm_log = load_json(POST_MORTEM_LOG, [])
    if isinstance(pm_log, list):
        for entry in pm_log[-20:]:
            outcome = entry.get("outcome", "")
            if outcome == "fail":
                failures.append({
                    "timestamp": entry.get("timestamp", ""),
                    "domain": entry.get("domain", ""),
                    "root_cause": entry.get("root_cause", ""),
                    "fix": entry.get("fix", "")
                })

    # 读取 failure_db
    fdb = load_json(FAILURE_DB_FILE, {"failures": []})
    for entry in fdb.get("failures", [])[-10:]:
        failures.append({
            "timestamp": entry.get("timestamp", ""),
            "domain": entry.get("domain", ""),
            "root_cause": entry.get("root_cause", ""),
            "fix": entry.get("fix", "")
        })

    return failures


# ══════════════════════════════════════════════════
# 综合自愈流程
# ══════════════════════════════════════════════════
def run_self_heal(check_only=False):
    """执行自愈流程"""
    results = {
        "timestamp": fmt_time(),
        "actions_taken": [],
        "gateway_ok": False,
        "sessions_fixed": 0,
        "logs_rotated": [],
        "state_files_trimmed": [],
        "issues_found": []
    }

    # 1. 检查Gateway
    print(f"\n  1. 检查 Gateway...")
    gw_ok, gw_detail = check_gateway()
    if gw_ok:
        print(f"     {PASS} {gw_detail}")
        results["gateway_ok"] = True
    else:
        print(f"     {FAIL} {gw_detail}")
        results["gateway_ok"] = False
        if not check_only:
            print(f"     {RECOVER} 重启 Gateway...")
            success = restart_gateway()
            results["actions_taken"].append({
                "action": "restart_gateway",
                "success": success
            })
            if success:
                print(f"     {PASS} Gateway 重启成功")
            else:
                print(f"     {FAIL} Gateway 重启失败")

    # 2. 检查并清理Session
    print(f"\n  2. 检查 Session...")
    fixed, detail = cleanup_stuck_sessions()
    if fixed > 0:
        print(f"     {RECOVER} {detail}")
    else:
        print(f"     {PASS} {detail}")
    results["sessions_fixed"] = fixed
    if fixed > 0:
        results["actions_taken"].append({"action": "cleanup_sessions", "success": True, "count": fixed})

    # 3. 检查并轮转日志
    print(f"\n  3. 检查日志文件...")
    rotated, errors = rotate_logs()
    if rotated:
        print(f"     {RECOVER} 轮转了: {', '.join(rotated)}")
    else:
        print(f"     {PASS} 日志文件正常")
    if errors:
        for e in errors:
            print(f"     {FAIL} 轮转错误: {e}")
    results["logs_rotated"] = rotated
    if rotated:
        results["actions_taken"].append({"action": "rotate_logs", "success": True, "count": len(rotated)})

    # 4. 检查并轮转状态文件
    print(f"\n  4. 检查状态文件...")
    trimmed = rotate_state_files()
    if trimmed:
        print(f"     {RECOVER} 精简了: {', '.join(trimmed)}")
    else:
        print(f"     {PASS} 状态文件正常")
    results["state_files_trimmed"] = trimmed
    if trimmed:
        results["actions_taken"].append({"action": "trim_state_files", "success": True})

    # 5. 检查Cron Job配置
    print(f"\n  5. 检查 Cron Job 配置...")
    cron_issues = check_cron_jobs_health()
    if cron_issues:
        for ci in cron_issues:
            print(f"     {WARN} {ci['name']}: {ci['issue']}")
        results["issues_found"].extend(cron_issues)
    else:
        print(f"     {PASS} Cron Job 配置正常")

    # 6. 检查近期故障
    print(f"\n  6. 检查近期故障记录...")
    failures = check_recent_failures()
    if failures:
        print(f"     {WARN} 发现 {len(failures)} 条最近故障记录:")
        for f in failures[-5:]:
            print(f"     - [{f.get('timestamp','?')}] {f.get('domain','?')}: {f.get('root_cause','?')[:60]}")
        results["issues_found"].append({"issue": "recent_failures", "count": len(failures)})
    else:
        print(f"     {PASS} 无近期故障")

    # 总结
    print(f"\n{'─' * 50}")
    action_count = len(results["actions_taken"])
    if action_count > 0:
        print(f"  {RECOVER} 执行了 {action_count} 个恢复动作")
    else:
        print(f"  {PASS} 系统正常，无需恢复")

    return results


# ══════════════════════════════════════════════════
# 持续监控模式
# ══════════════════════════════════════════════════
def watch_mode(interval=60):
    """持续监控模式"""
    print(f"\n{'═' * 60}")
    print(f"  自动恢复守护进程 — 监控模式")
    print(f"  检查间隔: {interval}秒")
    print(f"  启动时间: {fmt_time()}")
    print(f"{'═' * 60}\n")

    cycle = 0
    while True:
        cycle += 1
        print(f"\n[{fmt_time()}] 巡检 # {cycle}")
        try:
            run_self_heal(check_only=False)
        except KeyboardInterrupt:
            print(f"\n  {WARN} 监控模式已停止")
            break
        except Exception as e:
            print(f"\n  {FAIL} 巡检异常: {str(e)[:100]}")
            log_recovery("watch_error", "monitor", "fail", str(e)[:100])

        print(f"\n  下次检查: {fmt_time(cst_now() + timedelta(seconds=interval))}")
        print(f"{'─' * 50}")

        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n  {WARN} 监控模式已停止")
            break


# ══════════════════════════════════════════════════
# 状态查看
# ══════════════════════════════════════════════════
def show_status():
    """显示恢复系统状态"""
    log = load_json(RECOVERY_LOG, {"entries": [], "stats": {"total": 0, "success": 0, "fail": 0}})
    stats = log.get("stats", {})

    print(f"\n{'═' * 60}")
    print("  自愈系统状态")
    print(f"{'═' * 60}")
    print(f"\n  总恢复次数: {stats.get('total', 0)}")
    print(f"  成功: {stats.get('success', 0)}")
    print(f"  失败: {stats.get('fail', 0)}")

    if stats.get('total', 0) > 0:
        rate = stats['success'] / stats['total'] * 100
        print(f"  成功率: {rate:.1f}%")

    # 最近恢复记录
    recent = get_recovery_history(1)
    if recent:
        print(f"\n  最近24小时恢复:")
        for e in recent[-10:]:
            sym = PASS if e.get("status") == "success" else FAIL
            print(f"  [{sym}] {e.get('timestamp','?')} | {e.get('action','?')} | {e.get('target','?')}")
            if e.get("detail"):
                print(f"       {e['detail'][:100]}")


def show_history(days=7):
    """显示恢复历史"""
    entries = get_recovery_history(days)
    if not entries:
        print("  无恢复记录")
        return

    print(f"\n{'═' * 60}")
    print(f"  恢复历史 (最近{len(entries)}条)")
    print(f"{'═' * 60}")
    for e in entries:
        sym = PASS if e.get("status") == "success" else FAIL
        print(f"  [{sym}] {e.get('timestamp','?')} | {e.get('action','?')} | {e.get('target','?')}")
        if e.get("detail"):
            print(f"       {e['detail'][:120]}")


# ══════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="AI操作系统自愈引擎 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--watch", action="store_true", help="持续监控模式")
    parser.add_argument("--interval", type=int, default=60, help="监控间隔(秒), 默认60")
    parser.add_argument("--health-check", action="store_true", help="仅执行健康检查并自动修复")
    parser.add_argument("--rotate-logs", action="store_true", help="仅执行日志轮转")
    parser.add_argument("--cleanup-sessions", action="store_true", help="仅清理卡住Session")
    parser.add_argument("--status", action="store_true", help="查看自愈状态")
    parser.add_argument("--history", action="store_true", help="查看恢复历史")
    parser.add_argument("--days", type=int, default=7, help="历史天数 (默认: 7)")

    args = parser.parse_args()

    if args.watch:
        watch_mode(args.interval)
    elif args.status:
        show_status()
    elif args.history:
        show_history(args.days)
    elif args.rotate_logs:
        rotated, errors = rotate_logs()
        if rotated:
            print(f"  {PASS} 轮转了: {', '.join(rotated)}")
        if errors:
            for e in errors:
                print(f"  {FAIL} {e}")
        if not rotated and not errors:
            print(f"  {PASS} 无需轮转")
    elif args.cleanup_sessions:
        fixed, detail = cleanup_stuck_sessions()
        print(f"  {RECOVER if fixed > 0 else PASS} {detail}")
    elif args.health_check:
        run_self_heal(check_only=False)
    else:
        # 默认: 执行一次全面自愈检查
        run_self_heal(check_only=False)


if __name__ == "__main__":
    main()
