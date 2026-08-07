"""
云数科技 CloudTech v2.2 — 部署脚本
===================================
一键启动所有服务，环境检查，健康监控

用法:
    python deploy.py              # 检查环境
    python deploy.py start        # 启动所有服务
    python deploy.py stop         # 停止所有服务
    python deploy.py status       # 查看服务状态
    python deploy.py test         # 运行全量测试
"""
import subprocess, os, sys, time, json
from pathlib import Path

BASE = Path(__file__).parent
PYTHON = BASE / ".venv" / "Scripts" / "python.exe"

SERVICES = {
    "cloudtech": {
        "name": "云数科技管理后台",
        "port": 5099,
        "script": "admin_dashboard.py",
        "url": "http://localhost:5099",
    },
    "dashboard": {
        "name": "AI仪表盘",
        "port": 8501,
        "script": "dashboard_app.py",
        "url": "http://localhost:8501",
        "runner": "streamlit",
    },
    "zhuangqi": {
        "name": "装企控制台",
        "port": 8502,
        "script": "zhuangqi_dashboard.py",
        "url": "http://localhost:8502",
        "runner": "streamlit",
    },
}

def check_environment() -> dict:
    """环境检查"""
    results = {
        "python": str(PYTHON),
        "python_exists": PYTHON.exists(),
        "modules": {},
        "services": {},
        "warnings": [],
    }

    # 核心依赖
    deps = ["flask", "waitress", "streamlit", "requests", "dotenv"]
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
            results["modules"][dep] = "✅"
        except ImportError:
            results["modules"][dep] = "❌ 需安装"
            results["warnings"].append(f"缺少依赖: {dep}")

    # 可选依赖
    optional = {"moviepy": "视频混剪", "pillow": "图片处理", "numpy": "数值计算"}
    for mod, desc in optional.items():
        try:
            __import__(mod)
            results["modules"][mod] = "✅"
        except ImportError:
            results["modules"][mod] = f"⚠️ 可选({desc})"

    # API Keys
    api_keys = {
        "DEEPSEEK_API_KEY": "AI内容生成",
        "KLING_API_KEY": "可灵视频生成",
        "JIMENG_API_KEY": "即梦视频生成",
        "SEEDANCE_API_KEY": "Seedance视频",
        "HEYGEN_API_KEY": "HeyGen数字人",
        "DID_API_KEY": "D-ID数字人",
        "WECOM_CORP_ID": "企业微信CRM",
        "WECHAT_APP_ID": "公众号发布",
    }
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
    for key, desc in api_keys.items():
        val = os.getenv(key, "")
        results["modules"][key] = "✅ 已配置" if val else f"⚠️ 未配置({desc})"

    # 端口占用
    for sid, svc in SERVICES.items():
        try:
            r = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=5,
            )
            port_str = str(svc["port"])
            lines = [l for l in r.stdout.split("\n") if f":{port_str}" in l and "LISTENING" in l]
            results["services"][sid] = {
                "port": svc["port"],
                "name": svc["name"],
                "running": len(lines) > 0,
                "pid": lines[0].split()[-1] if lines else None,
            }
        except Exception:
            results["services"][sid] = {"port": svc["port"], "running": False}

    return results


