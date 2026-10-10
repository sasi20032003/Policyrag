"""Simple liveness/readiness endpoint."""
from fastapi import APIRouter

from config import get_settings
from schemas.schemas import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", env=settings.env)
