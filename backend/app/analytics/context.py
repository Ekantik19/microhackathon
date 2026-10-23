"""Context helpers that later feed the FactPack (EXPLAIN). Only data at or before `t` is ever returned."""

from collections.abc import Sequence

from app.analytics.score import score_at
from app.analytics.windows import window_stats
from app.models.events import Event


def recent_events(events: Sequence[Event], t: int, n: int) -> list[Event]:
    return [e for e in events if e.match_second <= t][-n:]


def match_context(events: Sequence[Event], t: int, teams: Sequence[str], window: str = "last_5") -> dict:
    received = [e for e in events if e.match_second <= t]
    last = received[-1] if received else None
    return {
        "clock_second": t,
        "period": last.period if last else 1,
        "minute": last.minute if last else 0,
        "score": {team: m.value for team, m in score_at(received, t, teams).items()},
        "window": window_stats(received, t, window, teams, with_players=False),
        "recent_events": received[-8:],
    }
