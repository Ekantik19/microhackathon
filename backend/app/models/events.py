"""Match event schema (INGEST). One `Event` per row of `data/matches/{match_id}.jsonl`.

Coordinates are pitch metres (x 0-105, y 0-68), normalized so the acting team (`team_id`) always attacks
toward x = 105. `match_second` is continuous across halves: the 2nd half starts at 2700 + 1st-half stoppage.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0


class EventType(StrEnum):
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"
    KICKOFF = "kickoff"
    PASS = "pass"
    CARRY = "carry"
    SHOT = "shot"
    GOAL = "goal"
    TACKLE = "tackle"
    INTERCEPTION = "interception"
    RECOVERY = "recovery"
    PRESSURE = "pressure"
    CLEARANCE = "clearance"
    FOUL = "foul"
    CARD = "card"
    OUT_OF_PLAY = "out_of_play"
    SUBSTITUTION = "substitution"


ALLOWED_OUTCOMES: dict[EventType, set[str]] = {
    EventType.PASS: {"complete", "incomplete"},
    EventType.SHOT: {"goal", "saved", "off_target", "blocked"},
    EventType.TACKLE: {"won", "lost"},
    EventType.CARD: {"yellow", "red"},
}

Coord = Field(default=None, ge=0.0, le=PITCH_LENGTH)
CoordY = Field(default=None, ge=0.0, le=PITCH_WIDTH)


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str
    event_id: str
    seq: int = Field(ge=0)
    period: Literal[1, 2]
    match_second: int = Field(ge=0)
    minute: int = Field(ge=0)
    second: int = Field(ge=0, le=59)
    team_id: str
    player_id: str | None = None
    event_type: EventType
    outcome: str | None = None
    x: float | None = Coord
    y: float | None = CoordY
    end_x: float | None = Coord
    end_y: float | None = CoordY
    possession_team_id: str | None = None
    possession_id: int = Field(ge=0)
    # For passes: the receiver when complete. For substitutions: the player coming on (player_id goes off).
    recipient_id: str | None = None
    shot_outcome: str | None = None
    xg: float | None = Field(default=None, ge=0.0, le=1.0)
    under_pressure: bool = False
    in_play: bool = True
    related_event_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_consistency(self) -> "Event":
        allowed = ALLOWED_OUTCOMES.get(self.event_type)
        if allowed is not None and self.outcome not in allowed:
            raise ValueError(
                f"{self.event_type} outcome must be one of {sorted(allowed)}, got {self.outcome!r}"
            )
        if self.event_type == EventType.SHOT:
            if self.xg is None or self.shot_outcome != self.outcome:
                raise ValueError("shot needs xg and shot_outcome equal to outcome")
        elif self.xg is not None or self.shot_outcome is not None:
            raise ValueError("only shots carry xg / shot_outcome")
        return self


def display_clock(match_second: int, period: int, second_half_start: int) -> tuple[int, int]:
    """Broadcast-style clock. 1st-half stoppage shows 45:xx-47:xx; the 2nd half restarts the display at 45:00."""
    shown = match_second if period == 1 else 2700 + (match_second - second_half_start)
    return shown // 60, shown % 60
