"""CloudTech auto-repair watchdog — runs every 5 min via Windows schtasks.
If any of the 5 core ports is down, attempt restart of the missing service.
Logs to D:\AIOS\_workzone\logs\ct_auto_repair.log.

Triggers:
  - :5000 gateway down -> powershell start_v22.ps1
  - :5099 bridge down   -> same ps1 (bridge embedded)
  - :5002 admin down    -> pythonw admin_dashboard.py
  - :8080 landing down  -> pythonw -m http.server 8080
  - :9099 streamlit down-> pythonw streamlit run
"""
import os, sys, time, socket, subprocess, datetime, json
from pathlib import Path

LOG = Path(r"D:\AIOS\_workzone\logs\ct_auto_repair.log")
LOG.parent.mkdir(parents=True, exist_ok=True)
LIVE = Path(r"D:\CloudTech-Portable")
DIST = LIVE / "landing-page" / "dist" / "v2.0.0"
PYTHONW = Path(r"D:/AIOS/aios_venv/Scripts/pythonw.exe")

SERVICES = [
    {"port": 5000, "name": "gateway_v22", "cmd": ["powershell", "-Command", f"Start-Process powershell -ArgumentList '-ExecutionPolicy','Bypass','-File','{LIVE}/tools/start_v22.ps1' -WindowStyle Hidden -RedirectStandardOutput 'D:\AIOS\_workzone\logs\start_v22_stdout.log' -RedirectStandardError 'D:\AIOS\_workzone\logs\start_v22_stderr.log'"]},
    {"port": 5099, "name": "bridge", "cmd": ["powershell", "-Command", f"Start-Process powershell -ArgumentList '-ExecutionPolicy','Bypass','-File','{LIVE}/tools/start_v22.ps1' -WindowStyle Hidden"]},
    {"port": 5002, "name": "dist_flask_admin", "cmd": [str(PYTHONW), str(DIST / "admin_dashboard.py")]},
    {"port": 8080, "name": "landing_static", "cmd": [str(PYTHONW), "-m", "http.server", "8080", "--directory", str(LIVE / "landing-page")]},
    {"port": 9099, "name": "dist_streamlit", "cmd": [str(PYTHONW), "-m", "streamlit", "run", str(DIST / "dashboard_app.py"), "--server.port", "9099"]},
]

def port_alive(p: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=2):
            return True
    except Exception:
        return False

def log_line(msg: str):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def try_start(svc):
    try:
        subprocess.Popen(svc["cmd"], creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log_line(f"RESTART_TRIGGERED name={svc['name']} port={svc['port']}")
        return True
    except Exception as e:
        log_line(f"RESTART_FAIL name={svc['name']} err={e!r}")
        return False

def main():
    log_line("auto_repair cycle begin")
    fixes = []
    for s in SERVICES:
        if port_alive(s["port"]):
            log_line(f"OK name={s['name']} port={s['port']}")
            continue
        log_line(f"DOWN name={s['name']} port={s['port']} -> restart")
        time.sleep(2)
        if port_alive(s["port"]):
            log_line(f"RECOVERED_BY_ITSELF port={s['port']}")
            continue
        if try_start(s):
            fixes.append({"name": s["name"], "port": s["port"]})
    if fixes:
        log_line(f"restarted = {json.dumps(fixes, ensure_ascii=False)}")
    else:
        log_line("all_5_alive")
    log_line("auto_repair cycle end")

if __name__ == "__main__":
    main()
