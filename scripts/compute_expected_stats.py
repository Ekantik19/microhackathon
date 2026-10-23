"""Independent, deliberately simple implementation of docs/metrics.md.

It shares no code with backend/app/analytics: it reads the raw JSONL as plain dicts and recomputes every metric
from the written definitions. Possession uses a different method from the engine: it walks the clock one second
at a time and asks "who controlled the ball during this second?". A test asserts the fast engine produces
exactly these numbers.

    python scripts/compute_expected_stats.py [--match-id demo_01]

Writes data/matches/{match_id}.expected_stats.json with stats at 15', 45', 69' and 90'.
"""

import argparse
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "matches"
WINDOW_LENGTHS = {"last_5": 300, "last_10": 600, "full": None}
CHECKPOINT_MINUTES = [15, 45, 69, 90]
ON_BALL = {"kickoff", "pass", "carry", "shot", "tackle", "interception", "recovery", "clearance"}


def checkpoint_second(minute, second_half_start):
    # 15' and 45' are 1st-half clock times (45' = end of regulation 1st half, before stoppage).
    # 69' and 90' are 2nd-half clock times, which restart at 45:00 from second_half_start.
    if minute <= 45:
        return minute * 60
    return second_half_start + (minute - 45) * 60


def percent(n, d):
    if d == 0:
        return None
    return (200 * n + d) // (2 * d)  # integer arithmetic, rounds half up


def inside(e, t0, t1):
    return (t0 is None or e["match_second"] > t0) and e["match_second"] <= t1


def is_win(e):
    if e["event_type"] in ("recovery", "interception"):
        return True
    return e["event_type"] == "tackle" and e["outcome"] == "won"


def is_entry(e):
    moving = e["event_type"] == "carry" or (e["event_type"] == "pass" and e["outcome"] == "complete")
    if not moving or e["x"] is None or e["end_x"] is None:
        return False
    return e["x"] < 70 and e["end_x"] >= 70


def cents(events):
    total = 0
    for e in events:
        total += round(e["xg"] * 100)
    return total / 100


def possession_by_second(received, t0, t1, teams):
    """For each one-second slice [s, s+1) inside the window, find the latest event at or before s and the
    first event after s. The slice belongs to a team only if both are in the same possession, the earlier event
    is in play, and it names a team."""
    seconds = {team: 0 for team in teams}
    start = 0 if t0 is None else t0
    i = 0
    for s in range(start, t1):
        while i + 1 < len(received) and received[i + 1]["match_second"] <= s:
            i += 1
        current = received[i]
        if current["match_second"] > s or i + 1 >= len(received):
            continue
        following = received[i + 1]
        if following["match_second"] > t1:
            continue
        same = current["possession_id"] == following["possession_id"]
        team = current["possession_team_id"]
        if same and current["in_play"] and team in seconds:
            seconds[team] += 1
    return seconds


def team_numbers(received, t0, t1, team, poss_seconds):
    window = [e for e in received if inside(e, t0, t1) and e["team_id"] == team]
    shots = [e for e in window if e["event_type"] == "shot"]
    passes = [e for e in window if e["event_type"] == "pass"]
    completed = [e for e in passes if e["outcome"] == "complete"]
    wins = [e for e in window if is_win(e)]
    total_poss = sum(poss_seconds.values())
    return {
        "possession_seconds": poss_seconds[team],
        "possession_pct": percent(poss_seconds[team], total_poss),
        "shots": len(shots),
        "shots_on_target": len([e for e in shots if e["outcome"] in ("saved", "goal")]),
        "xg": cents(shots),
        "passes_attempted": len(passes),
        "passes_completed": len(completed),
        "pass_accuracy": percent(len(completed), len(passes)),
        "final_third_entries": len([e for e in window if is_entry(e)]),
        "high_recoveries": len([e for e in wins if e["x"] is not None and e["x"] >= 70]),
        "recoveries": len(wins),
    }


def player_numbers(received, t1, player_id, team):
    mine = [e for e in received if e["match_second"] <= t1 and e["player_id"] == player_id and e["team_id"] == team]
    passes = [e for e in mine if e["event_type"] == "pass"]
    completed = [e for e in passes if e["outcome"] == "complete"]
    shots = [e for e in mine if e["event_type"] == "shot"]
    return {
        "involvement": len([e for e in mine if e["event_type"] in ON_BALL]),
        "passes_attempted": len(passes),
        "passes_completed": len(completed),
        "pass_accuracy": percent(len(completed), len(passes)),
        "shots": len(shots),
        "xg": cents(shots),
        "recoveries": len([e for e in mine if is_win(e)]),
        "final_third_entries": len([e for e in mine if is_entry(e)]),
    }


def compute(match_id):
    events = [json.loads(line) for line in (DATA / f"{match_id}.jsonl").read_text().splitlines()]
    events.sort(key=lambda e: e["seq"])
    meta = json.loads((DATA / f"{match_id}.meta.json").read_text())
    teams = [t["team_id"] for t in meta["teams"]]
    second_half_start = [p["start_second"] for p in meta["periods"] if p["period"] == 2][0]

    checkpoints = {}
    for minute in CHECKPOINT_MINUTES:
        t1 = checkpoint_second(minute, second_half_start)
        received = [e for e in events if e["match_second"] <= t1]
        windows = {}
        for name, length in WINDOW_LENGTHS.items():
            t0 = None if length is None else t1 - length
            poss = possession_by_second(received, t0, t1, teams)
            windows[name] = {team: team_numbers(received, t0, t1, team, poss) for team in teams}
        players = {}
        for team in teams:
            ids = sorted({e["player_id"] for e in received if e["team_id"] == team and e["player_id"]})
            players[team] = {p: player_numbers(received, t1, p, team) for p in ids}
        goals = [e for e in received if e["event_type"] == "goal"]
        checkpoints[f"{minute}'"] = {
            "clock_second": t1,
            "score": {team: len([g for g in goals if g["team_id"] == team]) for team in teams},
            "windows": windows,
            "players_full": players,
        }
    return {"match_id": match_id, "definitions": "docs/metrics.md", "checkpoints": checkpoints}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", default="demo_01")
    args = parser.parse_args()
    result = compute(args.match_id)
    out = DATA / f"{args.match_id}.expected_stats.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
