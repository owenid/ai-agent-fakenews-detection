import json
import re

from openai import OpenAI

from . import config
from .schemas import AIFactCheck

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


SYSTEM_PROMPT = """\
You are a fact-checking assistant. Given a piece of text (a news article, \
social media post, or claim) and optionally its source, your job is to:

1. Identify the main factual claims made in the text.
2. Use web search to check each claim against credible, verifiable sources \
(established news outlets, government/scientific institutions, fact-checking \
organizations). Prefer primary sources when possible.
3. Judge the overall reliability of the source itself, if one is given.
4. Produce a single overall verdict and a numeric ai_score from 0-100, where \
0 means confirmed false/fabricated, 50 means unverifiable/mixed evidence, and \
100 means well-corroborated by multiple credible, independent sources.

Respond with ONLY a single JSON object (no markdown fences, no commentary) \
matching exactly this shape:

{
  "verdict": "true" | "mostly_true" | "misleading" | "false" | "unverified" | "satire_or_opinion",
  "confidence": <float 0-1>,
  "summary": "<2-4 sentence plain-language summary of your findings>",
  "key_claims": [
    {"claim": "<claim text>", "assessment": "<same enum as verdict>", "explanation": "<why>"}
  ],
  "cited_sources": [
    {"name": "<publisher/site name>", "url": "<url or null>", "stance": "supports" | "contradicts" | "context"}
  ],
  "red_flags": ["<any credibility concerns, e.g. no named sources, contradicts known facts, fabricated quotes>"],
  "ai_score": <float 0-100>
}
"""


def _build_user_prompt(text: str, url: str | None, source_name: str | None) -> str:
    parts = [f"TEXT TO ANALYZE:\n{text.strip()}"]
    if url:
        parts.append(f"\nSOURCE URL: {url}")
    if source_name:
        parts.append(f"\nSOURCE NAME: {source_name}")
    return "\n".join(parts)


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            raw = brace_match.group(0)
    return json.loads(raw)


def run_fact_check(text: str, url: str | None, source_name: str | None) -> AIFactCheck:
    if not config.OPENAI_API_KEY:
        return AIFactCheck(
            error="OPENAI_API_KEY not configured; AI fact-check skipped.",
            summary="AI fact-check unavailable — no OpenAI API key configured on the server.",
        )

    client = _get_client()
    user_prompt = _build_user_prompt(text, url, source_name)
    tools = [{"type": "web_search"}] if config.ENABLE_WEB_SEARCH else []
    used_web_search = False

    try:
        response = client.responses.create(
            model=config.OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=user_prompt,
            tools=tools,
        )
        used_web_search = bool(tools) and any(
            getattr(item, "type", None) == "web_search_call"
            for item in getattr(response, "output", [])
        )
        raw_text = response.output_text
        data = _extract_json(raw_text)
        data["used_web_search"] = used_web_search
        return AIFactCheck(**data)
    except Exception as exc:  # noqa: BLE001 - surface any failure as a soft error
        return AIFactCheck(
            error=f"AI fact-check failed: {exc}",
            summary="AI fact-check could not be completed due to an error.",
            used_web_search=used_web_search,
        )
