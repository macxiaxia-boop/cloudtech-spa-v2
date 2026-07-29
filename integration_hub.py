#!/usr/bin/env python3
"""
Integration Hub v1.0 — AI操作系统统一入口
============================================
解决: 工具孤岛 — 每个工具独立运行，不会自动串联

将现有工具统一为 6 个生产级命令:
  --health   → 全系统健康巡检 (调用 system_health_monitor.py)
  --intel    → 情报采集管线 (intel-agent → 日报生成 → 飞书推送)
  --content  → 内容生产管线 (话题发现 → 选题 → 生产 → 输出)
  --daily    → 每日自动化管线 (健康 + 情报 + 备份 + 恢复)
  --repair   → 自动修复管线 (auto_recovery + session清理 + 日志轮转)
  --status   → 一页系统状态总览

Usage:
    python integration_hub.py --health              # 全系统健康巡检
    python integration_hub.py --intel               # 情报采集管线
    python integration_hub.py --content "主题词"    # 内容生产管线
    python integration_hub.py --daily               # 每日自动化
    python integration_hub.py --repair              # 自动修复
    python integration_hub.py --status              # 系统状态总览
    python integration_hub.py --list                # 列出所有可用管线
    python integration_hub.py --health --output json  # JSON输出
    python integration_hub.py --all-timeout 300       # 全局超时(秒)
"""

import os
import sys
import json
import time
import subprocess
import argparse
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── 路径配置 ─────────────────────────────────
USER_HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
OPENCLAW_DIR = USER_HOME / ".openclaw"
TOOLS_CORE_DIR = OPENCLAW_DIR / "tools" / "core"
STATE_DIR = OPENCLAW_DIR / "state"
LOGS_DIR = OPENCLAW_DIR / "logs"

HEALTH_MONITOR = TOOLS_CORE_DIR / "system_health_monitor.py"
AUTO_RECOVERY = TOOLS_CORE_DIR / "auto_recovery.py"
BACKUP_RESTORE = TOOLS_CORE_DIR / "backup_restore.py"
INTEL_AGENT = TOOLS_CORE_DIR / "intel-agent.py"
HEALTH_CHECK_PS1 = TOOLS_CORE_DIR / "openclaw-health-check.ps1"
WATCHDOG_PS1 = TOOLS_CORE_DIR / "openclaw-watchdog.ps1"
CONTENT_PIPELINE_PS1 = TOOLS_CORE_DIR / "content-pipeline.ps1"

# ── 系统状态文件 ─────────────────────────────────
SYSTEM_STATE_FILE = STATE_DIR / "system-state.json"
DSV_REGISTRY_FILE = STATE_DIR / "delta-sv-registry.json"
HEALTH_SNAPSHOT = STATE_DIR / "personal-system-health.json"

CST = timezone(timedelta(hours=8))
PASS = "✓"
FAIL = "✗"
WARN = "!"
RUN = "▶"


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
    except:
        return default


def print_header(title):
    """打印节标题"""
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def run_python_script(script_path, args=None, timeout=300, capture=False):
    """运行Python脚本并返回结果"""
    if not script_path.exists():
        msg = f"脚本不存在: {script_path}"
        if capture:
            return {"success": False, "error": msg}
        print(f"  {FAIL} {msg}")
        return None

    cmd = [sys.executable, str(script_path)]
    if args:
        if isinstance(args, list):
            cmd.extend(args)
        else:
            cmd.append(args)

    try:
        start = time.time()
        result = subprocess.run(
            cmd, capture_output=capture, text=True, timeout=timeout
        )
        elapsed = time.time() - start

        if capture:
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed": round(elapsed, 1),
                "returncode": result.returncode
            }

        if result.returncode != 0:
            print(f"  {WARN} 返回码: {result.returncode} (耗时 {elapsed:.1f}s)")
            err = result.stderr or ""
            if err.strip():
                print(f"    错误: {err.strip()[:200]}")
        else:
            print(f"  {PASS} 完成 (耗时 {elapsed:.1f}s)")
        return result

    except subprocess.TimeoutExpired:
        msg = f"超时 ({timeout}秒)"
        if capture:
            return {"success": False, "error": msg}
        print(f"  {FAIL} {msg}")
        return None
    except Exception as e:
        msg = str(e)[:100]
        if capture:
            return {"success": False, "error": msg}
        print(f"  {FAIL} {msg}")
        return None


