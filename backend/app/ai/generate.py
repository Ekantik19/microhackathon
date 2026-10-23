"""The grounded generation loop: draft → validate → (regenerate once with the violations) → template fallback.
Every attempt is recorded so the UI can show an honest "Grounding check"."""

import asyncio
import logging
import time

from app.ai.fallback import TemplateFallback
from app.ai.models import FactPack, InsightDraft, RecapDraft, RecapFactPack
from app.ai.modes import ModeConfig
from app.ai.providers import AIProvider
from app.ai.validator import validate_insight, validate_recap
from app.models.insights import GenerationAttempt, ValidatorResult

log = logging.getLogger(__name__)
MAX_PROVIDER_ATTEMPTS = 2  # the first draft, plus one regeneration with the violations listed


async def generate_insight(
    provider: AIProvider, fallback: TemplateFallback, fp: FactPack, mode: ModeConfig, timeout: float
) -> tuple[InsightDraft, str, ValidatorResult, list[GenerationAttempt], int]:
    start = time.perf_counter()
    attempts: list[GenerationAttempt] = []
    violations: list[str] | None = None
    method = (
        provider.generate_live_insight
        if fp.trigger.kind == "pattern"
        else provider.generate_event_explanation
    )
    for _ in range(MAX_PROVIDER_ATTEMPTS):
        try:
            draft = await asyncio.wait_for(method(fp, mode, violations), timeout=timeout)
        except Exception as exc:  # timeout, network, bad JSON: fall back, never crash
            attempts.append(
                GenerationAttempt(
                    generated_by=provider.name,
                    passed=False,
                    violations=[f"provider error: {type(exc).__name__}"],
                )
            )
            log.warning(
                "ai provider=%s trigger=%s mode=%s error=%s",
                provider.name,
                fp.trigger.detection_id,
                mode.name,
                type(exc).__name__,
            )
            break
        result = validate_insight(draft, fp, mode)
        attempts.append(
            GenerationAttempt(generated_by=provider.name, passed=result.passed, violations=result.violations)
        )
        log.info(
            "ai provider=%s trigger=%s mode=%s validator=%s violations=%d",
            provider.name,
            fp.trigger.detection_id,
            mode.name,
            "passed" if result.passed else "failed",
            len(result.violations),
        )
        if result.passed:
            return draft, provider.name, result, attempts, int((time.perf_counter() - start) * 1000)
        violations = result.violations
    draft = fallback.insight(fp, mode)
    result = validate_insight(draft, fp, mode)
    attempts.append(
        GenerationAttempt(generated_by="template", passed=result.passed, violations=result.violations)
    )
    return draft, "template", result, attempts, int((time.perf_counter() - start) * 1000)


async def generate_recap(
    provider: AIProvider, fallback: TemplateFallback, fp: RecapFactPack, mode: ModeConfig, timeout: float
) -> tuple[RecapDraft, str, ValidatorResult, list[GenerationAttempt]]:
    attempts: list[GenerationAttempt] = []
    violations: list[str] | None = None
    for _ in range(MAX_PROVIDER_ATTEMPTS):
        try:
            draft = await asyncio.wait_for(
                provider.generate_match_recap(fp, mode, violations), timeout=timeout
            )
        except Exception as exc:
            attempts.append(
                GenerationAttempt(
                    generated_by=provider.name,
                    passed=False,
                    violations=[f"provider error: {type(exc).__name__}"],
                )
            )
            break
        result = validate_recap(draft, fp)
        attempts.append(
            GenerationAttempt(generated_by=provider.name, passed=result.passed, violations=result.violations)
        )
        if result.passed:
            return draft, provider.name, result, attempts
        violations = result.violations
    draft = fallback.recap(fp, mode)
    result = validate_recap(draft, fp)
    attempts.append(
        GenerationAttempt(generated_by="template", passed=result.passed, violations=result.violations)
    )
    return draft, "template", result, attempts
