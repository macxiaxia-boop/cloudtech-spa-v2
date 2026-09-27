"""CloudTech V22 R290 重启脚本 · L1 治本"""
import os, sys, subprocess, time, socket
from pathlib import Path

PYTHONW = r"D:\AIOS\aios_venv\Scripts\pythonw.exe"
LIVE = Path(r"D:\CloudTech-Portable")

def kill_all():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout
    killed = []
    for line in out.splitlines():
        if "pythonw.exe" not in line and "python.exe" not in line:
            continue
        parts = line.split()
        if len(parts) < 2: continue
        pid = parts[1]
        if pid == str(os.getpid()): continue
        try:
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=2)
            killed.append(pid)
        except: pass
    return killed

def check(p, t=0.5):
    s = socket.socket(); s.settimeout(t)
    try: return s.connect_ex(("127.0.0.1", p)) == 0
    finally: s.close()

def wait_port(p, t=20):
    t0 = time.time()
    while time.time() - t0 < t:
        if check(p): return True
        time.sleep(0.5)
    return False

print("=== 杀残留 ===")
k = kill_all()
print(f"  杀 {len(k)} 个")
time.sleep(2)

print("\n=== 启 V22 (R290 · v21 模块) ===")
env = os.environ.copy()
env["PYTHONPATH"] = "D:\\CloudTech-Portable\\src"
env["CLOUDTECH_RC2_USE_QUALITY_AWARE"] = "1"
env["CLOUDTECH_RC2_USE_FAKE"] = "0"
log_path = LIVE / "logs" / "v22_r290.log"
log_path.parent.mkdir(exist_ok=True)
log_f = open(log_path, "w", encoding="utf-8")
p = subprocess.Popen(
    [PYTHONW, "-m", "cloudtech.live_migration.start_cloudtech", "--port", "5000", "--host", "127.0.0.1"],
    cwd=str(LIVE), env=env, stdout=log_f, stderr=subprocess.STDOUT,
    creationflags=0x08000000,
)
print(f"  pid={p.pid}")
ok5000 = wait_port(5000, 25)
print(f"  :5000 {'OK' if ok5000 else 'TIMEOUT'}")

print("\n=== 启 :8080 静态 ===")
py = sys.executable
log2_f = open(LIVE / "logs" / "static_r290.log", "w", encoding="utf-8")
p8 = subprocess.Popen(
    [py, "-m", "http.server", "8080", "--bind", "127.0.0.1"],
    cwd=str(LIVE / "landing-page"), stdout=log2_f, stderr=subprocess.STDOUT,
    creationflags=0x08000000,
)
print(f"  pid={p8.pid}")
ok8080 = wait_port(8080, 8)
print(f"  :8080 {'OK' if ok8080 else 'TIMEOUT'}")

print("\n=== 完成 ===")
print(f"V22 pid={p.pid} :5000={ok5000} | static pid={p8.pid} :8080={ok8080}")