"""
应用日志系统 — Structured Logging
替代print·分级(DEBUG/INFO/WARN/ERROR)·文件轮转·JSON格式
"""
import json, logging, sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

LOG_DIR = Path("D:/个人文件/AI/云数科技/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 文件输出(旋转: 10MB×5个备份)
    fh = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    fh.setFormatter(_fmt)
    logger.addHandler(fh)

    # 控制台输出
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(_fmt)
    logger.addHandler(ch)

    return logger

# 预置logger
log = get_logger("cloudtech")

def log_event(event: str, detail: dict = None):
    """记录业务事件"""
    entry = {"time": datetime.now().isoformat()[:19], "event": event, "detail": detail or {}}
    ef = LOG_DIR / "events.jsonl"
    with open(ef, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
