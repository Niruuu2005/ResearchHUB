import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify that /health returns HTTP 200 and expected metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["service"] in ("ResearchOps AI", "ResearchLite")
    assert "version" in data


def test_root_endpoint_serves_html():
    """Verify that root / serves index.html or welcome response."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "") or "application/json" in response.headers.get("content-type", "")


def test_system_config_exposes_no_secrets():
    response = client.get("/api/system/config")
    assert response.status_code == 200
    data = response.json()
    assert "llm_provider" in data
    assert "embedding_model" in data
    assert "database_dialect" in data
    assert "use_celery" in data
    assert "llm_api_key" not in data
    assert "api_key" not in data
    # Nested secret keys must not appear either
    blob = str(data).lower()
    assert "sk-" not in blob
