"""Replays demo_01 through the analytics + pattern engine and builds every FactPack at its detection moment."""

from functools import lru_cache

from app.ai.factpack import build_factpack, build_recap_factpack
from app.ai.models import FactPack, RecapFactPack
from app.ai.modes import ModeConfig, load_modes
from app.analytics.state import MatchState
from app.config import get_settings
from app.events.catalog import load_meta
from app.models.detections import Detection
from app.models.events import Event
from app.models.meta import MatchMeta
from app.patterns.config import load_patterns_config
from app.patterns.engine import PatternEngine

SETTINGS = get_settings()


@lru_cache
def demo_meta() -> MatchMeta:
    return load_meta(SETTINGS.data_dir, "demo_01")


@lru_cache
def demo_events() -> tuple[Event, ...]:
    lines = (SETTINGS.data_dir / "matches" / "demo_01.jsonl").read_text().splitlines()
    return tuple(Event.model_validate_json(line) for line in lines)


@lru_cache
def modes() -> dict[str, ModeConfig]:
    return load_modes(SETTINGS.config_dir)


@lru_cache
def demo_factpacks() -> tuple[list[tuple[Detection, FactPack]], list[tuple[Detection, RecapFactPack]]]:
    state = MatchState("demo_01", ["NBR", "RVA"])
    engine = PatternEngine(load_patterns_config(SETTINGS.config_dir))
    detections: list[Detection] = []
    packs: list[tuple[Detection, FactPack]] = []
    recaps: list[tuple[Detection, RecapFactPack]] = []
    for e in demo_events():
        state.ingest(e)
        for d in engine.process(state, e):
            detections.append(d)
            if d.pattern in ("half_time", "full_time"):
                recaps.append(
                    (d, build_recap_factpack(state, demo_meta(), detections, d.pattern, d.end_second))
                )
            else:
                packs.append((d, build_factpack(state, d, demo_meta(), detections)))
    return packs, recaps


def factpack_for(pattern: str, team: str | None = None) -> FactPack:
    packs, _ = demo_factpacks()
    return next(fp for d, fp in packs if d.pattern == pattern and (team is None or d.team_id == team))
