from app.models.detections import Detection
from app.models.events import Event
from app.patterns.base import Context, Cooldown, rule_strength, strength_note
from app.patterns.config import SustainedPressureConfig


class SustainedPressure:
    """Sustained pressure: over the last 5 minutes one team has at least 65% of the possession AND at least 3 shots
    AND at least 6 final-third entries. Fires at most once per team every 5 minutes."""

    name = "sustained_pressure"

    def __init__(self, cfg: SustainedPressureConfig, scale: float):
        self.cfg = cfg
        self.scale = scale
        self.cooldown = Cooldown(cfg.cooldown_seconds)

    def reset(self) -> None:
        self.cooldown.reset()

    def evaluate(self, ctx: Context, event: Event) -> Detection | None:
        cfg = self.cfg
        for team, stats in ctx.last_window.teams.items():
            pct = stats.possession_pct.value
            shots = int(stats.shots.value or 0)
            entries = int(stats.final_third_entries.value or 0)
            if (
                pct is None
                or pct < cfg.min_possession_pct
                or shots < cfg.min_shots
                or entries < cfg.min_final_third_entries
            ):
                continue
            if not self.cooldown.ready(team, ctx.t):
                continue
            self.cooldown.fire(team, ctx.t)
            strength = rule_strength(
                [
                    pct / (self.scale * cfg.min_possession_pct),
                    shots / (self.scale * cfg.min_shots),
                    entries / (self.scale * cfg.min_final_third_entries),
                ]
            )
            return Detection(
                detection_id="",
                match_id=event.match_id,
                pattern=self.name,
                team_id=team,
                start_second=max(0, ctx.t - ctx.window_seconds),
                end_second=ctx.t,
                minute=event.minute,
                second=event.second,
                period=event.period,
                rule_strength=strength,
                rule_strength_note=strength_note(self.scale),
                evidence={
                    "possession_pct_last_5": pct,
                    "shots_last_5": shots,
                    "final_third_entries_last_5": entries,
                },
                event_ids=stats.shots.event_ids + stats.final_third_entries.event_ids,
            )
        return None
