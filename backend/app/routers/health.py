from fastapi import APIRouter
from ..models.file import HealthResponse
import time
from datetime import timedelta

router = APIRouter(tags=["health"])

START_TIME = time.time()


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the API health status, current version, and server uptime. Useful for monitoring and load balancer health checks.",
)
async def health_check():
    uptime = str(timedelta(seconds=int(time.time() - START_TIME)))
    return HealthResponse(status="ok", version="1.0.0", uptime=uptime)
