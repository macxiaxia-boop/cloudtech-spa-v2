#!/usr/bin/env python3
"""
CloudTech V22 Watchdog - 端口 5099 alive check + 不在就拉起
==================================================================
设计原则:
  - 不杀任何进程 (红线 #6.5 V2 避免误伤 AIOS)
  - 端口 5099 alive? skip
  - 端口 5099 dead? start V22 gateway
  - 5min 间隔 (schtasks standard)
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
        print(f"[watchdog] log write failed: {e}", file=sys.stderr)
    print(line)


def start_v22():
    """uvicorn gateway_v22:app 启动 (后台)."""
    log_event("restart", f"端口{PORT}无监听 → 触发 uvicorn gateway_v22:app 启动")
    try:
        # 用 CREATE_NEW_PROCESS_GROUP 避免被 watchdog 父进程信号杀
        creationflags = 0x00000200 if sys.platform == "win32" else 0
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


def main():
    if check_port(PORT):
        log_event("alive", f"端口{PORT}正常监听")
        return 0
    log_event("dead", f"端口{PORT}无监听")
    pid = start_v22()
    # 等启动
    if pid and not check_port(PORT, timeout=0.5):
        for _ in range(20):
            time.sleep(0.5)
            if check_port(PORT):
                log_event("recovery", f"端口{PORT}已恢复 (PID={pid})")
                return 0
    log_event("recovery_fail", f"端口{PORT}启动超时")
    return 1


if __name__ == "__main__":
    sys.exit(main())