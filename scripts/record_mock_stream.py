"""Record a slice of the real pipeline as a fixture for the frontend's mock data layer.

    cd backend && uv run python ../scripts/record_mock_stream.py

Runs the real app in-process (simulator → stats → detectors → orchestrator → mock AI provider → validator) on
demo_01 from 63:30 to 70:30 (Northbridge's sustained pressure and the 69' equaliser). It captures every bus message
plus REST snapshots and writes frontend/lib/mock/recording.json. A "recap so far" is generated at the end.
Synthetic match data. Clubs and players are fictional.
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import httpx  # noqa: E402

from app.main import create_app  # noqa: E402

OUT = ROOT / "frontend" / "lib" / "mock" / "recording.json"
START, END = (63, 30), (70, 30)
WINDOWS = ("last_5", "last_10", "full")


async def snapshot(client: httpx.AsyncClient) -> dict:
    base = "/matches/demo_01"
    state = (await client.get(f"{base}/state")).json()
    return {
        "state": state,
        "stats": {w: (await client.get(f"{base}/stats", params={"window": w})).json() for w in WINDOWS},
        "timeline": (await client.get(f"{base}/timeline")).json()["items"],
        "recent_events": (
            await client.get(f"{base}/events", params={"since_seq": max(0, state["events_emitted"] - 12)})
        ).json()["events"],
    }


async def main() -> None:
    app = create_app()
    app.state.bus.max_queue = 1_000_000
    orchestrator = app.state.orchestrator
    sim = await app.state.registry.get("demo_01")
    start, end = sim.at(*START), sim.at(*END)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mock") as client:
        await sim.seek(start)
        await orchestrator.idle()
        first = await snapshot(client)

        messages: list[dict] = []
        with app.state.bus.subscribe("demo_01") as queue:
            while sim.clock < end:
                await sim.advance(2)
                await orchestrator.idle()
                clock = int(sim.clock)
                while not queue.empty():
                    m = queue.get_nowait()
                    if m.topic == "sim_status":
                        continue
                    at = {"event": lambda d: d["match_second"], "stats": lambda d: d["clock_second"]}.get(
                        m.topic, lambda d: clock + (2 if m.topic == "insight" else 0)  # show "Analysing…" briefly
                    )(m.data)
                    messages.append({"at": at, "topic": m.topic, "data": m.data})
            for mode in ("casual", "tactical"):
                await orchestrator.recap_now(sim, mode, "now")
            while not queue.empty():
                m = queue.get_nowait()
                if m.topic == "recap":
                    messages.append({"at": end, "topic": "recap", "data": m.data})
        last = await snapshot(client)
        match = (await client.get("/matches/demo_01")).json()

    messages.sort(key=lambda m: m["at"])  # stable: keeps emission order within a second
    recording = {
        "note": "Recorded from the real pipeline (mock AI provider) by scripts/record_mock_stream.py. "
        "Synthetic match data. Clubs and players are fictional.",
        "match": match,
        "start_second": start,
        "end_second": end,
        "snapshot": first,
        "messages": messages,
        "end_stats": last["stats"],
        "end_timeline": last["timeline"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(recording, separators=(",", ":")))
    topics: dict[str, int] = {}
    for m in messages:
        topics[m["topic"]] = topics.get(m["topic"], 0) + 1
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB): {topics}")


if __name__ == "__main__":
    asyncio.run(main())
