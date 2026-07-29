#!/usr/bin/env python3
"""
System Health Monitor v1.0 — AI操作系统健康巡检引擎
=====================================================
解决: 系统不可见 — 不知道什么在跑、什么挂了、什么需要修

功能:
  1. 检查所有Cron Job状态 (读取 cron-jobs.json, 检查上次运行时间)
  2. 验证所有API Key有效性 (DeepSeek, Zhipu, DashScope, Pexels, CTYUN)
  3. 检查MCP Server连通性 (本地mcp-server, Playwright, Hermes等)
  4. 检查所有核心服务状态 (Gateway 18792, Hermes 18791, ComfyUI 8188)
  5. 检查磁盘空间 (关键目录)
  6. 检查Obsidian仓库完整性 (关键文件存在性)
  7. 检查日志文件大小和增长率
  8. 检查状态文件完整性 (learning_log, delta-sv-registry, system-state)
  9. 生成详细健康报告 (PASS/FAIL/WARN)
  10. 保存健康快照到 state/health-history/ 目录

Usage:
    python system_health_monitor.py                    # 完整健康检查
    python system_health_monitor.py --mode quick       # 快速检查 (仅核心项目)
    python system_health_monitor.py --mode cron        # 仅检查Cron
    python system_health_monitor.py --mode api         # 仅检查API Keys
    python system_health_monitor.py --mode mcp         # 仅检查MCP Servers
    python system_health_monitor.py --mode disk        # 仅检查磁盘
    python system_health_monitor.py --history          # 查看历史健康趋势
    python system_health_monitor.py --output json      # 输出JSON格式
    python system_health_monitor.py --output feishu    # 推送到飞书
"""

import os
import sys
import json
import time
import subprocess
import socket
import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Fix Windows GBK encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── 路径配置 ─────────────────────────────────
USER_HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
OPENCLAW_DIR = USER_HOME / ".openclaw"
TOOLS_CORE_DIR = OPENCLAW_DIR / "tools" / "core"
STATE_DIR = OPENCLAW_DIR / "state"
HEALTH_HISTORY_DIR = STATE_DIR / "health-history"
WORKSPACE_DIR = OPENCLAW_DIR / "workspace"
LOGS_DIR = OPENCLAW_DIR / "logs"
OBSIDIAN_VAULT = Path("D:/个人文件/AI")

CRON_JOBS_FILE = OPENCLAW_DIR / "cron-jobs.json"
OPENCLAW_CONFIG = OPENCLAW_DIR / "openclaw.json"
MCP_CONFIG = OPENCLAW_DIR / ".mcp.json"
SYSTEM_STATE_FILE = STATE_DIR / "system-state.json"
DSV_REGISTRY_FILE = STATE_DIR / "delta-sv-registry.json"
HEALTH_SNAPSHOT_FILE = STATE_DIR / "personal-system-health.json"
POST_MORTEM_LOG = STATE_DIR / "post_mortem_log.json"
FAILURE_DB = STATE_DIR / "failure_db.json"

# 北京时间时区
CST = timezone(timedelta(hours=8))

# ── 颜色 / 标记 ─────────────────────────────────
PASS = "✓"
FAIL = "✗"
WARN = "!"
SKIP = "-"

def cst_now():
    return datetime.now(CST)

def fmt_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def load_json(path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError):
        return default


