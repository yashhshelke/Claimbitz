"""FastAPI application factory for the agentcore multi-agent system.

Creates and configures the FastAPI app with all v2 routes. The app can be
run standalone (``uvicorn agentcore.api.app:create_app --factory``) or
imported by a parent app that mounts it under a prefix.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Startup: nothing heavy here — agents/LLM/Pinecone are lazy-init.
    # Could warm up connections if needed in production.
    yield
    # Shutdown: cleanup would go here (close LLM client, Pinecone, Redis)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="ClaimBlitz Multi-Agent API",
        version="2.0.0",
        description=(
            "Enterprise-grade collaborative multi-agent system for "
            "medical insurance claim processing."
        ),
        lifespan=lifespan,
    )

    # CORS for frontend dev server
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/v2")
    # Also mount /process at root for frontend compatibility
    app.include_router(router, prefix="")
    return app


# Module-level instance for ``uvicorn agentcore.api.app:app``
app = create_app()
