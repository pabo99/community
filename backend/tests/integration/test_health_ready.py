"""Readiness endpoint integration tests against real PostgreSQL."""

from __future__ import annotations

import app.api.health as health_module
import pytest
from app.config import get_settings
from app.db import engine as engine_module
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import Engine

pytestmark = pytest.mark.integration


@pytest.fixture
def client(migrated_engine: Engine) -> TestClient:
    """TestClient whose readiness probe hits the real test database.

    ``migrated_engine`` has already repointed DATABASE_URL at the test
    database; clearing the settings/engine caches makes the app use it.
    """
    get_settings.cache_clear()
    engine_module.get_engine.cache_clear()
    engine_module.get_sessionmaker.cache_clear()
    return TestClient(create_app())


def test_liveness_is_database_independent(client: TestClient) -> None:
    # Liveness must not depend on the database being reachable.
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_ok_when_database_available(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_503_when_database_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate PostgreSQL becoming unavailable after startup.
    monkeypatch.setattr(health_module, "database_is_available", lambda: False)

    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}
    # Readiness must not leak connection details.
    body = response.text
    assert "postgresql" not in body
    assert "psycopg" not in body
