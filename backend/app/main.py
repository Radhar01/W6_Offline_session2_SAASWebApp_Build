"""FastAPI application entrypoint for ClipCreator.

No authentication is configured in this MVP (single-tenant / open access —
see INITIAL.md). Do not add login/JWT/OAuth routes or middleware here.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.routers import clip_generation, clips, dashboard, videos
from app.services.storage_service import get_media_root

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


def create_app() -> FastAPI:
    """Application factory: builds and configures the FastAPI instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Convert long-form video into logically-segmented short clips/reels.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # --- Routers ---------------------------------------------------------
    app.include_router(videos.router)
    app.include_router(clip_generation.router, prefix="/api/v1")
    app.include_router(clips.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1/dashboard")
    # -----------------------------------------------------------------------

    # Static thumbnails (clip video files still go through the dedicated
    # streamed /clips/{id}/download endpoint, not this mount).
    media_root = get_media_root()
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness/readiness probe."""
        return {"status": "ok"}

    return app


app = create_app()
