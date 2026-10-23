"""Phase 4: event sources, bus and the real-time simulator."""

import asyncio

import pytest

from app.config import get_settings
from app.events.catalog import list_match_ids, load_meta
from app.events.simulator import Simulator
from app.events.sources import InMemoryEventSource, LocalSyntheticEventSource
from app.services.bus import EventBus
from tests.fixtures.factory import ev
from tests.fixtures.fake_clock import FakeClock

DATA = get_settings().data_dir


@pytest.fixture
def meta():
    return load_meta(DATA, "demo_01")


def in_play_events(n: int = 30, step: int = 10) -> list:
    """n live-ball passes every `step` seconds (no stoppages, so no compression)."""
    return [
        ev(i + 1, i * step, "pass", "NBR", outcome="complete", x=40, match_id="demo_01") for i in range(n)
    ]


async def make_sim(meta, events=None, clock: FakeClock | None = None, **kw) -> tuple[Simulator, EventBus]:
    bus = EventBus(max_queue=100_000)  # tests drain at the end, so never drop
    clock = clock or FakeClock()
    source = InMemoryEventSource(events) if events is not None else LocalSyntheticEventSource(DATA)
    sim = Simulator(meta, source, bus, now=clock.now, sleep=clock.sleep, **kw)
    await sim.load()
    return sim, bus


def drain(queue) -> list:
    out = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


async def test_local_source_and_catalog(meta):
    assert "demo_01" in list_match_ids(DATA)
    events = [e async for e in LocalSyntheticEventSource(DATA).events("demo_01")]
    assert len(events) == 1959 and meta.final_score == {"NBR": 1, "RVA": 1}
    with pytest.raises(FileNotFoundError):
        [e async for e in LocalSyntheticEventSource(DATA).events("nope")]


async def test_emits_every_event_in_order_without_duplicates(meta):
    sim, bus = await make_sim(meta)
    with bus.subscribe("demo_01") as q:
        while sim.status != "finished":
            await sim.advance(60)
        messages = drain(q)
    event_ids = [m.data["event_id"] for m in messages if m.topic == "event"]
    assert event_ids == [e.event_id for e in sim.events]
    assert len(sim.state.events) == len(sim.events)
    stats_msgs = [m for m in messages if m.topic == "stats"]
    assert len(stats_msgs) == len(event_ids)  # one stats push per event
    assert stats_msgs[-1].data["score"] == {"NBR": 1, "RVA": 1}
    assert messages[-1].topic == "sim_status" and messages[-1].data["status"] == "finished"


async def test_never_emits_events_after_the_clock(meta):
    sim, _ = await make_sim(meta)
    for _ in range(50):
        await sim.advance(37)
        assert all(e.match_second <= sim.clock for e in sim.received())


async def test_speed_scales_match_time(meta):
    clock = FakeClock()
    sim, _ = await make_sim(meta, in_play_events(), clock)
    await sim.start(speed=10)
    await clock.run_for(5.0)
    await sim.pause()
    assert sim.clock == pytest.approx(50.0, abs=1.5)  # 5 wall s × 10
    emitted = [e.match_second for e in sim.received()]
    assert emitted == [0, 10, 20, 30, 40, 50][: len(emitted)] and len(emitted) >= 5

    await sim.set_speed(60)
    await sim.resume()
    await clock.run_for(1.0)
    await sim.pause()
    assert sim.clock == pytest.approx(110.0, abs=8)  # + 1 wall s × 60


async def test_pause_freezes_and_resume_continues(meta):
    clock = FakeClock()
    sim, _ = await make_sim(meta, in_play_events(), clock)
    await sim.start(speed=10)
    await clock.run_for(2.0)
    await sim.pause()
    frozen, count = sim.clock, len(sim.received())
    await clock.sleep(30)
    await asyncio.sleep(0)
    assert (sim.clock, len(sim.received())) == (frozen, count)
    await sim.resume()
    await clock.run_for(2.0)
    assert sim.clock > frozen and len(sim.received()) > count
    await sim.pause()


