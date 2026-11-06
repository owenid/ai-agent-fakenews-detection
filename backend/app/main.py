import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from .schemas import AnalyzeRequest, AnalyzeResponse
from .scoring import analyze


class NoCacheStaticFiles(StaticFiles):
    """Serves frontend files with caching disabled.

    During active development the frontend changes on nearly every request;
    without this, browsers and intermediary proxies (e.g. the Codespaces
    port-forwarding tunnel) can keep serving a stale index.html/app.js/
    style.css even after a hard refresh, since Starlette's default
    StaticFiles response still supports conditional (304) caching.
    """

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

app = FastAPI(title="Fake News Detection Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(request: AnalyzeRequest) -> AnalyzeResponse:
    return analyze(request)


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", NoCacheStaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
