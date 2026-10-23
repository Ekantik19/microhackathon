"""Constants and shared helpers for the statistics engine. Definitions are documented in docs/metrics.md."""

from collections.abc import Iterable, Sequence

from app.models.events import PITCH_LENGTH, PITCH_WIDTH, Event, EventType

__all__ = ["PITCH_LENGTH", "PITCH_WIDTH"]

FINAL_THIRD_X = 70.0
HIGH_REGION_X = 70.0
WINDOWS: dict[str, int | None] = {"last_5": 300, "last_10": 600, "full": None}

# A team wins the ball with one of these (a tackle only when it is won).
BALL_WIN_TYPES = {EventType.RECOVERY, EventType.INTERCEPTION, EventType.TACKLE}
# "Involvement" counts these recorded on-ball actions. It is not a count of touches.
ON_BALL_TYPES = {
    EventType.KICKOFF,
    EventType.PASS,
    EventType.CARRY,
    EventType.SHOT,
    EventType.TACKLE,
    EventType.INTERCEPTION,
    EventType.RECOVERY,
    EventType.CLEARANCE,
}


def in_window(e: Event, t0: int | None, t1: int) -> bool:
    """Windows are (t0, t1]: exclusive start, inclusive end. t0=None means from kickoff."""
    return (t0 is None or e.match_second > t0) and e.match_second <= t1


def select(events: Iterable[Event], t0: int | None, t1: int) -> list[Event]:
    return [e for e in events if in_window(e, t0, t1)]


def window_bounds(window: str, end_second: int) -> tuple[int | None, int]:
    length = WINDOWS[window]
    return (None if length is None else end_second - length), end_second


def pct(numerator: float, denominator: float) -> int | None:
    """Whole-number percentage, rounded half up. None ("n/a") when the denominator is 0."""
    if denominator == 0:
        return None
    return int(100 * numerator / denominator + 0.5)


def ids(events: Sequence[Event]) -> list[str]:
    return [e.event_id for e in events]


def is_ball_win(e: Event) -> bool:
    return e.event_type in BALL_WIN_TYPES and (e.event_type != EventType.TACKLE or e.outcome == "won")


def is_final_third_entry(e: Event) -> bool:
    """A completed pass or a carry that starts before x = 70 and ends at or beyond it."""
    moves = (e.event_type == EventType.PASS and e.outcome == "complete") or e.event_type == EventType.CARRY
    return (
        moves and e.x is not None and e.end_x is not None and e.x < FINAL_THIRD_X and e.end_x >= FINAL_THIRD_X
    )