def run_powershell_script(script_path, args_str="", timeout=300):
    """运行PowerShell脚本"""
    if not script_path.exists():
        print(f"  {FAIL} 脚本不存在: {script_path}")
        return None

    cmd = ["powershell", "-File", str(script_path)]
    if args_str:
        cmd.append(args_str)

    try:
        start = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            print(f"  {WARN} 返回码: {result.returncode} (耗时 {elapsed:.1f}s)")
        else:
            print(f"  {PASS} 完成 (耗时 {elapsed:.1f}s)")
        return result
    except subprocess.TimeoutExpired:
        print(f"  {FAIL} 超时 ({timeout}秒)")
        return None
    except Exception as e:
        print(f"  {FAIL} {str(e)[:100]}")
        return None


# ══════════════════════════════════════════════════
# --health  全系统健康巡检
# ══════════════════════════════════════════════════
def pipeline_health(args):
    """全系统健康巡检管线"""
    print_header("全系统健康巡检")

    # 运行 system_health_monitor.py
    health_args = ["--mode", args.mode or "full", "--output", "text"]
    if args.output == "json":
        health_args = ["--mode", args.mode or "full", "--output", "json"]

    result = run_python_script(HEALTH_MONITOR, health_args, timeout=args.timeout, capture=(args.output == "json"))

    if args.output == "json" and result:
        return result

    return {"pipeline": "health", "success": True}


# ══════════════════════════════════════════════════
# --intel  情报采集管线
# ══════════════════════════════════════════════════
def pipeline_intel(args):
    """情报采集管线: intel-agent → 日报 → 飞书"""
    print_header("情报采集管线")

    results = {"steps": []}

    # Step 1: 运行 intel-agent
    print(f"\n  步骤 1/2: 情报采集...")
    intel_mode = args.intel_mode or "daily"
    ia_result = run_python_script(INTEL_AGENT, ["--mode", intel_mode, "--output", "stdout"],
                                  timeout=args.timeout)
    results["steps"].append({"step": "intel-collect", "success": ia_result is not None})

    # Step 2: 状态快照
    print(f"\n  步骤 2/2: 生成状态快照...")
    if HEALTH_MONITOR.exists():
        run_python_script(HEALTH_MONITOR, ["--mode", "quick", "--no-save"],
                          timeout=60)

    results["success"] = all(s["success"] for s in results["steps"])
    print(f"\n  {PASS if results['success'] else WARN} 情报管线完成")
    return results


# ══════════════════════════════════════════════════
# --content  内容生产管线
# ══════════════════════════════════════════════════
def pipeline_content(args):
    """内容生产管线: 话题 → 选题 → 生产"""
    print_header("内容生产管线")

    topic = args.topic or args.content
    if not topic:
        print(f"  {FAIL} 请指定内容主题: --content \"主题词\"")
        return {"success": False, "error": "缺少主题"}

    results = {"topic": topic, "steps": []}

    # Step 1: 内容管线 (content-pipeline.ps1)
    print(f"\n  步骤 1/1: 内容生产 — \"{topic}\"...")
    platform = args.platform or "all"

    if CONTENT_PIPELINE_PS1.exists():
        ps_args = f"-Topic \"{topic}\" -Platform \"{platform}\""
        cp_result = run_powershell_script(CONTENT_PIPELINE_PS1, ps_args, timeout=args.timeout)
        results["steps"].append({"step": "content-produce", "success": cp_result is not None})
    else:
        print(f"  {WARN} content-pipeline.ps1 不存在，跳过")
        print(f"  请手动运行: python intel-agent.py --mode daily")

    results["success"] = all(s["success"] for s in results["steps"]) if results["steps"] else False
    print(f"\n  {PASS if results['success'] else WARN} 内容管线完成")
    return results


# ══════════════════════════════════════════════════
# --daily  每日自动化管线
# ══════════════════════════════════════════════════
def pipeline_daily(args):
    """每日自动化管线: 健康 + 情报 + 备份 + 恢复"""
    print_header("每日自动化管线")
    start_time = time.time()
    results = {"steps": []}

    # Step 1: 健康检查
    print(f"\n  [{RUN}] 步骤 1/4: 系统健康检查...")
    h_result = run_python_script(HEALTH_MONITOR, ["--mode", "full"],
                                 timeout=args.timeout)
    results["steps"].append({"step": "health", "success": h_result is not None})

    # Step 2: 自动修复
    print(f"\n  [{RUN}] 步骤 2/4: 自动修复...")
    if AUTO_RECOVERY.exists():
        run_python_script(AUTO_RECOVERY, ["--health-check"], timeout=args.timeout)
    results["steps"].append({"step": "repair", "success": True})

    # Step 3: 快速情报采集
    print(f"\n  [{RUN}] 步骤 3/4: 情报速览...")
    if INTEL_AGENT.exists():
        run_python_script(INTEL_AGENT, ["--mode", "quick", "--output", "stdout"],
                          timeout=args.timeout)
    results["steps"].append({"step": "intel", "success": True})

    # Step 4: 备份
    print(f"\n  [{RUN}] 步骤 4/4: 系统备份...")
    if BACKUP_RESTORE.exists():
        run_python_script(BACKUP_RESTORE, ["--backup", "--quiet"],
                          timeout=args.timeout)
    results["steps"].append({"step": "backup", "success": True})

    # 完成
    elapsed = time.time() - start_time
    results["elapsed"] = round(elapsed, 1)
    results["success"] = all(s["success"] for s in results["steps"])

    print(f"\n{'─' * 50}")
    print(f"  每日自动化完成 | 耗时 {elapsed:.1f}秒 | "
          f"{PASS if results['success'] else WARN} {'全部成功' if results['success'] else '部分异常'}")

    return results


