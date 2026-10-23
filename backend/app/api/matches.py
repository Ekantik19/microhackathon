"""Read-only match endpoints. Everything is computed from events received so far: never the future."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_sim, registry, store
from app.events.catalog import load_meta
from app.events.simulator import Simulator
from app.models.api import (
    EventsPage,
    MatchInfo,
    MatchSummary,
    SimState,
    StatsResponse,
    Timeline,
    TimelineItem,
    WindowName,
)
from app.models.events import Event, EventType

router = APIRouter(prefix="/matches", tags=["matches"])
Sim = Annotated[Simulator, Depends(get_sim)]

TIMELINE_EVENTS = {
    EventType.GOAL,
    EventType.SHOT,
    EventType.CARD,
    EventType.SUBSTITUTION,
    EventType.PERIOD_END,
}


@router.get("", response_model=list[MatchSummary])
async def list_matches(request: Request) -> list[MatchSummary]:
    reg = registry(request)
    return [MatchSummary.model_validate(load_meta(reg.data_dir, m).model_dump()) for m in reg.match_ids()]


@router.get("/{match_id}", response_model=MatchInfo)
async def match_info(sim: Sim) -> MatchInfo:
    return MatchInfo.model_validate(sim.meta.model_dump(exclude={"final_score", "seed"}))


@router.get("/{match_id}/state", response_model=SimState)
async def match_state(sim: Sim) -> SimState:
    return SimState.model_validate(sim.snapshot())


@router.get("/{match_id}/stats", response_model=StatsResponse)
async def match_stats(sim: Sim, window: WindowName = "full") -> StatsResponse:
    return StatsResponse(
        match_id=sim.match_id,
        clock_second=sim.state.clock,
        score=sim.state.score(),
        stats=sim.state.window(window),
    )


def _label(event: Event, names: dict[str, str]) -> str:
    who = names.get(event.player_id or "", "")
    match event.event_type:
        case EventType.GOAL:
            return f"Goal: {who}"
        case EventType.SHOT:
            return f"Shot ({(event.outcome or '').replace('_', ' ')}): {who}, synthetic xG {event.xg:.2f}"
        case EventType.CARD:
            return f"{(event.outcome or '').capitalize()} card: {who}"
        case EventType.SUBSTITUTION:
            return f"Substitution: {names.get(event.recipient_id or '', '')} on, {who} off"
        case EventType.PERIOD_END:
            return "Half-time" if event.period == 1 else "Full-time"
    return event.event_type.value


@router.get("/{match_id}/timeline", response_model=Timeline)
async def match_timeline(sim: Sim, request: Request) -> Timeline:
    names = sim.meta.player_names()
    items = [
        TimelineItem(
            kind="event",
            id=e.event_id,
            match_second=e.match_second,
            minute=e.minute,
            second=e.second,
            period=e.period,
            type=e.event_type.value,
            team_id=e.team_id if e.event_type != EventType.PERIOD_END else None,
            player_id=e.player_id,
            label=_label(e, names),
        )
        for e in sim.received()
        if e.event_type in TIMELINE_EVENTS
    ]
    items += [
        TimelineItem(
            kind="detection",
            id=d.detection_id,
            match_second=d.end_second,
            minute=d.minute,
            second=d.second,
            period=d.period,
            type=d.pattern,
            team_id=d.team_id,
            label=d.pattern.replace("_", " ").capitalize(),
        )
        for d in store(request).detections(sim.match_id, up_to_second=sim.state.clock)
        if d.kind == "pattern"
    ]
    return Timeline(
        match_id=sim.match_id,
        clock_second=sim.state.clock,
        items=sorted(items, key=lambda i: (i.match_second, i.kind)),
    )


@router.get("/{match_id}/events", response_model=EventsPage)
async def match_events(
    sim: Sim,
    since_seq: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> EventsPage:
    page = [e for e in sim.received() if e.seq > since_seq][:limit]
    return EventsPage(match_id=sim.match_id, events=page, next_since_seq=page[-1].seq if page else since_seq)
