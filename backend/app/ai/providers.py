"""AI providers. `MockAIProvider` is deterministic and template-based: it uses only FactPack values and is instant.
`FoundryAIProvider` (Microsoft Foundry) is added in Phase 10 and implements the same protocol."""

from typing import Protocol

from app.ai.models import Fact, FactPack, InsightDraft, RecapDraft, RecapFactPack
from app.ai.modes import ModeConfig
from app.config import Settings
from app.models.insights import KeyMoment, SupportingStat

PATTERN_WORDS = {
    "sustained_pressure": "sustained pressure",
    "momentum_shift": "momentum shift",
    "high_press_sequence": "high-press sequence",
}
PATTERN_PHRASES = {
    "sustained_pressure": "sustained pressure from",
    "momentum_shift": "a momentum shift towards",
    "high_press_sequence": "a high-press sequence by",
}


class AIProvider(Protocol):
    name: str  # "foundry" | "mock"
    model: str | None

    async def generate_live_insight(
        self, facts: FactPack, mode: ModeConfig, violations: list[str] | None = None
    ) -> InsightDraft: ...

    async def generate_event_explanation(
        self, facts: FactPack, mode: ModeConfig, violations: list[str] | None = None
    ) -> InsightDraft: ...

    async def generate_match_recap(
        self, facts: RecapFactPack, mode: ModeConfig, violations: list[str] | None = None
    ) -> RecapDraft: ...


# --- helpers shared by the mock provider and the template fallback ---


def fact(fp: FactPack | RecapFactPack, key: str, team: str | None) -> Fact | None:
    return next((f for f in fp.facts if f.key == key and f.team == team), None)


def value(fp: FactPack | RecapFactPack, key: str, team: str | None, default: float | int = 0) -> float | int:
    f = fact(fp, key, team)
    return default if f is None or f.value is None else f.value


def fmt(v: float | int | None) -> str:
    if v is None:
        return "n/a"
    return str(int(v)) if float(v).is_integer() else f"{v:.2f}".rstrip("0")


def count(n: float | int, noun: str) -> str:
    """'1 shot', '3 shots', '1 final-third entry', '6 final-third entries'."""
    plural = noun[:-1] + "ies" if noun.endswith("y") else noun + "s"
    return f"{fmt(n)} {noun if n == 1 else plural}"


def stat(f: Fact | None) -> list[SupportingStat]:
    if f is None or f.value is None:
        return []
    return [SupportingStat(label=f.label, value=f.value, unit=f.unit)]


def supporting(fp: FactPack, keys: list[str], n: int) -> list[SupportingStat]:
    team = fp.trigger.team
    out: list[SupportingStat] = []
    for key in keys:
        out += stat(fact(fp, key, team))
    return out[:n]


def short(name: str | None) -> str:
    return (name or "").replace(" FC", "").replace(" Athletic", "")


def citations(fp: FactPack, keys: list[str]) -> list[str]:
    ids = list(fp.trigger.event_ids)
    for key in keys:
        f = fact(fp, key, fp.trigger.team)
        if f:
            ids += f.event_ids
    seen: dict[str, None] = dict.fromkeys(i for i in ids if i in fp.event_seconds)
    return list(seen)[:12]


