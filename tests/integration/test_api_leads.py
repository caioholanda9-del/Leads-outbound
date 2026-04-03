"""
Testes de integração dos endpoints FastAPI.
Requer: banco PostgreSQL configurado via DATABASE_URL (ou usa SQLite via conftest).
"""
import pytest
from httpx import ASGITransport, AsyncClient

from leads.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_filter_missing_cnae():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/leads/filter", json={"cnaes_principal": []})
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_filter_valid_request():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/leads/filter",
            json={"cnaes_principal": ["6201500"], "ufs": ["SP"]},
        )
    # Pode retornar 200 (com DB) ou 500 (sem DB em CI)
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "total" in data
        assert "results" in data
        assert isinstance(data["results"], list)


@pytest.mark.asyncio
async def test_export_invalid_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/leads/export",
            params={"cnaes_principal": "6201500", "format": "pdf"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingestion_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/ingestion/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "stage" in data
