"""Deterministic grounding validator. Nothing an AI writes is shown unless it passes these checks:

1. Every number in the headline, body and supporting stats (digits, percentages, minutes, and the number words one
   to twenty) equals a FactPack value (percentages as whole numbers), a score, or a minute present in the FactPack.
2. Every capitalized word is part of an allowed team or player name, or an allow-listed common word.
3. Every cited event ID exists in the FactPack and happened at or before the clock (no future leakage).
4. Every supporting stat's value equals a fact value exactly.
5. The body respects the mode's word limit.
"""

import re

from app.ai.models import FactPack, InsightDraft, RecapDraft, RecapFactPack
from app.ai.modes import ModeConfig
from app.models.insights import ValidatorResult

NUMBER_WORDS = {
    w: i + 1
    for i, w in enumerate(
        "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen twenty".split()
    )
}
NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
WORD_RE = re.compile(r"\b(" + "|".join(NUMBER_WORDS) + r")\b", re.IGNORECASE)
CAPITALIZED_RE = re.compile(r"(?<![\w'’-])[A-Z][\w'’-]*")
TOLERANCE = 0.005

# Ordinary words that may start a sentence or appear capitalized in labels. Names are never listed here.
COMMON_WORDS = set(
    """
    a after again against all also although an and another any are around as at attack attacking back be because
    been before behind being both but by came can chance city club clear could defence despite did do down during
    each early either end equaliser even every evidence facts few final first for from full game goal goals had half
    has have having he her here high his how however if in inside into is it its just keep kept key last late lead
    led less level levels like live long many match meanwhile minute minutes moment momentum more most much near
    neither new next no nor not now of off on one only or other out over pass passes pattern possession pressing
    pressure previous recap recaps recovery recoveries rule same score scored scores second shot shots side since so
    some spell still such sustained synthetic tactical than that the their them then there these they this those
    three through time to too two under until up very was we were what when where which while who why will with
    within without yellow red card booked you your xg sequence press shift swing turn turns win wins won big
    signal strength final-third entries entry accuracy window windows verified recorded rule-based half-time
    full-time so-far target pressure-based
    """.split()
)


def _allowed_numbers(*groups: list[float] | list[int]) -> list[float]:
    return [float(v) for group in groups for v in group]


def _matches(value: float, allowed: list[float]) -> bool:
    return any(abs(value - a) < TOLERANCE for a in allowed)


def _numbers_in(text: str) -> list[float]:
    found = [float(n) for n in NUMBER_RE.findall(text)]
    found += [float(NUMBER_WORDS[w.lower()]) for w in WORD_RE.findall(text)]
    return found


def _name_tokens(names: list[str]) -> set[str]:
    tokens = set()
    for name in names:
        for part in name.split():
            tokens.add(part)
            tokens.update(part.split("-"))
    return tokens


def _check_text(text: str, numbers: list[float], name_tokens: set[str], violations: list[str]) -> None:
    for n in _numbers_in(text):
        if not _matches(n, numbers):
            shown = int(n) if n.is_integer() else n
            violations.append(f"invented number {shown} (not in the facts)")
    for raw in CAPITALIZED_RE.findall(text):
        word = re.sub(r"['’]s?$", "", raw)
        if word in name_tokens or word.lower() in COMMON_WORDS:
            continue
        if all(part in name_tokens or part.lower() in COMMON_WORDS for part in word.split("-") if part):
            continue
        violations.append(f"unknown name {word!r} (not a team or player in this match)")


def _normalize(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()


def _check_stat(label: str, value: float, facts: list, violations: list[str]) -> None:
    """A stat must use a fact's label (a team name may follow) and that fact's exact value."""
    wanted = _normalize(label)
    candidates = [f for f in facts if f.value is not None and wanted.startswith(_normalize(f.label))]
    if not candidates:
        violations.append(f"supporting stat {label!r} does not use a fact label")
    elif not any(_matches(value, [float(f.value)]) for f in candidates):
        violations.append(f"supporting stat {label!r} = {value:g} does not match the facts")


def _check_citations(
    ids: list[str], event_seconds: dict[str, int], clock: int, violations: list[str]
) -> None:
    for event_id in ids:
        if event_id not in event_seconds:
            violations.append(f"cited event {event_id} is not in the facts")
        elif event_seconds[event_id] > clock:
            violations.append(f"cited event {event_id} is after the clock (future leakage)")


def factpack_numbers(fp: FactPack) -> tuple[list[float], list[float]]:
    """(numbers allowed in text, values allowed as supporting stats)."""
    fact_values = [float(f.value) for f in fp.facts if f.value is not None]
    minutes = (
        [fp.trigger.minute] + [d.minute for d in fp.detections] + [d.since_minute for d in fp.detections]
    )
    minutes += [e.minute for e in fp.recent_events]
    scores = list(fp.score_before.values()) + list(fp.score_after.values())
    return _allowed_numbers(fact_values, minutes, scores), _allowed_numbers(fact_values)


def validate_insight(draft: InsightDraft, fp: FactPack, mode: ModeConfig) -> ValidatorResult:
    numbers, stat_values = factpack_numbers(fp)
    tokens = _name_tokens(fp.allowed_names)
    violations: list[str] = []
    _check_text(draft.headline, numbers, tokens, violations)
    _check_text(draft.body, numbers, tokens, violations)
    for stat in draft.supporting_stats:
        _check_text(stat.label, numbers, tokens, violations)
        value = stat.value
        if isinstance(value, str):
            _check_text(value, numbers, tokens, violations)
        else:
            _check_stat(stat.label, float(value), fp.facts, violations)
    _check_citations(draft.cited_event_ids, fp.event_seconds, fp.clock_second, violations)
    words = len(draft.body.split())
    if words > mode.max_words:
        violations.append(f"body has {words} words (limit {mode.max_words})")
    return ValidatorResult(passed=not violations, violations=violations)


RECAP_MAX_WORDS = 130


def validate_recap(draft: RecapDraft, fp: RecapFactPack) -> ValidatorResult:
    fact_values = [float(f.value) for f in fp.facts if f.value is not None]
    minutes = [fp.minute] + [m.minute for m in fp.key_moments] + [d.minute for d in fp.detections]
    numbers = _allowed_numbers(fact_values, minutes, list(fp.score.values()))
    tokens = _name_tokens(fp.allowed_names)
    violations: list[str] = []
    _check_text(draft.body, numbers, tokens, violations)
    moment_minutes = {m.minute for m in fp.key_moments} | {d.minute for d in fp.detections}
    for moment in draft.key_moments:
        if moment.minute not in moment_minutes:
            violations.append(f"key moment at {moment.minute}' is not in the facts")
        _check_text(moment.text, numbers, tokens, violations)
    for stat in draft.stats_summary:
        _check_text(stat.label, numbers, tokens, violations)
        if not isinstance(stat.value, str):
            _check_stat(stat.label, float(stat.value), fp.facts, violations)
    _check_citations(draft.cited_event_ids, fp.event_seconds, fp.clock_second, violations)
    if len(draft.body.split()) > RECAP_MAX_WORDS:
        violations.append(f"recap body is longer than {RECAP_MAX_WORDS} words")
    return ValidatorResult(passed=not violations, violations=violations)
