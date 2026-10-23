"""Real-time replay simulator (INGEST → INTERPRET), one per match.

It buffers the whole match from an `EventSource`, then runs a simulated clock and emits each event when the clock
reaches its `match_second`. For every emitted event, in order:

1. `MatchState` ingests it (stats are recomputed by code, synchronously),
2. the bus gets an `event` message and a `stats` message,
3. hooks run (pattern detectors, and the orchestrator that schedules AI work in background tasks).

Stats never wait for AI. The emitted sequence depends only on the events and the control sequence, never on wall
time, so replays are deterministic. Dead-ball gaps are compressed so the demo does not stall.

Wall time and sleeping are injectable (`now`, `sleep`) so tests can run a whole match instantly.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.analytics.state import MatchState
from app.events.sources import EventSource
from app.models.events import Event, EventType
from app.models.meta import MatchMeta
from app.services.bus import EventBus
from app.services.payloads import clock_fields, stats_payload

log = logging.getLogger(__name__)

SPEEDS = (1, 5, 10, 30, 60)
MAX_DEAD_BALL_SECONDS = 2  # a stoppage longer than this (in match seconds) is skipped
TICK_SECONDS = 0.1

# Called after every ingested event. `replaying` is True while seek fast-forwards through skipped events.
Hook = Callable[["Simulator", Event, bool], Awaitable[None]]


class Simulator:
    def __init__(
        self,
        meta: MatchMeta,
        source: EventSource,
        bus: EventBus,
        *,
        hooks: list[Hook] | None = None,
        tick: float = TICK_SECONDS,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ):
        self.meta = meta
        self.match_id = meta.match_id
        self.source = source
        self.bus = bus
        self.hooks = list(hooks or [])
        self.tick = tick
        self._now = now
        self._sleep = sleep
        self.state = MatchState(meta.match_id, [t.team_id for t in meta.teams])
        self.events: list[Event] = []
        self.status = "idle"  # idle | running | paused | finished
        self.speed = 10
        self.clock = 0.0
        self._cursor = 0
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    # --- setup ---

    async def load(self) -> None:
        """Buffer the full match from the source, in seq order."""
        self.events = sorted([e async for e in self.source.events(self.match_id)], key=lambda e: e.seq)
        if not self.events:
            raise ValueError(f"source {self.source.name!r} returned no events for {self.match_id!r}")
        log.info(
            "simulator loaded match=%s events=%d source=%s", self.match_id, len(self.events), self.source.name
        )

    @property
    def end_second(self) -> int:
        return self.events[-1].match_second if self.events else 0

    def received(self) -> list[Event]:
        """Events emitted so far. Never anything after the replay clock."""
        return self.state.events

    def snapshot(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "status": self.status,
            "speed": self.speed,
            **clock_fields(int(self.clock), self.state.period, self.meta.second_half_start),
            "score": self.state.score(),
            "events_emitted": len(self.state.events),
            "events_total": len(self.events),
        }

    def _publish_status(self) -> None:
        self.bus.publish("sim_status", self.match_id, self.snapshot())

    # --- controls ---

    async def start(self, speed: int | None = None) -> None:
        if speed is not None:
            self._check_speed(speed)
            self.speed = speed
        if self.status == "finished":
            await self.reset()
        if self.status != "running":
            self.status = "running"
            self._ensure_task()
        self._publish_status()

    async def pause(self) -> None:
        if self.status == "running":
            self.status = "paused"
        self._publish_status()

    async def resume(self) -> None:
        if self.status == "paused":
            self.status = "running"
            self._ensure_task()
        self._publish_status()

    async def set_speed(self, speed: int) -> None:
        self._check_speed(speed)
        self.speed = speed
        self._publish_status()

    async def reset(self) -> None:
        async with self._lock:
            self.status = "idle"
            self.clock = 0.0
            self._cursor = 0
            self.state.reset()
        self._publish_status()

    async def seek(self, match_second: int) -> None:
        """Rebuild state from scratch with every event up to `match_second`. Hooks run with replaying=True."""
        target = max(0, min(int(match_second), self.end_second))
        async with self._lock:
            self.state.reset()
            self._cursor = 0
            while self._cursor < len(self.events) and self.events[self._cursor].match_second <= target:
                event = self.events[self._cursor]
                self._cursor += 1
                self.state.ingest(event)
                for hook in self.hooks:
                    await hook(self, event, True)
            self.clock = float(target)
            self.state.advance_clock(target)
            if self._cursor >= len(self.events):
                self.status = "finished"
            elif self.status in ("idle", "finished"):
                self.status = "paused"
        self.bus.publish("stats", self.match_id, stats_payload(self.state, self.meta.second_half_start))
        self._publish_status()

    @staticmethod
    def _check_speed(speed: int) -> None:
        if speed not in SPEEDS:
            raise ValueError(f"speed must be one of {SPEEDS}")

    # --- the clock ---

    def _ensure_task(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name=f"simulator-{self.match_id}")

    async def _run(self) -> None:
        last = self._now()
        while self.status == "running":
            await self._sleep(self.tick)
            current = self._now()
            elapsed, last = current - last, current
            if self.status != "running":
                break
            await self.advance(elapsed * self.speed)

    async def advance(self, match_seconds: float) -> list[Event]:
        """Move the simulated clock forward and emit every event that is now due. Returns the emitted events."""
        emitted: list[Event] = []
        async with self._lock:
            if self._cursor >= len(self.events):
                return emitted
            last = self.state.last_event()
            upcoming = self.events[self._cursor]
            if (
                last is not None
                and not last.in_play
                and upcoming.match_second - self.clock > MAX_DEAD_BALL_SECONDS
            ):
                self.clock = float(upcoming.match_second - MAX_DEAD_BALL_SECONDS)  # compress the stoppage
            self.clock = min(self.clock + match_seconds, float(self.end_second))
            while self._cursor < len(self.events) and self.events[self._cursor].match_second <= self.clock:
                event = self.events[self._cursor]
                self._cursor += 1
                await self._emit(event)
                emitted.append(event)
            self.state.advance_clock(int(self.clock))
            if self._cursor >= len(self.events):
                self.status = "finished"
        if self.status == "finished" and emitted:
            self._publish_status()
        return emitted

    async def _emit(self, event: Event) -> None:
        if not self.state.ingest(event):
            return
        self.bus.publish("event", self.match_id, event.model_dump(mode="json"))
        self.bus.publish("stats", self.match_id, stats_payload(self.state, self.meta.second_half_start))
        if event.event_type == EventType.PERIOD_END:
            self._publish_status()
        for hook in self.hooks:
            await hook(self, event, False)

    async def play_until(self, match_second: int) -> None:
        """Wait (in wall time) until the running clock reaches `match_second` or the match ends."""
        while self.clock < match_second and self.status == "running":
            await self._sleep(self.tick)

    # --- demo mode ---

    def at(self, minute: int, second: int = 0) -> int:
        """Display clock → match_second for this match (minutes ≥ 45 are 2nd-half times)."""
        if minute < 45:
            return minute * 60 + second
        return self.meta.second_half_start + (minute - 45) * 60 + second

    async def run_demo(self) -> None:
        """Scripted walkthrough of the storyline in well under 90 s of wall time at 30x:
        a few minutes from kickoff, then 60'-70:30 (sustained pressure and the equaliser), 76'-80' (momentum
        shift), and 85:30 to full time (the 86' big chance; the full-time recap follows from the full_time key moment)."""
        await self.reset()
        await self.start(speed=30)
        await self.play_until(self.at(3))
        for start, end in [
            (self.at(60), self.at(70, 30)),
            (self.at(76), self.at(80)),
            (self.at(85, 30), self.end_second),
        ]:
            await self.seek(start)
            await self.start(speed=30)
            await self.play_until(end)
