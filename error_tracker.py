"""
Error Tracking — Lightweight error aggregation (Sentry-compatible)
Collects, deduplicates, and reports errors. Can forward to Sentry when DSN is set.
"""
import os, json, traceback, hashlib
from datetime import datetime
from pathlib import Path

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
ERROR_LOG = Path(__file__).parent.parent / "logs" / "errors.jsonl"


def _ensure_log():
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)


def _fingerprint(exc_type: str, message: str, location: str) -> str:
    raw = f"{exc_type}:{message}:{location}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def capture_exception(exc: Exception = None, context: dict = None):
    """Capture exception with context for aggregation"""
    _ensure_log()

    if exc is None:
        exc_type = "ManualReport"
        exc_value = context.get("message", "") if context else ""
    else:
        exc_type = type(exc).__name__
        exc_value = str(exc)

    tb = traceback.format_exc() if exc else ""
    location = ""
    if tb:
        lines = tb.strip().split("\n")
        for line in reversed(lines):
            if line.strip().startswith("File "):
                location = line.strip()
                break

    fp = _fingerprint(exc_type, exc_value, location)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "fingerprint": fp,
        "type": exc_type,
        "message": exc_value[:500],
        "location": location,
        "context": context or {},
        "traceback": tb[:2000],
    }

    # Write to local log
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Forward to Sentry if configured
    if SENTRY_DSN:
        _forward_sentry(entry)

    return fp


def _forward_sentry(entry: dict):
    """Forward error to Sentry"""
    try:
        import urllib.request
        sentry_data = {
            "exception": {"values": [{
                "type": entry["type"],
                "value": entry["message"],
            }]},
            "tags": entry.get("context", {}),
            "timestamp": entry["timestamp"],
            "fingerprint": [entry["fingerprint"]],
        }
        body = json.dumps(sentry_data).encode()
        req = urllib.request.Request(
            f"{SENTRY_DSN}/api/1/store/",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # Don't let Sentry errors crash the app


def get_error_stats(days: int = 7) -> dict:
    """Get aggregated error statistics"""
    if not ERROR_LOG.exists():
        return {"total": 0, "by_type": {}, "by_fingerprint": {}, "recent": []}

    cutoff = datetime.now().timestamp() - days * 86400
    by_type = {}
    by_fp = {}
    recent = []

    with open(ERROR_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                ts = datetime.fromisoformat(e["timestamp"]).timestamp()
                if ts < cutoff:
                    continue
                et = e["type"]
                fp = e["fingerprint"]
                by_type[et] = by_type.get(et, 0) + 1
                by_fp[fp] = {"type": et, "message": e["message"][:100], "count": by_fp.get(fp, {}).get("count", 0) + 1}
                recent.append(e)
            except Exception:
                continue

    return {
        "total": sum(by_type.values()),
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])[:10]),
        "by_error": dict(sorted(by_fp.items(), key=lambda x: -x[1]["count"])[:10]),
        "recent": recent[-20:],
    }


# Flask integration
def setup_error_handler(app):
    """Register error handlers on Flask app"""
    @app.errorhandler(500)
    def handle_500(e):
        capture_exception(e, {"url": str(getattr(e, 'request', '')), "status": 500})
        return {"error": "服务器内部错误，已记录"}, 500

    @app.errorhandler(Exception)
    def handle_all(e):
        capture_exception(e, {"url": str(getattr(e, 'request', '')), "status": getattr(e, 'code', 500)})
        return {"error": str(e)}, getattr(e, 'code', 500)
