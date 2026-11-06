from . import config
from .heuristics import assess_language_style, assess_source_reputation
from .openai_client import run_fact_check
from .schemas import AnalyzeRequest, AnalyzeResponse, ScoreBreakdown, Verdict


def _verdict_from_score(score: float) -> Verdict:
    if score >= 70:
        return "likely_credible"
    if score >= 45:
        return "mixed_or_uncertain"
    return "likely_misinformation"


def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    source_reputation = assess_source_reputation(request.url, request.source_name)
    language_style = assess_language_style(request.text)
    ai_fact_check = run_fact_check(request.text, request.url, request.source_name)

    weights = {
        "source_reputation": config.WEIGHT_SOURCE_REPUTATION,
        "language_style": config.WEIGHT_LANGUAGE_STYLE,
        "ai_fact_check": config.WEIGHT_AI_FACT_CHECK,
    }

    if ai_fact_check.ai_score is None:
        # AI fact-check unavailable: redistribute its weight proportionally
        # across the two heuristic components instead of assuming a neutral
        # score, so the composite reflects real signal only.
        remaining = weights["source_reputation"] + weights["language_style"]
        if remaining > 0:
            weights = {
                "source_reputation": weights["source_reputation"] / remaining,
                "language_style": weights["language_style"] / remaining,
                "ai_fact_check": 0.0,
            }
        composite = (
            source_reputation.score * weights["source_reputation"]
            + language_style.score * weights["language_style"]
        )
    else:
        composite = (
            source_reputation.score * weights["source_reputation"]
            + language_style.score * weights["language_style"]
            + ai_fact_check.ai_score * weights["ai_fact_check"]
        )

    composite = max(0.0, min(100.0, composite))

    breakdown = ScoreBreakdown(
        source_reputation=source_reputation,
        language_style=language_style,
        ai_fact_check=ai_fact_check,
        weights=weights,
    )

    return AnalyzeResponse(
        composite_score=round(composite, 1),
        verdict=_verdict_from_score(composite),
        breakdown=breakdown,
    )
