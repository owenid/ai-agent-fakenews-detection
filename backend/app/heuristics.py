import re

import tldextract

from .schemas import LanguageStyle, SourceReputation

# Small curated seed lists. These are intentionally conservative starting
# points, not an exhaustive media-bias database — the AI fact-check step
# (which can search the web) is the primary signal for unfamiliar domains.
HIGH_CREDIBILITY_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "npr.org",
    "nytimes.com",
    "wsj.com",
    "washingtonpost.com",
    "theguardian.com",
    "afp.com",
    "bloomberg.com",
    "economist.com",
    "nature.com",
    "science.org",
    "who.int",
    "cdc.gov",
    "nih.gov",
    "un.org",
}

KNOWN_UNRELIABLE_DOMAINS = {
    "beforeitsnews.com",
    "worldnewsdailyreport.com",
    "empirenews.net",
    "nationalreport.net",
    "theonion.com",  # satire, not misinformation, but not a factual source
    "babylonbee.com",  # satire
    "yournewswire.com",
    "newspunch.com",
    "infowars.com",
}

CLICKBAIT_PHRASES = [
    r"\byou won'?t believe\b",
    r"\bshocking\b",
    r"\bthis one trick\b",
    r"\bdoctors hate (him|her|them)\b",
    r"\bwhat happens next\b",
    r"\bthe truth (about|they don'?t want)\b",
    r"\bmiracle cure\b",
    r"\bexposed\b",
    r"\bthey don'?t want you to know\b",
    r"\bwake up\b",
    r"\bmainstream media (won'?t|refuses to) (tell|show) you\b",
    r"\bgo viral\b",
]

VAGUE_ATTRIBUTION_PHRASES = [
    r"\bsources say\b",
    r"\bexperts say\b",
    r"\bpeople are saying\b",
    r"\bmany believe\b",
    r"\bit is (widely )?known\b",
    r"\bstudies show\b(?!.*\()",
]


def extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    ext = tldextract.extract(url)
    if not ext.domain or not ext.suffix:
        return None
    return f"{ext.domain}.{ext.suffix}".lower()


def assess_source_reputation(url: str | None, source_name: str | None) -> SourceReputation:
    domain = extract_domain(url)

    if domain in HIGH_CREDIBILITY_DOMAINS:
        return SourceReputation(
            domain=domain,
            category="high_credibility",
            score=90.0,
            notes="Domain matches a well-established news/scientific/institutional outlet.",
        )
    if domain in KNOWN_UNRELIABLE_DOMAINS:
        return SourceReputation(
            domain=domain,
            category="known_unreliable",
            score=10.0,
            notes="Domain matches a known satire, hoax, or low-reliability outlet.",
        )
    if domain:
        return SourceReputation(
            domain=domain,
            category="unknown",
            score=50.0,
            notes="Domain not in curated reputation lists; relying on AI fact-check for signal.",
        )
    return SourceReputation(
        domain=None,
        category="unknown",
        score=50.0,
        notes="No URL/source provided; source reputation not evaluated.",
    )


def assess_language_style(text: str) -> LanguageStyle:
    score = 100.0
    flags: list[str] = []
    lowered = text.lower()

    for pattern in CLICKBAIT_PHRASES:
        if re.search(pattern, lowered):
            score -= 8
            flags.append(f"Clickbait-style phrasing detected: matches /{pattern}/")

    for pattern in VAGUE_ATTRIBUTION_PHRASES:
        if re.search(pattern, lowered):
            score -= 5
            flags.append(f"Vague, unnamed attribution: matches /{pattern}/")

    exclamations = text.count("!")
    if exclamations >= 3:
        score -= min(15, exclamations * 2)
        flags.append(f"Excessive exclamation marks ({exclamations}).")

    words = re.findall(r"[A-Za-z]{3,}", text)
    if words:
        caps_words = [w for w in words if w.isupper()]
        caps_ratio = len(caps_words) / len(words)
        if caps_ratio > 0.1:
            score -= 15
            flags.append(f"High proportion of ALL-CAPS words ({caps_ratio:.0%}).")

    if len(text.strip()) < 100:
        score -= 5
        flags.append("Very short text provides limited context for analysis.")

    score = max(0.0, min(100.0, score))
    return LanguageStyle(score=score, flags=flags)