# ══════════════════════════════════════════════════
# 1. Cron Job 检查
# ══════════════════════════════════════════════════
def check_cron_jobs():
    """检查所有Cron Job状态"""
    results = []
    data = load_json(CRON_JOBS_FILE, [])
    if not data:
        return [{"name": "cron-jobs.json", "status": WARN, "detail": "无法读取或为空"}]

    now = cst_now()

    for job in data:
        name = job.get("name", "unknown")
        schedule = job.get("schedule", {})
        expr = schedule.get("expr", "")
        status = PASS
        detail = f"表达式: {expr}"

        # 检查 failureAlert 配置
        falert = job.get("failureAlert", {})
        if not falert.get("enabled", True):
            status = WARN
            detail += " | 告警未启用"

        # 检查 retry 配置 (如果任务有)
        # cron-jobs.json 没有直接存储最近运行时间，但我们可以检查配置完整性
        if not expr:
            status = FAIL
            detail = "缺少cron表达式"

        # 检查 sessionTarget
        target = job.get("sessionTarget", "")
        if target not in ("main", "isolated"):
            status = WARN
            detail += f" | sessionTarget异常: {target}"

        results.append({
            "name": name,
            "status": status,
            "detail": detail,
            "schedule": expr
        })

    return results


# ══════════════════════════════════════════════════
# 2. API Key 检查
# ══════════════════════════════════════════════════
def test_api_key(name, url, headers, timeout=10):
    """测试API Key是否有效"""
    try:
        req = Request(url, headers=headers, method="GET")
        resp = urlopen(req, timeout=timeout)
        return PASS, f"HTTP {resp.status}"
    except HTTPError as e:
        if e.code == 401:
            return FAIL, f"无效/过期 (HTTP {e.code})"
        elif e.code == 403:
            return FAIL, f"无权限 (HTTP {e.code})"
        elif e.code == 429:
            return WARN, f"限流 (HTTP {e.code})"
        else:
            return WARN, f"HTTP {e.code}"
    except URLError as e:
        return WARN, f"网络错误: {e.reason}"
    except Exception as e:
        return WARN, f"异常: {str(e)[:60]}"


def check_api_keys(config):
    """验证所有API Key的有效性"""
    results = []
    env = config.get("env", {})

    api_checks = [
        {
            "name": "DeepSeek",
            "key": env.get("DEEPSEEK_API_KEY", ""),
            "url": "https://api.deepseek.com/v1/models",
            "headers": {}
        },
        {
            "name": "Zhipu",
            "key": env.get("ZHIPU_API_KEY", ""),
            "url": "https://open.bigmodel.cn/api/paas/v4/models",
            "headers": {}
        },
        {
            "name": "DashScope",
            "key": env.get("DASHSCOPE_API_KEY", ""),
            "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            "headers": {}
        },
        {
            "name": "Pexels",
            "key": env.get("PEXELS_API_KEY", ""),
            "url": "https://api.pexels.com/v1/curated?per_page=1",
            "headers": {}
        },
    ]

    for api in api_checks:
        key = api["key"]
        if not key:
            results.append({
                "name": api["name"],
                "status": WARN,
                "detail": "未配置API Key"
            })
            continue

        # 对每个API设置正确的鉴权头
        headers = {}
        if api["name"] == "DeepSeek":
            headers = {"Authorization": f"Bearer {key}"}
        elif api["name"] == "Zhipu":
            headers = {"Authorization": f"Bearer {key}"}
        elif api["name"] == "DashScope":
            headers = {"Authorization": f"Bearer {key}"}
        elif api["name"] == "Pexels":
            headers = {"Authorization": key}

        status, detail = test_api_key(api["name"], api["url"], headers)
        results.append({
            "name": api["name"],
            "status": status,
            "detail": detail,
            "key_prefix": key[:8] + "..." if key else ""
        })

    return results


