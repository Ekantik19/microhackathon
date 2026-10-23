from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    version: str
    ai_provider: str
    event_source: str
    db: str


@router.get("/health", response_model=Health)
async def health(request: Request) -> Health:
    s = get_settings()
    provider = getattr(request.app.state, "ai_provider", None)
    # Dependency status is filled in by later phases (AI fallback, Fabric fallback, DB reachability).
    return Health(
        status="ok",
        version=__version__,
        ai_provider=provider.name if provider else s.ai_provider,
        event_source=s.event_source,
        db="n/a",
    )
