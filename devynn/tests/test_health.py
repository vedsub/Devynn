"""
Smoke-test for the /health endpoint.
Run with:  WHISPER_MODEL_SIZE=mock MODEL_PATH=mock pytest tests/test_health.py -v
"""

import os

os.environ.setdefault("WHISPER_MODEL_SIZE", "mock")
os.environ.setdefault("MODEL_PATH", "mock")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body():
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "model_version" in body
    assert isinstance(body["model_loaded"], bool)
