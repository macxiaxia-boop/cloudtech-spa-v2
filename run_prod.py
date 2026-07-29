#!/usr/bin/env python3
"""
CloudTech Production Server — Waitress WSGI (Windows-compatible)
Usage: python run_prod.py
       python run_prod.py --port 5099 --workers 4
"""
import sys, os
from pathlib import Path

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).parent))

from waitress import serve
from admin_dashboard import app

HOST = os.environ.get("CLOUDTECH_HOST", "127.0.0.1")
PORT = int(os.environ.get("CLOUDTECH_PORT", "5099"))
WORKERS = int(os.environ.get("CLOUDTECH_WORKERS", "4"))

if __name__ == "__main__":
    print(f"CloudTech v2.0 Production Server")
    print(f"  Server: waitress (multi-threaded)")
    print(f"  Host:   {HOST}:{PORT}")
    print(f"  Threads: {WORKERS}")
    print(f"  Admin:  http://{HOST}:{PORT}/admin")
    serve(app, host=HOST, port=PORT, threads=WORKERS)
