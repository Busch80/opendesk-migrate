"""Integration tests for tenant API routes.

Uses httpx ASGI transport + a fresh sqlite-free-style test DB.
Since we target Postgres-only types (UUID, INET, ARRAY, JSONB) for MVP
these tests are also Postgres-gated (skipped otherwise).
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgres"),
    reason="Tenant API integration tests require Postgres (UUID, INET, JSONB, ARRAY)",
)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert body["version"]


def test_create_tenant_requires_code(client):
    r = client.post("/api/v1/tenants", json={"display_name": "Test"})
    assert r.status_code == 422


def test_full_tenant_create_flow(client):
    payload = {
        "code": "testco",
        "display_name": "Test Co AG",
        "m365_tenant_id": "00000000-0000-0000-0000-000000000000",
        "m365_client_id": "cid",
        "m365_client_secret": "csecret",
        "ox_admin_url": "https://ox.example",
        "ox_admin_user": "admin",
        "ox_admin_password": "changeme",
    }
    r = client.post("/api/v1/tenants", json=payload)
    assert r.status_code == 201, r.text
    tenant_id = r.json()["id"]

    list_r = client.get("/api/v1/tenants")
    assert list_r.status_code == 200
    assert any(t["code"] == "testco" for t in list_r.json())

    get_r = client.get(f"/api/v1/tenants/{tenant_id}")
    assert get_r.status_code == 200
    assert get_r.json()["display_name"] == "Test Co AG"
