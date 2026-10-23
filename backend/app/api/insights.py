"""Insights and recaps generated so far. Generation itself arrives with the AI layer (Phase 9)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_sim, store
from app.api.errors import ApiError
from app.events.simulator import Simulator
from app.models.api import Mode, RecapRequest
from app.models.insights import Insight, Recap
from app.services.orchestrator import RecapNotAvailable

router = APIRouter(prefix="/matches/{match_id}", tags=["insights"])
Sim = Annotated[Simulator, Depends(get_sim)]


@router.get("/insights", response_model=list[Insight])
async def insights(sim: Sim, request: Request, mode: Mode = "casual") -> list[Insight]:
    clock = sim.state.clock
    return [i for i in store(request).insights(sim.match_id, mode) if i.match_second <= clock]


@router.get("/recaps", response_model=list[Recap])
async def recaps(sim: Sim, request: Request, mode: Mode | None = None) -> list[Recap]:
    return store(request).recaps(sim.match_id, mode)


@router.post("/generate-recap", response_model=Recap)
async def generate_recap(sim: Sim, request: Request, body: RecapRequest) -> Recap:
    generator = getattr(request.app.state, "recap_generator", None)
    if generator is None:
        raise ApiError(503, "recap_unavailable", "Recap generation is not configured yet.")
    try:
        return await generator(sim, body.mode, body.scope)
    except RecapNotAvailable as exc:
        raise ApiError(409, "recap_not_available", str(exc)) from None
