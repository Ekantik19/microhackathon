"""Phase 9: mock provider, modes, the regenerate-once loop, template fallback, recaps and FactPack time safety."""

import asyncio

import pytest

from app.ai.fallback import TemplateFallback
from app.ai.generate import generate_insight, generate_recap
from app.ai.models import InsightDraft
from app.ai.providers import MockAIProvider
from app.ai.validator import validate_insight, validate_recap
from tests.fixtures.demo import demo_factpacks, factpack_for, modes

MOCK = MockAIProvider()
FALLBACK = TemplateFallback()


class ScriptedProvider(MockAIProvider):
    """Returns pre-scripted drafts (or raises) in order, and records the violations it was sent."""

    name = "scripted"

    def __init__(self, outcomes: list):
        self.outcomes = list(outcomes)
        self.received: list[list[str] | None] = []

    async def generate_live_insight(self, facts, mode, violations=None):
        self.received.append(violations)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome == "slow":
            await asyncio.sleep(10)
        if outcome == "good":
            return await MOCK.generate_live_insight(facts, mode)
        return InsightDraft(headline="Northbridge FC", body="Northbridge FC have 99 shots.")

    generate_event_explanation = generate_live_insight


@pytest.mark.parametrize("mode", ["casual", "tactical"])
async def test_mock_output_passes_the_validator_for_every_demo_trigger(mode):
    packs, recaps = demo_factpacks()
    for detection, fp in packs:
        method = (
            MOCK.generate_live_insight if fp.trigger.kind == "pattern" else MOCK.generate_event_explanation
        )
        result = validate_insight(await method(fp, modes()[mode]), fp, modes()[mode])
        assert result.passed, (detection.pattern, detection.minute, result.violations)
    for _, fp in recaps:
        result = validate_recap(await MOCK.generate_match_recap(fp, modes()[mode]), fp)
        assert result.passed, result.violations


async def test_casual_and_tactical_differ_in_wording_but_cite_the_same_facts():
    fp = factpack_for("sustained_pressure", "NBR")
    casual = await MOCK.generate_live_insight(fp, modes()["casual"])
    tactical = await MOCK.generate_live_insight(fp, modes()["tactical"])
    assert casual.body != tactical.body
    assert len(casual.supporting_stats) == 1 and len(tactical.supporting_stats) == 3
    fact_values = {f.value for f in fp.facts}
    for d in (casual, tactical):
        assert {s.value for s in d.supporting_stats} <= fact_values
        assert set(d.cited_event_ids) <= set(fp.event_seconds)
        assert validate_insight(d, fp, modes()[d and ("casual" if d is casual else "tactical")]).passed


async def test_regenerates_once_with_the_violations_then_passes():
    fp = factpack_for("sustained_pressure", "NBR")
    provider = ScriptedProvider(["bad", "good"])
    draft, generated_by, result, attempts, _ = await generate_insight(
        provider, FALLBACK, fp, modes()["casual"], 8
    )
    assert generated_by == "scripted" and result.passed
    assert [a.passed for a in attempts] == [False, True]
    assert provider.received[0] is None
    assert provider.received[1] == [
        "invented number 99 (not in the facts)"
    ]  # the retry is told what was wrong


async def test_falls_back_to_template_after_two_failures():
    fp = factpack_for("sustained_pressure", "NBR")
    draft, generated_by, result, attempts, _ = await generate_insight(
        ScriptedProvider(["bad", "bad"]), FALLBACK, fp, modes()["tactical"], 8
    )
    assert generated_by == "template" and result.passed
    assert [(a.generated_by, a.passed) for a in attempts] == [
        ("scripted", False),
        ("scripted", False),
        ("template", True),
    ]


@pytest.mark.parametrize("failure", [RuntimeError("boom"), "slow"])
async def test_falls_back_on_error_or_timeout(failure):
    fp = factpack_for("momentum_shift", "RVA")
    draft, generated_by, result, attempts, _ = await generate_insight(
        ScriptedProvider([failure]), FALLBACK, fp, modes()["casual"], timeout=0.05
    )
    assert generated_by == "template" and result.passed
    assert attempts[0].violations[0].startswith("provider error:")


def test_template_fallback_passes_for_every_trigger():
    packs, recaps = demo_factpacks()
    for mode in ("casual", "tactical"):
        for _, fp in packs:
            assert validate_insight(FALLBACK.insight(fp, modes()[mode]), fp, modes()[mode]).passed
        for _, fp in recaps:
            assert validate_recap(FALLBACK.recap(fp, modes()[mode]), fp).passed


def test_factpacks_never_contain_the_future():
    packs, recaps = demo_factpacks()
    for _, fp in packs + recaps:  # type: ignore[operator]
        assert all(s <= fp.clock_second for s in fp.event_seconds.values())


def test_goal_factpack_has_score_before_and_after():
    fp = factpack_for("goal", "NBR")
    assert fp.score_before == {"Northbridge FC": 0, "Riverside Athletic": 1}
    assert fp.score_after == {"Northbridge FC": 1, "Riverside Athletic": 1}
    assert fp.trigger.player == "Tomas Reyes" and fp.trigger.minute == 69


async def test_half_time_recap_uses_only_first_half_events():
    _, recaps = demo_factpacks()
    detection, fp = recaps[0]
    assert fp.scope == "half_time" and fp.clock_second == 2820
    draft, generated_by, result, _ = await generate_recap(MOCK, FALLBACK, fp, modes()["tactical"], 8)
    assert result.passed and generated_by == "mock"
    assert {m.minute for m in draft.key_moments} <= {12, 23, 35, 42, 44}
    assert "Tomas Reyes" not in draft.body  # the 69' scorer cannot appear at half-time
    assert 4 <= draft.body.count(". ") + 1 <= 6
