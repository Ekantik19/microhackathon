"""Wires the pattern engine into a simulator: every ingested event is checked by every detector."""

from app.events.simulator import Hook, Simulator
from app.models.events import Event
from app.patterns.config import PatternsConfig
from app.patterns.engine import PatternEngine
from app.services.bus import EventBus
from app.services.registry import HookFactory
from app.services.store import MatchStore


def detection_hooks(store: MatchStore, bus: EventBus, cfg: PatternsConfig) -> HookFactory:
    def factory(sim: Simulator) -> list[Hook]:
        engine = PatternEngine(cfg)

        def on_reset() -> None:
            engine.reset()
            store.clear_detections(sim.match_id)

        async def hook(sim: Simulator, event: Event, replaying: bool) -> None:
            for detection in engine.process(sim.state, event):
                store.add_detection(detection)
                if not replaying:  # during a seek, clients resync from REST instead
                    bus.publish("detection", sim.match_id, detection.model_dump(mode="json"))

        sim.on_reset.append(on_reset)
        return [hook]

    return factory