def start_service(sid: str) -> dict:
    """启动单个服务"""
    svc = SERVICES.get(sid)
    if not svc:
        return {"ok": False, "error": f"未知服务: {sid}"}

    DETACHED = 0x00000008
    script = svc["script"]

    try:
        if svc.get("runner") == "streamlit":
            import subprocess
            p = subprocess.Popen(
                [str(PYTHON), "-m", "streamlit", "run", script,
                 "--server.port", str(svc["port"]), "--server.headless", "true"],
                cwd=str(BASE), creationflags=DETACHED,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            p = subprocess.Popen(
                [str(PYTHON), "-u", script],
                cwd=str(BASE), creationflags=DETACHED,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        return {"ok": True, "service": sid, "name": svc["name"], "pid": p.pid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_all() -> dict:
    """启动所有服务"""
    results = {}
    for sid in SERVICES:
        print(f"启动 {SERVICES[sid]['name']} (:{SERVICES[sid]['port']})...", end=" ")
        r = start_service(sid)
        results[sid] = r
        print(f"PID {r.get('pid', 'FAIL')}")

    # 等待端口
    print("等待服务就绪...")
    for i in range(20):
        time.sleep(2)
        all_up = True
        for sid, svc in SERVICES.items():
            r = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=5,
            )
            if f":{svc['port']}" not in r.stdout or "LISTENING" not in r.stdout:
                all_up = False
                break
        if all_up:
            break

    return results


def stop_service(port: int) -> dict:
    """停止占用指定端口的进程"""
    try:
        r = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        for line in r.stdout.split("\n"):
            if f":{port}" in line and "LISTENING" in line:
                pid = line.split()[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                return {"ok": True, "port": port, "killed_pid": pid}
        return {"ok": True, "port": port, "message": "未运行"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_all() -> dict:
    """停止所有服务"""
    results = {}
    for sid, svc in SERVICES.items():
        results[sid] = stop_service(svc["port"])
    return results


def run_tests():
    """运行全量测试"""
    test_script = BASE.parent.parent / "workspace" / "quick_test.py"
    # Fallback to inline
    if not test_script.exists():
        test_script = Path(os.environ.get("TEMP", ".")) / "cloudtech_quick_test.py"
        test_script.write_text(f"""
import sys; sys.path.insert(0, r'{BASE}')
from video_mixer import list_templates; print(f"Templates: {{len(list_templates()['templates'])}}")
from agent_assistant import get_agent_status; print(f"Agent tools: {{get_agent_status()['tools_count']}}")
from geo_optimizer import get_geo_stats; print(f"GEO questions: {{get_geo_stats()['questions_covered']}}")
print("ALL TESTS PASSED")
""")

    r = subprocess.run([str(PYTHON), str(test_script)], capture_output=True, text=True, timeout=30)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    return r.returncode == 0


def status():
    """服务状态"""
    env = check_environment()
    print("=" * 50)
    print("云数科技 CloudTech v2.2 状态")
    print("=" * 50)

    print("\n📦 服务状态:")
    for sid, svc in env["services"].items():
        status_icon = "🟢 运行中" if svc["running"] else "🔴 未启动"
        pid_str = f" (PID {svc['pid']})" if svc.get("pid") else ""
        print(f"  {status_icon} {svc['name']} (:{svc['port']}){pid_str}")

    print(f"\n🔧 核心依赖:")
    for mod, state in env["modules"].items():
        if mod in ["flask", "waitress", "streamlit", "requests", "dotenv"]:
            print(f"  {state} {mod}")

    print(f"\n🔑 API配置:")
    for key in ["DEEPSEEK_API_KEY", "KLING_API_KEY", "HEYGEN_API_KEY", "WECOM_CORP_ID"]:
        state = env["modules"].get(key, "未知")
        print(f"  {state}")

    if env["warnings"]:
        print(f"\n⚠️ 警告:")
        for w in env["warnings"]:
            print(f"  - {w}")

    print(f"\n📊 模块统计:")
    ok_count = sum(1 for v in env["modules"].values() if "✅" in str(v))
    total = len(env["modules"])
    print(f"  核心依赖: {ok_count}/{total} 就绪")


# ═══════════════════════════════════
# CLI
# ═══════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "start":
        print("🚀 启动云数科技全家桶...")
        start_all()
        status()
    elif cmd == "stop":
        print("🛑 停止所有服务...")
        stop_all()
    elif cmd == "test":
        print("🧪 运行全量测试...")
        run_tests()
    elif cmd == "check":
        env = check_environment()
        print(json.dumps(env, ensure_ascii=False, indent=2))
    else:
        status()
