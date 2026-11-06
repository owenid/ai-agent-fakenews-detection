# Fake News Detection Agent

A browser-accessible AI agent that scores the credibility of a piece of text —
a news article, claim, headline, or social media post — using three combined
signals, and shows its work at every step instead of returning a single
opaque "AI verdict."

## What it does

1. **Source reputation** — extracts the domain from the submitted URL and
   checks it against curated lists of high-credibility outlets (Reuters, AP,
   BBC, NYT, WHO, CDC, etc.) and known-unreliable/hoax/satire sites. An
   unfamiliar domain scores neutral, deferring to the AI fact-check.
2. **Language & style heuristics** — a pure writing-style signal (no factual
   judgement) that flags clickbait phrasing, vague/unnamed attribution
   ("sources say"), excessive punctuation/ALL-CAPS, and very short input.
3. **AI fact-check (OpenAI)** — sends the text to OpenAI's Responses API with
   the `web_search` tool enabled, so the model searches the live web to
   verify each claim, assess the source's reliability, and return a
   structured verdict, confidence score, per-claim breakdown, cited sources
   (each tagged supports/contradicts/context), and any credibility red
   flags.

These three signals are combined into a single weighted **composite score
(0–100)** and an overall verdict — `likely_credible`, `mixed_or_uncertain`,
or `likely_misinformation` — each with its own color coding. If the AI
fact-check is unavailable (no API key, or a failed/incomplete request), its
weight is redistributed proportionally across the two heuristic scores
rather than assumed neutral, and the specific failure reason is surfaced in
the UI and logged server-side.

## Interface

- A single-page, two-column layout (form on the left, results on the right)
  sized to the viewport, so the full result — score gauge, verdict badge,
  and all three signal cards — is visible without scrolling the page on
  typical desktop/laptop windows. Only the Key Claims / Cited Sources panel
  scrolls internally, since AI-generated content there is unbounded in
  length; below ~860px width it falls back to a normal scrolling page.
- A dark/light **theme toggle** (sun/moon icon, top right) that persists
  across sessions via `localStorage`.
- Inline citations the model embeds as markdown (`[text](url)`) are rendered
  as real clickable links, not raw text.
- "Text to analyze" and "Source URL" are both required fields; "Source /
  publisher name" is optional.

## Architecture

```
backend/            FastAPI app (no database — fully stateless)
  app/
    main.py          API routes; serves the frontend as static files with
                      caching disabled so updates are always picked up
    scoring.py        Combines heuristics + AI fact-check into a composite score
    heuristics.py     Source-reputation lookup + language/style scoring
    openai_client.py  OpenAI Responses API call (web_search + structured JSON,
                       with defensive parsing and detailed error/status logging)
    schemas.py        Pydantic request/response models and verdict enums
    config.py         Env-driven configuration (model, weights, API key)
  requirements.txt
frontend/            Static HTML/CSS/JS single-page UI (no build step)
  index.html
  style.css           Dark/light theme via CSS custom properties
  app.js               Rendering, theme toggle, markdown-link parsing
  favicon.svg
tests/               Pytest suite (22 tests; OpenAI calls are mocked)
  conftest.py
  test_api.py          FastAPI TestClient integration tests
  test_heuristics.py   Source-reputation + language/style unit tests
  test_openai_client.py  JSON-parsing/error-handling unit tests
  test_scoring.py      Composite-score and weight-fallback unit tests
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
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in a browser, paste in some text and a source
URL, and click **Analyze**.

If `OPENAI_API_KEY` is not set, the app still runs — it falls back to
scoring using only the source-reputation and language/style heuristics, and
clearly labels the AI fact-check as unavailable in the UI.

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

The `openai` Python package is pinned to `>=1.66.0,<2.0.0` in
`requirements.txt` — this is the earliest release whose `client.responses`
API matches what `openai_client.py` calls; older versions will fail with
`'OpenAI' object has no attribute 'responses'`.

## API

`POST /api/analyze`

```json
{
  "text": "Article text or claim to analyze...",
  "url": "https://example.com/article",
  "source_name": "Example News Network"
}
```

`text` is required (minimum 10 characters); `url` and `source_name` are
optional at the API layer (the frontend form requires `url` for consistent
source-reputation scoring, but the endpoint itself does not enforce that).

Returns a JSON object with `composite_score`, `verdict`, and a detailed
`breakdown` of each component score (see `backend/app/schemas.py`).

`GET /api/health` returns `{"status": "ok"}`.

## Security notes

- All dynamic content is inserted via DOM APIs (`textContent`,
  `createElement`), never `innerHTML`, so AI- or user-supplied text can never
  execute as script in the browser.
- Parsed citation links are restricted to `http`/`https` URLs before being
  turned into clickable anchors.
- The OpenAI API key is read from environment configuration and is never
  sent to or exposed in the frontend.

## Notes & limitations

- The curated source-reputation lists in `heuristics.py` are small seed
  lists, not an exhaustive media-bias database. For unfamiliar domains the
  AI fact-check (grounded by live web search) is the primary signal.
- The system is stateless — no history of past analyses is stored.
- This tool is meant to assist judgment, not replace it — always check
  primary sources for anything consequential.
