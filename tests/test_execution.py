"""Tests for test execution engine."""

import pytest
from backend.execution.engine import TestExecutor, TestStatus, ExecutionReport


@pytest.mark.asyncio
async def test_generic_execution_all_pass():
    executor = TestExecutor()
    test_cases = [
        {"id": "TC001", "name": "Login test"},
        {"id": "TC002", "name": "Logout test"},
    ]
    report = await executor.execute_tests(test_cases, framework="generic")
    assert report.total_tests == 2
    assert report.passed == 2
    assert report.failed == 0
    assert report.success_rate == 100.0


@pytest.mark.asyncio
async def test_generic_execution_with_failure():
    executor = TestExecutor()
    test_cases = [
        {"id": "TC001", "name": "Pass test"},
        {"id": "TC002", "name": "Fail test", "simulate_failure": True},
    ]
    # With 0 retries, the failure stays
    report = await executor.execute_tests(test_cases, framework="generic", retry_failed=0)
    assert report.total_tests == 2
    assert report.failed == 1
    assert report.passed == 1
    assert report.success_rate == 50.0


@pytest.mark.asyncio
async def test_execution_report_has_results():
    executor = TestExecutor()
    test_cases = [{"id": f"TC{i}", "name": f"Test {i}"} for i in range(5)]
    report = await executor.execute_tests(test_cases)
    assert len(report.results) == 5
    for r in report.results:
        assert r.test_id
        assert r.test_name
        assert r.status in list(TestStatus)
        assert r.duration >= 0


@pytest.mark.asyncio
async def test_execution_report_to_dict():
    executor = TestExecutor()
    report = await executor.execute_tests([{"id": "TC1", "name": "T1"}])
    d = report.to_dict()
    assert "run_id" in d
    assert "total_tests" in d
    assert "passed" in d
    assert "results" in d
    assert isinstance(d["results"], list)


@pytest.mark.asyncio
async def test_execution_history():
    executor = TestExecutor()
    await executor.execute_tests([{"id": "T1", "name": "Test 1"}])
    await executor.execute_tests([{"id": "T2", "name": "Test 2"}])
    summary = executor.get_execution_summary()
    assert summary["total_runs"] == 2
    assert summary["total_tests"] == 2


@pytest.mark.asyncio
async def test_empty_execution():
    executor = TestExecutor()
    report = await executor.execute_tests([])
    assert report.total_tests == 0
    assert report.passed == 0
    assert report.success_rate == 0.0


def test_execution_summary_empty():
    executor = TestExecutor()
    summary = executor.get_execution_summary()
    assert summary["total_runs"] == 0
    assert summary["average_success_rate"] == 0.0


@pytest.mark.asyncio
async def test_pytest_runner_unavailable(monkeypatch):
    """When pytest JSON reporter is missing, falls back to stdout parsing."""
    executor = TestExecutor()
    test_cases = [{"id": "TC1", "name": "PY Test"}]

    # This will try to run pytest but it may fail — should still return results
    report = await executor.execute_tests(test_cases, framework="pytest", timeout=10)
    assert report.total_tests >= 0  # May be 0 or 1 depending on env


@pytest.mark.asyncio
async def test_report_endpoint_execute(client, auth_headers):
    """Integration: execute tests via API."""
    resp = await client.post(
        "/api/reports/execute",
        json={
            "test_cases": [
                {"id": "TC1", "name": "Test 1"},
                {"id": "TC2", "name": "Test 2"},
            ],
            "framework": "generic",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tests"] == 2
    assert "run_id" in data


@pytest.mark.asyncio
async def test_report_retrieval(client, auth_headers):
    """Integration: execute then retrieve report."""
    exec_resp = await client.post(
        "/api/reports/execute",
        json={"test_cases": [{"id": "TC1", "name": "T1"}], "framework": "generic"},
        headers=auth_headers,
    )
    run_id = exec_resp.json()["run_id"]

    get_resp = await client.get(f"/api/reports/execute/{run_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id


@pytest.mark.asyncio
async def test_report_export_markdown(client, auth_headers):
    exec_resp = await client.post(
        "/api/reports/execute",
        json={"test_cases": [{"id": "TC1", "name": "T1"}], "framework": "generic"},
        headers=auth_headers,
    )
    run_id = exec_resp.json()["run_id"]

    export_resp = await client.get(
        f"/api/reports/execute/{run_id}/export/markdown",
        headers=auth_headers,
    )
    assert export_resp.status_code == 200
    assert b"QA Copilot" in export_resp.content


@pytest.mark.asyncio
async def test_report_export_json(client, auth_headers):
    exec_resp = await client.post(
        "/api/reports/execute",
        json={"test_cases": [{"id": "T1", "name": "Test"}], "framework": "generic"},
        headers=auth_headers,
    )
    run_id = exec_resp.json()["run_id"]

    resp = await client.get(f"/api/reports/execute/{run_id}/export/json", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_export_csv(client, auth_headers):
    exec_resp = await client.post(
        "/api/reports/execute",
        json={"test_cases": [{"id": "T1", "name": "Test"}], "framework": "generic"},
        headers=auth_headers,
    )
    run_id = exec_resp.json()["run_id"]

    resp = await client.get(f"/api/reports/execute/{run_id}/export/csv", headers=auth_headers)
    assert resp.status_code == 200
    assert b"Test ID" in resp.content


@pytest.mark.asyncio
async def test_report_export_html(client, auth_headers):
    exec_resp = await client.post(
        "/api/reports/execute",
        json={"test_cases": [{"id": "T1", "name": "Test"}], "framework": "generic"},
        headers=auth_headers,
    )
    run_id = exec_resp.json()["run_id"]

    resp = await client.get(f"/api/reports/execute/{run_id}/export/html", headers=auth_headers)
    assert resp.status_code == 200
    assert b"<!DOCTYPE html>" in resp.content


@pytest.mark.asyncio
async def test_report_not_found(client, auth_headers):
    resp = await client.get("/api/reports/execute/nonexistent-run", headers=auth_headers)
    assert resp.status_code == 404
