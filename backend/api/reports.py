"""Reporting and test execution API endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user_db, require_permission
from backend.config import settings
from backend.db import get_db
from backend.db.crud import list_execution_runs, save_execution_run
from backend.db.models import UserDB
from backend.execution import TestExecutor, ExecutionReport
from backend.reporting import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["reports"])
test_executor = TestExecutor()

MIME_TYPES = {
    "markdown": "text/markdown",
    "json": "application/json",
    "html": "text/html",
    "csv": "text/csv",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "confluence": "text/plain",
}

EXTENSIONS = {
    "markdown": "md", "json": "json", "html": "html", "csv": "csv",
    "excel": "xlsx", "pdf": "pdf", "docx": "docx", "confluence": "txt",
}


class TestCaseItem(BaseModel):
    id: str
    name: str
    description: str = ""
    steps: List[str] = []
    expected_result: str = ""
    simulate_failure: bool = False
    collection_path: Optional[str] = None


class ExecutionRequest(BaseModel):
    test_cases: List[TestCaseItem]
    framework: str = "generic"
    timeout: int = 300
    retry_failed: int = 1


@router.post("/execute")
async def execute_tests(
    request: ExecutionRequest,
    current_user: UserDB = Depends(require_permission("execute:tests")),
    db: AsyncSession = Depends(get_db),
):
    """Execute test cases and return execution report. Persists result to DB."""
    test_cases = [tc.model_dump() for tc in request.test_cases]
    report = await test_executor.execute_tests(
        test_cases,
        framework=request.framework,
        timeout=request.timeout,
        retry_failed=request.retry_failed,
    )

    # Persist to DB
    await save_execution_run(
        db,
        run_id=report.run_id,
        framework=report.framework,
        total_tests=report.total_tests,
        passed=report.passed,
        failed=report.failed,
        skipped=report.skipped,
        success_rate=report.success_rate,
        duration=report.duration,
        start_time=report.start_time,
        end_time=report.end_time,
        results_json=report.to_dict(),
        created_by=current_user.id,
    )
    await db.commit()

    return report.to_dict()


@router.get("/execute/{run_id}")
async def get_execution_report(
    run_id: str,
    current_user: UserDB = Depends(require_permission("view:reports")),
    db: AsyncSession = Depends(get_db),
):
    """Get full execution report for a run (from memory or DB)."""
    # Check in-memory first
    for report in test_executor.execution_history:
        if report.run_id == run_id:
            return report.to_dict()

    # Fall back to DB
    runs = await list_execution_runs(db, limit=200)
    for run in runs:
        if run.run_id == run_id:
            return run.results_json

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.get("/execute/{run_id}/export/{fmt}")
async def export_report(
    run_id: str,
    fmt: str,
    current_user: UserDB = Depends(require_permission("export:reports")),
    db: AsyncSession = Depends(get_db),
):
    """Export a report in the requested format.

    Supported formats: markdown, json, html, csv, excel, pdf, docx, confluence
    """
    if fmt not in MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{fmt}'. Choose from: {list(MIME_TYPES)}",
        )

    # Find report data
    report_data = None
    for report in test_executor.execution_history:
        if report.run_id == run_id:
            report_data = report
            break

    if report_data is None:
        runs = await list_execution_runs(db, limit=200)
        for run in runs:
            if run.run_id == run_id:
                report_data = run.results_json
                break

    if report_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    generator = ReportGenerator(report_data)
    filename = f"report_{run_id}.{EXTENSIONS[fmt]}"
    mime = MIME_TYPES[fmt]

    try:
        if fmt == "markdown":
            content = generator.generate_markdown().encode("utf-8")
        elif fmt == "json":
            content = generator.generate_json().encode("utf-8")
        elif fmt == "html":
            content = generator.generate_html().encode("utf-8")
        elif fmt == "csv":
            content = generator.generate_csv().encode("utf-8")
        elif fmt == "excel":
            content = generator.generate_excel()
        elif fmt == "pdf":
            content = generator.generate_pdf()
        elif fmt == "docx":
            content = generator.generate_docx()
        elif fmt == "confluence":
            content = generator.generate_confluence().encode("utf-8")
        else:
            raise ValueError(f"Unhandled format: {fmt}")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))

    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history")
async def list_execution_history(
    limit: int = 50,
    current_user: UserDB = Depends(require_permission("view:reports")),
    db: AsyncSession = Depends(get_db),
):
    """List recent execution runs from the database."""
    runs = await list_execution_runs(db, limit=limit)
    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "framework": r.framework,
            "total_tests": r.total_tests,
            "passed": r.passed,
            "failed": r.failed,
            "success_rate": r.success_rate,
            "duration": r.duration,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.get("/summary")
async def get_execution_summary(
    current_user: UserDB = Depends(require_permission("view:reports")),
):
    """Get aggregate summary of all in-memory test executions."""
    return test_executor.get_execution_summary()
