import json
import logging
import re

from openai import OpenAI

from . import config
from .schemas import AIFactCheck

logger = logging.getLogger(__name__)

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

Your entire response must be that JSON object and nothing else — no preamble, no \
explanation, no markdown code fences, even if the text is short, ambiguous, or you are \
uncertain. If you cannot verify a claim, still return the JSON with "verdict": "unverified" \
rather than declining to answer.
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
    if not raw:
        raise ValueError("Model returned an empty response (no text output).")

    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            raw = brace_match.group(0)
        else:
            preview = raw[:300] + ("…" if len(raw) > 300 else "")
            raise ValueError(f"No JSON object found in model output. Raw response: {preview!r}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        preview = raw[:300] + ("…" if len(raw) > 300 else "")
        raise ValueError(f"Model output was not valid JSON ({exc}). Raw response: {preview!r}") from exc


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
        status = getattr(response, "status", None)
        incomplete_details = getattr(response, "incomplete_details", None)
        logger.info(
            "AI fact-check response: status=%s incomplete_details=%s output_text_len=%d used_web_search=%s",
            status, incomplete_details, len(raw_text or ""), used_web_search,
        )
        if raw_text:
            logger.debug("AI fact-check raw output_text: %r", raw_text)

        if not (raw_text or "").strip() and status != "completed":
            reason = getattr(incomplete_details, "reason", None) if incomplete_details else None
            raise ValueError(
                f"OpenAI response did not complete (status={status!r}"
                + (f", reason={reason!r}" if reason else "")
                + "). This usually means the request hit a token/time limit before producing output — "
                "try a shorter input or disable web search."
            )

        data = _extract_json(raw_text)
        data["used_web_search"] = used_web_search
        return AIFactCheck(**data)
    except Exception as exc:  # noqa: BLE001 - surface any failure as a soft error
        logger.exception("AI fact-check request failed")
        return AIFactCheck(
            error=f"AI fact-check failed: {exc}",
            summary=f"AI fact-check could not be completed: {exc}",
            used_web_search=used_web_search,
        )