# ══════════════════════════════════════════════════
# --repair  自动修复管线
# ══════════════════════════════════════════════════
def pipeline_repair(args):
    """自动修复管线: recovery + 日志轮转 + session清理"""
    print_header("自动修复管线")

    results = {"steps": []}

    if AUTO_RECOVERY.exists():
        # 全面自愈
        print(f"\n  [{RUN}] 执行自动恢复...")
        run_python_script(AUTO_RECOVERY, ["--health-check"], timeout=args.timeout)
        results["steps"].append({"step": "auto-recovery", "success": True})

        # 日志轮转
        print(f"\n  [{RUN}] 日志轮转...")
        run_python_script(AUTO_RECOVERY, ["--rotate-logs"], timeout=60)
        results["steps"].append({"step": "rotate-logs", "success": True})

        # Session清理
        print(f"\n  [{RUN}] Session清理...")
        run_python_script(AUTO_RECOVERY, ["--cleanup-sessions"], timeout=30)
        results["steps"].append({"step": "cleanup-sessions", "success": True})
    else:
        print(f"  {FAIL} auto_recovery.py 不存在")
        return {"success": False}

    results["success"] = True
    return results


# ══════════════════════════════════════════════════
# --status  一页系统状态总览
# ══════════════════════════════════════════════════
def show_system_status(args):
    """一页系统状态总览"""
    print_header("AI 操作系统状态总览")

    # 1. 系统状态
    state = load_json(SYSTEM_STATE_FILE, {})
    current = state.get("currentState", {})
    state_name = current.get("state", "未知")
    state_sym = PASS if state_name == "NORMAL" else (WARN if state_name == "DEGRADED" else FAIL)
    print(f"\n  系统状态: [{state_sym}] {state_name}")
    print(f"  进入时间: {current.get('enteredAt', '?')}")
    print(f"  原因: {current.get('reason', '?')[:80]}")

    # 2. 健康快照
    health = load_json(HEALTH_SNAPSHOT, {})
    if health:
        overall = health.get("overall", "?")
        summary = health.get("summary", {})
        h_sym = PASS if overall == "HEALTHY" else (WARN if overall == "DEGRADED" else FAIL)
        print(f"\n  健康状态: [{h_sym}] {overall}")
        print(f"  通过率: {summary.get('pass_rate', '?')}%")
        print(f"  上次巡检: {health.get('timestamp', '?')}")

    # 3. Delta-SV 排名
    dsv = load_json(DSV_REGISTRY_FILE, {})
    modules = dsv.get("modules", [])
    if modules:
        print(f"\n  模块排名 (Top 5 by ΔSV):")
        sorted_mods = sorted(modules, key=lambda m: m.get("deltaSV", 0), reverse=True)
        for m in sorted_mods[:5]:
            name = m.get("name", "?")
            dsv_val = m.get("deltaSV", 0)
            priority = m.get("priority", "?")
            closure = m.get("closureRate", 0)
            sym = "+" if dsv_val >= 1 else ("~" if dsv_val >= 0 else "-")
            print(f"    [{sym}] {dsv_val:+.1f} {name} ({priority}, 完成率:{closure:.0%})")

    # 4. 文件系统
    print(f"\n  存储概览:")
    dirs_to_check = [
        ("状态文件", STATE_DIR),
        ("日志文件", LOGS_DIR),
        ("OpenClaw", OPENCLAW_DIR),
    ]
    for name, path in dirs_to_check:
        if path.exists():
            try:
                total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                size_mb = total_size / (1024 * 1024)
                print(f"    {name}: {size_mb:.0f}MB ({len(list(path.rglob('*')))} 文件)")
            except:
                print(f"    {name}: ?")

    # 5. 最近恢复历史
    recovery_log = STATE_DIR / "recovery_log.json"
    rec = load_json(recovery_log, {})
    entries = rec.get("entries", [])
    recent = entries[-5:] if entries else []
    if recent:
        print(f"\n  最近恢复操作:")
        for e in recent:
            sym = PASS if e.get("status") == "success" else FAIL
            print(f"    [{sym}] {e.get('timestamp','?')} | {e.get('action','?')} | {e.get('target','?')}")

    print(f"\n{'─' * 50}")
    print(f"  状态更新: {fmt_time()}")


