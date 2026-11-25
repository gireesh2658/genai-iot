"""
IoTSynth AI - System Health Router
Lightweight health and operational readiness endpoints.
Strictly non-blocking: never loads ML models, reads large datasets, or triggers experiments.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends
from backend.config import Settings, get_settings

router = APIRouter(tags=["System Health"])


@router.get(
    "/health",
    summary="System Health & API Operational Status",
    response_description="Structured health and API status",
)
def get_system_health(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """Return lightweight health status and application metadata.

    Guaranteed zero-overhead: does not load ML models, parse datasets, or execute experiments.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": "development" if settings.DEBUG else "production",
    }
