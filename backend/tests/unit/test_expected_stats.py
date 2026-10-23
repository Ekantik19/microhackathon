"""The fast engine must equal the independent slow implementation (scripts/compute_expected_stats.py) exactly."""

import importlib.util
import json

import pytest

from app.analytics.state import MatchState
from app.config import REPO_ROOT, get_settings
from app.models.events import Event
from app.models.meta import MatchMeta

MATCHES = get_settings().data_dir / "matches"
EXPECTED = json.loads((MATCHES / "demo_01.expected_stats.json").read_text())


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "compute_expected_stats", REPO_ROOT / "scripts" / "compute_expected_stats.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def replay() -> tuple[list[Event], MatchMeta]:
    events = [
        Event.model_validate_json(line) for line in (MATCHES / "demo_01.jsonl").read_text().splitlines()
    ]
    meta = MatchMeta.model_validate_json((MATCHES / "demo_01.meta.json").read_text())
    return events, meta


def test_committed_expected_stats_are_current():
    assert _load_script().compute("demo_01") == EXPECTED


@pytest.mark.parametrize("checkpoint", ["15'", "45'", "69'", "90'"])
def test_engine_matches_expected_stats(replay, checkpoint):
    events, meta = replay
    expected = EXPECTED["checkpoints"][checkpoint]
    t = expected["clock_second"]

    state = MatchState("demo_01", [team.team_id for team in meta.teams])
    for e in events:
        if e.match_second > t:
            break
        state.ingest(e)
    state.advance_clock(t)

    assert state.score() == expected["score"]
    for window, teams in expected["windows"].items():
        stats = state.window(window)
        for team_id, numbers in teams.items():
            got = {name: metric.value for name, metric in stats.teams[team_id] if name != "team_id"}
            assert got == numbers, f"{checkpoint} {window} {team_id}"
    full = state.window("full")
    for team_id, players in expected["players_full"].items():
        got = {
            p.player_id: {name: m.value for name, m in p if name not in ("player_id", "team_id")}
            for p in full.players[team_id]
        }
        assert got == players, f"{checkpoint} players {team_id}"
