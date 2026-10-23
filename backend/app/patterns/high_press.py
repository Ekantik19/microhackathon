from app.analytics.territory import high_recoveries
from app.models.detections import Detection
from app.models.events import Event
from app.patterns.base import Context, Cooldown, rule_strength, strength_note
from app.patterns.config import HighPressConfig


class HighPressSequence:
    """High-press sequence: one team wins the ball high up the pitch (a recovery, interception or won tackle at
    x ≥ 70) at least 3 times within 180 seconds. Fires at most once per team every 5 minutes."""

    name = "high_press_sequence"

    def __init__(self, cfg: HighPressConfig, scale: float):
        self.cfg = cfg
        self.scale = scale
        self.cooldown = Cooldown(cfg.cooldown_seconds)

    def reset(self) -> None:
        self.cooldown.reset()

    def evaluate(self, ctx: Context, event: Event) -> Detection | None:
        cfg = self.cfg
        team = event.team_id
        found = high_recoveries([event], team, None, ctx.t)
        if not found.value:  # only a new high recovery can complete a sequence
            return None
        t0 = ctx.t - cfg.window_seconds
        window = ctx.events_since(t0)
        recent = high_recoveries(window, team, t0, ctx.t)
        if int(recent.value or 0) < cfg.min_high_recoveries or not self.cooldown.ready(team, ctx.t):
            return None
        self.cooldown.fire(team, ctx.t)
        by_id = {e.event_id: e for e in window}
        first = by_id.get(recent.event_ids[0])
        linked = [rid for eid in recent.event_ids if eid in by_id for rid in by_id[eid].related_event_ids]
        return Detection(
            detection_id="",
            match_id=event.match_id,
            pattern=self.name,
            team_id=team,
            start_second=first.match_second if first else t0,
            end_second=ctx.t,
            minute=event.minute,
            second=event.second,
            period=event.period,
            rule_strength=rule_strength([int(recent.value or 0) / (self.scale * cfg.min_high_recoveries)]),
            rule_strength_note=strength_note(self.scale),
            evidence={"high_recoveries_last_180s": recent.value, "linked_pressure_events": len(linked)},
            event_ids=recent.event_ids + linked,
        )
