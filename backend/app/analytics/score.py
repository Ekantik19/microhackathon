"""Score at a point in time, from goal events only."""

from collections.abc import Sequence

from app.analytics.definitions import ids
from app.models.events import Event, EventType
from app.models.stats import Metric


def score_at(events: Sequence[Event], t: int, teams: Sequence[str]) -> dict[str, Metric]:
    goals = [e for e in events if e.event_type == EventType.GOAL and e.match_second <= t]
    return {
        team: Metric(
            value=sum(1 for g in goals if g.team_id == team),
            event_ids=ids([g for g in goals if g.team_id == team]),
        )
        for team in teams
    }
