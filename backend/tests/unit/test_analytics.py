"""Phase 3: the deterministic statistics engine. Expected values are worked out by hand in each docstring."""

import pytest

from app.analytics import passing, possession, shots, territory
from app.analytics.players import player_stats
from app.analytics.score import score_at
from app.analytics.state import MatchState
from app.analytics.windows import window_stats
from tests.fixtures.factory import ev

TEAMS = ["NBR", "RVA"]


def values(metrics: dict) -> dict:
    return {team: m.value for team, m in metrics.items()}


# --- possession --------------------------------------------------------------------------------------------


def test_possession_worked_example_71_29():
    """NBR controls 0→100→213 (213 s) in possession 1. RVA wins it at 213 and controls 213→300 (87 s).
    Total assigned = 300 s. NBR = 213 / 300 × 100 = 71%; RVA = 87 / 300 × 100 = 29%."""
    events = [
        ev(1, 0, "pass", "NBR", pid=1, outcome="complete", x=30),
        ev(2, 100, "pass", "NBR", pid=1, outcome="complete", x=40),
        ev(3, 213, "pass", "NBR", pid=1, outcome="incomplete", x=50, poss=None),
        ev(4, 213, "interception", "RVA", pid=2, x=55),
        ev(5, 300, "pass", "RVA", pid=2, outcome="complete", x=60),
    ]
    assert values(possession.possession_seconds(events, None, 300, TEAMS)) == {"NBR": 213, "RVA": 87}
    assert values(possession.possession_pct(events, None, 300, TEAMS)) == {"NBR": 71, "RVA": 29}


def test_out_of_play_unassigned_and_transitions_are_excluded():
    """NBR 0→6 (6 s, same possession). 6→10 ends in an out-of-play event in a new possession: not credited.
    10→30 starts out of play: excluded. RVA 30→35 (5 s). 35→40 ends with an incomplete pass (loose ball, new
    possession): excluded. 40→45 is unassigned (team None): excluded. NBR 45→50 (5 s).
    NBR 11 s, RVA 5 s, total 16 → NBR 11/16 = 68.75 → 69%, RVA 5/16 = 31.25 → 31%."""
    events = [
        ev(1, 0, "pass", "NBR", pid=1, outcome="complete", x=30),
        ev(2, 6, "carry", "NBR", pid=1, x=40, end_x=45),
        ev(3, 10, "out_of_play", "NBR", pid=2, poss="RVA", in_play=False),
        ev(4, 30, "pass", "RVA", pid=2, outcome="complete", x=20),
        ev(5, 35, "pass", "RVA", pid=2, outcome="complete", x=30),
        ev(6, 40, "pass", "RVA", pid=3, outcome="incomplete", x=40, poss=None),
        ev(7, 45, "recovery", "NBR", pid=4, x=60),
        ev(8, 50, "pass", "NBR", pid=4, outcome="complete", x=60),
    ]
    assert values(possession.possession_seconds(events, None, 50, TEAMS)) == {"NBR": 11, "RVA": 5}
    assert values(possession.possession_pct(events, None, 50, TEAMS)) == {"NBR": 69, "RVA": 31}


def test_possession_is_clipped_to_the_window():
    """Window last_5 at t=450 is (150, 450]. NBR 100→400 overlaps by 400−150 = 250 s, plus 400→450 = 50 s → 300.
    Full match: 300 + 50 = 350."""
    events = [
        ev(1, 100, "pass", "NBR", outcome="complete", x=30),
        ev(2, 400, "pass", "NBR", outcome="complete", x=40),
        ev(3, 450, "pass", "NBR", outcome="complete", x=50),
    ]
    assert window_stats(events, 450, "last_5", TEAMS).teams["NBR"].possession_seconds.value == 300
    assert window_stats(events, 450, "full", TEAMS).teams["NBR"].possession_seconds.value == 350


def test_possession_is_na_without_assigned_time():
    """A single event closes no interval, so there is no assigned time: pct is None ("n/a")."""
    events = [ev(1, 0, "kickoff", "NBR", x=52.5)]
    assert values(possession.possession_pct(events, None, 300, TEAMS)) == {"NBR": None, "RVA": None}


# --- shots, passing, territory ------------------------------------------------------------------------------


