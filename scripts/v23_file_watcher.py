#!/usr/bin/env python
"""
CloudTech V23 file watcher · stdlib polling (no watchdog dep)
R361 P0 治本 · 红线 #86 EXTEND (state-loading → code-loading)

监听 v23_health.py mtime 变化 → 自动 kill 旧进程 + 重启 V23 子服务
轮询间隔 3s · 启动延迟 2s 让端口释放
"""
import os
import sys
import time
import signal
import subprocess
import socket
from pathlib import Path

# R361 · 强制 UTF-8 输出, 治本 Windows GBK 噪音 (Popen reader thread UnicodeDecodeError)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    sys.stderr.reconfigure(encoding="utf-8", errors="ignore")
except Exception:
    pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

BASE = Path(__file__).resolve().parent.parent  # D:/CloudTech-Portable
WATCH_FILE = BASE / "v23_health.py"
LOG_FILE = BASE / "logs" / "v23_file_watcher.log"
PORT = 7791
POLL_INTERVAL = 3  # seconds
STARTUP_DELAY = 2   # seconds after kill

def log(msg: str):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_v23_pid() -> int | None:
    """通过端口 7791 找 V23 进程 PID (Windows netstat GBK 编码)"""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            timeout=5,
        )
        # Windows netstat 是 GBK 编码 · 用 errors='ignore' 防 UnicodeDecodeError
        out = result.stdout.decode("gbk", errors="ignore")
        for line in out.splitlines():
            if f":{PORT}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    try:
                        pid = int(parts[-1])
                        return pid
                    except ValueError:
                        continue
    except Exception as e:
        log(f"[ERR] get_v23_pid: {e}")
    return None

def kill_v23() -> bool:
    pid = get_v23_pid()
    if not pid:
        return False
    try:
        log(f"[KILL] V23 PID={pid}")
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, timeout=5
        )
        time.sleep(STARTUP_DELAY)
        return True
    except Exception as e:
        log(f"[ERR] kill_v23: {e}")
        return False

def start_v23() -> bool:
    try:
        log(f"[START] python {WATCH_FILE}")
        # 不加 creationflags, 让 V23 直接 inherit watcher stdin/stdout (治本 DETACHED_PROCESS empty reply 副作用)
        subprocess.Popen(
            [sys.executable, str(WATCH_FILE)],
            cwd=str(BASE),
            stdout=None,
            stderr=None,
        )
        time.sleep(2)
        return True
    except Exception as e:
        log(f"[ERR] start_v23: {e}")
        return False

def wait_v23_ready(timeout: int = 15) -> bool:
    """等 V23 端口 LISTENING (治本 Popen detached 后 HTTP empty reply)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                # TCP 握手成功 → V23 已 listen → 算 ready
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    log(f"[BOOT] V23 file watcher · watching {WATCH_FILE}")
    log(f"[BOOT] poll_interval={POLL_INTERVAL}s · port={PORT}")

    # 启动时若 V23 没跑, 主动拉起 (治本 R361 接管)
    if get_v23_pid() is None:
        log("[BOOT] V23 not running · auto-starting")
        start_v23()
        if wait_v23_ready(15):
            log(f"[READY] V23 healthy on :{PORT} (initial start)")
        else:
            log("[WARN] V23 not ready after 15s · will retry on next change")

    last_mtime = None
    if WATCH_FILE.exists():
        last_mtime = WATCH_FILE.stat().st_mtime

    while True:
        try:
            # R361 治本 · 主循环也检查 V23 是否 LISTENING (如果 crash 了自动拉起)
            if get_v23_pid() is None:
                log("[RESTART] V23 not listening · auto-starting (poll loop)")
                start_v23()
                if wait_v23_ready(15):
                    log(f"[READY] V23 healthy on :{PORT} (auto-restart)")
                else:
                    log("[WARN] V23 not ready after 15s")

            if WATCH_FILE.exists():
                current_mtime = WATCH_FILE.stat().st_mtime
                if last_mtime is not None and current_mtime > last_mtime:
                    log(f"[CHANGE] {WATCH_FILE.name} mtime changed ({last_mtime:.1f} → {current_mtime:.1f})")
                    if kill_v23():
                        start_v23()
                        if wait_v23_ready(15):
                            log(f"[READY] V23 healthy on :{PORT}")
                        else:
                            log(f"[WARN] V23 not ready after 15s")
                elif last_mtime is None:
                    log(f"[INIT] first poll · mtime={current_mtime:.1f}")
                last_mtime = current_mtime
        except Exception as e:
            log(f"[ERR] main loop: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("[SHUTDOWN] user interrupt")
        sys.exit(0)