"""Final-third entries, high recoveries and all ball recoveries."""

from collections.abc import Sequence

from app.analytics.definitions import HIGH_REGION_X, ids, is_ball_win, is_final_third_entry, select
from app.models.events import Event
from app.models.stats import Metric


def final_third_entries(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    found = [e for e in select(events, t0, t1) if e.team_id == team and is_final_third_entry(e)]
    return Metric(value=len(found), event_ids=ids(found))


def recoveries(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    """Ball wins anywhere: recovery, interception, or a won tackle."""
    found = [e for e in select(events, t0, t1) if e.team_id == team and is_ball_win(e)]
    return Metric(value=len(found), event_ids=ids(found))


def high_recoveries(events: Sequence[Event], team: str, t0: int | None, t1: int) -> Metric:
    """Ball wins at x ≥ 70, i.e. in the opponent's defensive third."""
    found = [
        e
        for e in select(events, t0, t1)
        if e.team_id == team and is_ball_win(e) and e.x is not None and e.x >= HIGH_REGION_X
    ]
    return Metric(value=len(found), event_ids=ids(found))
