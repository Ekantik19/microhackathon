"""Detected patterns and key moments (INTERPRET). Filled by the detectors in Phase 8."""

from typing import Any

from pydantic import BaseModel, Field

RULE_STRENGTH_NOTE = "Rule-derived: average of each metric's ratio to its threshold, capped at 1. Not a calibrated probability."


class Detection(BaseModel):
    detection_id: str
    match_id: str
    pattern: str  # sustained_pressure | momentum_shift | high_press_sequence | goal | big_chance | card | half_time | full_time
    kind: str = "pattern"  # pattern | key_moment
    team_id: str | None = None
    start_second: int
    end_second: int
    minute: int
    second: int
    period: int
    rule_strength: float | None = None  # shown as "Signal strength (rule-based)", never as confidence
    rule_strength_note: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    event_ids: list[str] = Field(default_factory=list)
