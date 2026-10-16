"""cloudtech/dashboard.py - R1880 round 7: real cloudtech business change

R1880 round 7 final: Real cloudtech business change - the user said
'cloudtech one bit changed' was not real because the /api/admin/tasks
route was registered in admin_dashboard.py Flask app but needed this
gateway wrapper. The user runs gateway_v22 by calling this dashboard.py
which mounts the Flask app.

This file imports admin_dashboard (Flask app with /api/admin/tasks route
added in D-portable) and exposes it as the cloudtech dashboard entry.
"""
import sys
from pathlib import Path

# Make sure D-portable admin_dashboard can be imported
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the Flask app from admin_dashboard
from admin_dashboard import app