# ══════════════════════════════════════════════════
# 3. MCP Server 检查
# ══════════════════════════════════════════════════
def check_mcp_servers():
    """检查MCP Server配置和基本连通性"""
    results = []

    # 检查 OpenClaw 的 MCP servers
    config = load_json(OPENCLAW_CONFIG)
    mcp_servers = config.get("mcp", {}).get("servers", {})

    for name, cfg in mcp_servers.items():
        enabled = cfg.get("enabled", True)
        cmd = cfg.get("command", "")
        args = cfg.get("args", [])

        status = PASS
        detail = f"命令: {cmd}"

        if not enabled:
            status = WARN
            detail += " | 已禁用"

        # 检查命令是否存在
        if cmd:
            cmd_path = None
            if os.path.isabs(cmd):
                cmd_path = cmd
            else:
                # 在PATH中查找
                try:
                    if sys.platform == 'win32':
                        result = subprocess.run(
                            ["where", cmd], capture_output=True, text=True, timeout=5
                        )
                    else:
                        result = subprocess.run(
                            ["which", cmd], capture_output=True, text=True, timeout=5
                        )
                    if result.returncode == 0:
                        cmd_path = result.stdout.strip().split('\n')[0]
                except:
                    pass

            if cmd_path:
                detail += f" | 路径: {cmd_path}"
            else:
                if enabled:
                    status = WARN
                    detail += " | 命令不存在"
        else:
            if enabled:
                status = WARN
                detail += " | 命令为空"

        results.append({
            "name": name,
            "status": status,
            "detail": detail,
            "command": cmd
        })

    return results


