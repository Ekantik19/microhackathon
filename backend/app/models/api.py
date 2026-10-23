"""Request and response bodies for the HTTP API."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.events import Event
from app.models.meta import PeriodMeta, PlayerMeta, TeamMeta
from app.models.stats import WindowStats

Speed = Literal[1, 5, 10, 30, 60]
WindowName = Literal["last_5", "last_10", "full"]
Mode = Literal["casual", "tactical"]


class MatchSummary(BaseModel):
    match_id: str
    competition: str
    venue: str
    kickoff: str
    home_team_id: str
    away_team_id: str
    teams: list[TeamMeta]


class MatchInfo(MatchSummary):
    """Match metadata. The final score is deliberately not exposed: the UI must not see the future."""

    squads: dict[str, list[PlayerMeta]]
    periods: list[PeriodMeta]


class SimState(BaseModel):
    match_id: str
    status: Literal["idle", "running", "paused", "finished"]
    speed: int
    clock_second: int
    minute: int
    second: int
    period: int
    score: dict[str, int]
    events_emitted: int
    events_total: int


class StatsResponse(BaseModel):
    match_id: str
    clock_second: int
    score: dict[str, int]
    stats: WindowStats


class TimelineItem(BaseModel):
    kind: Literal["event", "detection"]
    id: str
    match_second: int
    minute: int
    second: int
    period: int
    type: str
    team_id: str | None
    player_id: str | None = None
    label: str
    start_second: int | None = None  # detections: start of the window the rule looked at
    rule_strength: float | None = None  # detections: "Signal strength (rule-based)", never a probability


class Timeline(BaseModel):
    match_id: str
    clock_second: int
    items: list[TimelineItem]


class EventsPage(BaseModel):
    match_id: str
    events: list[Event]
    next_since_seq: int


class StartBody(BaseModel):
    speed: Speed | None = None


class SpeedBody(BaseModel):
    speed: Speed


class SeekBody(BaseModel):
    match_second: int = Field(ge=0)


class RecapRequest(BaseModel):
    mode: Mode = "casual"
    scope: Literal["half_time", "full_time", "now"] = "now"