class MockAIProvider:
    """Deterministic templates. Every number comes from the FactPack. Outputs are tagged generated_by="mock"."""

    name = "mock"
    model: str | None = None

    async def generate_live_insight(
        self, facts: FactPack, mode: ModeConfig, violations: list[str] | None = None
    ) -> InsightDraft:
        fp, tactical = facts, mode.terminology == "advanced"
        team, opp, w = fp.trigger.team or "", fp.trigger.opponent or "", 5
        pct, shots = value(fp, "possession_pct", team), value(fp, "shots", team)
        entries, highs = value(fp, "final_third_entries", team), value(fp, "high_recoveries", team)
        kind = fp.trigger.type
        if kind == "sustained_pressure":
            keys = ["possession_pct", "shots", "final_third_entries"]
            if tactical:
                headline = f"Sustained pressure from {short(team)}"
                body = (
                    f"Last {w} minutes: {team} have {fmt(pct)}% possession, {count(shots, 'shot')} and "
                    f"{count(entries, 'final-third entry')}, which meets the sustained-pressure rule. {opp} have "
                    f"{fmt(value(fp, 'shots', opp))} shots in the same window."
                )
            else:
                headline = f"{short(team)} turn up the pressure"
                body = f"{team} have had {fmt(pct)}% of the ball in the last {w} minutes and keep getting close to {short(opp)}'s goal."
        elif kind == "momentum_shift":
            keys = ["shots", "final_third_entries", "high_recoveries"]
            now = value(fp, "attacking_index_last_5", team)
            before = value(fp, "attacking_index_previous_5", team)
            if tactical:
                headline = f"Momentum shift towards {short(team)}"
                body = (
                    f"{team}'s attacking index is {fmt(now)} over the last {w} minutes against {fmt(before)} in the "
                    f"{w} before, when {opp} led. It counts {count(shots, 'shot')} and {count(entries, 'final-third entry')}."
                )
            else:
                headline = f"Momentum swings to {short(team)}"
                body = f"{team} are on top now, with {count(shots, 'shot')} in the last {w} minutes after {opp} had the upper hand."
        else:  # high_press_sequence
            keys = ["high_recoveries", "shots", "final_third_entries"]
            n = value(fp, "high_recoveries_window", team, highs)
            seconds = value(fp, "press_window_seconds", None, 180)
            if tactical:
                headline = f"High-press sequence by {short(team)}"
                body = (
                    f"{team} made {count(n, 'high recovery')} in the attacking third within {fmt(seconds)} seconds, "
                    f"each after pressure on {opp}'s build-up."
                )
            else:
                headline = f"{short(team)} win it back high"
                body = f"{team} have won the ball near {short(opp)}'s goal {fmt(n)} times in the last {fmt(seconds)} seconds by pressing."
        return InsightDraft(
            headline=headline,
            body=body,
            supporting_stats=supporting(fp, keys, mode.include_stats),
            cited_event_ids=citations(fp, keys),
        )

    async def generate_event_explanation(
        self, facts: FactPack, mode: ModeConfig, violations: list[str] | None = None
    ) -> InsightDraft:
        fp, tactical = facts, mode.terminology == "advanced"
        team, opp, player, minute, w = (
            fp.trigger.team or "",
            fp.trigger.opponent or "",
            fp.trigger.player or "",
            fp.trigger.minute,
            5,
        )
        pct, shots = value(fp, "possession_pct", team), value(fp, "shots", team)
        entries = value(fp, "final_third_entries", team)
        kind = fp.trigger.type
        if kind == "goal":
            keys = ["possession_pct", "shots", "final_third_entries"]
            score = "-".join(str(v) for v in fp.score_after.values())
            if tactical:
                headline = f"{player} goal after {short(team)} spell"
                body = (
                    f"{player} scored at {minute}' ({score}). In the previous {w} minutes {team} had {fmt(pct)}% "
                    f"possession, {count(shots, 'shot')} and {count(entries, 'final-third entry')}."
                )
            else:
                headline = f"{player} scores for {short(team)}"
                body = f"{player} made it {score} at {minute}'. {team} had {fmt(pct)}% of the ball in the {w} minutes before."
        elif kind == "big_chance":
            keys = ["shot_xg", "shots", "xg"]
            shot_xg = value(fp, "shot_xg", team)
            if tactical:
                headline = f"Big chance for {player}"
                body = (
                    f"{player}'s shot at {minute}' was worth {fmt(shot_xg)} synthetic xG and was saved. {team} have "
                    f"{count(shots, 'shot')} and {fmt(value(fp, 'xg', team))} synthetic xG in the last {w} minutes."
                )
            else:
                headline = f"Big chance for {short(team)}"
                body = f"{player} had a great chance at {minute}' (synthetic xG {fmt(shot_xg)}), but the shot was saved."
        else:  # card
            keys = ["possession_pct"]
            if tactical:
                headline = f"{player} booked"
                body = f"{player} ({team}) was shown a yellow card at {minute}'. {opp} had {fmt(value(fp, 'possession_pct', opp))}% possession in the last {w} minutes."
            else:
                headline = f"Yellow card for {player}"
                body = f"{player} of {team} was booked at {minute}' for a foul."
        return InsightDraft(
            headline=headline,
            body=body,
            supporting_stats=supporting(fp, keys, mode.include_stats),
            cited_event_ids=citations(fp, keys),
        )

    async def generate_match_recap(
        self, facts: RecapFactPack, mode: ModeConfig, violations: list[str] | None = None
    ) -> RecapDraft:
        return template_recap(facts, mode)


