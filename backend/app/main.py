"""FastAPI entry point. Pipeline stages: Ingest (events/) → Interpret (analytics/, patterns/) →
Explain + Personalize (ai/) → Render (frontend/, fed by api/ over SSE)."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import health
from app.api.errors import install_error_handlers
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    app = FastAPI(title="InsideMatch API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    return app


app = create_app()
