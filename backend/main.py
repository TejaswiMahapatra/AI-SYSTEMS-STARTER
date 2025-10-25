"""
FastAPI application entry point.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from backend.config import settings, validate_settings
from backend.core.database import init_db, close_db
from backend.core.redis_client import close_redis
from backend.api.v1 import health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan events.

    Startup:
    - Validate configuration
    - Initialize database tables
    - Connect to external services

    Shutdown:
    - Close database connections
    - Close Redis connections
    """
    # Startup
    logger.info("Starting AI Systems Starter API...")

    try:
        # Validate configuration
        validate_settings()
        logger.info("Configuration validated successfully")

        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")

        # Log configuration
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"LLM Provider: {settings.llm_provider}")
        logger.info(f"Embedding Provider: {settings.embedding_provider}")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down AI Systems Starter API...")

    try:
        await close_db()
        await close_redis()
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-ready AI system with RAG, LangGraph agents, and vector search",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Mount Prometheus metrics endpoint (if enabled)
if settings.enable_prometheus:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("Prometheus metrics enabled at /metrics")

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(_request, exc):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
        log_level=settings.log_level.lower()
    )