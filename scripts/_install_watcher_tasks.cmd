@echo off
REM R364 · CloudTech V22/V23 watcher 持久化 (schtasks 5min 周期 · 治本 pythonw & 启动不稳)
REM 用 schtasks (Windows Task Scheduler) 代替 pythonw.exe 后台启动 · 自愈 + 持久化
REM 安装: scripts\_install_watcher_tasks.cmd

set WATCHER_DIR=D:\CloudTech-Portable
set VENV_PY=D:\CloudTech-Portable\.venv\Scripts\python.exe

REM V23 file watcher (R361 · 3s 轮询 v23_health.py)
schtasks /Create /TN "CloudTech_V23FileWatcher" /TR "\"%VENV_PY%\" -u \"D:\CloudTech-Portable\scripts\v23_file_watcher.py\"" /SC MINUTE /MO 1 /F /RL HIGHEST >nul 2>&1

REM V22 watchdog (R363 · 30s 轮询 gateway_v22.py)
schtasks /Create /TN "CloudTech_V22Watchdog" /TR "\"%VENV_PY%\" -u \"D:\CloudTech-Portable\_ct_v22_watchdog.py\"" /SC MINUTE /MO 5 /F /RL HIGHEST >nul 2>&1

echo [V23] V23 file watcher task installed (1min)
echo [V22] V22 watchdog task installed (5min)
echo Done. Use Task Scheduler to verify.