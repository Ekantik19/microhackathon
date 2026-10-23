"""Required end-to-end test (spec §14): the whole pipeline, mock AI, demo_01 replayed at 60x.

Ingest (simulator) → Interpret (stats + detectors) → Explain (FactPack → mock AI → validator) → stream (bus/SSE).
A fake wall clock makes the 60x replay run in seconds."""

import asyncio

import pytest

from app.main import create_app
from tests.fixtures.fake_clock import FakeClock


@pytest.fixture(scope="module")
def messages():
    async def run() -> list:
        app = create_app()
        app.state.bus.max_queue = 1_000_000
        sim = await app.state.registry.get("demo_01")
        clock = FakeClock()
        sim._now, sim._sleep = clock.now, clock.sleep
        with app.state.bus.subscribe("demo_01") as queue:
            await sim.start(speed=60)
            while sim.status != "finished":
                await asyncio.sleep(0)
            await app.state.orchestrator.idle()
            out = []
            while not queue.empty():
                m = queue.get_nowait()
                out.append((m.topic, m.data))
        await app.state.registry.shutdown()
        return out

    return asyncio.run(run())


def test_1_stats_update_score_and_possession(messages):
    stats = [d for t, d in messages if t == "stats"]
    scores = [tuple(s["score"].values()) for s in stats]
    assert (0, 1) in scores and scores[-1] == (1, 1)
    assert scores.index((0, 1)) < scores.index((1, 1))
    full = stats[-1]["windows"]["full"]
    assert full["NBR"]["possession_pct"] + full["RVA"]["possession_pct"] == 100


def test_2_sustained_pressure_detection_arrives(messages):
    found = [d for t, d in messages if t == "detection" and d["pattern"] == "sustained_pressure"]
    assert [(d["team_id"], d["minute"]) for d in found] == [("NBR", 66)]


def test_3_insight_pending_then_validated_insight_for_that_detection(messages):
    detection = next(d for t, d in messages if t == "detection" and d["pattern"] == "sustained_pressure")
    did = detection["detection_id"]
    order = [(t, d) for t, d in messages if t in ("insight_pending", "insight") and d["trigger_id"] == did]
    for mode in ("casual", "tactical"):
        topics = [t for t, d in order if d["mode"] == mode]
        assert topics == ["insight_pending", "insight"], mode
        insight = next(d for t, d in order if t == "insight" and d["mode"] == mode)
        assert insight["validator"]["passed"] and insight["generated_by"] == "mock"
        assert insight["attempts"] == [{"generated_by": "mock", "passed": True, "violations": []}]


def test_4_goal_explanation_cites_only_events_up_to_69(messages):
    events = {d["event_id"]: d for t, d in messages if t == "event"}
    goal = next(
        d for t, d in messages if t == "detection" and d["pattern"] == "goal" and d["team_id"] == "NBR"
    )
    insights = [d for t, d in messages if t == "insight" and d["trigger_id"] == goal["detection_id"]]
    assert {i["mode"] for i in insights} == {"casual", "tactical"}
    for insight in insights:
        assert insight["type"] == "key_moment" and insight["minute"] == 69
        assert insight["cited_event_ids"]
        assert all(events[i]["match_second"] <= goal["end_second"] for i in insight["cited_event_ids"])
        assert all(events[i]["period"] == 2 and events[i]["minute"] <= 69 for i in insight["cited_event_ids"])


def test_5_full_time_produces_a_recap(messages):
    recaps = [d for t, d in messages if t == "recap" and d["scope"] == "full_time"]
    assert {r["mode"] for r in recaps} == {"casual", "tactical"}
    for r in recaps:
        assert r["validator"]["passed"]
        assert "1-1" in r["body"] and len(r["key_moments"]) >= 4