def template_recap(fp: RecapFactPack, mode: ModeConfig) -> RecapDraft:
    """4-6 sentences, a key-moments list and a stats summary, all from the RecapFactPack."""
    home, away = fp.home, fp.away
    h, a = fp.score[home], fp.score[away]
    label = {"half_time": "At half-time", "full_time": "At full-time"}.get(
        fp.scope, f"After {fp.minute} minutes"
    )
    sentences = [f"{label} it is {home} {h}-{a} {away}."]
    goals = [m for m in fp.key_moments if m.type == "goal"]
    for g in goals[:2]:
        sentences.append(f"{g.player} scored for {g.team} at {g.minute}'.")
    if not goals:
        sentences.append("There have been no goals so far.")
    sentences.append(
        f"{home} have {count(value(fp, 'shots', home), 'shot')} to {fmt(value(fp, 'shots', away))} for {away}, "
        f"with {fmt(value(fp, 'possession_pct', home))}% of the possession."
    )
    if mode.terminology == "advanced":
        sentences.append(
            f"Synthetic xG is {fmt(value(fp, 'xg', home))} to {fmt(value(fp, 'xg', away))}, and final-third entries "
            f"{fmt(value(fp, 'final_third_entries', home))} to {fmt(value(fp, 'final_third_entries', away))}."
        )
    for d in fp.detections[-2:][: max(0, 6 - len(sentences))]:
        sentences.append(
            f"The replay detected {PATTERN_PHRASES.get(d.pattern, d.pattern)} {d.team} at {d.minute}'."
        )
    moment_text = {
        "goal": lambda m: f"{m.player} scores for {m.team}.",
        "big_chance": lambda m: f"Big chance for {m.player} of {m.team}.",
        "card": lambda m: f"Yellow card for {m.player} of {m.team}.",
    }
    key_moments = [
        KeyMoment(minute=m.minute, type=m.type, text=moment_text[m.type](m)) for m in fp.key_moments
    ]
    key_moments += [
        KeyMoment(
            minute=d.minute, type=d.pattern, text=f"{d.team}: {PATTERN_WORDS.get(d.pattern, d.pattern)}."
        )
        for d in fp.detections
    ]
    key_moments.sort(key=lambda k: k.minute)
    stats: list[SupportingStat] = []
    for team in (home, away):
        for key in ("shots", "possession_pct", "xg"):
            f = fact(fp, key, team)
            if f and f.value is not None:
                stats.append(SupportingStat(label=f"{f.label} ({short(team)})", value=f.value, unit=f.unit))
    cited = [i for m in fp.key_moments for i in m.event_ids if i in fp.event_seconds]
    return RecapDraft(
        body=" ".join(sentences), key_moments=key_moments, stats_summary=stats, cited_event_ids=cited
    )


def get_provider(settings: Settings) -> AIProvider:
    """Microsoft Foundry when configured (Phase 10); otherwise the clearly-labeled mock."""
    if settings.ai_provider == "foundry" and settings.foundry_endpoint:
        raise NotImplementedError("FoundryAIProvider arrives in Phase 10")
    return MockAIProvider()