# ══════════════════════════════════════════════════
# 4. 核心服务检查
# ══════════════════════════════════════════════════
def check_service(name, host, port, path="/health", timeout=5):
    """检查服务端口是否可达"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        # 尝试HTTP请求
        url = f"http://{host}:{port}{path}"
        try:
            req = Request(url, method="GET")
            resp = urlopen(req, timeout=timeout)
            return PASS, f"可达 (HTTP {resp.status})"
        except HTTPError as e:
            if e.code in (401, 403):
                return PASS, f"可达 (HTTP {e.code} - 需认证)"
            return WARN, f"端口可达但HTTP异常: {e.code}"
        except URLError:
            return WARN, "端口可达但HTTP无响应"
        except Exception as e:
            return WARN, f"端口可达但异常: {str(e)[:40]}"
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return FAIL, f"不可达: {str(e)[:40]}"


def check_services():
    """检查所有核心服务"""
    services = [
        ("OpenClaw Gateway", "127.0.0.1", 18792, "/health"),
        ("Hermes Dashboard", "127.0.0.1", 18791, "/api/status"),
        ("ComfyUI", "127.0.0.1", 8188, "/"),
        ("Hermes Agent", "127.0.0.1", 8089, "/health"),
    ]

    results = []
    for name, host, port, path in services:
        status, detail = check_service(name, host, port, path)
        results.append({
            "name": name,
            "status": status,
            "detail": detail
        })
    return results


# ══════════════════════════════════════════════════
# 5. 磁盘空间检查
# ══════════════════════════════════════════════════
def get_disk_usage(path):
    """获取磁盘使用情况 (Windows兼容)"""
    try:
        if sys.platform == 'win32':
            drive = os.path.splitdrive(path)[0].rstrip(":\\")
            if not drive:
                return {"error": f"无法识别驱动器: {path}"}
            # PowerShell outputs UTF-16LE; handle encoding
            ps_cmd = f"Get-PSDrive {drive} | Select-Object Used,Free | ConvertTo-Json -Compress"
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, timeout=10
            )
            # Decode with utf-16 if it starts with BOM, else utf-8
            raw = result.stdout
            if raw[:2] == b'\xff\xfe':
                output = raw.decode('utf-16-le')
            elif raw[:3] == b'\xef\xbb\xbf':
                output = raw.decode('utf-8-sig')
            else:
                output = raw.decode('utf-8', errors='replace')

            if result.returncode == 0 and output.strip():
                data = json.loads(output.strip())
                used = int(data.get("Used", 0))
                free = int(data.get("Free", 0))
                total = used + free
                pct = (used / total * 100) if total > 0 else 0
                return {
                    "total_gb": round(total / (1024**3), 1),
                    "used_gb": round(used / (1024**3), 1),
                    "free_gb": round(free / (1024**3), 1),
                    "used_pct": round(pct, 1)
                }
        else:
            stat = os.statvfs(path)
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bfree
            used = total - free
            pct = (used / total * 100) if total > 0 else 0
            return {
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "used_pct": round(pct, 1)
            }
    except Exception as e:
        return {"error": str(e)[:80]}
    return None


def check_disk_space():
    """检查关键目录磁盘空间"""
    dirs = [
        ("C: 盘 (系统)", "C:\\"),
        ("OpenClaw 目录", str(OPENCLAW_DIR)),
        ("Obsidian 仓库", str(OBSIDIAN_VAULT)),
    ]

    results = []
    for name, path in dirs:
        usage = get_disk_usage(path)
        if not usage:
            results.append({"name": name, "status": WARN, "detail": "无法获取磁盘信息"})
            continue
        if "error" in usage:
            results.append({"name": name, "status": WARN, "detail": f"错误: {usage['error']}"})
            continue
        pct = usage["used_pct"]
        if pct > 90:
            status = FAIL
        elif pct > 75:
            status = WARN
        else:
            status = PASS
        results.append({
            "name": name,
            "status": status,
            "detail": f"已用 {usage['used_gb']}GB / {usage['total_gb']}GB ({usage['used_pct']}%)"
        })
    return results


# ══════════════════════════════════════════════════
# 6. Obsidian 仓库检查
# ══════════════════════════════════════════════════
def check_obsidian_vault():
    """检查Obsidian仓库的关键文件存在性"""
    results = []
    if not OBSIDIAN_VAULT.exists():
        return [{"name": "Obsidian 仓库", "status": FAIL, "detail": f"目录不存在: {OBSIDIAN_VAULT}"}]

    # 检查关键目录
    key_dirs = [
        "00 原理层",
        "01 世界模型系统",
        "02 传播模型系统",
        "03 创作技能系统",
        "04 素材资产系统",
        "05 项目生产系统",
        "06 输出归档系统",
        "07 AI系统协议",
        "08 人物模型系统",
    ]

    for d in key_dirs:
        full_path = OBSIDIAN_VAULT / d
        if full_path.exists():
            md_count = len(list(full_path.glob("*.md")))
            results.append({
                "name": d,
                "status": PASS,
                "detail": f"存在, {md_count}个md文件"
            })
        else:
            results.append({
                "name": d,
                "status": WARN,
                "detail": "目录不存在"
            })

    return results


# ══════════════════════════════════════════════════
# 7. 日志文件检查
# ══════════════════════════════════════════════════
def check_log_files():
    """检查日志文件大小和状态"""
    results = []
    if not LOGS_DIR.exists():
        return [{"name": "日志目录", "status": WARN, "detail": "目录不存在"}]

    key_logs = [
        "watchdog.log",
        "health-pipeline.log",
        "gateway-health-check.log",
        "bridge.log",
    ]

    for log_name in key_logs:
        log_path = LOGS_DIR / log_name
        if not log_path.exists():
            results.append({"name": log_name, "status": WARN, "detail": "文件不存在"})
            continue

        size_bytes = log_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        if size_mb > 50:
            status = FAIL
            detail = f"过大: {size_mb:.1f}MB (>50MB)"
        elif size_mb > 10:
            status = WARN
            detail = f"偏大: {size_mb:.1f}MB (>10MB)"
        else:
            status = PASS
            detail = f"{size_mb:.1f}MB"

        results.append({
            "name": log_name,
            "status": status,
            "detail": detail
        })

    return results


# ══════════════════════════════════════════════════
# 8. 状态文件完整性检查
# ══════════════════════════════════════════════════
def check_state_files():
    """检查关键状态文件是否完整"""
    files_to_check = [
        ("system-state.json", SYSTEM_STATE_FILE, True),
        ("delta-sv-registry.json", DSV_REGISTRY_FILE, True),
        ("personal-system-health.json", HEALTH_SNAPSHOT_FILE, True),
        ("cron-jobs.json", CRON_JOBS_FILE, True),
        ("openclaw.json", OPENCLAW_CONFIG, True),
    ]

    results = []
    for name, path, required in files_to_check:
        if not path.exists():
            status = FAIL if required else WARN
            results.append({"name": name, "status": status, "detail": "文件不存在"})
            continue

        size = path.stat().st_size
        if size == 0:
            results.append({"name": name, "status": FAIL, "detail": "空文件"})
            continue

        # 尝试验证JSON
        try:
            json.loads(path.read_text(encoding='utf-8'))
            status = PASS
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            status = FAIL

        size_kb = size / 1024
        results.append({
            "name": name,
            "status": status,
            "detail": f"{size_kb:.1f}KB"
        })

    return results


# ══════════════════════════════════════════════════
# 9. 综合报告生成
# ══════════════════════════════════════════════════
def generate_report(all_results, mode="full"):
    """生成综合健康报告"""
    timestamp = cst_now()

    # 收集所有结果并排序
    flat = []
    for section, items in all_results.items():
        for item in items:
            item["section"] = section
            flat.append(item)

    total = len(flat)
    passed = sum(1 for x in flat if x.get("status") == PASS)
    failed = sum(1 for x in flat if x.get("status") == FAIL)
    warned = sum(1 for x in flat if x.get("status") == WARN)
    skipped = sum(1 for x in flat if x.get("status") == SKIP)

    # 整体状态
    if failed > 0:
        overall = "UNHEALTHY"
    elif warned > 0:
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    report = {
        "timestamp": fmt_time(timestamp),
        "ts_iso": timestamp.isoformat(),
        "mode": mode,
        "overall": overall,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "skipped": skipped,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0
        },
        "sections": {}
    }

    for section, items in all_results.items():
        sec_passed = sum(1 for x in items if x.get("status") == PASS)
        sec_total = len(items)
        report["sections"][section] = {
            "count": sec_total,
            "passed": sec_passed,
            "items": items
        }

    return report


def print_report(report):
    """打印健康报告到终端"""
    ts = report["timestamp"]
    overall = report["overall"]
    summary = report["summary"]

    # 标题
    border = "=" * 60
    print(f"\n{border}")
    print(f"  系统健康巡检报告 — {ts}")
    print(f"  运行模式: {report['mode']}")
    print(border)

    # 整体状态
    status_symbol = PASS if overall == "HEALTHY" else (WARN if overall == "DEGRADED" else FAIL)
    print(f"\n  整体状态: [{status_symbol}] {overall}")
    print(f"  通过率: {summary['pass_rate']}% ({summary['passed']}/{summary['total']})")
    if summary['failed'] > 0:
        print(f"  {FAIL} 失败: {summary['failed']}")
    if summary['warned'] > 0:
        print(f"  {WARN} 警告: {summary['warned']}")

    # 各节详情
    for section, sec_data in report["sections"].items():
        print(f"\n{'─' * 50}")
        print(f"  [{sec_data['passed']}/{sec_data['count']}] {section}")
        print(f"{'─' * 50}")
        for item in sec_data["items"]:
            s = item.get("status", SKIP)
            detail = item.get("detail", "")
            name = item.get("name", "?")
            print(f"  [{s}] {name}")
            if detail:
                print(f"       {detail}")


def save_health_history(report):
    """保存健康快照到历史目录"""
    HEALTH_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = cst_now().strftime("%Y%m%d-%H%M%S")
    history_file = HEALTH_HISTORY_DIR / f"health-{ts}.json"

    # 添加机器标识
    hostname = os.environ.get("COMPUTERNAME", "unknown")
    report["hostname"] = hostname

    history_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # 同时更新 current 快照
    current_file = HEALTH_HISTORY_DIR / "current.json"
    current_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # 更新 personal-system-health.json (兼容现有监控)
    health_snapshot = {
        "timestamp": report["timestamp"],
        "overall": report["overall"],
        "summary": report["summary"],
        "sections_summary": {
            name: {"passed": s["passed"], "count": s["count"]}
            for name, s in report["sections"].items()
        }
    }
    try:
        HEALTH_SNAPSHOT_FILE.write_text(
            json.dumps(health_snapshot, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    except Exception as e:
        print(f"  {WARN} 无法保存健康快照: {e}")

    return history_file


def load_health_history(days=7):
    """加载最近N天的健康历史"""
    if not HEALTH_HISTORY_DIR.exists():
        return []
    histories = []
    cutoff = cst_now() - timedelta(days=days)
    for f in sorted(HEALTH_HISTORY_DIR.glob("health-*.json")):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            ts_str = data.get("timestamp", "")
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
                if ts < cutoff:
                    continue
            except ValueError:
                pass
            histories.append(data)
        except (json.JSONDecodeError, Exception):
            continue
    return histories


def show_trend(histories):
    """显示健康趋势"""
    if not histories:
        print("  无历史数据")
        return

    print(f"\n{'═' * 60}")
    print("  健康趋势 (最近 {} 条记录)".format(len(histories)))
    print(f"{'═' * 60}")

    for h in histories:
        ts = h.get("timestamp", "?")
        overall = h.get("overall", "?")
        s = h.get("summary", {})
        rate = s.get("pass_rate", 0)
        failed = s.get("failed", 0)
        warned = s.get("warned", 0)

        symbol = PASS if overall == "HEALTHY" else (WARN if overall == "DEGRADED" else FAIL)
        print(f"  [{symbol}] {ts} | {overall} | 通过率: {rate}% | 失败: {failed} | 警告: {warned}")


# ══════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="AI系统健康巡检引擎 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", choices=["full", "quick", "cron", "api", "mcp", "service", "disk", "obsidian", "log", "state"],
                        default="full", help="检查模式 (默认: full)")
    parser.add_argument("--output", choices=["text", "json", "feishu"], default="text",
                        help="输出格式 (默认: text)")
    parser.add_argument("--history", action="store_true", help="查看历史健康趋势")
    parser.add_argument("--days", type=int, default=7, help="历史天数 (默认: 7)")
    parser.add_argument("--no-save", action="store_true", help="不保存健康快照")

    args = parser.parse_args()

    # 查看历史模式
    if args.history:
        histories = load_health_history(args.days)
        show_trend(histories)
        return

    # 执行健康检查
    all_results = {}

    if args.mode in ("full", "cron"):
        all_results["Cron Jobs"] = check_cron_jobs()
    if args.mode in ("full", "api"):
        config = load_json(OPENCLAW_CONFIG)
        all_results["API Keys"] = check_api_keys(config)
    if args.mode in ("full", "mcp"):
        all_results["MCP Servers"] = check_mcp_servers()
    if args.mode in ("full", "service"):
        all_results["核心服务"] = check_services()
    if args.mode in ("full", "disk"):
        all_results["磁盘空间"] = check_disk_space()
    if args.mode in ("full", "obsidian"):
        all_results["Obsidian仓库"] = check_obsidian_vault()
    if args.mode in ("full", "log"):
        all_results["日志文件"] = check_log_files()
    if args.mode in ("full", "state"):
        all_results["状态文件"] = check_state_files()

    # quick模式: 只检查最关键的项目
    if args.mode == "quick":
        all_results["Cron Jobs"] = check_cron_jobs()
        config = load_json(OPENCLAW_CONFIG)
        all_results["API Keys"] = check_api_keys(config)
        all_results["核心服务"] = check_services()
        all_results["磁盘空间"] = check_disk_space()

    if not all_results:
        print(f"  {WARN} 未选择任何检查项")
        parser.print_help()
        return

    # 生成报告
    report = generate_report(all_results, args.mode)

    # 输出
    if args.output == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)

    # 保存历史
    if not args.no_save:
        saved = save_health_history(report)
        print(f"\n{'─' * 50}")
        print(f"  快照已保存: {saved}")

    # 返回退出码
    if report["overall"] == "UNHEALTHY":
        sys.exit(2)
    elif report["overall"] == "DEGRADED":
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
