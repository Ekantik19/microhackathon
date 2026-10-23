"""AI-written (or template) insights and recaps (EXPLAIN + PERSONALIZE). Produced from FactPacks in Phase 9."""

from datetime import datetime

from pydantic import BaseModel, Field


class SupportingStat(BaseModel):
    label: str
    value: float | int | str
    unit: str = ""


class ValidatorResult(BaseModel):
    passed: bool
    violations: list[str] = Field(default_factory=list)


class GenerationAttempt(BaseModel):
    """One draft and what the grounding validator said about it (shown as the "Grounding check")."""

    generated_by: str  # foundry | mock | template
    passed: bool
    violations: list[str] = Field(default_factory=list)


class Insight(BaseModel):
    insight_id: str
    match_id: str
    trigger_id: str  # detection_id that caused it
    mode: str  # casual | tactical
    type: str  # pattern | key_moment
    minute: int
    match_second: int
    headline: str
    body: str
    supporting_stats: list[SupportingStat] = Field(default_factory=list)
    cited_event_ids: list[str] = Field(default_factory=list)
    generated_by: str  # foundry | mock | template
    model: str | None = None
    latency_ms: int | None = None
    validator: ValidatorResult
    attempts: list[GenerationAttempt] = Field(default_factory=list)
    facts: list[SupportingStat] = Field(default_factory=list)  # the verified facts the text was written from
    created_at: datetime


class KeyMoment(BaseModel):
    minute: int
    type: str
    text: str


class Recap(BaseModel):
    recap_id: str
    match_id: str
    scope: str  # half_time | full_time | now
    mode: str
    minute: int
    match_second: int
    body: str
    key_moments: list[KeyMoment] = Field(default_factory=list)
    stats_summary: list[SupportingStat] = Field(default_factory=list)
    generated_by: str
    validator: ValidatorResult
    attempts: list[GenerationAttempt] = Field(default_factory=list)
    cited_event_ids: list[str] = Field(default_factory=list)
    created_at: datetime
