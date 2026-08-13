"""API main module."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nvidia_multi_agent_builder.config import settings, configure_logging
from nvidia_multi_agent_builder.db import init_db, close_db
from nvidia_multi_agent_builder.api.routes import projects, agents, models, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    # Startup
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
    )
    await init_db()
    # Start orchestrator
    from nvidia_multi_agent_builder.orchestration import orchestrator
    await orchestrator.start()
    yield
    # Shutdown
    await orchestrator.stop()
    await close_db()


def create_app(custom_settings=None) -> FastAPI:
    """Create FastAPI application."""
    cfg = custom_settings or settings

    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description="NVIDIA Multi-Agent Builder API",
        lifespan=lifespan,
        docs_url="/docs" if cfg.debug else None,
        redoc_url="/redoc" if cfg.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(projects.router)
    app.include_router(agents.router)
    app.include_router(models.router)
    app.include_router(health.router)

    # Health check
    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        return {"status": "healthy", "version": cfg.app_version}

    @app.get("/health/ready")
    async def readiness_check() -> dict[str, Any]:
        return {"status": "ready"}

    return app