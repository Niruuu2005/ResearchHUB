import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_readiness_probe():
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "database" in data
    assert data["database"] == "healthy"


def test_prometheus_metrics():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    text = res.text
    assert "researchops_total_papers" in text
    assert "researchops_active_background_jobs" in text
    assert "researchops_http_requests_total" not in text


def test_devops_overview_and_deployments():
    overview_res = client.get("/api/operations/overview")
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert "total_papers" in data
    assert "providers" in data
    assert "api_health" in data

    # Simulated rollback endpoint removed — build metadata remains available
    assert client.post("/api/operations/rollback").status_code == 404
    deploys = client.get("/api/operations/deployments")
    assert deploys.status_code == 200
    assert isinstance(deploys.json(), list)
