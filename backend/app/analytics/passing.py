"""Passes attempted, completed, and pass accuracy (None when no passes were attempted)."""

from collections.abc import Sequence

from app.analytics.definitions import ids, pct, select
from app.models.events import Event, EventType
from app.models.stats import Metric


def _passes(events: Sequence[Event], team: str, t0: int | None, t1: int) -> list[Event]:
    return [e for e in select(events, t0, t1) if e.team_id == team and e.event_type == EventType.PASS]


def passes_attempted(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    found = _passes(events, team, t0, t1)
    return Metric(value=len(found), event_ids=ids(found))


def passes_completed(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    found = [e for e in _passes(events, team, t0, t1) if e.outcome == "complete"]
    return Metric(value=len(found), event_ids=ids(found))


def pass_accuracy(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    attempted = _passes(events, team, t0, t1)
    completed = [e for e in attempted if e.outcome == "complete"]
    return Metric(value=pct(len(completed), len(attempted)), event_ids=ids(attempted))
