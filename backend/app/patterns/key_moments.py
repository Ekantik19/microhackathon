"""Key moments: goal, big chance (a shot with synthetic xG ≥ 0.30 that is not a goal), card, half-time, full-time.
Each fires on the single event that defines it."""

from app.analytics.score import score_at
from app.models.detections import Detection
from app.models.events import Event, EventType
from app.patterns.base import Context
from app.patterns.config import KeyMomentsConfig


class KeyMoments:
    name = "key_moments"

    def __init__(self, cfg: KeyMomentsConfig):
        self.cfg = cfg

    def reset(self) -> None:
        pass

    def evaluate(self, ctx: Context, event: Event) -> Detection | None:
        pattern: str | None = None
        evidence: dict = {}
        ids = [event.event_id]
        team: str | None = event.team_id
        score = {t: int(m.value or 0) for t, m in score_at(ctx.state.events, ctx.t, ctx.state.teams).items()}

        if event.event_type == EventType.GOAL:
            pattern = "goal"
            ids = event.related_event_ids + ids
            evidence = {"player_id": event.player_id, "score_after": score}
        elif (
            event.event_type == EventType.SHOT
            and event.outcome != "goal"
            and (event.xg or 0) >= self.cfg.big_chance_min_xg
        ):
            pattern = "big_chance"
            evidence = {"player_id": event.player_id, "xg": event.xg, "outcome": event.outcome}
        elif event.event_type == EventType.CARD:
            pattern = "card"
            ids = event.related_event_ids + ids
            evidence = {"player_id": event.player_id, "card": event.outcome}
        elif event.event_type == EventType.PERIOD_END:
            pattern = "half_time" if event.period == 1 else "full_time"
            team = None
            evidence = {"score": score}
        if pattern is None:
            return None
        return Detection(
            detection_id="",
            match_id=event.match_id,
            pattern=pattern,
            kind="key_moment",
            team_id=team,
            start_second=event.match_second,
            end_second=event.match_second,
            minute=event.minute,
            second=event.second,
            period=event.period,
            evidence=evidence,
            event_ids=ids,
        )
