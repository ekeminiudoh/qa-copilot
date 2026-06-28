"""Tests for report generation in multiple formats."""

import json
import pytest
from datetime import datetime

from backend.execution.engine import TestStatus, TestResult, ExecutionReport
from backend.reporting.generator import ReportGenerator


def _make_report(n_pass=3, n_fail=1, n_skip=1) -> ExecutionReport:
    results = []
    for i in range(n_pass):
        results.append(TestResult(
            test_id=f"TC{i:03d}",
            test_name=f"Pass Test {i}",
            status=TestStatus.PASSED,
            duration=0.1 * (i + 1),
        ))
    for i in range(n_fail):
        results.append(TestResult(
            test_id=f"TC_FAIL{i}",
            test_name=f"Fail Test {i}",
            status=TestStatus.FAILED,
            duration=0.5,
            error_message="AssertionError: Expected 200 got 404",
        ))
    for i in range(n_skip):
        results.append(TestResult(
            test_id=f"TC_SKIP{i}",
            test_name=f"Skip Test {i}",
            status=TestStatus.SKIPPED,
            duration=0.0,
        ))

    total = n_pass + n_fail + n_skip
    return ExecutionReport(
        run_id="test-run-001",
        framework="pytest",
        total_tests=total,
        passed=n_pass,
        failed=n_fail,
        skipped=n_skip,
        duration=2.5,
        start_time=datetime(2026, 1, 1, 10, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 2),
        results=results,
    )


def test_markdown_generation():
    report = _make_report()
    gen = ReportGenerator(report)
    md = gen.generate_markdown()

    assert "# QA Copilot" in md
    assert "test-run-001" in md
    assert "Total Tests" in md
    assert "AssertionError" in md


def test_json_generation():
    report = _make_report()
    gen = ReportGenerator(report)
    raw = gen.generate_json()
    data = json.loads(raw)

    assert data["run_id"] == "test-run-001"
    assert data["summary"]["total_tests"] == 5
    assert data["summary"]["passed"] == 3
    assert data["summary"]["failed"] == 1
    assert len(data["results"]) == 5


def test_html_generation():
    report = _make_report()
    gen = ReportGenerator(report)
    html = gen.generate_html()

    assert "<!DOCTYPE html>" in html
    assert "test-run-001" in html


def test_csv_generation():
    report = _make_report()
    gen = ReportGenerator(report)
    csv = gen.generate_csv()

    lines = csv.strip().splitlines()
    assert lines[0].startswith("Test ID")
    assert len(lines) == 6  # header + 5 results


def test_confluence_generation():
    report = _make_report()
    gen = ReportGenerator(report)
    wiki = gen.generate_confluence()

    assert "h1." in wiki
    assert "test-run-001" in wiki
    assert "||" in wiki


def test_report_generator_from_dict():
    data = {
        "run_id": "dict-run",
        "framework": "generic",
        "total_tests": 2,
        "passed": 2,
        "failed": 0,
        "skipped": 0,
        "success_rate": 100.0,
        "failure_rate": 0.0,
        "duration": 1.0,
        "results": [
            {"test_id": "T1", "test_name": "Test 1", "status": "passed", "duration": 0.5},
            {"test_id": "T2", "test_name": "Test 2", "status": "passed", "duration": 0.5},
        ],
    }
    gen = ReportGenerator(data)
    md = gen.generate_markdown()
    assert "dict-run" in md


def test_success_rate_calculation():
    report = _make_report(n_pass=4, n_fail=1, n_skip=0)
    assert report.success_rate == 80.0
    assert report.failure_rate == 20.0


def test_zero_total_tests():
    report = _make_report(n_pass=0, n_fail=0, n_skip=0)
    assert report.success_rate == 0.0
    assert report.failure_rate == 0.0


def test_excel_generation():
    pytest.importorskip("openpyxl", reason="openpyxl not installed")
    report = _make_report()
    gen = ReportGenerator(report)
    xlsx_bytes = gen.generate_excel()
    assert len(xlsx_bytes) > 0
    assert xlsx_bytes[:2] == b"PK"  # ZIP magic bytes


def test_pdf_generation():
    pytest.importorskip("reportlab", reason="reportlab not installed")
    report = _make_report()
    gen = ReportGenerator(report)
    pdf_bytes = gen.generate_pdf()
    assert pdf_bytes[:4] == b"%PDF"


def test_docx_generation():
    pytest.importorskip("docx", reason="python-docx not installed")
    report = _make_report()
    gen = ReportGenerator(report)
    docx_bytes = gen.generate_docx()
    assert len(docx_bytes) > 0
    assert docx_bytes[:2] == b"PK"
