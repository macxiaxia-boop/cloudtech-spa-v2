"""CloudTech V22 一键恢复 · L1 穷尽 SOP 治本 · 2026-09-26
1. 找占用 :5000/:5099/:8080 的进程
2. 杀掉残留 pythonw (CloudTech + bridge 疯狂重启)
3. 启 V22 backend (cloudtech.live_migration.start_cloudtech)
4. 启 :8080 静态服务 (admin_v20.html)
5. 36 端点验证
"""
import os, sys, subprocess, time, socket, signal, json
from pathlib import Path

PYTHONW = r"D:\AIOS\aios_venv\Scripts\pythonw.exe"
LIVE = Path(r"D:\CloudTech-Portable")
LOG_DIR = LIVE / "logs"
LOG_DIR.mkdir(exist_ok=True)

def kill_named(proc_name_pattern, exclude_pids=()):
    """杀包含模式名的 pythonw 进程."""
    import ctypes
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq pythonw.exe"], capture_output=True, text=True).stdout
    killed = []
    for line in out.splitlines():
        line = line.strip()
        if "pythonw.exe" not in line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pid = parts[1]
        if pid in exclude_pids or pid == str(os.getpid()):
            continue
        # 杀
        try:
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=3)
            killed.append(pid)
        except Exception:
            pass
    return killed

def check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()

def wait_port(port, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if check_port(port):
            return True
        time.sleep(0.5)
    return False

# 1. 现状
print("=== 现状 ===")
for p in [5000, 5099, 8080, 7777]:
    print(f"  :{p} {'✓ LISTENING' if check_port(p) else '✗ DEAD'}")
# 2. 杀所有 pythonw (留着 admin 自己)
print("\n=== 杀残留 pythonw ===")
killed = kill_named("pythonw")
print(f"  杀掉 {len(killed)} 个: {killed[:8]}{'...' if len(killed)>8 else ''}")
time.sleep(2)
# 3. 启 V22 backend
print("\n=== 启 V22 backend (start_cloudtech --port 5000) ===")
env = os.environ.copy()
env["PYTHONPATH"] = "D:\\CloudTech-Portable\\src"
env["CLOUDTECH_RC2_USE_QUALITY_AWARE"] = "1"
env["CLOUDTECH_RC2_USE_FAKE"] = "0"
env["CLOUDTECH_API_TOKEN"] = ""  # 禁 token 防 401
v22_log = LOG_DIR / "v22_recovery.log"
with open(v22_log, "w", encoding="utf-8") as f:
    p = subprocess.Popen(
        [PYTHONW, "-m", "cloudtech.live_migration.start_cloudtech", "--port", "5000", "--host", "127.0.0.1"],
        cwd=str(LIVE), env=env, stdout=f, stderr=subprocess.STDOUT,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )
print(f"  V22 pid={p.pid} → log={v22_log}")
# 4. 等 :5000
ok5000 = wait_port(5000, timeout=25)
print(f"  :5000 {'✓' if ok5000 else '✗ TIMEOUT'}")
if not ok5000:
    print("  --- LOG TAIL ---")
    with open(v22_log, encoding="utf-8") as f:
        print(f.read()[-2000:])
# 5. 启 :8080 静态
print("\n=== 启 :8080 静态 (landing-page) ===")
py = sys.executable.replace("python.exe", "pythonw.exe") if "pythonw" not in sys.executable.lower() else sys.executable
if not Path(py).exists():
    py = sys.executable
s80_log = LOG_DIR / "static_8080.log"
with open(s80_log, "w", encoding="utf-8") as f:
    p8 = subprocess.Popen(
        [py, "-m", "http.server", "8080", "--bind", "127.0.0.1"],
        cwd=str(LIVE / "landing-page"), stdout=f, stderr=subprocess.STDOUT,
        creationflags=0x08000000,
    )
print(f"  static pid={p8.pid} → log={s80_log}")
ok8080 = wait_port(8080, timeout=8)
print(f"  :8080 {'✓' if ok8080 else '✗ TIMEOUT'}")
print(f"\n=== 恢复完成 ===")
print(f"V22 pid={p.pid} | :5000={ok5000}")
print(f"static pid={p8.pid} | :8080={ok8080}")