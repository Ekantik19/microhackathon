"""Phase 2: the seeded generator and the committed demo_01 dataset."""

import json
from collections import Counter

import pytest

from app.config import get_settings
from app.events.generator import FULL_TIME, H2_START, generate, to_jsonl
from app.events.xg import synthetic_xg
from app.models.events import Event, EventType
from app.models.meta import MatchMeta

MATCHES = get_settings().data_dir / "matches"


@pytest.fixture(scope="module")
def events() -> list[Event]:
    lines = (MATCHES / "demo_01.jsonl").read_text().splitlines()
    return [Event.model_validate_json(line) for line in lines]


@pytest.fixture(scope="module")
def meta() -> MatchMeta:
    return MatchMeta.model_validate_json((MATCHES / "demo_01.meta.json").read_text())


def test_same_seed_gives_identical_bytes():
    a, _ = generate("demo_01", 42)
    b, _ = generate("demo_01", 42)
    assert to_jsonl(a) == to_jsonl(b)


def test_committed_file_matches_generator_output():
    events, meta = generate("demo_01", 42)
    assert to_jsonl(events) == (MATCHES / "demo_01.jsonl").read_text()
    assert json.loads((MATCHES / "demo_01.meta.json").read_text()) == meta.model_dump(mode="json")


def test_different_seed_changes_background_but_keeps_storyline():
    a, meta_a = generate("demo_01", 42)
    b, meta_b = generate("demo_01", 7)
    assert to_jsonl(a) != to_jsonl(b)
    assert meta_a.final_score == meta_b.final_score == {"NBR": 1, "RVA": 1}


def test_volume_ids_and_ordering(events):
    assert 1600 <= len(events) <= 2000
    ids = [e.event_id for e in events]
    assert len(set(ids)) == len(ids)
    assert all(b.seq > a.seq for a, b in zip(events, events[1:], strict=False))
    assert all(b.match_second >= a.match_second for a, b in zip(events, events[1:], strict=False))
    assert {e.match_id for e in events} == {"demo_01"}


def test_periods_and_clock(events):
    marks = [(e.event_type, e.period, e.match_second) for e in events if e.event_type.startswith("period")]
    assert marks == [
        (EventType.PERIOD_START, 1, 0),
        (EventType.PERIOD_END, 1, H2_START),
        (EventType.PERIOD_START, 2, H2_START),
        (EventType.PERIOD_END, 2, FULL_TIME),
    ]
    second_half_kickoff = next(e for e in events if e.period == 2 and e.event_type == EventType.KICKOFF)
    assert (second_half_kickoff.minute, second_half_kickoff.second) == (45, 0)


def test_goals_link_to_their_shots(events):
    by_id = {e.event_id: e for e in events}
    goals = [e for e in events if e.event_type == EventType.GOAL]
    assert [(g.team_id, g.minute) for g in goals] == [("RVA", 23), ("NBR", 69)]
    for goal in goals:
        shot = by_id[goal.related_event_ids[0]]
        assert shot.event_type == EventType.SHOT and shot.outcome == "goal"
        assert (shot.team_id, shot.player_id) == (goal.team_id, goal.player_id)
        assert shot.match_second <= goal.match_second
    assert [s.event_id for s in events if s.event_type == EventType.SHOT and s.outcome == "goal"] == [
        g.related_event_ids[0] for g in goals
    ]


def test_final_score_matches_meta(events, meta):
    goals = Counter(e.team_id for e in events if e.event_type == EventType.GOAL)
    assert dict(goals) == meta.final_score == {"NBR": 1, "RVA": 1}


def test_storyline_beats_present(events):
    shots = [e for e in events if e.event_type == EventType.SHOT]
    big_chances = [s for s in shots if s.xg is not None and s.xg >= 0.30 and s.outcome != "goal"]
    assert [(s.team_id, s.minute, s.outcome) for s in big_chances] == [("RVA", 86, "saved")]

    cards = [e for e in events if e.event_type == EventType.CARD]
    assert any(c.outcome == "yellow" for c in cards)
    assert Counter(e.team_id for e in events if e.event_type == EventType.SUBSTITUTION) == {
        "NBR": 3,
        "RVA": 3,
    }

    def high_recoveries(team: str, lo: int, hi: int) -> list[Event]:
        wins = {EventType.RECOVERY, EventType.INTERCEPTION}
        return [
            e
            for e in events
            if e.team_id == team
            and e.period == 1
            and lo <= e.minute < hi
            and (e.event_type in wins or (e.event_type == EventType.TACKLE and e.outcome == "won"))
            and e.x is not None
            and e.x >= 70
        ]

    press = high_recoveries("RVA", 40, 44)
    assert len(press) >= 3
    assert press[2].match_second - press[0].match_second <= 180
    assert all(r.related_event_ids for r in press[:4])  # each high regain links to its pressure event

    nbr_pressure_shots = [s for s in shots if s.team_id == "NBR" and s.period == 2 and 62 <= s.minute <= 69]
    assert len(nbr_pressure_shots) >= 4


def test_xg_only_on_shots_and_matches_formula(events):
    for e in events:
        if e.event_type == EventType.SHOT:
            assert e.x is not None and e.y is not None
            assert e.xg == synthetic_xg(e.x, e.y)
        else:
            assert e.xg is None


def test_players_are_in_squads(events, meta):
    squads = {team: {p.player_id for p in players} for team, players in meta.squads.items()}
    for e in events:
        if e.player_id is not None:
            assert e.player_id in squads[e.team_id], e.event_id


def test_schema_file_is_current():
    schema_path = get_settings().data_dir / "schema" / "event.schema.json"
    assert json.loads(schema_path.read_text()) == Event.model_json_schema()


def test_meta_is_fictional(meta):
    assert {t.name for t in meta.teams} == {"Northbridge FC", "Riverside Athletic"}
    assert meta.competition == "Synthetic League"


def test_xg_reference_points():
    assert synthetic_xg(97, 34) == pytest.approx(0.36, abs=0.02)  # 8 m, central
    assert synthetic_xg(87, 34) < synthetic_xg(94, 34) < synthetic_xg(99, 34)
    assert synthetic_xg(100, 5) < synthetic_xg(100, 34)  # tight angle is worse
