"""Phase 5: the SSE stream delivers ordered `event` and `stats` messages during a 60x replay.

A real uvicorn server runs on a free local port, because the in-process test transport buffers whole responses
and cannot read an endless stream."""

import asyncio
import json

import httpx
import uvicorn

from app.main import create_app


async def read_sse(response: httpx.Response, want_events: int) -> list[tuple[str, dict]]:
    messages: list[tuple[str, dict]] = []
    topic, data = None, None
    async for line in response.aiter_lines():
        if line.startswith("event:"):
            topic = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
        elif line == "" and topic and data is not None:
            messages.append((topic, json.loads(data)))
            topic, data = None, None
            if sum(1 for t, _ in messages if t == "event") >= want_events:
                return messages
    return messages


async def test_stream_delivers_ordered_events_and_stats_at_60x():
    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="on"))
    serve = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    try:
        async with httpx.AsyncClient(base_url=base, timeout=20) as client:
            async with client.stream(
                "GET", "/matches/demo_01/stream", params={"mode": "tactical"}
            ) as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                await client.post("/matches/demo_01/simulation/start", json={"speed": 60})
                messages = await asyncio.wait_for(read_sse(response, want_events=40), timeout=20)
    finally:
        server.should_exit = True
        await serve

    assert messages[0][0] == "sim_status"  # snapshot on connect
    events = [d for t, d in messages if t == "event"]
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs) and seqs[0] == 1

    # Every event is immediately followed by its stats push, whose clock never runs ahead of the event.
    pairs = [(t, d) for t, d in messages if t in ("event", "stats")]
    for (t1, d1), (t2, d2) in zip(pairs, pairs[1:], strict=False):
        if t1 == "event":
            assert t2 == "stats" and d2["clock_second"] == d1["match_second"]
    clocks = [d["clock_second"] for t, d in messages if t == "stats"]
    assert clocks == sorted(clocks)
