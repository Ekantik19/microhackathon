"""Event sources (INGEST). Everything downstream consumes `Event` objects from an `EventSource` and never assumes
where they come from. `FabricEventSource` (Microsoft Fabric Eventstream) is added in Phase 11."""

import json
from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from typing import Protocol

from app.models.events import Event


class EventSource(Protocol):
    name: str

    def events(self, match_id: str) -> AsyncIterator[Event]: ...


class LocalSyntheticEventSource:
    """Reads the committed synthetic match from `data/matches/{match_id}.jsonl`."""

    name = "local"

    def __init__(self, data_dir: Path):
        self.matches_dir = data_dir / "matches"

    async def events(self, match_id: str) -> AsyncIterator[Event]:
        path = self.matches_dir / f"{match_id}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"no event file for match {match_id!r}")
        with path.open() as f:
            for line in f:
                if line.strip():
                    yield Event.model_validate(json.loads(line))


class InMemoryEventSource:
    """Serves a fixed list of events. Used by tests and by adapters that load a whole match up front."""

    name = "memory"

    def __init__(self, events: Iterable[Event]):
        self._events = list(events)

    async def events(self, match_id: str) -> AsyncIterator[Event]:
        for e in self._events:
            if e.match_id == match_id:
                yield e
