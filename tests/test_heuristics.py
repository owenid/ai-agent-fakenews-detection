from app.heuristics import assess_language_style, assess_source_reputation, extract_domain


def test_extract_domain_basic():
    assert extract_domain("https://www.reuters.com/world/article-123") == "reuters.com"


def test_extract_domain_none_for_missing_url():
    assert extract_domain(None) is None


def test_source_reputation_high_credibility():
    result = assess_source_reputation("https://www.bbc.com/news/story", None)
    assert result.category == "high_credibility"
    assert result.score >= 80


def test_source_reputation_known_unreliable():
    result = assess_source_reputation("https://beforeitsnews.com/some-story", None)
    assert result.category == "known_unreliable"
    assert result.score <= 20


def test_source_reputation_unknown_domain():
    result = assess_source_reputation("https://random-blog-example.net/post", None)
    assert result.category == "unknown"
    assert result.score == 50


def test_source_reputation_no_url():
    result = assess_source_reputation(None, None)
    assert result.domain is None
    assert result.category == "unknown"


def test_language_style_clean_text_scores_high():
    text = (
        "Officials from the city council announced a new budget plan on Tuesday. "
        "The plan, reviewed by independent auditors, allocates funds for road repairs."
    )
    result = assess_language_style(text)
    assert result.score >= 90
    assert result.flags == []


def test_language_style_flags_clickbait_and_caps():
    text = "YOU WON'T BELIEVE what they found!!! This is SHOCKING and EXPOSED!!!"
    result = assess_language_style(text)
    assert result.score < 90
    assert len(result.flags) > 0


def test_language_style_flags_vague_attribution():
    text = (
        "Sources say the plan will change everything and experts say it is unprecedented. "
        "Many believe this will have lasting effects on the region for years to come."
    )
    result = assess_language_style(text)
    assert any("attribution" in flag.lower() for flag in result.flags)
