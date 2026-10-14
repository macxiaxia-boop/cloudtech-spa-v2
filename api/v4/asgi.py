"""ASGI entry for the EXISTING CloudTech V4 router.

For authenticated loopback integration testing alongside the current
CloudTech WSGI UI server. No duplicate business service or data layer.
Mount api.v4.router into an existing ASGI host in production after an
independent deployment review.

Local explicit start only:
    python -m uvicorn api.v4.asgi:app --host 127.0.0.1 --port 5089
"""
from fastapi import FastAPI

from . import router

app = FastAPI(
    title="CloudTech V4 WorkPath API (integration host)",
    version="P9",
)
app.include_router(router)
