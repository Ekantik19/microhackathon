"""Rolling windows: last 5 min (300 s), last 10 min (600 s) and the full match, all ending at the replay clock."""

from bisect import bisect_right
from collections.abc import Sequence

from app.analytics import passing, possession, shots, territory
from app.analytics.definitions import WINDOWS, window_bounds
from app.analytics.players import player_table
from app.models.events import Event
from app.models.stats import TeamStats, WindowStats


def team_stats(events: Sequence[Event], team: str, t0: int | None, t1: int, poss: dict) -> TeamStats:
    return TeamStats(
        team_id=team,
        possession_seconds=poss["seconds"][team],
        possession_pct=poss["pct"][team],
        shots=shots.shots(events, team, t0, t1),
        shots_on_target=shots.shots_on_target(events, team, t0, t1),
        xg=shots.xg_total(events, team, t0, t1),
        passes_attempted=passing.passes_attempted(events, team, t0, t1),
        passes_completed=passing.passes_completed(events, team, t0, t1),
        pass_accuracy=passing.pass_accuracy(events, team, t0, t1),
        final_third_entries=territory.final_third_entries(events, team, t0, t1),
        high_recoveries=territory.high_recoveries(events, team, t0, t1),
        recoveries=territory.recoveries(events, team, t0, t1),
    )


def window_stats(
    events: Sequence[Event], end_second: int, window: str, teams: Sequence[str], with_players: bool = True
) -> WindowStats:
    """`events` must be in seq order and contain only events received so far."""
    t0, t1 = window_bounds(window, end_second)
    return window_stats_between(events, t0, t1, teams, window=window, with_players=with_players)


def window_stats_between(
    events: Sequence[Event],
    t0: int | None,
    t1: int,
    teams: Sequence[str],
    window: str = "custom",
    with_players: bool = True,
) -> WindowStats:
    """Stats for the window (t0, t1]. `events` must be in seq order; events after t1 are ignored."""
    # Keep one event before the window: its control interval may run into the window.
    seconds = [e.match_second for e in events]
    start = 0 if t0 is None else max(0, bisect_right(seconds, t0) - 1)
    scoped = events[start : bisect_right(seconds, t1)]
    poss = {
        "seconds": possession.possession_seconds(scoped, t0, t1, teams),
        "pct": possession.possession_pct(scoped, t0, t1, teams),
    }
    return WindowStats(
        window=window,
        start_second=t0,
        end_second=t1,
        teams={team: team_stats(scoped, team, t0, t1, poss) for team in teams},
        players={team: player_table(scoped, team, t0, t1) for team in teams} if with_players else {},
    )


def all_windows(events: Sequence[Event], end_second: int, teams: Sequence[str]) -> dict[str, WindowStats]:
    return {w: window_stats(events, end_second, w, teams) for w in WINDOWS}
