"""Shots, shots on target and synthetic xG. A goal linked to a shot is not a second shot."""

from collections.abc import Sequence

from app.analytics.definitions import ids, select
from app.models.events import Event, EventType
from app.models.stats import Metric

ON_TARGET = {"saved", "goal"}


def _shots(events: Sequence[Event], team: str, t0: int | None, t1: int) -> list[Event]:
    return [e for e in select(events, t0, t1) if e.team_id == team and e.event_type == EventType.SHOT]


def shots(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    found = _shots(events, team, t0, t1)
    return Metric(value=len(found), event_ids=ids(found))


def shots_on_target(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    found = [e for e in _shots(events, team, t0, t1) if e.outcome in ON_TARGET]
    return Metric(value=len(found), event_ids=ids(found))


def xg_total(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    found = _shots(events, team, t0, t1)
    return Metric(value=round(sum(e.xg or 0.0 for e in found), 2), event_ids=ids(found))
