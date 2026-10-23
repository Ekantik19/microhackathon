"""In-process async event bus. The simulator and orchestrator publish; SSE streams subscribe per match.

Publishing never blocks: each subscriber has a bounded queue, and if a slow subscriber falls behind, its oldest
message is dropped (the client resyncs from the REST endpoints on reconnect)."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

TOPICS = ("event", "stats", "detection", "insight_pending", "insight", "recap", "sim_status")


@dataclass(frozen=True)
class Message:
    topic: str
    match_id: str
    data: Any


class EventBus:
    def __init__(self, max_queue: int = 2000):
        self.max_queue = max_queue
        self._subscribers: dict[str, set[asyncio.Queue[Message]]] = defaultdict(set)

    def publish(self, topic: str, match_id: str, data: Any) -> None:
        if topic not in TOPICS:
            raise ValueError(f"unknown topic {topic!r}")
        message = Message(topic, match_id, data)
        for queue in list(self._subscribers[match_id]):
            if queue.full():
                queue.get_nowait()  # drop the oldest message for this slow subscriber
                log.warning("bus subscriber queue full; dropped oldest message (match=%s)", match_id)
            queue.put_nowait(message)

    @contextmanager
    def subscribe(self, match_id: str) -> Iterator[asyncio.Queue[Message]]:
        queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=self.max_queue)
        self._subscribers[match_id].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[match_id].discard(queue)

    def subscriber_count(self, match_id: str) -> int:
        return len(self._subscribers[match_id])
