"""Possession: seconds of in-play control, and share of assigned control time."""

from collections.abc import Sequence

from app.analytics.definitions import pct
from app.models.events import Event
from app.models.stats import Metric


def possession_seconds(
    events: Sequence[Event], t0: int | None, t1: int, teams: Sequence[str]
) -> dict[str, Metric]:
    """Control runs from an event to the next event in the same `possession_id`, credited to the event's
    `possession_team_id`. Skipped: out-of-play events (in_play=False), unassigned control (team None), and gaps
    between different possessions. Each interval is clipped to the window (t0, t1]. Only intervals closed by an
    event at or before t1 count, so nothing after the replay clock is used. `events` must be in seq order."""
    seconds = {team: 0 for team in teams}
    contributing: dict[str, list[str]] = {team: [] for team in teams}
    for a, b in zip(events, events[1:], strict=False):
        if b.match_second > t1:
            break
        if a.possession_id != b.possession_id or not a.in_play or a.possession_team_id not in seconds:
            continue
        lo = a.match_second if t0 is None else max(a.match_second, t0)
        overlap = b.match_second - lo
        if overlap > 0:
            seconds[a.possession_team_id] += overlap
            contributing[a.possession_team_id].append(a.event_id)
    return {team: Metric(value=seconds[team], event_ids=contributing[team]) for team in teams}


def possession_pct(
    events: Sequence[Event], t0: int | None, t1: int, teams: Sequence[str]
) -> dict[str, Metric]:
    """Team seconds ÷ all assigned seconds × 100, whole number rounded half up; None if no assigned time."""
    secs = possession_seconds(events, t0, t1, teams)
    total = sum(int(m.value or 0) for m in secs.values())
    return {
        team: Metric(value=pct(int(m.value or 0), total), event_ids=m.event_ids) for team, m in secs.items()
    }
