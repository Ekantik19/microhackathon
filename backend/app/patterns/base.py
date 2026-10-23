"""Shared pieces for detectors. A detector is a small class with `evaluate(ctx, event) -> Detection | None`.

`ctx` wraps the MatchState and caches the window stats every detector needs for this event, so each window is
computed once per event no matter how many detectors read it."""

from functools import cached_property
from typing import Protocol

from app.analytics.state import MatchState
from app.analytics.windows import window_stats_between
from app.models.detections import Detection
from app.models.events import Event
from app.models.stats import WindowStats


def strength_note(scale: float) -> str:
    return (
        f"Rule-derived: average of each metric's ratio to {scale:g}× its threshold, capped at 1. "
        "Not a calibrated probability."
    )


def rule_strength(ratios: list[float]) -> float:
    return round(sum(min(1.0, max(0.0, r)) for r in ratios) / len(ratios), 2)


class Context:
    """Per-event view of the match for detectors. Everything here is at or before the replay clock."""

    def __init__(self, state: MatchState, event: Event, window_seconds: int = 300):
        self.state = state
        self.event = event
        self.t = event.match_second
        self.window_seconds = window_seconds

    @cached_property
    def last_window(self) -> WindowStats:
        return self._window(self.t)

    @cached_property
    def previous_window(self) -> WindowStats:
        return self._window(self.t - self.window_seconds)

    def _window(self, end: int) -> WindowStats:
        return window_stats_between(
            self.state.events, end - self.window_seconds, end, self.state.teams, with_players=False
        )

    def events_since(self, t0: int) -> list[Event]:
        """Received events with match_second in (t0, t], scanning back from the newest."""
        out = []
        for e in reversed(self.state.events):
            if e.match_second <= t0:
                break
            out.append(e)
        return out[::-1]


class Detector(Protocol):
    name: str

    def evaluate(self, ctx: Context, event: Event) -> Detection | None: ...

    def reset(self) -> None: ...


class Cooldown:
    """Remembers when a rule last fired, per key (a team, or one shared key)."""

    def __init__(self, seconds: int):
        self.seconds = seconds
        self._last: dict[str, int] = {}

    def ready(self, key: str, t: int) -> bool:
        last = self._last.get(key)
        return last is None or t - last >= self.seconds

    def fire(self, key: str, t: int) -> None:
        self._last[key] = t

    def reset(self) -> None:
        self._last.clear()
