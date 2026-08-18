from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import AIFactCheck

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_returns_expected_shape():
    unavailable = AIFactCheck(error="no key", summary="AI fact-check unavailable.")
    with patch("app.scoring.run_fact_check", return_value=unavailable):
        response = client.post(
            "/api/analyze",
            json={
                "text": "Officials confirmed the new policy will take effect next month.",
                "url": "https://www.bbc.com/news/story",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "composite_score" in data
    assert "verdict" in data
    assert "breakdown" in data


def test_analyze_endpoint_rejects_short_text():
    response = client.post("/api/analyze", json={"text": "short"})
    assert response.status_code == 422
