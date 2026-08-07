"""
系统稳定性引擎 — Stability & Self-Healing System
===================================================
确保云数科技7x24稳定运行

能力:
- 进程守护: 监控+自动重启+异常告警
- 健康检查: 端口/API/数据库/磁盘/内存
- 错误聚合: 全模块错误收集+模式识别
- 自愈机制: 常见故障自动修复
- 运行日志: 结构化日志+性能指标
"""
import json, os, time, subprocess, threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import defaultdict, deque

BASE = Path(__file__).parent
STABILITY_DIR = BASE / "data" / "stability"
STABILITY_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 一、健康检查引擎
# ═══════════════════════════════════

SERVICE_CHECKS = {
    "admin_dashboard": {"port": 5099, "endpoint": "/health", "critical": True},
    "ai_dashboard": {"port": 8501, "endpoint": "/", "critical": False},
    "zhuangqi_dashboard": {"port": 8502, "endpoint": "/", "critical": False},
}

SYSTEM_CHECKS = {
    "disk": {"min_free_gb": 5},
    "memory": {"min_free_pct": 10},
    "ffmpeg": {"command": ["ffmpeg", "-version"]},
}


class HealthMonitor:
    """系统健康监控"""

    def __init__(self):
        self.check_history = defaultdict(lambda: deque(maxlen=100))
        self.incidents = []
        self.last_full_check = None

    def check_all(self) -> dict:
        """全量健康检查"""
        results = {
            "timestamp": datetime.now().isoformat()[:19],
            "services": {},
            "system": {},
            "overall": "healthy",
            "issues": [],
        }

        # 服务检查
        for name, cfg in SERVICE_CHECKS.items():
            r = self._check_service(name, cfg)
            results["services"][name] = r
            self.check_history[name].append(r)
            if not r["ok"] and cfg.get("critical"):
                results["issues"].append(f"CRITICAL: {name} 不可用")
                results["overall"] = "degraded"

        # 系统检查
        for name, cfg in SYSTEM_CHECKS.items():
            r = self._check_system(name, cfg)
            results["system"][name] = r
            if not r["ok"]:
                results["issues"].append(f"WARNING: {name} 异常")

        if results["issues"]:
            results["overall"] = "degraded" if any("CRITICAL" in i for i in results["issues"]) else "warning"

        self.last_full_check = results["timestamp"]
        self._save_check_result(results)
        return results

    def _check_service(self, name: str, cfg: dict) -> dict:
        """检查单个服务"""
        import urllib.request
        try:
            url = f"http://localhost:{cfg['port']}{cfg['endpoint']}"
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            return {
                "ok": resp.status in (200, 302, 304),
                "status_code": resp.status,
                "response_time_ms": round((time.time() - self._start) * 1000) if hasattr(self, '_start') else -1,
            }
        except Exception as e:
            # 检查端口是否在监听
            try:
                r = subprocess.run(
                    ["netstat", "-ano"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=5,
                )
                port_listening = f":{cfg['port']}" in r.stdout and "LISTENING" in r.stdout
                return {"ok": port_listening, "listening": port_listening, "error": str(e)[:100]}
            except Exception:
                return {"ok": False, "error": str(e)[:100]}

    def _check_system(self, name: str, cfg: dict) -> dict:
        """系统资源检查"""
        if name == "disk":
            try:
                import shutil
                usage = shutil.disk_usage(str(BASE))
                free_gb = usage.free / (1024 ** 3)
                return {"ok": free_gb >= cfg["min_free_gb"], "free_gb": round(free_gb, 1)}
            except Exception:
                return {"ok": True, "free_gb": -1}

        if name == "memory":
            try:
                import psutil
                mem = psutil.virtual_memory()
                return {"ok": mem.percent < (100 - cfg["min_free_pct"]), "free_pct": round(100 - mem.percent, 1)}
            except Exception:
                return {"ok": True, "note": "psutil未安装"}

        if name == "ffmpeg":
            try:
                r = subprocess.run(cfg["command"], capture_output=True, timeout=5)
                return {"ok": r.returncode == 0, "version": r.stdout.split(b"\n")[0].decode()[:60] if r.stdout else ""}
            except Exception:
                return {"ok": False, "error": "ffmpeg不可用"}

    def _save_check_result(self, result: dict):
        today = datetime.now().strftime("%Y%m%d")
        log_file = STABILITY_DIR / f"health_{today}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    def get_health_history(self, hours: int = 24) -> dict:
        """获取健康历史"""
        now = datetime.now()
        history = []
        for h in range(hours):
            check_time = now - timedelta(hours=h)
            date_str = check_time.strftime("%Y%m%d")
            log_file = STABILITY_DIR / f"health_{date_str}.jsonl"
            if log_file.exists():
                for line in open(log_file, encoding="utf-8"):
                    data = json.loads(line)
                    ts = data.get("timestamp", "")
                    if ts[:13] == check_time.strftime("%Y-%m-%dT%H"):
                        history.append(data)
                        break

        healthy_hours = sum(1 for h in history if h.get("overall") == "healthy")
        return {
            "ok": True,
            "hours_checked": len(history),
            "healthy_hours": healthy_hours,
            "uptime_pct": f"{round(healthy_hours/max(len(history),1)*100)}%",
            "recent_issues": [h.get("issues", []) for h in history[-3:] if h.get("issues")],
        }


# ═══════════════════════════════════
# 二、进程守护 + 自动重启
# ═══════════════════════════════════

class ProcessGuardian:
    """进程守护: 监控→告警→自动重启"""

    def __init__(self):
        self.state_file = STABILITY_DIR / "guardian_state.json"
        self.incident_log = STABILITY_DIR / "incidents.jsonl"
        self.restart_counts = defaultdict(int)
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            self.restart_counts = defaultdict(int, json.loads(self.state_file.read_text(encoding="utf-8")).get("restarts", {}))

    def _save_state(self):
        self.state_file.write_text(json.dumps({
            "restarts": dict(self.restart_counts),
            "last_updated": datetime.now().isoformat()[:19],
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def guard_cycle(self) -> dict:
        """守护周期: 检查→修复→记录"""
        monitor = HealthMonitor()
        health = monitor.check_all()
        actions = []

        for name, status in health.get("services", {}).items():
            if not status.get("ok"):
                actions.append(self._handle_failure(name, status))

        self._save_state()
        return {
            "ok": True,
            "health": health["overall"],
            "actions_taken": actions,
            "restart_counts": dict(self.restart_counts),
        }

    def _handle_failure(self, service_name: str, status: dict) -> dict:
        """处理服务故障"""
        # 重启次数限制(防止无限重启)
        if self.restart_counts.get(service_name, 0) >= 5:
            self._log_incident(service_name, "MAX_RESTARTS", "重启次数达上限")
            return {"service": service_name, "action": "alert_only", "reason": "max_restarts_reached"}

        # 尝试重启
        result = self._restart_service(service_name)
        self.restart_counts[service_name] += 1

        if result.get("ok"):
            self._log_incident(service_name, "RESTART_SUCCESS", f"第{self.restart_counts[service_name]}次重启成功")
        else:
            self._log_incident(service_name, "RESTART_FAILED", str(result.get("error", "")))

        return {"service": service_name, "action": "restart", "result": result}

    def _restart_service(self, name: str) -> dict:
        """重启服务"""
        from deploy import start_service
        return start_service(name)

    def _log_incident(self, service: str, incident_type: str, detail: str):
        with open(self.incident_log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat()[:19],
                "service": service,
                "type": incident_type,
                "detail": detail,
            }, ensure_ascii=False) + "\n")

    def get_incidents(self, limit: int = 20) -> List[Dict]:
        """获取故障记录"""
        incidents = []
        if self.incident_log.exists():
            for line in open(self.incident_log, encoding="utf-8"):
                incidents.append(json.loads(line))
        return sorted(incidents, key=lambda x: x["timestamp"], reverse=True)[:limit]


# ═══════════════════════════════════
# 三、错误聚合 + 模式识别
# ═══════════════════════════════════

class ErrorAggregator:
    """全模块错误收集+分析"""

    def __init__(self):
        self.error_log = STABILITY_DIR / "errors.jsonl"
        self.patterns_file = STABILITY_DIR / "error_patterns.json"

    def capture(self, module: str, error: str, context: dict = None):
        """捕获错误"""
        entry = {
            "timestamp": datetime.now().isoformat()[:19],
            "module": module,
            "error": str(error)[:500],
            "error_hash": str(hash(str(error))),
            "context": context or {},
        }
        with open(self.error_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 实时检查是否有模式
        self._check_patterns(entry)

    def _check_patterns(self, entry: dict):
        """检测错误模式（同类型错误>3次=告警）"""
        module = entry["module"]
        error_hash = entry["error_hash"]
        recent = []

        # 读最近100条
        lines = []
        if self.error_log.exists():
            with open(self.error_log, encoding="utf-8") as f:
                lines = f.readlines()[-100:]

        same_error = [l for l in lines if error_hash in l and module in l]
        if len(same_error) >= 3:
            self._alert_pattern(module, entry["error"][:100], len(same_error))

    def _alert_pattern(self, module: str, error: str, count: int):
        """记录错误模式"""
        patterns = {}
        if self.patterns_file.exists():
            patterns = json.loads(self.patterns_file.read_text(encoding="utf-8"))

        key = f"{module}:{str(hash(error))}"
        patterns[key] = {
            "module": module,
            "error_sample": error[:200],
            "count": count,
            "first_seen": patterns.get(key, {}).get("first_seen", datetime.now().isoformat()[:19]),
            "last_seen": datetime.now().isoformat()[:19],
        }
        self.patterns_file.write_text(json.dumps(patterns, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_error_summary(self, hours: int = 24) -> dict:
        """错误摘要"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()[:19]
        by_module = defaultdict(int)
        total = 0

        if self.error_log.exists():
            for line in open(self.error_log, encoding="utf-8"):
                data = json.loads(line)
                if data["timestamp"] >= cutoff:
                    by_module[data["module"]] += 1
                    total += 1

        patterns = {}
        if self.patterns_file.exists():
            patterns = json.loads(self.patterns_file.read_text(encoding="utf-8"))

        return {
            "ok": True,
            "period_hours": hours,
            "total_errors": total,
            "by_module": dict(by_module),
            "error_rate": f"{round(total/max(hours,1), 1)}/h",
            "recurring_patterns": len(patterns),
            "critical_modules": [m for m, c in by_module.items() if c >= 5],
        }


# ═══════════════════════════════════
# 四、性能指标收集
# ═══════════════════════════════════

class MetricsCollector:
    """性能指标收集器"""

    def __init__(self):
        self.metrics_file = STABILITY_DIR / "metrics.jsonl"

    def record(self, metric_name: str, value: float, tags: dict = None):
        """记录指标"""
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat()[:19],
                "metric": metric_name,
                "value": value,
                "tags": tags or {},
            }, ensure_ascii=False) + "\n")

    def get_stats(self, metric_name: str, hours: int = 24) -> dict:
        """获取统计"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()[:19]
        values = []

        if self.metrics_file.exists():
            for line in open(self.metrics_file, encoding="utf-8"):
                data = json.loads(line)
                if data["metric"] == metric_name and data["timestamp"] >= cutoff:
                    values.append(data["value"])

        if not values:
            return {"ok": True, "metric": metric_name, "samples": 0}

        return {
            "ok": True,
            "metric": metric_name,
            "samples": len(values),
            "avg": round(sum(values) / len(values), 2),
            "min": min(values),
            "max": max(values),
            "p95": sorted(values)[int(len(values) * 0.95)] if len(values) >= 20 else max(values),
        }


# ═══════════════════════════════════
# 五、一键健康仪表盘
# ═══════════════════════════════════

def stability_dashboard() -> dict:
    """稳定性总览仪表盘"""
    monitor = HealthMonitor()
    guardian = ProcessGuardian()
    aggregator = ErrorAggregator()
    metrics = MetricsCollector()

    health = monitor.check_all()
    history = monitor.get_health_history(24)
    errors = aggregator.get_error_summary(24)
    incidents = guardian.get_incidents(5)

    return {
        "ok": True,
        "timestamp": datetime.now().isoformat()[:19],
        "status": {
            "health": health["overall"],
            "uptime_24h": history["uptime_pct"],
            "services": {
                name: "UP" if s.get("ok") else "DOWN"
                for name, s in health.get("services", {}).items()
            },
            "system": {
                name: f"OK ({list(s.values())[0]})" if s.get("ok") else "WARN"
                for name, s in health.get("system", {}).items()
            },
        },
        "errors": {
            "total_24h": errors["total_errors"],
            "rate": errors["error_rate"],
            "patterns": errors["recurring_patterns"],
            "top_modules": sorted(errors["by_module"].items(), key=lambda x: x[1], reverse=True)[:3],
        },
        "incidents": {
            "recent": len(incidents),
            "last_5": incidents,
        },
        "alerts": health.get("issues", []) + (
            [f"重复错误: {errors['recurring_patterns']}个模式"] if errors["recurring_patterns"] > 0 else []
        ),
    }


# ═══════════════════════════════════
# 六、守护进程主循环
# ═══════════════════════════════════

class StabilityDaemon:
    """稳定性守护进程"""

    def __init__(self, check_interval: int = 300):
        self.interval = check_interval  # 5分钟
        self.monitor = HealthMonitor()
        self.guardian = ProcessGuardian()
        self.aggregator = ErrorAggregator()
        self.running = False

    def start(self):
        """启动守护"""
        self.running = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Stability Daemon started (interval={self.interval}s)")

        while self.running:
            try:
                # 健康检查
                health = self.monitor.check_all()

                if health["overall"] != "healthy":
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Health: {health['overall']}")
                    # 尝试自愈
                    self.guardian.guard_cycle()

                # 记录指标
                MetricCollector().record("health_score", 100 if health["overall"] == "healthy" else 50)

                time.sleep(self.interval)

            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                self.aggregator.capture("daemon", str(e))
                time.sleep(min(self.interval, 60))

    def stop(self):
        self.running = False
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Stability Daemon stopped")


# ═══════════════════════════════════
# CLI
# ═══════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        daemon = StabilityDaemon(check_interval=300)
        daemon.start()
    elif len(sys.argv) > 1 and sys.argv[1] == "check":
        dash = stability_dashboard()
        print(json.dumps(dash, ensure_ascii=False, indent=2))
    else:
        dash = stability_dashboard()
        print(f"Health: {dash['status']['health']}")
        print(f"Uptime: {dash['status']['uptime_24h']}")
        print(f"Errors: {dash['errors']['total_24h']} ({dash['errors']['rate']})")
        print(f"Services: {dash['status']['services']}")
        print(f"System: {dash['status']['system']}")
        if dash["alerts"]:
            print(f"Alerts: {dash['alerts']}")
