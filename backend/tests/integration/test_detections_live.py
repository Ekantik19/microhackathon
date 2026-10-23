"""Phase 8: detectors run inside the live simulator, publish `detection` messages, and rebuild on seek/reset."""

import httpx
import pytest

from app.main import create_app


@pytest.fixture
async def app_and_sim():
    app = create_app()
    app.state.bus.max_queue = 100_000
    sim = await app.state.registry.get("demo_01")
    yield app, sim
    await app.state.registry.shutdown()


def drain(queue) -> list:
    out = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


async def test_live_replay_publishes_every_detection(app_and_sim):
    app, sim = app_and_sim
    with app.state.bus.subscribe("demo_01") as q:
        while sim.status != "finished":
            await sim.advance(120)
        live = [m.data for m in drain(q) if m.topic == "detection"]
    assert len(live) == 12
    assert [d["detection_id"] for d in live] == [f"d_{i:04d}" for i in range(1, 13)]
    assert [d.detection_id for d in app.state.store.detections("demo_01")] == [
        d["detection_id"] for d in live
    ]


async def test_seek_rebuilds_detections_silently_and_deterministically(app_and_sim):
    app, sim = app_and_sim
    store = app.state.store
    with app.state.bus.subscribe("demo_01") as q:
        await sim.seek(sim.at(70))
        assert not [
            m for m in drain(q) if m.topic == "detection"
        ]  # replay is silent; clients resync over REST
    after_70 = [(d.detection_id, d.pattern) for d in store.detections("demo_01")]
    assert len(after_70) == 9 and after_70[-1][1] == "goal"

    await sim.seek(sim.at(30))
    assert [d.pattern for d in store.detections("demo_01")] == ["momentum_shift", "goal"]
    await sim.seek(sim.at(70))
    assert [(d.detection_id, d.pattern) for d in store.detections("demo_01")] == after_70  # same IDs again

    with app.state.bus.subscribe("demo_01") as q:
        while sim.clock < sim.at(80):
            await sim.advance(30)
        assert [m.data["pattern"] for m in drain(q) if m.topic == "detection"] == ["momentum_shift"]

    await sim.reset()
    assert store.detections("demo_01") == []


async def test_timeline_api_shows_pattern_detections_with_signal_strength(app_and_sim):
    app, sim = app_and_sim
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/matches/demo_01/simulation/seek", json={"match_second": sim.at(70)})
        items = (await client.get("/matches/demo_01/timeline")).json()["items"]
    patterns = [i for i in items if i["kind"] == "detection"]
    assert [(i["type"], i["team_id"], i["minute"]) for i in patterns] == [
        ("momentum_shift", "RVA", 12),
        ("high_press_sequence", "RVA", 42),
        ("momentum_shift", "RVA", 44),
        ("sustained_pressure", "NBR", 66),
    ]
    assert all(0 < i["rule_strength"] <= 1 and i["start_second"] < i["match_second"] for i in patterns)
