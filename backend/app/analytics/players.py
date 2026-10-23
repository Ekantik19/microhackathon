"""Per-player statistics. "Involvement" counts recorded on-ball actions; it is never called touches."""

from collections.abc import Sequence

from app.analytics.definitions import ON_BALL_TYPES, ids, is_ball_win, is_final_third_entry, pct, select
from app.models.events import Event, EventType
from app.models.stats import Metric, PlayerStats


def player_stats(events: Sequence[Event], player_id: str, team: str, t0: int | None, t1: int) -> PlayerStats:
    mine = [e for e in select(events, t0, t1) if e.player_id == player_id and e.team_id == team]
    on_ball = [e for e in mine if e.event_type in ON_BALL_TYPES]
    passes = [e for e in mine if e.event_type == EventType.PASS]
    completed = [e for e in passes if e.outcome == "complete"]
    shots = [e for e in mine if e.event_type == EventType.SHOT]
    wins = [e for e in mine if is_ball_win(e)]
    entries = [e for e in mine if is_final_third_entry(e)]
    return PlayerStats(
        player_id=player_id,
        team_id=team,
        involvement=Metric(value=len(on_ball), event_ids=ids(on_ball)),
        passes_attempted=Metric(value=len(passes), event_ids=ids(passes)),
        passes_completed=Metric(value=len(completed), event_ids=ids(completed)),
        pass_accuracy=Metric(value=pct(len(completed), len(passes)), event_ids=ids(passes)),
        shots=Metric(value=len(shots), event_ids=ids(shots)),
        xg=Metric(value=round(sum(e.xg or 0.0 for e in shots), 2), event_ids=ids(shots)),
        recoveries=Metric(value=len(wins), event_ids=ids(wins)),
        final_third_entries=Metric(value=len(entries), event_ids=ids(entries)),
    )


def player_table(events: Sequence[Event], team: str, t0: int | None, t1: int) -> list[PlayerStats]:
    """Every player of `team` with at least one recorded event in the window, most involved first."""
    window = select(events, t0, t1)
    player_ids = sorted({e.player_id for e in window if e.team_id == team and e.player_id is not None})
    table = [player_stats(window, p, team, t0, t1) for p in player_ids]
    return sorted(table, key=lambda p: (-int(p.involvement.value or 0), p.player_id))
