"""Tests for core API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_query_requires_input(client, auth_headers):
    resp = await client.post("/api/query", json={"query": ""}, headers=auth_headers)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_query_requires_auth(client):
    resp = await client.post("/api/query", json={"query": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_query_with_specific_agent(client, auth_headers, monkeypatch):
    """Query endpoint should accept a named agent."""
    from backend.agents.base import SimpleAgent

    async def mock_process(self, query, context=""):
        return f"Mock response to: {query}"

    monkeypatch.setattr(SimpleAgent, "process", mock_process)
    resp = await client.post(
        "/api/query",
        json={"query": "generate test cases", "agent": "tester"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "agent" in data


@pytest.mark.asyncio
async def test_query_unknown_agent(client, auth_headers):
    resp = await client.post(
        "/api/query",
        json={"query": "something", "agent": "nonexistent_agent"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
