"""Inputs and outputs of the AI layer. A FactPack contains only verified values computed by code."""

from pydantic import BaseModel, Field

from app.models.insights import KeyMoment, SupportingStat


class Fact(BaseModel):
    key: str  # e.g. possession_pct, shots, window_minutes
    label: str  # human label, e.g. "Possession (last 5)"
    team: str | None = None  # team name, or None for context facts
    value: float | int | None
    unit: str = ""
    event_ids: list[str] = Field(default_factory=list)


class Trigger(BaseModel):
    detection_id: str
    type: str  # pattern name or key moment
    kind: str  # pattern | key_moment
    minute: int
    second: int
    match_second: int
    team: str | None = None  # team name
    opponent: str | None = None
    player: str | None = None  # player name
    event_ids: list[str] = Field(default_factory=list)


class RecentEvent(BaseModel):
    event_id: str
    minute: int
    type: str
    team: str
    player: str | None = None
    outcome: str | None = None


class DetectionSummary(BaseModel):
    pattern: str
    team: str | None
    since_minute: int
    minute: int


class FactPack(BaseModel):
    match_id: str
    trigger: Trigger
    score_before: dict[str, int]  # by team name
    score_after: dict[str, int]
    window: str = "last_5"
    facts: list[Fact]
    detections: list[DetectionSummary]
    recent_events: list[RecentEvent]
    allowed_names: list[str]
    event_seconds: dict[str, int]  # every citable event_id → its match_second
    clock_second: int


class RecapMoment(BaseModel):
    minute: int
    type: str
    team: str | None = None
    player: str | None = None
    event_ids: list[str] = Field(default_factory=list)


class RecapFactPack(BaseModel):
    match_id: str
    scope: str  # half_time | full_time | now
    minute: int
    clock_second: int
    score: dict[str, int]
    home: str
    away: str
    key_moments: list[RecapMoment]
    detections: list[DetectionSummary]
    facts: list[Fact]  # full-match team stats up to the clock
    allowed_names: list[str]
    event_seconds: dict[str, int]


class InsightDraft(BaseModel):
    headline: str
    body: str
    supporting_stats: list[SupportingStat] = Field(default_factory=list)
    cited_event_ids: list[str] = Field(default_factory=list)


class RecapDraft(BaseModel):
    body: str
    key_moments: list[KeyMoment] = Field(default_factory=list)
    stats_summary: list[SupportingStat] = Field(default_factory=list)
    cited_event_ids: list[str] = Field(default_factory=list)
