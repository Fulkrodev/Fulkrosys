"""Health check endpoint."""
from fastapi import APIRouter

from backend.app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.app_env,
    }
