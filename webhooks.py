"""
Webhook系统 — 管线事件订阅·回调通知
事件: content.created / content.published / quota.warning / payment.received
"""
import json, urllib.request
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
WEBHOOK_DIR = Path("D:/个人文件/AI/云数科技/webhooks")
WEBHOOK_DIR.mkdir(parents=True, exist_ok=True)

EVENTS = ["content.created", "content.published", "quota.warning", "payment.received", "tenant.created"]


def register_webhook(tid: str, event: str, url: str, secret: str = "") -> dict:
    """注册webhook"""
    if event not in EVENTS:
        return {"ok": False, "error": f"不支持的事件: {event}"}
    wid = f"wh-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    wh = {
        "id": wid, "tenant_id": tid, "event": event, "url": url,
        "secret": secret, "active": True, "created_at": datetime.now().isoformat()[:19],
        "last_triggered": None, "success_count": 0, "fail_count": 0,
    }
    wf = WEBHOOK_DIR / f"{wid}.json"
    wf.write_text(json.dumps(wh, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "webhook": wh}


def list_webhooks(tid: str = "") -> list:
    """列出webhooks"""
    hooks = []
    for f in sorted(WEBHOOK_DIR.glob("wh-*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            wh = json.loads(f.read_text(encoding="utf-8"))
            if tid and wh.get("tenant_id") != tid: continue
            hooks.append(wh)
        except Exception: pass
    return hooks


def delete_webhook(wid: str) -> dict:
    f = WEBHOOK_DIR / f"{wid}.json"
    if f.exists():
        f.unlink()
        return {"ok": True}
    return {"ok": False, "error": "不存在"}


def trigger_event(event: str, tid: str, payload: dict) -> dict:
    """触发事件: 查找匹配webhook并POST"""
    results = []
    for hook in list_webhooks():
        if hook["event"] != event: continue
        if hook["tenant_id"] != tid and hook["tenant_id"] != "*": continue
        if not hook["active"]: continue

        try:
            data = json.dumps({"event": event, "tenant_id": tid, "payload": payload, "timestamp": datetime.now().isoformat()}).encode()
            req = urllib.request.Request(hook["url"], data=data, headers={
                "Content-Type": "application/json",
                "X-Webhook-Secret": hook.get("secret", ""),
                "X-CloudTech-Event": event,
            })
            urllib.request.urlopen(req, timeout=10)
            hook["success_count"] += 1
            hook["last_triggered"] = datetime.now().isoformat()[:19]
            results.append({"wid": hook["id"], "status": "ok"})
        except Exception as e:
            hook["fail_count"] += 1
            results.append({"wid": hook["id"], "status": "failed", "error": str(e)[:100]})

        # Update hook stats
        wf = WEBHOOK_DIR / f'{hook["id"]}.json'
        wf.write_text(json.dumps(hook, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"event": event, "tenant_id": tid, "delivered": len([r for r in results if r["status"] == "ok"]), "results": results}
