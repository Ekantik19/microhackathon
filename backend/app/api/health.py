from fastapi import APIRouter
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
async def health() -> Health:
    s = get_settings()
    # Dependency status is filled in by later phases (AI fallback, Fabric fallback, DB reachability).
    return Health(
        status="ok", version=__version__, ai_provider=s.ai_provider, event_source=s.event_source, db="n/a"
    )
