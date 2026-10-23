"""Phase 8: each detector fires and stays silent on hand-built fixtures. Expected values are worked out in the
docstrings. Shots at x=90 (y=34) have synthetic xG 0.12."""

from app.patterns.config import PatternsConfig
from app.patterns.engine import detect_all
from tests.fixtures.factory import ev

TEAMS = ["NBR", "RVA"]
CFG = PatternsConfig()


class Seq:
    """Appends fixture events with increasing seq numbers."""

    def __init__(self) -> None:
        self.events: list = []

    def add(self, t: int, etype: str, team: str = "NBR", **kw) -> None:
        self.events.append(ev(len(self.events) + 1, t, etype, team, **kw))


def patterns(events, name: str) -> list:
    return [d for d in detect_all(events, TEAMS, CFG) if d.pattern == name]


# --- sustained pressure --------------------------------------------------------------------------------------


def pressure_spell(
    shot_times: list[int], end: int = 280, rva_share: int = 0, entries_until: int = 180, entry_step: int = 30
) -> list:
    """NBR keep the ball (one possession) with a final-third entry every `entry_step` s up to `entries_until`
    (default 30, 60, ..., 180) and shots at `shot_times`.
    If `rva_share` > 0, RVA hold the ball for that many seconds first."""
    s = Seq()
    start = 0
    if rva_share:
        s.add(0, "pass", "RVA", pid=1, outcome="complete", x=40)
        s.add(rva_share, "pass", "RVA", pid=1, outcome="complete", x=40)
        s.add(rva_share, "interception", "NBR", pid=2, x=50)
        start = rva_share
    pid = 2 if rva_share else 1
    for t in range(start + 10, end + 1, 10):
        if t in shot_times:
            s.add(t, "shot", "NBR", pid=pid, outcome="blocked", x=90)
        elif (t - start) % entry_step == 0 and t - start <= entries_until:
            s.add(t, "carry", "NBR", pid=pid, x=60, end_x=75)
        else:
            s.add(t, "pass", "NBR", pid=pid, outcome="complete", x=50)
    return s.events


def test_sustained_pressure_fires_with_evidence_and_strength():
    """At t=240 the last 5 min hold 100% NBR possession, 3 shots (200, 220, 240) and 6 entries.
    Strength = mean(min(1, 100/97.5), 3/4.5, 6/9) = mean(1, 0.667, 0.667) = 0.78."""
    found = patterns(pressure_spell([200, 220, 240]), "sustained_pressure")
    assert len(found) == 1
    d = found[0]
    assert (d.team_id, d.end_second, d.start_second) == ("NBR", 240, 0)
    assert d.evidence == {"possession_pct_last_5": 100, "shots_last_5": 3, "final_third_entries_last_5": 6}
    assert d.rule_strength == 0.78
    assert "Not a calibrated probability" in (d.rule_strength_note or "")
    assert {"e00020", "e00022", "e00024"} <= set(d.event_ids)  # the three shots are cited


def test_sustained_pressure_silent_with_two_shots():
    assert patterns(pressure_spell([200, 240]), "sustained_pressure") == []


def test_sustained_pressure_depends_on_possession():
    """RVA hold the ball from 0 until NBR win it; then NBR make 6 entries and shoot at 400, 410 and 430.
    RVA until 240: at t=430 the window (130, 430] gives RVA 110 s, NBR 190 s → 63% < 65% → silent.
    RVA until 200 (control): RVA 70 s, NBR 230 s → 77% → fires. Shots and entries are identical in both."""
    quiet = pressure_spell([400, 410, 430], end=430, rva_share=240)
    assert patterns(quiet, "sustained_pressure") == []
    loud = pressure_spell([400, 410, 430], end=430, rva_share=200)
    assert [d.evidence["possession_pct_last_5"] for d in patterns(loud, "sustained_pressure")] == [77]


def test_sustained_pressure_cooldown():
    """Shots at 210, 230, ... and entries every 20 s keep the rule true from t=250 (third shot) onwards. The 5-minute
    cooldown blocks it until t ≥ 550, so over 0-660 it fires exactly twice: at 250 and at 550."""
    shots = list(range(210, 661, 20))
    events = pressure_spell(shots, end=660, entries_until=660, entry_step=20)
    ends = [d.end_second for d in patterns(events, "sustained_pressure")]
    assert ends == [250, 550]


# --- momentum shift ------------------------------------------------------------------------------------------


def momentum_fixture(nbr_previous_shots: int = 0, rva_previous_shots: int = 1, nbr_entries: int = 3) -> list:
    """Previous window (180, 480]: RVA entries at 200 and 250, RVA shots from 260, NBR shots from 270. Last window
    (480, 780]: NBR entries from 700 and NBR shots at 760 and 780."""
    s = Seq()
    s.add(0, "kickoff", "NBR", x=52.5)
    for t in (200, 250):
        s.add(t, "carry", "RVA", x=60, end_x=75)
    for k in range(rva_previous_shots):
        s.add(260 + k, "shot", "RVA", outcome="saved", x=90)
    for k in range(nbr_previous_shots):
        s.add(270 + k, "shot", "NBR", outcome="saved", x=90)
    for k in range(nbr_entries):
        s.add(700 + 20 * k, "carry", "NBR", x=60, end_x=75)
    s.add(760, "shot", "NBR", outcome="saved", x=90)
    s.add(780, "shot", "NBR", outcome="saved", x=90)
    s.events.sort(key=lambda e: (e.match_second, e.seq))
    return [e.model_copy(update={"seq": i + 1, "event_id": f"e{i + 1:05d}"}) for i, e in enumerate(s.events)]


