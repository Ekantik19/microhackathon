"""Runs every detector on every ingested event (INTERPRET). Deterministic: the same events in the same order give
the same detections with the same IDs."""

from app.analytics.state import MatchState
from app.models.detections import Detection
from app.models.events import Event
from app.patterns.base import Context, Detector
from app.patterns.config import PatternsConfig
from app.patterns.high_press import HighPressSequence
from app.patterns.key_moments import KeyMoments
from app.patterns.momentum_shift import MomentumShift
from app.patterns.sustained_pressure import SustainedPressure


class PatternEngine:
    def __init__(self, cfg: PatternsConfig):
        self.cfg = cfg
        scale = cfg.strength_scale
        self.detectors: list[Detector] = [
            KeyMoments(cfg.key_moments),
            SustainedPressure(cfg.sustained_pressure, scale),
            HighPressSequence(cfg.high_press_sequence, scale),
            MomentumShift(cfg.momentum_shift, scale),
        ]
        self._count = 0

    def reset(self) -> None:
        self._count = 0
        for d in self.detectors:
            d.reset()

    def process(self, state: MatchState, event: Event) -> list[Detection]:
        ctx = Context(state, event, self.cfg.momentum_shift.window_seconds)
        found = []
        for detector in self.detectors:
            detection = detector.evaluate(ctx, event)
            if detection is not None:
                self._count += 1
                found.append(detection.model_copy(update={"detection_id": f"d_{self._count:04d}"}))
        return found


def detect_all(events: list[Event], teams: list[str], cfg: PatternsConfig) -> list[Detection]:
    """Replay a whole list of events through a fresh state and engine."""
    state = MatchState(events[0].match_id, teams) if events else MatchState("", teams)
    engine = PatternEngine(cfg)
    out: list[Detection] = []
    for e in events:
        if state.ingest(e):
            out.extend(engine.process(state, e))
    return out
