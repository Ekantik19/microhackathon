"""Phase 9: the grounding validator catches invented numbers, unknown names and future events."""

from app.ai.models import InsightDraft
from app.ai.validator import validate_insight
from app.models.insights import SupportingStat
from tests.fixtures.demo import factpack_for, modes

FP = factpack_for("sustained_pressure", "NBR")  # 66:40: NBR 89% possession, 3 shots, 6 final-third entries
TACTICAL = modes()["tactical"]


def draft(body: str, headline: str = "Northbridge keep pushing", stats=None, cited=None) -> InsightDraft:
    return InsightDraft(
        headline=headline, body=body, supporting_stats=stats or [], cited_event_ids=cited or []
    )


def test_grounded_text_passes():
    result = validate_insight(
        draft(
            "Northbridge FC have 89% possession, three shots and 6 final-third entries in the last five minutes.",
            stats=[SupportingStat(label="Possession (last 5)", value=89, unit="%")],
            cited=FP.trigger.event_ids[:2],
        ),
        FP,
        TACTICAL,
    )
    assert result.passed, result.violations


def test_catches_an_invented_number():
    result = validate_insight(
        draft("Northbridge FC have 89% possession and 7 shots in the last five minutes."), FP, TACTICAL
    )
    assert not result.passed
    assert result.violations == ["invented number 7 (not in the facts)"]


def test_catches_an_invented_number_word_and_percentage():
    result = validate_insight(
        draft("Northbridge FC have 91% of the ball and fourteen corners."), FP, TACTICAL
    )
    assert set(result.violations) == {
        "invented number 91 (not in the facts)",
        "invented number 14 (not in the facts)",
    }
    # 11 is a real fact (Riverside's possession share), so it is allowed
    assert validate_insight(draft("Riverside Athletic have 11% of the ball."), FP, TACTICAL).passed


def test_catches_an_unknown_name():
    result = validate_insight(draft("Northbridge FC press as Marco Silvestri drives forward."), FP, TACTICAL)
    assert "unknown name 'Marco' (not a team or player in this match)" in result.violations
    assert "unknown name 'Silvestri' (not a team or player in this match)" in result.violations


def test_allows_possessives_hyphenated_names_and_short_names():
    result = validate_insight(
        draft("Riverside's Leon Vasquez-Aldana and Northbridge's Tomas Reyes."), FP, TACTICAL
    )
    assert result.passed, result.violations


def test_catches_a_future_event_id_and_an_unknown_one():
    future = "e01900"  # an 86' event, cited at 66:40
    result = validate_insight(draft("Northbridge FC keep pushing.", cited=[future, "e99999"]), FP, TACTICAL)
    assert "cited event e01900 is not in the facts" in result.violations
    assert "cited event e99999 is not in the facts" in result.violations

    leaky = FP.model_copy(update={"event_seconds": {**FP.event_seconds, future: FP.clock_second + 1200}})
    result = validate_insight(draft("Northbridge FC keep pushing.", cited=[future]), leaky, TACTICAL)
    assert result.violations == ["cited event e01900 is after the clock (future leakage)"]


def test_catches_a_supporting_stat_that_does_not_match():
    stats = [
        SupportingStat(label="Shots (last 5)", value=5, unit=""),  # 5 is a fact (window length) but not shots
        SupportingStat(label="Corners", value=3, unit=""),  # no such fact
    ]
    result = validate_insight(draft("Northbridge FC keep pushing.", stats=stats), FP, TACTICAL)
    assert "supporting stat 'Shots (last 5)' = 5 does not match the facts" in result.violations
    assert "supporting stat 'Corners' does not use a fact label" in result.violations


def test_enforces_the_mode_word_limit():
    long_body = "Northbridge FC keep pushing forward " * 10
    result = validate_insight(draft(long_body.strip()), FP, modes()["casual"])
    assert any(v.startswith("body has 50 words (limit 35)") for v in result.violations)
