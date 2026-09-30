#!/usr/bin/env python3
"""
CloudTech V22 Watchdog - 端口 5099 alive check + gateway_v22.py mtime 监听
==================================================================
设计原则:
  - 不杀 AIOS 保护进程 (红线 #6.5 V2 避免误伤)
  - 但 gateway_v22.py (cloudtech 业务组件, NOT AIOS) 可以重启
  - 端口 5099 alive + gateway_v22.py mtime 未变 → skip
  - 端口 5099 dead → start V22
  - gateway_v22.py mtime 变化 → taskkill 当前 V22 + 重启加载新代码 (R363 治本 R362 catch-all)
  - 间隔 30s (类比 R361 v23_file_watcher 3s · 但 V22 watchdog 是 schtasks 周期, 折中 30s)
"""
import os
import sys
import json
import socket
import subprocess
import time
from pathlib import Path
from datetime import datetime

PORT = 5099
LIVE = Path(r"D:\CloudTech-Portable")
PYTHON = LIVE / ".venv" / "Scripts" / "python.exe"
LOG_FILE = LIVE / "ct_v22_watchdog.log"
WATCH_FILE = LIVE / "gateway_v22.py"  # R363 mtime 监听 (治本 R362 catch-all 激活)
POLL_INTERVAL = 30  # seconds (R363 折中 schtasks 周期)


def check_port(port, timeout=0.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def log_event(event_type, detail):
    """JSONL 事件日志 (兼容 cloudtech-events.jsonl 风格)."""
    ts = datetime.now().isoformat(timespec="seconds")
    line = json.dumps({"time": ts, "type": event_type, "detail": detail}, ensure_ascii=False)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[watchdog] log write failed: {e}", file=sys.stderr, flush=True)
    print(line, flush=True)  # R363 治本 nohup stdout buffer


def get_v22_pid() -> int | None:
    """找 V22 (5099 LISTENING) PID · Windows netstat GBK encoding"""
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, timeout=5)
        out = result.stdout.decode("gbk", errors="ignore")
        for line in out.splitlines():
            if f":{PORT}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        continue
    except Exception as e:
        log_event("err", f"get_v22_pid: {e}")
    return None


def kill_v22(pid: int) -> bool:
    """taskkill 当前 V22 PID (R363 治本 R362 catch-all)"""
    try:
        log_event("kill", f"taskkill V22 PID={pid}")
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=5)
        time.sleep(2)
        return True
    except Exception as e:
        log_event("err", f"kill_v22: {e}")
        return False


def start_v22():
    """uvicorn gateway_v22:app 启动 (后台)."""
    log_event("restart", f"端口{PORT}无监听 → 触发 uvicorn gateway_v22:app 启动")
    try:
        creationflags = 0x00000200 if sys.platform == "win32" else 0  # CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "gateway_v22:app",
             "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=str(LIVE),
            stdout=open(LIVE / "ct_v22_watchdog_runner.log", "ab", 0),
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        log_event("restart_ok", f"uvicorn 启动 PID={proc.pid}")
        return proc.pid
    except Exception as e:
        log_event("restart_fail", f"启动失败: {e}")
        return None


def ensure_v22_running() -> bool:
    """检查 V22 端口 listening, 不在就启动"""
    if check_port(PORT):
        return True
    log_event("dead", f"端口{PORT}无监听")
    pid = start_v22()
    if pid and not check_port(PORT, timeout=0.5):
        for _ in range(20):
            time.sleep(0.5)
            if check_port(PORT):
                log_event("recovery", f"端口{PORT}已恢复 (PID={pid})")
                return True
    log_event("recovery_fail", f"端口{PORT}启动超时")
    return False


def main():
    """主循环 · 每 30s 检查 mtime 变化 → reload + 端口 alive check"""
    log_event("boot", f"V22 watchdog mtime-watch 启动 · poll={POLL_INTERVAL}s")

    last_mtime = None
    if WATCH_FILE.exists():
        last_mtime = WATCH_FILE.stat().st_mtime

    # 第一次跑: 启动 V22 if needed
    ensure_v22_running()

    while True:
        try:
            # R363 P0 治本 · mtime 变化 → 主动 reload (类比 R361 v23_file_watcher)
            if WATCH_FILE.exists():
                current_mtime = WATCH_FILE.stat().st_mtime
                if last_mtime is not None and current_mtime > last_mtime:
                    log_event("mtime_change", f"{WATCH_FILE.name} {last_mtime:.1f} → {current_mtime:.1f}")
                    pid = get_v22_pid()
                    if pid:
                        kill_v22(pid)
                    ensure_v22_running()
                    log_event("reload_ok", f"V22 已加载新 gateway_v22.py")
                last_mtime = current_mtime

            # 端口 alive check (V22 crash 时拉起)
            if not check_port(PORT):
                log_event("dead_poll", f"端口{PORT}无监听 · 启动")
                ensure_v22_running()

        except Exception as e:
            log_event("err", f"main loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_event("shutdown", "user interrupt")
        sys.exit(0)