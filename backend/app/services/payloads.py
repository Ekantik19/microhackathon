"""Compact message payloads for the bus/SSE. Event-ID lists are stripped here to keep per-event pushes small;
the REST endpoints return the full metrics with their contributing event IDs."""

from typing import Any

from app.analytics.definitions import WINDOWS
from app.analytics.state import MatchState
from app.models.events import display_clock


def clock_fields(match_second: int, period: int, second_half_start: int) -> dict[str, int]:
    minute, second = display_clock(match_second, period, second_half_start)
    return {"clock_second": match_second, "minute": minute, "second": second, "period": period}


def stats_payload(state: MatchState, second_half_start: int) -> dict[str, Any]:
    windows = {}
    for name in WINDOWS:
        stats = state.window(name, with_players=False)
        windows[name] = {
            team_id: {field: metric.value for field, metric in team if field != "team_id"}
            for team_id, team in stats.teams.items()
        }
    return {
        **clock_fields(state.clock, state.period, second_half_start),
        "score": state.score(),
        "windows": windows,
    }
