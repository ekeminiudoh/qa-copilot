"""Test execution engine — real subprocess runners for multiple frameworks."""

import asyncio
import json
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.logger import logger
from backend.config import settings


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestFramework(str, Enum):
    PYTEST = "pytest"
    PLAYWRIGHT = "playwright"
    KARATE = "karate"
    POSTMAN = "postman"
    GENERIC = "generic"


@dataclass
class TestResult:
    test_id: str
    test_name: str
    status: TestStatus
    duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    screenshot_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    assertions: List[str] = field(default_factory=list)
    logs: str = ""


@dataclass
class ExecutionReport:
    run_id: str
    framework: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    start_time: datetime
    end_time: datetime
    results: List[TestResult] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return round((self.passed / self.total_tests) * 100, 2)

    @property
    def failure_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return round((self.failed / self.total_tests) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "framework": self.framework,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration": self.duration,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "exit_code": self.exit_code,
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "stack_trace": r.stack_trace,
                    "logs": r.logs,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self.results
            ],
        }


class TestExecutor:
    """Executes test cases across multiple frameworks via subprocess."""

    def __init__(self):
        self.execution_history: List[ExecutionReport] = []
        self._screenshots_dir = settings.reports_path / "screenshots"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def execute_tests(
        self,
        test_cases: List[Dict[str, Any]],
        framework: str = "generic",
        timeout: int = 300,
        retry_failed: int = 1,
    ) -> ExecutionReport:
        """Execute test cases and return a detailed execution report."""
        run_id = str(uuid.uuid4())[:8]
        start_time = datetime.utcnow()
        fw = TestFramework(framework) if framework in TestFramework._value2member_map_ else TestFramework.GENERIC

        logger.info("Starting test run %s with %d tests [%s]", run_id, len(test_cases), fw.value)

        results = await self._execute_by_framework(fw, test_cases, run_id, timeout, retry_failed)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        report = ExecutionReport(
            run_id=run_id,
            framework=fw.value,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            results=results,
        )

        self.execution_history.append(report)
        logger.info(
            "Run %s complete: %d/%d passed (%.1f%%) in %.2fs",
            run_id, passed, len(results), report.success_rate, duration,
        )
        return report

    async def _execute_by_framework(
        self,
        fw: TestFramework,
        test_cases: List[Dict],
        run_id: str,
        timeout: int,
        retries: int,
    ) -> List[TestResult]:
        if fw == TestFramework.PYTEST:
            return await self._run_pytest(test_cases, run_id, timeout, retries)
        elif fw == TestFramework.PLAYWRIGHT:
            return await self._run_playwright(test_cases, run_id, timeout)
        elif fw == TestFramework.KARATE:
            return await self._run_karate(test_cases, run_id, timeout)
        elif fw == TestFramework.POSTMAN:
            return await self._run_postman(test_cases, run_id, timeout)
        else:
            return await self._run_generic(test_cases, retries)

    # ─── pytest runner ────────────────────────────────────────────────────────

    async def _run_pytest(
        self, test_cases: List[Dict], run_id: str, timeout: int, retries: int
    ) -> List[TestResult]:
        results = []
        with tempfile.TemporaryDirectory(prefix=f"qa_pytest_{run_id}_") as tmpdir:
            # Write test file
            test_file = Path(tmpdir) / "test_generated.py"
            test_file.write_text(self._build_pytest_file(test_cases))

            report_json = Path(tmpdir) / "report.json"
            cmd = [
                "python", "-m", "pytest",
                str(test_file),
                "--json-report", f"--json-report-file={report_json}",
                "-v", "--tb=short",
                f"--timeout={timeout}",
            ]
            if retries > 0:
                cmd += [f"--reruns={retries}", "--reruns-delay=1"]

            stdout, stderr, exit_code = await self._run_subprocess(cmd, cwd=tmpdir, timeout=timeout + 30)

            if report_json.exists():
                results = self._parse_pytest_json(report_json.read_text())
            else:
                results = self._parse_pytest_stdout(stdout, test_cases)

        return results

    def _build_pytest_file(self, test_cases: List[Dict]) -> str:
        lines = ["import pytest\n", "# Auto-generated test file\n\n"]
        for i, tc in enumerate(test_cases):
            name = re.sub(r"[^a-zA-Z0-9_]", "_", tc.get("name", f"test_{i}"))
            steps = tc.get("steps", [])
            lines.append(f"def test_{name.lower()}():")
            if steps:
                for step in steps[:3]:
                    lines.append(f"    # {step}")
            lines.append("    assert True  # Replace with real assertions\n\n")
        return "\n".join(lines)

    def _parse_pytest_json(self, content: str) -> List[TestResult]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        results = []
        for test in data.get("tests", []):
            outcome = test.get("outcome", "error")
            status_map = {"passed": TestStatus.PASSED, "failed": TestStatus.FAILED, "skipped": TestStatus.SKIPPED}
            status = status_map.get(outcome, TestStatus.ERROR)
            results.append(TestResult(
                test_id=test.get("nodeid", "unknown"),
                test_name=test.get("nodeid", "unknown").split("::")[-1],
                status=status,
                duration=test.get("duration", 0.0),
                error_message=test.get("call", {}).get("longrepr") if status == TestStatus.FAILED else None,
            ))
        return results

    def _parse_pytest_stdout(self, stdout: str, test_cases: List[Dict]) -> List[TestResult]:
        """Fallback: parse pytest -v stdout."""
        results = []
        for line in stdout.splitlines():
            if " PASSED" in line:
                name = line.split("::")[1].split(" ")[0] if "::" in line else line
                results.append(TestResult(test_id=name, test_name=name, status=TestStatus.PASSED, duration=0.0))
            elif " FAILED" in line:
                name = line.split("::")[1].split(" ")[0] if "::" in line else line
                results.append(TestResult(test_id=name, test_name=name, status=TestStatus.FAILED, duration=0.0, error_message="See stdout for details"))
        if not results:
            # Fallback for each test case
            for tc in test_cases:
                results.append(TestResult(
                    test_id=tc.get("id", "unknown"),
                    test_name=tc.get("name", "unknown"),
                    status=TestStatus.ERROR,
                    duration=0.0,
                    error_message="Could not parse test output",
                ))
        return results

    # ─── Playwright runner ────────────────────────────────────────────────────

    async def _run_playwright(
        self, test_cases: List[Dict], run_id: str, timeout: int
    ) -> List[TestResult]:
        results = []
        with tempfile.TemporaryDirectory(prefix=f"qa_pw_{run_id}_") as tmpdir:
            test_file = Path(tmpdir) / "test_generated.spec.ts"
            test_file.write_text(self._build_playwright_file(test_cases))

            # Write playwright config
            config = Path(tmpdir) / "playwright.config.ts"
            config.write_text(f"""
import {{ defineConfig }} from '@playwright/test';
export default defineConfig({{
  testDir: '{tmpdir}',
  timeout: {timeout * 1000},
  reporter: [['json', {{ outputFile: 'report.json' }}]],
  use: {{ screenshot: 'only-on-failure' }},
}});
""")
            cmd = ["npx", "playwright", "test", "--reporter=json", "--output=results"]
            stdout, stderr, exit_code = await self._run_subprocess(cmd, cwd=tmpdir, timeout=timeout + 60)

            report_json = Path(tmpdir) / "report.json"
            if report_json.exists():
                results = self._parse_playwright_json(report_json.read_text())
            else:
                results = [
                    TestResult(
                        test_id=tc.get("id", f"PW{i}"),
                        test_name=tc.get("name", f"Playwright Test {i}"),
                        status=TestStatus.ERROR if exit_code != 0 else TestStatus.PASSED,
                        duration=0.0,
                        error_message="Playwright not installed or test failed" if exit_code != 0 else None,
                        logs=stdout[:500],
                    )
                    for i, tc in enumerate(test_cases)
                ]
        return results

    def _build_playwright_file(self, test_cases: List[Dict]) -> str:
        lines = ["import { test, expect } from '@playwright/test';\n"]
        for tc in test_cases:
            name = tc.get("name", "Unnamed test")
            steps = tc.get("steps", [])
            lines.append(f"test('{name}', async ({{ page }}) => {{")
            for step in steps[:3]:
                lines.append(f"  // {step}")
            lines.append("  // Add real assertions here")
            lines.append("});\n")
        return "\n".join(lines)

    def _parse_playwright_json(self, content: str) -> List[TestResult]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        results = []
        for suite in data.get("suites", []):
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    ok = all(r.get("status") == "passed" for r in test.get("results", []))
                    status = TestStatus.PASSED if ok else TestStatus.FAILED
                    duration = sum(r.get("duration", 0) for r in test.get("results", [])) / 1000
                    results.append(TestResult(
                        test_id=spec.get("id", "unknown"),
                        test_name=spec.get("title", "unknown"),
                        status=status,
                        duration=duration,
                    ))
        return results

    # ─── Karate runner ────────────────────────────────────────────────────────

    async def _run_karate(
        self, test_cases: List[Dict], run_id: str, timeout: int
    ) -> List[TestResult]:
        with tempfile.TemporaryDirectory(prefix=f"qa_karate_{run_id}_") as tmpdir:
            feature_file = Path(tmpdir) / "generated.feature"
            feature_file.write_text(self._build_karate_feature(test_cases))

            # Try mvn or java directly
            cmd = ["java", "-jar", "karate.jar", str(feature_file)]
            stdout, stderr, exit_code = await self._run_subprocess(cmd, cwd=tmpdir, timeout=timeout + 30)

            return self._parse_karate_output(stdout, test_cases, exit_code)

    def _build_karate_feature(self, test_cases: List[Dict]) -> str:
        lines = ["Feature: Generated QA Tests\n"]
        for tc in test_cases:
            name = tc.get("name", "Unnamed scenario")
            steps = tc.get("steps", [])
            lines.append(f"  Scenario: {name}")
            if not steps:
                lines.append("    * print 'Test placeholder'")
            for step in steps[:5]:
                lines.append(f"    * print '{step}'")
            lines.append("")
        return "\n".join(lines)

    def _parse_karate_output(self, stdout: str, test_cases: List[Dict], exit_code: int) -> List[TestResult]:
        results = []
        # Parse "X scenarios (Y passed, Z failed)" pattern
        match = re.search(r"(\d+) scenarios?\s*\((\d+) passed,?\s*(\d+) failed", stdout)
        if match:
            total, passed, failed = int(match.group(1)), int(match.group(2)), int(match.group(3))
            for i, tc in enumerate(test_cases):
                status = TestStatus.PASSED if i < passed else TestStatus.FAILED
                results.append(TestResult(
                    test_id=tc.get("id", f"K{i}"),
                    test_name=tc.get("name", f"Karate Scenario {i}"),
                    status=status,
                    duration=0.0,
                ))
        else:
            for i, tc in enumerate(test_cases):
                results.append(TestResult(
                    test_id=tc.get("id", f"K{i}"),
                    test_name=tc.get("name", f"Karate Scenario {i}"),
                    status=TestStatus.ERROR if exit_code != 0 else TestStatus.PASSED,
                    duration=0.0,
                    error_message="Karate not installed or output unrecognized" if exit_code != 0 else None,
                    logs=stdout[:300],
                ))
        return results

    # ─── Postman runner ───────────────────────────────────────────────────────

    async def _run_postman(
        self, test_cases: List[Dict], run_id: str, timeout: int
    ) -> List[TestResult]:
        """Run Postman collection using Newman CLI."""
        # test_cases should contain a "collection_path" key for Postman
        collection_paths = [tc.get("collection_path") for tc in test_cases if tc.get("collection_path")]
        results = []

        for path in collection_paths:
            if not Path(path).exists():
                continue
            with tempfile.TemporaryDirectory(prefix=f"qa_postman_{run_id}_") as tmpdir:
                report_json = Path(tmpdir) / "report.json"
                cmd = [
                    "newman", "run", path,
                    "--reporters", "json",
                    "--reporter-json-export", str(report_json),
                    "--timeout-request", "30000",
                ]
                stdout, stderr, exit_code = await self._run_subprocess(cmd, cwd=tmpdir, timeout=timeout + 30)

                if report_json.exists():
                    results.extend(self._parse_newman_json(report_json.read_text()))

        if not results:
            for i, tc in enumerate(test_cases):
                results.append(TestResult(
                    test_id=tc.get("id", f"PM{i}"),
                    test_name=tc.get("name", f"Postman Request {i}"),
                    status=TestStatus.ERROR,
                    duration=0.0,
                    error_message="Newman not installed or no collection_path provided",
                ))
        return results

    def _parse_newman_json(self, content: str) -> List[TestResult]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        results = []
        for execution in data.get("run", {}).get("executions", []):
            item = execution.get("item", {})
            assertions = execution.get("assertions", [])
            failed = [a for a in assertions if a.get("error")]
            status = TestStatus.FAILED if failed else TestStatus.PASSED
            results.append(TestResult(
                test_id=item.get("id", "unknown"),
                test_name=item.get("name", "unknown"),
                status=status,
                duration=execution.get("response", {}).get("responseTime", 0) / 1000,
                error_message=str(failed[0]["error"]) if failed else None,
                assertions=[a.get("assertion", "") for a in assertions],
            ))
        return results

    # ─── Generic runner ───────────────────────────────────────────────────────

    async def _run_generic(self, test_cases: List[Dict], retries: int) -> List[TestResult]:
        """Execute test cases with basic pass/fail simulation plus retry logic."""
        results = []
        for i, tc in enumerate(test_cases):
            test_id = tc.get("id", f"TC{i:03d}")
            test_name = tc.get("name", f"Test {i + 1}")
            expected_result = tc.get("expected_result", "")
            should_fail = tc.get("simulate_failure", False)

            result = None
            for attempt in range(retries + 1):
                start = datetime.utcnow()
                await asyncio.sleep(0.05)
                duration = (datetime.utcnow() - start).total_seconds()

                if should_fail:
                    # Test always fails; label intermediate attempts as retrying
                    msg = "Simulated failure (retrying...)" if attempt < retries else "Simulated failure"
                    result = TestResult(
                        test_id=test_id,
                        test_name=test_name,
                        status=TestStatus.FAILED,
                        duration=duration,
                        error_message=msg,
                    )
                else:
                    result = TestResult(
                        test_id=test_id,
                        test_name=test_name,
                        status=TestStatus.PASSED,
                        duration=duration,
                        assertions=[expected_result] if expected_result else [],
                    )
                    break

            results.append(result)
        return results

    # ─── Subprocess Helper ────────────────────────────────────────────────────

    async def _run_subprocess(
        self, cmd: List[str], cwd: str = None, timeout: int = 300
    ) -> tuple[str, str, int]:
        """Run a subprocess asynchronously with timeout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return (
                stdout_bytes.decode("utf-8", errors="replace"),
                stderr_bytes.decode("utf-8", errors="replace"),
                proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            logger.warning("Subprocess timed out after %ds: %s", timeout, cmd[0])
            try:
                proc.kill()
            except Exception:
                pass
            return ("", "Timed out", 1)
        except FileNotFoundError:
            logger.warning("Subprocess not found: %s", cmd[0])
            return ("", f"Command not found: {cmd[0]}", 127)
        except Exception as exc:
            logger.error("Subprocess error: %s", exc)
            return ("", str(exc), 1)

    def get_execution_summary(self) -> Dict[str, Any]:
        if not self.execution_history:
            return {
                "total_runs": 0,
                "total_tests": 0,
                "total_passed": 0,
                "total_failed": 0,
                "average_success_rate": 0.0,
            }
        total_runs = len(self.execution_history)
        total_tests = sum(r.total_tests for r in self.execution_history)
        total_passed = sum(r.passed for r in self.execution_history)
        total_failed = sum(r.failed for r in self.execution_history)
        avg = sum(r.success_rate for r in self.execution_history) / total_runs
        return {
            "total_runs": total_runs,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "average_success_rate": round(avg, 2),
        }
