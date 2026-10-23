"""TemplateFallback: used when the provider times out or errors, or a draft fails the validator twice. It lists the
verified facts plainly. Outputs are tagged generated_by="template"."""

from app.ai.models import FactPack, InsightDraft, RecapDraft, RecapFactPack
from app.ai.modes import ModeConfig
from app.ai.providers import PATTERN_WORDS, fmt, supporting, template_recap

LABELS = {**PATTERN_WORDS, "goal": "goal", "big_chance": "big chance", "card": "yellow card"}
FACT_KEYS = ["possession_pct", "shots", "final_third_entries", "high_recoveries", "shot_xg"]


class TemplateFallback:
    name = "template"

    def insight(self, fp: FactPack, mode: ModeConfig) -> InsightDraft:
        team = fp.trigger.team or ""
        label = LABELS.get(fp.trigger.type, fp.trigger.type)
        headline = f"{label.capitalize()}: {team}"
        stats = supporting(fp, FACT_KEYS, 3)
        facts = ", ".join(
            f"{s.label.lower().replace(' (last 5)', '')} {s.value if isinstance(s.value, str) else fmt(s.value)}{s.unit}"
            for s in stats
        )
        who = f"{fp.trigger.player}, {team}" if fp.trigger.player else team
        body = f"{label.capitalize()} at {fp.trigger.minute}' ({who}). Last 5 minutes: {facts}."
        return InsightDraft(
            headline=headline,
            body=body,
            supporting_stats=stats[: mode.include_stats],
            cited_event_ids=[i for i in fp.trigger.event_ids if i in fp.event_seconds][:12],
        )

    def recap(self, fp: RecapFactPack, mode: ModeConfig) -> RecapDraft:
        return template_recap(fp, mode)
