# api/routers/health.py
"""
Health check router.
GET /health — returns service status and version.
Used by load balancers, Docker health checks, and uptime monitors.
"""
from fastapi import APIRouter
from api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service status. Useful for load balancers and uptime monitoring.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")
