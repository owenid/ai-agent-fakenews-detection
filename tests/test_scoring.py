from unittest.mock import patch

from app.schemas import AIFactCheck, AnalyzeRequest, CitedSource, KeyClaim
from app.scoring import analyze


def _fake_fact_check(**overrides) -> AIFactCheck:
    defaults = dict(
        verdict="true",
        confidence=0.9,
        summary="Multiple credible outlets corroborate this claim.",
        key_claims=[KeyClaim(claim="X happened", assessment="true", explanation="Confirmed by AP.")],
        cited_sources=[CitedSource(name="AP News", url="https://apnews.com/x", stance="supports")],
        red_flags=[],
        ai_score=95.0,
        used_web_search=True,
    )
    defaults.update(overrides)
    return AIFactCheck(**defaults)


def test_analyze_high_credibility_source_and_ai_score():
    request = AnalyzeRequest(
        text="Officials confirmed the new policy will take effect next month, according to city records.",
        url="https://www.reuters.com/world/policy-story",
    )
    with patch("app.scoring.run_fact_check", return_value=_fake_fact_check()):
        result = analyze(request)

    assert result.verdict == "likely_credible"
    assert result.composite_score > 70
    assert result.breakdown.source_reputation.category == "high_credibility"
    assert result.breakdown.ai_fact_check.ai_score == 95.0


def test_analyze_unreliable_source_and_low_ai_score():
    request = AnalyzeRequest(
        text="YOU WON'T BELIEVE this SHOCKING secret they don't want you to know!!!",
        url="https://beforeitsnews.com/story",
    )
    fake = _fake_fact_check(
        verdict="false",
        summary="This claim is fabricated and contradicted by credible sources.",
        ai_score=5.0,
        red_flags=["No named sources", "Contradicts established facts"],
    )
    with patch("app.scoring.run_fact_check", return_value=fake):
        result = analyze(request)

    assert result.verdict == "likely_misinformation"
    assert result.composite_score < 45


def test_analyze_without_openai_key_reweights_score():
    request = AnalyzeRequest(
        text="Officials confirmed the new policy will take effect next month, according to city records.",
        url="https://www.reuters.com/world/policy-story",
    )
    unavailable = AIFactCheck(error="no key", summary="AI fact-check unavailable.")
    with patch("app.scoring.run_fact_check", return_value=unavailable):
        result = analyze(request)

    assert result.breakdown.weights["ai_fact_check"] == 0.0
    assert result.breakdown.ai_fact_check.ai_score is None
    # Composite should be driven entirely by source reputation + language style.
    assert result.composite_score > 0
