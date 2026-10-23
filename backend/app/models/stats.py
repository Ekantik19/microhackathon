"""Statistics output models (INTERPRET). Every metric carries its value and the event IDs that produced it."""

from pydantic import BaseModel, Field


class Metric(BaseModel):
    value: float | int | None
    event_ids: list[str] = Field(default_factory=list)


class TeamStats(BaseModel):
    team_id: str
    possession_seconds: Metric
    possession_pct: Metric
    shots: Metric
    shots_on_target: Metric
    xg: Metric
    passes_attempted: Metric
    passes_completed: Metric
    pass_accuracy: Metric
    final_third_entries: Metric
    high_recoveries: Metric
    recoveries: Metric


class PlayerStats(BaseModel):
    player_id: str
    team_id: str
    involvement: Metric
    passes_attempted: Metric
    passes_completed: Metric
    pass_accuracy: Metric
    shots: Metric
    xg: Metric
    recoveries: Metric
    final_third_entries: Metric


class WindowStats(BaseModel):
    window: str  # last_5 | last_10 | full
    start_second: int | None  # exclusive lower bound; None for the full match
    end_second: int  # inclusive upper bound (the replay clock)
    teams: dict[str, TeamStats]
    players: dict[str, list[PlayerStats]]
