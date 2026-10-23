"""Phase 5: every REST endpoint, through the real FastAPI app."""

import httpx
import pytest

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await app.state.registry.shutdown()


async def at(client, minute: int, second: int = 0) -> int:
    """Display clock → match_second for demo_01 (2nd half starts at 2820)."""
    return minute * 60 + second if minute < 45 else 2820 + (minute - 45) * 60 + second


async def test_health(client):
    body = (await client.get("/health")).json()
    assert body["status"] == "ok" and body["ai_provider"] == "mock" and body["event_source"] == "local"


async def test_list_and_get_match_without_spoilers(client):
    matches = (await client.get("/matches")).json()
    assert [m["match_id"] for m in matches] == ["demo_01"]
    info = (await client.get("/matches/demo_01")).json()
    assert {t["name"] for t in info["teams"]} == {"Northbridge FC", "Riverside Athletic"}
    assert len(info["squads"]["NBR"]) == 16
    assert "final_score" not in info and "seed" not in info


async def test_unknown_match_is_404_with_error_shape(client):
    r = await client.get("/matches/nope/state")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "match_not_found", "message": "No match with id 'nope'"}}


async def test_initial_state(client):
    state = (await client.get("/matches/demo_01/state")).json()
    assert state["status"] == "idle" and state["clock_second"] == 0 and state["score"] == {"NBR": 0, "RVA": 0}
    assert state["events_total"] == 1959 and state["events_emitted"] == 0


async def test_seek_then_stats_events_timeline(client):
    t = await at(client, 70)
    state = (await client.post("/matches/demo_01/simulation/seek", json={"match_second": t})).json()
    assert state["status"] == "paused" and state["clock_second"] == t and state["minute"] == 70
    assert state["score"] == {"NBR": 1, "RVA": 1}

    stats = (await client.get("/matches/demo_01/stats", params={"window": "last_5"})).json()
    assert stats["stats"]["window"] == "last_5" and stats["stats"]["end_second"] == t
    nbr = stats["stats"]["teams"]["NBR"]
    assert nbr["shots"]["value"] >= 3 and len(nbr["shots"]["event_ids"]) == nbr["shots"]["value"]
    assert stats["stats"]["players"]["NBR"]  # player table included

    page = (await client.get("/matches/demo_01/events", params={"limit": 2000})).json()
    assert page["events"] and max(e["match_second"] for e in page["events"]) <= t  # never the future
    more = (await client.get("/matches/demo_01/events", params={"since_seq": page["next_since_seq"]})).json()
    assert more["events"] == []

    timeline = (await client.get("/matches/demo_01/timeline")).json()
    goals = [i for i in timeline["items"] if i["type"] == "goal"]
    assert [(g["team_id"], g["minute"], g["label"]) for g in goals] == [
        ("RVA", 23, "Goal: Andrei Kovalski"),
        ("NBR", 69, "Goal: Tomas Reyes"),
    ]
    assert any(i["label"] == "Half-time" for i in timeline["items"])
    assert not any(i["label"] == "Full-time" for i in timeline["items"])


async def test_events_paging(client):
    await client.post("/matches/demo_01/simulation/seek", json={"match_second": 600})
    first = (await client.get("/matches/demo_01/events", params={"limit": 10})).json()
    assert [e["seq"] for e in first["events"]] == list(range(1, 11))
    second = (
        await client.get(
            "/matches/demo_01/events", params={"limit": 10, "since_seq": first["next_since_seq"]}
        )
    ).json()
    assert second["events"][0]["seq"] == 11


async def test_controls(client):
    base = "/matches/demo_01/simulation"
    assert (await client.post(f"{base}/start", json={"speed": 60})).json()["status"] == "running"
    assert (await client.post(f"{base}/pause")).json()["status"] == "paused"
    assert (await client.post(f"{base}/speed", json={"speed": 5})).json()["speed"] == 5
    assert (await client.post(f"{base}/resume")).json()["status"] == "running"
    assert (await client.post(f"{base}/start")).json()["status"] == "running"  # body is optional
    reset = (await client.post(f"{base}/reset")).json()
    assert reset["status"] == "idle" and reset["clock_second"] == 0 and reset["events_emitted"] == 0


async def test_bad_speed_and_seek_are_422(client):
    r = await client.post("/matches/demo_01/simulation/speed", json={"speed": 7})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = await client.post("/matches/demo_01/simulation/seek", json={"match_second": -5})
    assert r.status_code == 422
    r = await client.get("/matches/demo_01/stats", params={"window": "last_99"})
    assert r.status_code == 422


async def test_demo_starts_in_background_and_reset_cancels_it(client):
    r = await client.post("/matches/demo_01/simulation/demo")
    assert r.status_code == 200
    app_registry = client._transport.app.state.registry  # type: ignore[attr-defined]
    assert app_registry.demo_running("demo_01")
    await client.post("/matches/demo_01/simulation/reset")
    assert not app_registry.demo_running("demo_01")


async def test_insights_and_recaps_empty_before_ai(client):
    assert (await client.get("/matches/demo_01/insights", params={"mode": "tactical"})).json() == []
    assert (await client.get("/matches/demo_01/recaps")).json() == []
    r = await client.get("/matches/demo_01/insights", params={"mode": "pirate"})
    assert r.status_code == 422
    r = await client.post("/matches/demo_01/generate-recap", json={"mode": "casual", "scope": "now"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "recap_unavailable"
