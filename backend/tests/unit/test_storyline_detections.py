"""Phase 8: on demo_01 the detectors find the scripted storyline (data/matches/demo_01.storyline.md)."""

import pytest

from app.config import get_settings
from app.models.events import Event
from app.patterns.config import load_patterns_config
from app.patterns.engine import detect_all

SETTINGS = get_settings()


@pytest.fixture(scope="module")
def detections():
    lines = (SETTINGS.data_dir / "matches" / "demo_01.jsonl").read_text().splitlines()
    events = [Event.model_validate_json(line) for line in lines]
    return detect_all(events, ["NBR", "RVA"], load_patterns_config(SETTINGS.config_dir))


def minutes(d) -> float:
    return d.minute + d.second / 60


@pytest.mark.parametrize(
    ("pattern", "team", "scripted_minute"),
    [
        ("high_press_sequence", "RVA", 42),  # 40:50-43:30 press, 3rd high regain at ~42:40
        ("sustained_pressure", "NBR", 66),  # 62'-70' spell
        ("momentum_shift", "RVA", 78),  # ~78' swing to Riverside
        ("goal", "RVA", 23),
        ("goal", "NBR", 69),
        ("big_chance", "RVA", 86),
    ],
)
def test_scripted_beats_are_detected_within_two_minutes(detections, pattern, team, scripted_minute):
    hits = [d for d in detections if d.pattern == pattern and d.team_id == team]
    assert any(abs(minutes(d) - scripted_minute) <= 2 for d in hits), [(d.minute, d.second) for d in hits]


def test_full_detection_list_is_pinned(detections):
    """Pins every detection, including the two emergent (unscripted) momentum shifts documented in the storyline.
    If the generator or thresholds change, update storyline.md and this list together."""
    got = [(d.kind, d.pattern, d.team_id, d.period, d.minute) for d in detections]
    assert got == [
        ("pattern", "momentum_shift", "RVA", 1, 12),  # emergent
        ("key_moment", "goal", "RVA", 1, 23),
        ("key_moment", "card", "NBR", 1, 35),
        ("pattern", "high_press_sequence", "RVA", 1, 42),
        ("pattern", "momentum_shift", "RVA", 1, 44),  # emergent
        ("key_moment", "half_time", None, 1, 47),
        ("key_moment", "card", "RVA", 2, 52),
        ("pattern", "sustained_pressure", "NBR", 2, 66),
        ("key_moment", "goal", "NBR", 2, 69),
        ("pattern", "momentum_shift", "RVA", 2, 77),
        ("key_moment", "big_chance", "RVA", 2, 86),
        ("key_moment", "full_time", None, 2, 94),
    ]


def test_cooldowns_respected(detections):
    by_key: dict[tuple, list[int]] = {}
    for d in detections:
        if d.kind == "pattern":
            key = (d.pattern,) if d.pattern == "momentum_shift" else (d.pattern, d.team_id)
            by_key.setdefault(key, []).append(d.end_second)
    cooldown = {"momentum_shift": 480, "sustained_pressure": 300, "high_press_sequence": 300}
    for key, ends in by_key.items():
        assert all(b - a >= cooldown[key[0]] for a, b in zip(ends, ends[1:], strict=False)), key


def test_detections_only_cite_past_events(detections):
    lines = (SETTINGS.data_dir / "matches" / "demo_01.jsonl").read_text().splitlines()
    second = {e.event_id: e.match_second for e in (Event.model_validate_json(x) for x in lines)}
    for d in detections:
        assert all(second[i] <= d.end_second for i in d.event_ids), d.detection_id