def test_momentum_shift_fires_when_the_leader_changes():
    """At t=780: last 5 min NBR = 3×2 shots + 3 entries + 5×0.24 xG = 10.2, RVA = 0. Previous 5 min (180, 480]:
    RVA = 3×1 + 2 + 5×0.12 = 5.6 (leader), NBR = 0. NBR now leads, 10.2 ≥ 8 and ≥ 2 × 0."""
    found = patterns(momentum_fixture(), "momentum_shift")
    assert len(found) == 1
    d = found[0]
    assert (d.team_id, d.end_second) == ("NBR", 780)
    assert d.evidence["attacking_index_last_5"] == {"NBR": 10.2, "RVA": 0.0}
    assert d.evidence["attacking_index_previous_5"] == {"NBR": 0.0, "RVA": 5.6}
    assert d.evidence["previous_leader"] == "RVA"


def test_momentum_shift_silent_below_min_index():
    """With 1 entry, NBR's index at 780 = 6 + 1 + 1.2 = 8.2 ≥ 8 → fires; with 0 entries 7.2 < 8 → silent."""
    assert len(patterns(momentum_fixture(nbr_entries=1), "momentum_shift")) == 1
    assert patterns(momentum_fixture(nbr_entries=0), "momentum_shift") == []


def test_momentum_shift_silent_without_doubling():
    """NBR already had 2 shots before (index 6.0 + 1.2 = 7.2) while RVA led with 3 shots (9 + 2 + 1.8 = 12.8):
    NBR's 10.2 now is less than 2 × 7.2 = 14.4 → silent."""
    assert patterns(momentum_fixture(nbr_previous_shots=2, rva_previous_shots=3), "momentum_shift") == []


# --- high-press sequence -------------------------------------------------------------------------------------


def press_fixture(times: list[int], x: float = 75) -> list:
    s = Seq()
    s.add(0, "kickoff", "NBR", x=52.5)
    for k, t in enumerate(times):
        s.add(t, "recovery" if k % 2 == 0 else "tackle", "RVA", x=x, outcome=None if k % 2 == 0 else "won")
    return s.events


def test_high_press_fires_on_third_high_recovery_within_180s():
    """High recoveries at 100, 160, 270: at 270 the window (90, 270] holds all three."""
    found = patterns(press_fixture([100, 160, 270]), "high_press_sequence")
    assert [(d.team_id, d.start_second, d.end_second) for d in found] == [("RVA", 100, 270)]
    assert found[0].evidence["high_recoveries_last_180s"] == 3


def test_high_press_silent_when_spread_out_or_not_high():
    assert patterns(press_fixture([100, 160, 290]), "high_press_sequence") == []  # (110, 290] holds two
    assert patterns(press_fixture([100, 160, 270], x=65), "high_press_sequence") == []  # x < 70 is not high


def test_high_press_cooldown():
    found = patterns(press_fixture([100, 160, 270, 300, 330]), "high_press_sequence")
    assert len(found) == 1


# --- key moments ---------------------------------------------------------------------------------------------


def test_key_moments():
    """A goal (linked to its shot), a big chance (xG 0.36 saved), a shot at exactly xG 0.30 (counts), a shot at
    xG 0.28 (does not), a goal from a 0.36 shot (a goal, not also a big chance), a card, half- and full-time."""
    s = Seq()
    s.add(100, "shot", "RVA", outcome="goal", x=94)
    s.add(101, "goal", "RVA", x=105, related=["e00001"], in_play=False)
    s.add(200, "shot", "NBR", outcome="saved", x=97)
    s.add(210, "shot", "NBR", outcome="off_target", x=96)
    s.add(220, "shot", "NBR", outcome="saved", x=95.5)
    s.add(300, "shot", "NBR", outcome="goal", x=97)
    s.add(301, "goal", "NBR", x=105, related=["e00006"], in_play=False)
    s.add(400, "foul", "RVA", x=40, in_play=False)
    s.add(420, "card", "RVA", outcome="yellow", in_play=False, related=["e00008"])
    s.add(2800, "period_end", "NBR", in_play=False)
    s.add(5760, "period_end", "NBR", in_play=False)
    found = [d for d in detect_all(s.events, TEAMS, CFG) if d.kind == "key_moment"]
    assert [(d.pattern, d.team_id, d.end_second) for d in found] == [
        ("goal", "RVA", 101),
        ("big_chance", "NBR", 200),
        ("big_chance", "NBR", 210),
        ("goal", "NBR", 301),
        ("card", "RVA", 420),
        ("half_time", None, 2800),
        ("full_time", None, 5760),
    ]
    assert found[0].event_ids == ["e00001", "e00002"]  # goal cites its shot
    assert found[0].evidence["score_after"] == {"NBR": 0, "RVA": 1}
    assert found[-1].evidence["score"] == {"NBR": 1, "RVA": 1}


def test_detection_ids_are_deterministic():
    a = detect_all(pressure_spell([200, 220, 240]), TEAMS, CFG)
    b = detect_all(pressure_spell([200, 220, 240]), TEAMS, CFG)
    assert [d.model_dump() for d in a] == [d.model_dump() for d in b]
    assert [d.detection_id for d in a] == [f"d_{i + 1:04d}" for i in range(len(a))]