def test_goal_is_not_a_second_shot():
    """One shot (outcome goal) and its linked goal event: 1 shot, 1 on target, xG equals the shot's xG."""
    shot = ev(1, 100, "shot", "NBR", outcome="goal", x=94, y=33)
    goal = ev(2, 101, "goal", "NBR", x=105, related=["e00001"], in_play=False, poss="RVA", pid=2)
    events = [shot, goal]
    assert shots.shots(events, "NBR", None, 200).value == 1
    assert shots.shots_on_target(events, "NBR", None, 200).value == 1
    assert shots.xg_total(events, "NBR", None, 200).value == shot.xg


def test_shots_on_target_and_xg_sum():
    """saved + goal are on target (2 of 4). xG is the 2-decimal sum of the four shots' xG."""
    events = [
        ev(1, 10, "shot", "NBR", outcome="saved", x=90, y=30),
        ev(2, 20, "shot", "NBR", outcome="off_target", x=85, y=40),
        ev(3, 30, "shot", "NBR", outcome="blocked", x=88, y=34),
        ev(4, 40, "shot", "NBR", outcome="goal", x=97, y=34),
        ev(5, 50, "shot", "RVA", outcome="saved", x=90, y=34),
    ]
    assert shots.shots(events, "NBR", None, 60).value == 4
    assert shots.shots_on_target(events, "NBR", None, 60).value == 2
    assert shots.shots_on_target(events, "NBR", None, 60).event_ids == ["e00001", "e00004"]
    expected = round(sum(e.xg or 0 for e in events[:4]), 2)
    assert shots.xg_total(events, "NBR", None, 60).value == expected


def test_pass_accuracy():
    """No passes → None. 3 of 4 → 75. 2 of 3 = 66.7 → 67. 1 of 8 = 12.5 → 13 (half up)."""
    assert passing.pass_accuracy([], "NBR", None, 100).value is None

    def passes(n_complete: int, n_total: int) -> list:
        return [
            ev(i + 1, i, "pass", "NBR", outcome="complete" if i < n_complete else "incomplete", x=30)
            for i in range(n_total)
        ]

    assert passing.pass_accuracy(passes(3, 4), "NBR", None, 100).value == 75
    assert passing.pass_accuracy(passes(2, 3), "NBR", None, 100).value == 67
    assert passing.pass_accuracy(passes(1, 8), "NBR", None, 100).value == 13
    assert passing.passes_attempted(passes(1, 8), "NBR", None, 100).value == 8
    assert passing.passes_completed(passes(1, 8), "NBR", None, 100).value == 1


def test_final_third_entries():
    """Counts: complete pass 60→75, carry 65→70 (end exactly 70). Not counted: incomplete pass 60→75,
    pass already inside 72→90, carry 50→69.9 that stops short, RVA entry (other team)."""
    events = [
        ev(1, 1, "pass", "NBR", outcome="complete", x=60, end_x=75),
        ev(2, 2, "carry", "NBR", x=65, end_x=70),
        ev(3, 3, "pass", "NBR", outcome="incomplete", x=60, end_x=75),
        ev(4, 4, "pass", "NBR", outcome="complete", x=72, end_x=90),
        ev(5, 5, "carry", "NBR", x=50, end_x=69.9),
        ev(6, 6, "pass", "RVA", outcome="complete", x=60, end_x=80),
    ]
    metric = territory.final_third_entries(events, "NBR", None, 10)
    assert (metric.value, metric.event_ids) == (2, ["e00001", "e00002"])


def test_high_recoveries_and_recoveries():
    """High (x ≥ 70): recovery at 70, interception at 80, won tackle at 75 → 3. Not high: lost tackle at 80
    (not a ball win), recovery at 69.9 (a ball win, but not high). All ball wins: 4."""
    events = [
        ev(1, 1, "recovery", "RVA", x=70),
        ev(2, 2, "interception", "RVA", x=80),
        ev(3, 3, "tackle", "RVA", outcome="won", x=75),
        ev(4, 4, "tackle", "RVA", outcome="lost", x=80),
        ev(5, 5, "recovery", "RVA", x=69.9),
    ]
    assert territory.high_recoveries(events, "RVA", None, 10).value == 3
    assert territory.recoveries(events, "RVA", None, 10).value == 4


def test_window_boundaries_are_exclusive_start_inclusive_end():
    """last_5 at t=450 is (150, 450]: a shot at exactly 150 is outside, a shot at exactly 450 is inside."""
    events = [ev(1, 150, "shot", "NBR", outcome="saved"), ev(2, 450, "shot", "NBR", outcome="saved")]
    stats = window_stats(events, 450, "last_5", TEAMS)
    assert stats.teams["NBR"].shots.event_ids == ["e00002"]
    assert (stats.start_second, stats.end_second) == (150, 450)
    assert window_stats(events, 450, "full", TEAMS).teams["NBR"].shots.value == 2


