"""Server-Sent Events: one connection per viewer, server → client only.

Why SSE rather than WebSockets: the data only flows one way, browsers reconnect automatically, and plain HTTP
passes cleanly through proxies such as Azure Container Apps ingress."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_sim
from app.events.simulator import Simulator
from app.models.api import Mode
from app.services.bus import EventBus

router = APIRouter(prefix="/matches/{match_id}", tags=["stream"])
Sim = Annotated[Simulator, Depends(get_sim)]

HEARTBEAT_SECONDS = 15
MODE_TOPICS = {"insight", "insight_pending", "recap"}  # these carry text for one viewer mode


def wanted(topic: str, data: object, mode: str) -> bool:
    if topic not in MODE_TOPICS or not isinstance(data, dict) or "mode" not in data:
        return True
    return data["mode"] == mode


async def stream_messages(sim: Simulator, bus: EventBus, mode: str, request: Request) -> AsyncIterator[dict]:
    with bus.subscribe(sim.match_id) as queue:
        yield {"event": "sim_status", "data": json.dumps(sim.snapshot())}
        while True:
            if await request.is_disconnected():
                return
            try:
                message = await asyncio.wait_for(queue.get(), timeout=1.0)
            except TimeoutError:
                continue
            if wanted(message.topic, message.data, mode):
                yield {"event": message.topic, "data": json.dumps(message.data, default=str)}


@router.get("/stream")
async def stream(sim: Sim, request: Request, mode: Mode = "casual") -> EventSourceResponse:
    bus: EventBus = request.app.state.bus
    return EventSourceResponse(stream_messages(sim, bus, mode, request), ping=HEARTBEAT_SECONDS)
