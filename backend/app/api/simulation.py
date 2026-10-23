"""Replay controls. Any manual control cancels a running demo first."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request

from app.api.deps import get_sim, registry, store
from app.events.simulator import Simulator
from app.models.api import SeekBody, SimState, SpeedBody, StartBody

router = APIRouter(prefix="/matches/{match_id}/simulation", tags=["simulation"])
Sim = Annotated[Simulator, Depends(get_sim)]


def _state(sim: Simulator) -> SimState:
    return SimState.model_validate(sim.snapshot())


@router.post("/start", response_model=SimState)
async def start(sim: Sim, request: Request, body: Annotated[StartBody | None, Body()] = None) -> SimState:
    registry(request).cancel_demo(sim.match_id)
    await sim.start(speed=body.speed if body else None)
    return _state(sim)


@router.post("/pause", response_model=SimState)
async def pause(sim: Sim, request: Request) -> SimState:
    registry(request).cancel_demo(sim.match_id)
    await sim.pause()
    return _state(sim)


@router.post("/resume", response_model=SimState)
async def resume(sim: Sim, request: Request) -> SimState:
    registry(request).cancel_demo(sim.match_id)
    await sim.resume()
    return _state(sim)


@router.post("/reset", response_model=SimState)
async def reset(sim: Sim, request: Request) -> SimState:
    """Clears replay state, detections and live insights. Cached AI text is kept."""
    registry(request).cancel_demo(sim.match_id)
    await sim.reset()
    store(request).clear_live(sim.match_id)
    return _state(sim)


@router.post("/speed", response_model=SimState)
async def speed(sim: Sim, body: SpeedBody) -> SimState:
    await sim.set_speed(body.speed)
    return _state(sim)


@router.post("/seek", response_model=SimState)
async def seek(sim: Sim, request: Request, body: SeekBody) -> SimState:
    registry(request).cancel_demo(sim.match_id)
    await sim.seek(body.match_second)
    return _state(sim)


@router.post("/demo", response_model=SimState)
async def demo(sim: Sim, request: Request) -> SimState:
    """Scripted storyline walkthrough (under 90 s). Runs in the background; returns immediately."""
    store(request).clear_live(sim.match_id)
    registry(request).start_demo(sim)
    return _state(sim)
