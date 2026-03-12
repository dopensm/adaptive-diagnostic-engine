"""Top-level API router."""

from fastapi import APIRouter

from app.api import admin, sessions

api_router = APIRouter()
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
