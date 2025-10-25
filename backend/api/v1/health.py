"""
Health check endpoints.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel

from backend.config import settings
from backend.core.database import check_db_health
from backend.core.redis_client import check_redis_health
from backend.plugins.vector_dbs.weaviate_db import get_weaviate

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    version: str
    environment: str
    services: Dict[str, Any]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic API health status"
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns API status, version, and environment.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Returns detailed health status of all services"
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check endpoint.

    Checks connectivity to:
    - PostgreSQL database
    - Redis cache
    - Weaviate vector database
    - Ollama LLM (if enabled)
    """
    services = {}

    # Check PostgreSQL
    try:
        postgres_healthy = await check_db_health()
        services["postgresql"] = {
            "status": "healthy" if postgres_healthy else "unhealthy",
            "url": f"{settings.postgres_host}:{settings.postgres_port}"
        }
    except Exception as e:
        services["postgresql"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check Redis
    try:
        redis_healthy = await check_redis_health()
        services["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "url": f"{settings.redis_host}:{settings.redis_port}"
        }
    except Exception as e:
        services["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check Weaviate
    try:
        weaviate = get_weaviate()
        weaviate_healthy = await weaviate.health_check()
        services["weaviate"] = {
            "status": "healthy" if weaviate_healthy else "unhealthy",
            "url": settings.weaviate_url
        }
    except Exception as e:
        services["weaviate"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check Ollama (if enabled)
    if settings.llm_provider == "ollama":
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.ollama_url}/api/tags",
                    timeout=5.0
                )
                ollama_healthy = response.status_code == 200
                services["ollama"] = {
                    "status": "healthy" if ollama_healthy else "unhealthy",
                    "url": settings.ollama_url,
                    "model": settings.ollama_model
                }
        except Exception as e:
            services["ollama"] = {
                "status": "unhealthy",
                "error": str(e)
            }

    # Determine overall status
    all_healthy = all(
        svc.get("status") == "healthy"
        for svc in services.values()
    )

    return DetailedHealthResponse(
        status="healthy" if all_healthy else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        services=services
    )


@router.get(
    "/readiness",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint"
)
async def readiness_check() -> Dict[str, str]:
    """
    Readiness probe for Kubernetes.

    Returns 200 if the service is ready to accept traffic.
    """
    # Check critical services
    db_healthy = await check_db_health()

    if not db_healthy:
        return {"status": "not_ready", "reason": "Database unavailable"}

    return {"status": "ready"}


@router.get(
    "/liveness",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint"
)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness probe for Kubernetes.

    Returns 200 if the service is alive (even if not ready).
    """
    return {"status": "alive"}
