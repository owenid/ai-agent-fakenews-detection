# Fake News Detection Agent

A browser-accessible AI agent that scores the credibility of a piece of text
(a news article, claim, or social media post) using three combined signals:

1. **Source reputation** — checks the domain of a provided URL against a
   curated list of high-credibility and known-unreliable outlets.
2. **Language & style heuristics** — flags clickbait phrasing, vague/unnamed
   attribution ("sources say"), excessive punctuation/ALL-CAPS, etc.
3. **AI fact-check (OpenAI)** — sends the text to OpenAI's Responses API with
   the `web_search` tool enabled, so the model can search the live web for
   credible corroborating or contradicting sources, identify key claims, and
   return a structured verdict, confidence, cited sources, and red flags.

These three signals are combined into a single weighted **composite score
(0–100)** and an overall verdict: `likely_credible`, `mixed_or_uncertain`, or
`likely_misinformation`.

## Architecture

```
backend/            FastAPI app
  app/
    main.py         API routes + serves the frontend as static files
    scoring.py       Combines heuristics + AI fact-check into a composite score
    heuristics.py    Source-reputation lookup + language/style scoring
    openai_client.py OpenAI Responses API call (web_search + structured JSON)
    schemas.py       Pydantic request/response models
    config.py        Env-driven configuration (model, weights, API key)
frontend/           Static HTML/CSS/JS single-page UI (no build step)
tests/              Pytest suite (OpenAI calls are mocked)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...
```

## Run

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in a browser, paste in some text (and optionally a
source URL), and click **Analyze**.

If `OPENAI_API_KEY` is not set, the app still runs — it falls back to scoring
using only the source-reputation and language/style heuristics, and clearly
labels the AI fact-check as unavailable.

## Tests

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt pytest httpx
python -m pytest tests/ -v
```

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | Required for the AI fact-check step. |
| `OPENAI_MODEL` | `gpt-4o` | Model used for fact-checking; must support the Responses API. |
| `ENABLE_WEB_SEARCH` | `true` | Whether to grant the model the `web_search` tool. |
| `WEIGHT_SOURCE_REPUTATION` | `0.3` | Weight of the source-reputation score. |
| `WEIGHT_AI_FACT_CHECK` | `0.5` | Weight of the AI fact-check score. |
| `WEIGHT_LANGUAGE_STYLE` | `0.2` | Weight of the language/style score. |

If the AI fact-check is unavailable (no API key, or a request error), its
weight is automatically redistributed proportionally across the two
heuristic scores rather than assumed neutral.

## API

`POST /api/analyze`

```json
{
  "text": "Article text or claim to analyze...",
  "url": "https://example.com/article",
  "source_name": "Example News Network"
}
```

Returns a JSON object with `composite_score`, `verdict`, and a detailed
`breakdown` of each component score (see `backend/app/schemas.py`).

## Notes & limitations

- The curated source-reputation lists in `heuristics.py` are small seed
  lists, not an exhaustive media-bias database. For unfamiliar domains the
  AI fact-check (grounded by live web search) is the primary signal.
- This tool is meant to assist judgment, not replace it — always check
  primary sources for anything consequential.