def test_player_stats_and_involvement():
    """Reyes: 3 passes (2 complete → 67%), 1 carry entry 60→78, 1 shot, 1 recovery. Pressure and foul are not
    on-ball actions. Involvement = 3 passes + carry + shot + recovery = 6."""
    p = "NBR_09"
    events = [
        ev(1, 1, "pass", "NBR", player=p, outcome="complete", x=40),
        ev(2, 2, "pass", "NBR", player=p, outcome="complete", x=50),
        ev(3, 3, "pass", "NBR", player=p, outcome="incomplete", x=55),
        ev(4, 4, "carry", "NBR", player=p, x=60, end_x=78),
        ev(5, 5, "shot", "NBR", player=p, outcome="saved", x=92, y=34),
        ev(6, 6, "recovery", "NBR", player=p, x=50),
        ev(7, 7, "pressure", "NBR", player=p, x=60),
        ev(8, 8, "foul", "NBR", player=p, x=60, in_play=False),
    ]
    stats = player_stats(events, p, "NBR", None, 10)
    assert stats.involvement.value == 6
    assert (stats.passes_attempted.value, stats.passes_completed.value, stats.pass_accuracy.value) == (
        3,
        2,
        67,
    )
    assert (stats.shots.value, stats.recoveries.value, stats.final_third_entries.value) == (1, 1, 1)
    assert stats.xg.value == events[4].xg


def test_score_at_uses_goal_events_up_to_t():
    events = [
        ev(1, 100, "shot", "RVA", outcome="goal", x=94),
        ev(2, 101, "goal", "RVA", x=105, related=["e00001"], in_play=False),
        ev(3, 500, "shot", "NBR", outcome="goal", x=94),
        ev(4, 501, "goal", "NBR", x=105, related=["e00003"], in_play=False),
    ]
    assert values(score_at(events, 300, TEAMS)) == {"NBR": 0, "RVA": 1}
    assert values(score_at(events, 600, TEAMS)) == {"NBR": 1, "RVA": 1}


# --- MatchState ---------------------------------------------------------------------------------------------


def _demo_like() -> list:
    return [
        ev(1, 0, "pass", "NBR", outcome="complete", x=60, end_x=75),
        ev(2, 30, "shot", "NBR", outcome="saved", x=90),
        ev(3, 32, "recovery", "RVA", pid=2, x=4),
        ev(4, 60, "pass", "RVA", pid=2, outcome="complete", x=10, end_x=30),
    ]


def test_state_ignores_duplicates():
    state = MatchState("fx", TEAMS)
    events = _demo_like()
    for e in events:
        assert state.ingest(e) is True
    before = state.window("full").model_dump()
    for e in events:
        assert state.ingest(e) is False
    assert state.window("full").model_dump() == before
    assert len(state.events) == 4


def test_state_reset_clears_everything():
    state = MatchState("fx", TEAMS)
    for e in _demo_like():
        state.ingest(e)
    state.reset()
    assert state.events == [] and state.clock == 0
    assert state.window("full").teams["NBR"].shots.value == 0
    assert state.ingest(_demo_like()[0]) is True  # the same event can be ingested again after a reset


def test_state_incremental_equals_batch_and_handles_out_of_order():
    events = _demo_like()
    ordered = MatchState("fx", TEAMS)
    for e in events:
        ordered.ingest(e)
    shuffled = MatchState("fx", TEAMS)
    for e in [events[0], events[2], events[1], events[3]]:
        shuffled.ingest(e)
    assert [e.seq for e in shuffled.events] == [1, 2, 3, 4]
    assert shuffled.window("full").model_dump() == ordered.window("full").model_dump()
    assert ordered.window("full").model_dump() == window_stats(events, 60, "full", TEAMS).model_dump()


def test_state_rejects_other_matches_and_tracks_clock():
    state = MatchState("fx", TEAMS)
    assert state.ingest(ev(1, 10, "pass", "NBR", outcome="complete", x=30, match_id="other")) is False
    state.ingest(ev(1, 10, "pass", "NBR", outcome="complete", x=30))
    state.advance_clock(400)
    assert state.clock == 400
    state.advance_clock(100)
    assert state.clock == 400


@pytest.mark.parametrize("window", ["last_5", "last_10", "full"])
def test_window_stats_have_both_teams(window):
    stats = window_stats(_demo_like(), 60, window, TEAMS)
    assert set(stats.teams) == {"NBR", "RVA"}