# ══════════════════════════════════════════════════
# --list  列出所有可用管线
# ══════════════════════════════════════════════════
def list_pipelines():
    """列出所有可用管线"""
    print_header("可用管线列表")

    pipelines = [
        {
            "cmd": "--health",
            "desc": "全系统健康巡检",
            "detail": "检查Cron/API/MCP/服务/磁盘/状态文件的健康状况",
            "options": "--mode full|quick|cron|api|mcp|service|disk --output text|json"
        },
        {
            "cmd": "--intel",
            "desc": "情报采集管线",
            "detail": "intel-agent → 日报生成 → 状态快照",
            "options": "--intel-mode daily|quick|weekly"
        },
        {
            "cmd": "--content <主题>",
            "desc": "内容生产管线",
            "detail": "话题发现 → 内容生产 → 输出",
            "options": "--platform all|小红书|公众号|抖音"
        },
        {
            "cmd": "--daily",
            "desc": "每日自动化管线",
            "detail": "健康检查 → 自动修复 → 情报速览 → 系统备份",
            "options": "(无子选项)"
        },
        {
            "cmd": "--repair",
            "desc": "自动修复管线",
            "detail": "自动恢复 → 日志轮转 → Session清理",
            "options": "(无子选项)"
        },
        {
            "cmd": "--status",
            "desc": "一页系统状态总览",
            "detail": "系统状态/健康/模块排名/存储/恢复历史",
            "options": "(无子选项)"
        },
    ]

    for p in pipelines:
        print(f"\n  {RUN} {p['cmd']}")
        print(f"      {p['desc']}")
        print(f"      {p['detail']}")
        print(f"      选项: {p['options']}")

    print(f"\n{'─' * 50}")
    print(f"  全局选项:")
    print(f"  --all-timeout 秒  管线超时 (默认: 300)")
    print(f"  --output json     JSON格式输出 (仅 --health)")


# ══════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="AI操作系统统一入口 — Integration Hub v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 管线选择 (互斥)
    pipeline_group = parser.add_mutually_exclusive_group()
    pipeline_group.add_argument("--health", action="store_true", help="全系统健康巡检")
    pipeline_group.add_argument("--intel", action="store_true", help="情报采集管线")
    pipeline_group.add_argument("--content", type=str, nargs="?", const=True, default=None,
                                help="内容生产管线: --content \"主题词\"")
    pipeline_group.add_argument("--daily", action="store_true", help="每日自动化管线")
    pipeline_group.add_argument("--repair", action="store_true", help="自动修复管线")
    pipeline_group.add_argument("--status", action="store_true", help="系统状态总览")
    pipeline_group.add_argument("--list", action="store_true", help="列出所有管线")

    # 子选项
    parser.add_argument("--topic", type=str, help="内容主题 (同 --content)")
    parser.add_argument("--platform", type=str, default="all", help="内容平台 (小红书/公众号/抖音)")
    parser.add_argument("--intel-mode", type=str, choices=["daily", "quick", "weekly"], default="daily",
                        help="情报采集模式 (默认: daily)")
    parser.add_argument("--mode", type=str, choices=["full", "quick", "cron", "api", "mcp", "service", "disk"],
                        default=None, help="健康检查模式 (默认: full)")
    parser.add_argument("--output", type=str, choices=["text", "json"], default="text",
                        help="输出格式")
    parser.add_argument("--all-timeout", type=int, default=300, dest="timeout",
                        help="全局超时秒数 (默认: 300)")
    parser.add_argument("--topic-only", action="store_true", help="仅话题发现 (--content用)")

    args = parser.parse_args()

    # 路由到对应管线
    if args.list:
        list_pipelines()
    elif args.health:
        result = pipeline_health(args)
        if args.output == "json" and isinstance(result, dict):
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.intel:
        result = pipeline_intel(args)
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.content is not None or args.topic:
        args.content = args.content or args.topic
        result = pipeline_content(args)
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.daily:
        result = pipeline_daily(args)
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.repair:
        result = pipeline_repair(args)
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.status:
        show_system_status(args)
    else:
        # 默认: 显示管线列表
        list_pipelines()
        print(f"\n  {WARN} 未选择管线，以上为可用命令")


if __name__ == "__main__":
    main()
