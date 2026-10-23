"""Orchestrator (EXPLAIN + PERSONALIZE): turns detections into insights and recaps.

- Pattern detection → live insight. Goal / big chance / card → key-moment explanation. Half-time / full-time → recap.
- The FactPack is built synchronously at the moment of the detection, so background AI work can never see later events.
- Generation runs in background tasks (stats never wait for AI), for every visible mode, with `insight_pending`
  published first. Results are cached by (match_id, trigger_id, mode) and survive resets and seeks.
- An epoch counter per match is bumped on every reset/seek: results from an older epoch fill the cache but are not
  added to the live feed.
"""

import asyncio
import logging
from datetime import UTC, datetime

from app.ai.factpack import build_factpack, build_recap_factpack
from app.ai.fallback import TemplateFallback
from app.ai.generate import generate_insight, generate_recap
from app.ai.models import FactPack, RecapFactPack
from app.ai.modes import ModeConfig, visible_modes
from app.ai.providers import AIProvider, short
from app.events.simulator import Hook, Simulator
from app.models.detections import Detection
from app.models.insights import Insight, Recap, SupportingStat
from app.services.bus import EventBus
from app.services.store import MatchStore

log = logging.getLogger(__name__)
RECAP_PATTERNS = {"half_time", "full_time"}


class RecapNotAvailable(ValueError):
    pass


class Orchestrator:
    def __init__(
        self,
        store: MatchStore,
        bus: EventBus,
        provider: AIProvider,
        modes: dict[str, ModeConfig],
        timeout: float = 8.0,
        max_concurrency: int = 4,
    ):
        self.store = store
        self.bus = bus
        self.provider = provider
        self.fallback = TemplateFallback()
        self.modes = modes
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._epoch: dict[str, int] = {}
        self._tasks: set[asyncio.Task] = set()

    @property
    def live_modes(self) -> list[str]:
        return visible_modes(self.modes)

    # --- wiring ---

    def attach(self, sim: Simulator) -> list[Hook]:
        """Hook factory: registers the reset callback. Detections arrive via `on_detection`, not via hooks."""
        sim.on_reset.append(lambda: self._reset(sim.match_id))
        return []

    def _reset(self, match_id: str) -> None:
        self._epoch[match_id] = self._epoch.get(match_id, 0) + 1
        self.store.clear_insights(match_id)

    def on_detection(self, sim: Simulator, detection: Detection, replaying: bool) -> None:
        match_id = sim.match_id
        detections = self.store.detections(match_id)
        epoch = self._epoch.get(match_id, 0)
        if detection.pattern in RECAP_PATTERNS:
            recap_fp = build_recap_factpack(
                sim.state, sim.meta, detections, detection.pattern, detection.end_second
            )
            for mode in self.live_modes:
                self._spawn(self._recap_task(recap_fp, self.modes[mode], epoch))
            return
        fp = build_factpack(sim.state, detection, sim.meta, detections)
        for mode in self.live_modes:
            if not replaying:
                self.bus.publish(
                    "insight_pending",
                    match_id,
                    {
                        "trigger_id": detection.detection_id,
                        "mode": mode,
                        "minute": detection.minute,
                        "type": detection.pattern,
                    },
                )
            self._spawn(self._insight_task(fp, self.modes[mode], epoch))

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def idle(self) -> None:
        """Wait for all background generation (used by tests and scripts)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    # --- insights ---

    async def _insight_task(self, fp: FactPack, mode: ModeConfig, epoch: int) -> None:
        try:
            insight = await self.insight_for(fp, mode)
            if self._epoch.get(fp.match_id, 0) == epoch:
                self.store.add_insight(insight)
                self.bus.publish("insight", fp.match_id, insight.model_dump(mode="json"))
        except Exception:  # never let one bad insight break the replay
            log.exception("insight generation failed trigger=%s mode=%s", fp.trigger.detection_id, mode.name)

    async def insight_for(self, fp: FactPack, mode: ModeConfig) -> Insight:
        key = (fp.match_id, fp.trigger.detection_id, mode.name)
        cached = self.store.insight_cache.get(key)
        if cached is not None:
            return cached
        async with self._semaphore:
            draft, generated_by, result, attempts, latency = await generate_insight(
                self.provider, self.fallback, fp, mode, self.timeout
            )
        insight = Insight(
            insight_id=f"{fp.match_id}:{fp.trigger.detection_id}:{mode.name}",
            match_id=fp.match_id,
            trigger_id=fp.trigger.detection_id,
            mode=mode.name,
            type="pattern" if fp.trigger.kind == "pattern" else "key_moment",
            minute=fp.trigger.minute,
            match_second=fp.trigger.match_second,
            headline=draft.headline,
            body=draft.body,
            supporting_stats=draft.supporting_stats,
            cited_event_ids=draft.cited_event_ids,
            generated_by=generated_by,
            model=self.provider.model if generated_by == self.provider.name else None,
            latency_ms=latency,
            validator=result,
            attempts=attempts,
            facts=[
                SupportingStat(
                    label=f"{f.label} · {short(f.team)}" if f.team else f.label,
                    value=f.value,
                    unit=f.unit,
                )
                for f in fp.facts
                if f.value is not None and f.key != "window_minutes"
            ],
            created_at=datetime.now(UTC),
        )
        self.store.insight_cache[key] = insight
        return insight

    # --- recaps ---

    async def _recap_task(self, fp: RecapFactPack, mode: ModeConfig, epoch: int) -> None:
        try:
            recap = await self.recap_for(fp, mode)
            if self._epoch.get(fp.match_id, 0) == epoch:
                self.store.add_recap(recap)
                self.bus.publish("recap", fp.match_id, recap.model_dump(mode="json"))
        except Exception:
            log.exception("recap generation failed scope=%s mode=%s", fp.scope, mode.name)

    async def recap_for(self, fp: RecapFactPack, mode: ModeConfig) -> Recap:
        key = (fp.match_id, f"recap:{fp.scope}:{fp.clock_second}", mode.name)
        cached = self.store.recap_cache.get(key)
        if cached is not None:
            return cached
        async with self._semaphore:
            draft, generated_by, result, attempts = await generate_recap(
                self.provider, self.fallback, fp, mode, self.timeout
            )
        recap = Recap(
            recap_id=f"{fp.match_id}:recap:{fp.scope}:{fp.clock_second}:{mode.name}",
            match_id=fp.match_id,
            scope=fp.scope,
            mode=mode.name,
            minute=fp.minute,
            match_second=fp.clock_second,
            body=draft.body,
            key_moments=draft.key_moments,
            stats_summary=draft.stats_summary,
            generated_by=generated_by,
            validator=result,
            attempts=attempts,
            cited_event_ids=draft.cited_event_ids,
            created_at=datetime.now(UTC),
        )
        self.store.recap_cache[key] = recap
        return recap

    async def recap_now(self, sim: Simulator, mode_name: str, scope: str) -> Recap:
        """On-demand recap (POST /generate-recap). Uses only events received so far."""
        clock = sim.state.clock
        if not sim.state.events:
            raise RecapNotAvailable("The replay has not started yet.")
        end = {"half_time": sim.meta.second_half_start, "full_time": sim.end_second}.get(scope, clock)
        if clock < end:
            raise RecapNotAvailable(f"The replay has not reached {scope.replace('_', ' ')} yet.")
        fp = build_recap_factpack(sim.state, sim.meta, self.store.detections(sim.match_id), scope, end)
        recap = await self.recap_for(fp, self.modes[mode_name])
        self.store.add_recap(recap)
        self.bus.publish("recap", sim.match_id, recap.model_dump(mode="json"))
        return recap
