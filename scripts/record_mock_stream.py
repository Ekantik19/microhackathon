"""Record a slice of the real replay as a fixture for the frontend's mock data layer.

    cd backend && uv run python ../scripts/record_mock_stream.py

Drives the real Simulator in-process from 63:30 to 70:30 of demo_01 (Northbridge's sustained pressure and the
69' equaliser), captures every bus message plus REST-shaped snapshots, and writes
frontend/lib/mock/recording.json.

The sample insights and recap in the fixture are written here from the recorded, code-computed stats (so every
number in them is real). They are labeled generated_by="mock". The real AI layer arrives in Phase 9; re-record
then so the fixture uses the real mock provider.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.events.catalog import load_meta  # noqa: E402
from app.events.simulator import Simulator  # noqa: E402
from app.events.sources import LocalSyntheticEventSource  # noqa: E402
from app.models.api import MatchInfo, SimState, StatsResponse  # noqa: E402
from app.services.bus import EventBus  # noqa: E402

OUT = ROOT / "frontend" / "lib" / "mock" / "recording.json"
START, END = (63, 30), (70, 30)
CREATED = datetime(2026, 10, 24, 15, 0, tzinfo=UTC).isoformat()


def stats_snapshot(sim: Simulator) -> dict:
    return {
        w: StatsResponse(
            match_id=sim.match_id, clock_second=sim.state.clock, score=sim.state.score(), stats=sim.state.window(w)
        ).model_dump(mode="json")
        for w in ("last_5", "last_10", "full")
    }


def timeline_snapshot(sim: Simulator) -> list[dict]:
    names = sim.meta.player_names()
    keep = {"goal", "shot", "card", "substitution", "period_end"}
    items = []
    for e in sim.received():
        if e.event_type.value not in keep:
            continue
        who = names.get(e.player_id or "", "")
        label = {
            "goal": f"Goal: {who}",
            "shot": f"Shot ({(e.outcome or '').replace('_', ' ')}): {who}, synthetic xG {e.xg or 0:.2f}",
            "card": f"{(e.outcome or '').capitalize()} card: {who}",
            "substitution": f"Substitution: {names.get(e.recipient_id or '', '')} on, {who} off",
            "period_end": "Half-time" if e.period == 1 else "Full-time",
        }[e.event_type.value]
        items.append(
            {
                "kind": "event",
                "id": e.event_id,
                "match_second": e.match_second,
                "minute": e.minute,
                "second": e.second,
                "period": e.period,
                "type": e.event_type.value,
                "team_id": None if e.event_type.value == "period_end" else e.team_id,
                "player_id": e.player_id,
                "label": label,
            }
        )
    return items


def insight(trigger_id, mode, kind, event, headline, body, stats, cited, n) -> dict:
    return {
        "insight_id": f"mock_{n:03d}_{mode}",
        "match_id": "demo_01",
        "trigger_id": trigger_id,
        "mode": mode,
        "type": kind,
        "minute": event.minute,
        "match_second": event.match_second,
        "headline": headline,
        "body": body,
        "supporting_stats": stats,
        "cited_event_ids": cited,
        "generated_by": "mock",
        "model": None,
        "latency_ms": 0,
        "validator": {"passed": True, "violations": []},
        "created_at": CREATED,
    }


async def main() -> None:
    data_dir = get_settings().data_dir
    meta = load_meta(data_dir, "demo_01")
    bus = EventBus(max_queue=1_000_000)
    sim = Simulator(meta, LocalSyntheticEventSource(data_dir), bus)
    await sim.load()
    start, end = sim.at(*START), sim.at(*END)
    await sim.seek(start)

    snapshot = {
        "state": SimState.model_validate(sim.snapshot()).model_dump(mode="json"),
        "stats": stats_snapshot(sim),
        "timeline": timeline_snapshot(sim),
        "recent_events": [e.model_dump(mode="json") for e in sim.received()[-12:]],
    }

    messages: list[dict] = []
    pressure_fired = False
    n = 0
    with bus.subscribe("demo_01") as queue:
        while sim.clock < end:
            emitted = await sim.advance(2)
            while not queue.empty():
                m = queue.get_nowait()
                if m.topic in ("event", "stats"):
                    at = m.data["match_second"] if m.topic == "event" else m.data["clock_second"]
                    messages.append({"at": at, "topic": m.topic, "data": m.data})
            for e in emitted:
                w = sim.state.window("last_5", with_players=False).teams
                nbr, rva = w["NBR"], w["RVA"]
                pct, shots, fte = nbr.possession_pct.value, nbr.shots.value, nbr.final_third_entries.value
                if not pressure_fired and (pct or 0) >= 65 and (shots or 0) >= 3 and (fte or 0) >= 6:
                    pressure_fired = True
                    n += 1
                    did = f"d_mock_{n}"
                    cited = nbr.shots.event_ids + nbr.final_third_entries.event_ids
                    detection = {
                        "detection_id": did,
                        "match_id": "demo_01",
                        "pattern": "sustained_pressure",
                        "kind": "pattern",
                        "team_id": "NBR",
                        "start_second": e.match_second - 300,
                        "end_second": e.match_second,
                        "minute": e.minute,
                        "second": e.second,
                        "period": e.period,
                        "rule_strength": 1.0,
                        "rule_strength_note": "Rule-derived: average of each metric's ratio to its threshold, capped at 1. Not a calibrated probability.",
                        "evidence": {"possession_pct_last_5": pct, "shots_last_5": shots, "final_third_entries_last_5": fte},
                        "event_ids": cited,
                    }
                    stats = [
                        {"label": "Possession (last 5)", "value": pct, "unit": "%"},
                        {"label": "Shots (last 5)", "value": shots, "unit": ""},
                        {"label": "Final-third entries (last 5)", "value": fte, "unit": ""},
                    ]
                    texts = {
                        "casual": (
                            "Northbridge turn up the heat",
                            f"Northbridge FC have had {pct}% of the ball in the last five minutes and keep getting into "
                            "the dangerous area near Riverside's goal.",
                            stats[:1],
                        ),
                        "tactical": (
                            "Sustained pressure from Northbridge",
                            f"Last 5 minutes: Northbridge FC {pct}% possession, {shots} shots and {fte} final-third "
                            f"entries, which meets the sustained-pressure rule. Riverside Athletic have {rva.shots.value} shots in the same window.",
                            stats,
                        ),
                    }
                    messages.append({"at": e.match_second, "topic": "detection", "data": detection})
                    for mode, (headline, body, sup) in texts.items():
                        messages.append(
                            {"at": e.match_second, "topic": "insight_pending", "data": {"trigger_id": did, "mode": mode, "minute": e.minute}}
                        )
                        messages.append(
                            {"at": e.match_second + 3, "topic": "insight", "data": insight(did, mode, "pattern", e, headline, body, sup, cited, n)}
                        )
                if e.event_type.value == "goal" and e.team_id == "NBR":
                    n += 1
                    did = f"d_mock_{n}"
                    shot_id = e.related_event_ids[0]
                    cited = [shot_id, e.event_id] + nbr.final_third_entries.event_ids[-3:]
                    detection = {
                        "detection_id": did,
                        "match_id": "demo_01",
                        "pattern": "goal",
                        "kind": "key_moment",
                        "team_id": "NBR",
                        "start_second": e.match_second,
                        "end_second": e.match_second,
                        "minute": e.minute,
                        "second": e.second,
                        "period": e.period,
                        "evidence": {"score_after": sim.state.score()},
                        "event_ids": [shot_id, e.event_id],
                    }
                    stats = [
                        {"label": "Possession (last 5)", "value": pct, "unit": "%"},
                        {"label": "Shots (last 5)", "value": shots, "unit": ""},
                        {"label": "Final-third entries (last 5)", "value": fte, "unit": ""},
                    ]
                    texts = {
                        "casual": (
                            "Reyes levels it at 1-1",
                            f"Tomas Reyes scored at {e.minute}' for Northbridge FC. It came after a spell where they had "
                            f"{pct}% of the ball.",
                            stats[:1],
                        ),
                        "tactical": (
                            "Equaliser follows sustained pressure",
                            f"Tomas Reyes finished at {e.minute}' (1-1). In the 5 minutes before, Northbridge FC had {pct}% "
                            f"possession, {shots} shots and {fte} final-third entries.",
                            stats,
                        ),
                    }
                    messages.append({"at": e.match_second, "topic": "detection", "data": detection})
                    for mode, (headline, body, sup) in texts.items():
                        messages.append(
                            {"at": e.match_second, "topic": "insight_pending", "data": {"trigger_id": did, "mode": mode, "minute": e.minute}}
                        )
                        messages.append(
                            {"at": e.match_second + 2, "topic": "insight", "data": insight(did, mode, "key_moment", e, headline, body, sup, cited, n)}
                        )

    full = sim.state.window("full", with_players=False).teams
    last = sim.received()[-1]
    for mode in ("casual", "tactical"):
        body = (
            f"Riverside Athletic led through Andrei Kovalski's 23' goal. Northbridge FC pushed hard after the break and "
            f"Tomas Reyes equalised at 69'. Northbridge FC have {full['NBR'].shots.value} shots to Riverside Athletic's "
            f"{full['RVA'].shots.value} so far."
        )
        if mode == "tactical":
            body += (
                f" Possession is {full['NBR'].possession_pct.value}% to {full['RVA'].possession_pct.value}%, and "
                f"Northbridge FC have {full['NBR'].final_third_entries.value} final-third entries."
            )
        messages.append(
            {
                "at": end,
                "topic": "recap",
                "data": {
                    "recap_id": f"mock_recap_{mode}",
                    "match_id": "demo_01",
                    "scope": "now",
                    "mode": mode,
                    "minute": last.minute,
                    "match_second": end,
                    "body": body,
                    "key_moments": [
                        {"minute": 23, "type": "goal", "text": "Andrei Kovalski scores for Riverside Athletic."},
                        {"minute": 69, "type": "goal", "text": "Tomas Reyes equalises for Northbridge FC."},
                    ],
                    "stats_summary": [
                        {"label": "Shots NBR", "value": full["NBR"].shots.value, "unit": ""},
                        {"label": "Shots RVA", "value": full["RVA"].shots.value, "unit": ""},
                    ],
                    "generated_by": "mock",
                    "validator": {"passed": True, "violations": []},
                    "created_at": CREATED,
                },
            }
        )

    messages.sort(key=lambda m: m["at"])  # stable: keeps emission order within a second
    recording = {
        "note": "Recorded from the real simulator by scripts/record_mock_stream.py. Synthetic match data. Clubs and players are fictional.",
        "match": MatchInfo.model_validate(meta.model_dump(exclude={"final_score", "seed"})).model_dump(mode="json"),
        "start_second": start,
        "end_second": end,
        "snapshot": snapshot,
        "messages": messages,
        "end_stats": stats_snapshot(sim),
        "end_timeline": timeline_snapshot(sim),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(recording, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(messages)} messages)")


if __name__ == "__main__":
    asyncio.run(main())
