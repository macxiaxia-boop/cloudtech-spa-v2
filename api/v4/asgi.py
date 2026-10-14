"""ASGI integration host for the EXISTING CloudTech V4 API router.

Mountable on loopback for AIOS two-service tests; this creates no
alternative product state, execution scheduler or provider connection.

    python -m uvicorn api.v4.asgi:app --host 127.0.0.1 --port 5089
"""
from fastapi import FastAPI

from . import router

app = FastAPI(title="CloudTech V4 WorkPath API", version="P12")
app.include_router(router)
