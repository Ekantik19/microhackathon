"""MatchState: incremental, idempotent ingestion of events as the replay emits them."""

from bisect import insort

from app.analytics.definitions import WINDOWS
from app.analytics.score import score_at
from app.analytics.windows import window_stats
from app.models.events import Event, EventType
from app.models.stats import WindowStats


class MatchState:
    def __init__(self, match_id: str, teams: list[str]):
        self.match_id = match_id
        self.teams = teams
        self.reset()

    def reset(self) -> None:
        self.events: list[Event] = []
        self._seen: set[str] = set()
        self.clock = 0  # replay clock in match seconds; may run ahead of the last event
        self.period = 1
        self.finished = False

    def ingest(self, event: Event) -> bool:
        """Add an event. Returns False (and changes nothing) if this event_id was already ingested."""
        if event.match_id != self.match_id or event.event_id in self._seen:
            return False
        self._seen.add(event.event_id)
        if self.events and event.seq < self.events[-1].seq:
            insort(self.events, event, key=lambda e: e.seq)
        else:
            self.events.append(event)
        self.clock = max(self.clock, event.match_second)
        self.period = event.period
        if event.event_type == EventType.PERIOD_END and event.period == 2:
            self.finished = True
        return True

    def advance_clock(self, match_second: int) -> None:
        self.clock = max(self.clock, match_second)

    def score(self) -> dict[str, int]:
        return {team: int(m.value or 0) for team, m in score_at(self.events, self.clock, self.teams).items()}

    def last_event(self) -> Event | None:
        return self.events[-1] if self.events else None

    def window(self, window: str, with_players: bool = True) -> WindowStats:
        return window_stats(self.events, self.clock, window, self.teams, with_players=with_players)

    def windows(self) -> dict[str, WindowStats]:
        return {w: self.window(w) for w in WINDOWS}
