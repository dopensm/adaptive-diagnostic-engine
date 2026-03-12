"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.router import api_router
from app.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Simple health-check endpoint."""

        return {"status": "ok", "environment": settings.app_env}

    return app


app = create_app()