async def test_invalid_speed_rejected(meta):
    sim, _ = await make_sim(meta)
    with pytest.raises(ValueError):
        await sim.set_speed(7)


async def test_reset_rebuilds_state_and_replays_identically(meta):
    sim, bus = await make_sim(meta)
    with bus.subscribe("demo_01") as q:
        for _ in range(40):
            await sim.advance(30)
        first = [m.data for m in drain(q) if m.topic in ("event", "stats")]
        await sim.reset()
        assert sim.state.events == [] and sim.clock == 0 and sim.status == "idle"
        assert sim.state.window("full").teams["NBR"].shots.value == 0
        drain(q)
        for _ in range(40):
            await sim.advance(30)
        second = [m.data for m in drain(q) if m.topic in ("event", "stats")]
    assert first == second


async def test_same_controls_give_same_sequence(meta):
    async def run() -> list:
        sim, bus = await make_sim(meta)
        with bus.subscribe("demo_01") as q:
            for step in [15, 300, 7, 120]:
                await sim.advance(step)
            await sim.seek(sim.at(60))
            for _ in range(30):
                await sim.advance(20)
            return [(m.topic, m.data) for m in drain(q)]

    assert await run() == await run()


async def test_seek_rebuilds_from_scratch_without_duplicates(meta):
    seen: list[tuple[str, bool]] = []

    async def hook(_sim, event, replaying):
        seen.append((event.event_id, replaying))

    sim, bus = await make_sim(meta, hooks=[hook])
    target = sim.at(60)
    with bus.subscribe("demo_01") as q:
        await sim.seek(target)
        msgs = drain(q)
    assert [m.topic for m in msgs] == ["stats", "sim_status"]  # skipped events are not streamed one by one
    assert sim.clock == target and sim.status == "paused"
    assert [e.event_id for e in sim.received()] == [
        e.event_id for e in sim.events if e.match_second <= target
    ]
    assert all(replaying for _, replaying in seen)

    await sim.seek(sim.at(20))  # backwards
    assert max(e.match_second for e in sim.received()) <= sim.at(20)
    await sim.seek(target)  # forwards again
    for _ in range(20):
        await sim.advance(30)
    ids = [e.event_id for e in sim.received()]
    assert len(ids) == len(set(ids))
    assert seen[-1][1] is False  # live events after the seek run hooks with replaying=False


async def test_stoppages_are_compressed(meta):
    events = [
        ev(1, 0, "pass", "NBR", outcome="complete", x=40, match_id="demo_01"),
        ev(2, 5, "out_of_play", "NBR", poss="RVA", pid=2, in_play=False, match_id="demo_01"),
        ev(3, 60, "pass", "RVA", pid=2, outcome="complete", x=20, match_id="demo_01"),
    ]
    sim, _ = await make_sim(meta, events)
    await sim.advance(5)
    assert [e.seq for e in sim.received()] == [1, 2]
    await sim.advance(2)  # 55 s of dead ball are skipped: the restart is emitted right away
    assert [e.seq for e in sim.received()] == [1, 2, 3]


async def test_bus_drops_oldest_for_slow_subscribers():
    bus = EventBus(max_queue=3)
    with bus.subscribe("m") as q:
        for i in range(5):
            bus.publish("event", "m", i)
        assert [m.data for m in drain(q)] == [2, 3, 4]
    assert bus.subscriber_count("m") == 0
    with pytest.raises(ValueError):
        bus.publish("nope", "m", 1)


async def test_demo_mode_finishes_well_under_90_seconds(meta):
    clock = FakeClock()
    sim, bus = await make_sim(meta, clock=clock)
    with bus.subscribe("demo_01") as q:
        await sim.run_demo()
        msgs = drain(q)
    assert sim.status == "finished"
    assert clock.t < 90
    live_minutes = {m.data["minute"] for m in msgs if m.topic == "event" and m.data["period"] == 2}
    assert {62, 66, 69, 77, 86}.issubset(live_minutes)  # the storyline beats are streamed live
    assert msgs[-1].data["score"] == {"NBR": 1, "RVA": 1}
