"""In-memory store for detections, insights and recaps per match. Phase 12 adds the database behind it.

Live items (detections, live insights, recaps) are cleared on reset. The AI text cache, keyed by
(match_id, trigger_id, mode), survives resets so a replay never waits on a model twice."""

from collections import defaultdict

from app.models.detections import Detection
from app.models.insights import Insight, Recap


class MatchStore:
    def __init__(self) -> None:
        self._detections: dict[str, list[Detection]] = defaultdict(list)
        self._insights: dict[str, list[Insight]] = defaultdict(list)
        self._recaps: dict[str, list[Recap]] = defaultdict(list)
        self.insight_cache: dict[tuple[str, str, str], Insight] = {}

    def add_detection(self, detection: Detection) -> None:
        self._detections[detection.match_id].append(detection)

    def detections(self, match_id: str, up_to_second: int | None = None) -> list[Detection]:
        items = self._detections[match_id]
        return [d for d in items if up_to_second is None or d.end_second <= up_to_second]

    def clear_detections(self, match_id: str) -> None:
        self._detections.pop(match_id, None)

    def add_insight(self, insight: Insight) -> None:
        live = self._insights[insight.match_id]
        live[:] = [i for i in live if (i.trigger_id, i.mode) != (insight.trigger_id, insight.mode)]
        live.append(insight)
        self.insight_cache[(insight.match_id, insight.trigger_id, insight.mode)] = insight

    def insights(self, match_id: str, mode: str) -> list[Insight]:
        return sorted((i for i in self._insights[match_id] if i.mode == mode), key=lambda i: i.match_second)

    def add_recap(self, recap: Recap) -> None:
        self._recaps[recap.match_id].append(recap)

    def recaps(self, match_id: str, mode: str | None = None) -> list[Recap]:
        return [r for r in self._recaps[match_id] if mode is None or r.mode == mode]

    def clear_live(self, match_id: str) -> None:
        self._detections.pop(match_id, None)
        self._insights.pop(match_id, None)
        self._recaps.pop(match_id, None)
