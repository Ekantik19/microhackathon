from app.models.detections import Detection
from app.models.events import Event
from app.models.stats import TeamStats
from app.patterns.base import Context, Cooldown, rule_strength, strength_note
from app.patterns.config import MomentumShiftConfig


def attacking_index(stats: TeamStats, weights: dict[str, float]) -> float:
    """3 × shots + 1 × final-third entries + 2 × high recoveries + 5 × synthetic xG (weights from config)."""
    return round(
        weights["shots"] * (stats.shots.value or 0)
        + weights["final_third_entries"] * (stats.final_third_entries.value or 0)
        + weights["high_recoveries"] * (stats.high_recoveries.value or 0)
        + weights["xg"] * (stats.xg.value or 0),
        2,
    )


def leader(indexes: dict[str, float]) -> str | None:
    """The team with the highest index, or None on a tie."""
    ranked = sorted(indexes.items(), key=lambda kv: kv[1], reverse=True)
    if len(ranked) < 2 or ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]


class MomentumShift:
    """Momentum shift: compare each team's attacking index in the last 5 minutes with the 5 minutes before. It fires
    when the leader changes (a tie is no leader, and there must have been a leader before), the new leader's index
    is at least 8, and at least double its own index in the previous 5 minutes. At most once every 8 minutes."""

    name = "momentum_shift"

    def __init__(self, cfg: MomentumShiftConfig, scale: float):
        self.cfg = cfg
        self.scale = scale
        self.cooldown = Cooldown(cfg.cooldown_seconds)

    def reset(self) -> None:
        self.cooldown.reset()

    def evaluate(self, ctx: Context, event: Event) -> Detection | None:
        cfg = self.cfg
        if ctx.t < 2 * cfg.window_seconds or not self.cooldown.ready("any", ctx.t):
            return None
        now = {team: attacking_index(s, cfg.weights) for team, s in ctx.last_window.teams.items()}
        before = {team: attacking_index(s, cfg.weights) for team, s in ctx.previous_window.teams.items()}
        new, old = leader(now), leader(before)
        if new is None or old is None or new == old:
            return None
        if now[new] < cfg.min_index or now[new] < cfg.min_growth * before[new]:
            return None
        self.cooldown.fire("any", ctx.t)
        growth_ratio = 1.0 if before[new] == 0 else now[new] / (cfg.min_growth * before[new]) / self.scale
        stats = ctx.last_window.teams[new]
        return Detection(
            detection_id="",
            match_id=event.match_id,
            pattern=self.name,
            team_id=new,
            start_second=max(0, ctx.t - cfg.window_seconds),
            end_second=ctx.t,
            minute=event.minute,
            second=event.second,
            period=event.period,
            rule_strength=rule_strength([now[new] / (self.scale * cfg.min_index), growth_ratio]),
            rule_strength_note=strength_note(self.scale),
            evidence={
                "attacking_index_last_5": now,
                "attacking_index_previous_5": before,
                "new_leader": new,
                "previous_leader": old,
            },
            event_ids=stats.shots.event_ids
            + stats.final_third_entries.event_ids
            + stats.high_recoveries.event_ids,
        )
