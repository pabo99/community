"""Tests for the liveness endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_returns_success(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
