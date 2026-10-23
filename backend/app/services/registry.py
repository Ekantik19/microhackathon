"""One simulator per match, created on first use and kept for the life of the API process."""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from app.events.catalog import list_match_ids, load_meta
from app.events.simulator import Hook, Simulator
from app.events.sources import EventSource, LocalSyntheticEventSource
from app.services.bus import EventBus
from app.services.store import MatchStore

log = logging.getLogger(__name__)

# Builds the hooks (detectors, orchestrator) for a new simulator. Added by later phases.
HookFactory = Callable[[Simulator], list[Hook]]


class UnknownMatch(LookupError):
    pass


class MatchRegistry:
    def __init__(
        self,
        data_dir: Path,
        bus: EventBus,
        store: MatchStore,
        source: EventSource | None = None,
        hook_factories: list[HookFactory] | None = None,
    ):
        self.data_dir = data_dir
        self.bus = bus
        self.store = store
        self.source = source or LocalSyntheticEventSource(data_dir)
        self.hook_factories = list(hook_factories or [])
        self._sims: dict[str, Simulator] = {}
        self._demo_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def match_ids(self) -> list[str]:
        return list_match_ids(self.data_dir)

    async def get(self, match_id: str) -> Simulator:
        if match_id in self._sims:
            return self._sims[match_id]
        async with self._lock:
            if match_id not in self._sims:
                if match_id not in self.match_ids():
                    raise UnknownMatch(match_id)
                sim = Simulator(load_meta(self.data_dir, match_id), self.source, self.bus)
                for factory in self.hook_factories:
                    sim.hooks.extend(factory(sim))
                await sim.load()
                self._sims[match_id] = sim
        return self._sims[match_id]

    def start_demo(self, sim: Simulator) -> None:
        self.cancel_demo(sim.match_id)
        self._demo_tasks[sim.match_id] = asyncio.create_task(sim.run_demo(), name=f"demo-{sim.match_id}")

    def cancel_demo(self, match_id: str) -> None:
        task = self._demo_tasks.pop(match_id, None)
        if task and not task.done():
            task.cancel()

    def demo_running(self, match_id: str) -> bool:
        task = self._demo_tasks.get(match_id)
        return task is not None and not task.done()

    async def shutdown(self) -> None:
        for match_id in list(self._demo_tasks):
            self.cancel_demo(match_id)
        for sim in self._sims.values():
            await sim.pause()
