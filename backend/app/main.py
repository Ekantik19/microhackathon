"""FastAPI entry point. Pipeline stages: Ingest (events/) → Interpret (analytics/, patterns/) →
Explain + Personalize (ai/) → Render (frontend/, fed by api/ over SSE)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.ai.modes import load_modes
from app.ai.providers import get_provider
from app.api import health, insights, matches, simulation, stream
from app.api.errors import install_error_handlers
from app.config import Settings, get_settings
from app.patterns.config import load_patterns_config
from app.patterns.hook import detection_hooks
from app.services.bus import EventBus
from app.services.orchestrator import Orchestrator
from app.services.registry import MatchRegistry
from app.services.store import MatchStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.registry.shutdown()

    app = FastAPI(title="InsideMatch API", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.bus = EventBus()
    app.state.store = MatchStore()
    app.state.ai_provider = get_provider(settings)
    orchestrator = Orchestrator(
        app.state.store,
        app.state.bus,
        app.state.ai_provider,
        load_modes(settings.config_dir),
        timeout=settings.ai_timeout_seconds,
    )
    app.state.orchestrator = orchestrator
    app.state.recap_generator = orchestrator.recap_now
    patterns = load_patterns_config(settings.config_dir)
    app.state.registry = MatchRegistry(
        settings.data_dir,
        app.state.bus,
        app.state.store,
        hook_factories=[
            orchestrator.attach,
            detection_hooks(app.state.store, app.state.bus, patterns, listeners=[orchestrator.on_detection]),
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    for module in (health, matches, simulation, stream, insights):
        app.include_router(module.router)
    return app


app = create_app()
