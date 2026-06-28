"""Advanced QA operations API endpoints — all wired to real AI agents."""

import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents import create_agents
from backend.auth import get_current_user_db, require_permission
from backend.config import settings
from backend.core.logger import logger
from backend.db import get_db
from backend.db.crud import create_document, save_prompt_history, update_document_status
from backend.db.models import UserDB
from backend.llm import llm_client

# Shared agent pool (created once at module load)
_agents = create_agents()

router = APIRouter(prefix="/api/qa", tags=["qa-operations"])


# ─── Request/Response Models ──────────────────────────────────────────────────

class TestCaseRequest(BaseModel):
    requirement: str
    test_types: List[str] = ["positive", "negative", "boundary", "edge"]
    framework: Optional[str] = None  # karate, playwright, cypress, selenium, rest_assured
    agent: str = "tester"
    include_automation: bool = False


class SQLReviewRequest(BaseModel):
    sql_query: str
    dialect: str = "generic"  # mysql, postgresql, oracle, mssql
    include_optimization: bool = True


class SecurityReviewRequest(BaseModel):
    code: str
    language: str = "python"
    focus: List[str] = ["owasp", "injection", "auth", "exposure"]


class BugInvestigationRequest(BaseModel):
    description: str
    logs: str = ""
    stack_trace: str = ""
    sql_queries: str = ""
    api_response: str = ""
    screenshots_descriptions: str = ""


class AutomationRequest(BaseModel):
    requirement: str
    framework: str  # karate, playwright, cypress, selenium, rest_assured, postman
    base_url: Optional[str] = None
    endpoints: Optional[List[str]] = None


class AnalysisRequest(BaseModel):
    content: str
    analysis_type: str = "general"  # general, requirements, api, performance


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _call_agent(agent_name: str, prompt: str, context: str = "") -> Dict[str, Any]:
    """Call a single agent and return response with metadata."""
    agent = _agents.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    start = time.time()
    try:
        response = await agent.process(prompt, context=context)
    except Exception as exc:
        logger.error("Agent '%s' failed: %s", agent_name, exc)
        raise HTTPException(status_code=502, detail=f"Agent error: {exc}")

    duration_ms = int((time.time() - start) * 1000)
    # Estimate a basic confidence score from response length and keyword presence
    confidence = _estimate_confidence(response, prompt)

    return {
        "agent": agent_name,
        "response": response,
        "confidence": confidence,
        "duration_ms": duration_ms,
    }


def _estimate_confidence(response: str, query: str) -> float:
    """Heuristic confidence: penalize very short / generic responses."""
    if len(response) < 100:
        return 0.4
    if len(response) < 300:
        return 0.65
    # Bonus if response references specific terms from query
    query_terms = set(query.lower().split())
    response_terms = set(response.lower().split())
    overlap = len(query_terms & response_terms) / max(len(query_terms), 1)
    base = 0.75 + min(overlap * 0.2, 0.2)
    return round(min(base, 0.98), 2)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/test-cases/generate")
async def generate_test_cases(
    request: TestCaseRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Generate comprehensive test cases from a requirement using the Tester agent."""
    test_types_str = ", ".join(request.test_types)
    framework_hint = f"\n\nGenerate test cases in {request.framework} format." if request.framework else ""

    prompt = f"""Generate comprehensive test cases for the following requirement.

Requirement:
{request.requirement}

Include these test types: {test_types_str}
{framework_hint}

Structure each test case with:
- ID (TC001, TC002, ...)
- Title
- Preconditions
- Test Steps (numbered)
- Expected Result
- Test Data (if applicable)
- Priority (High/Medium/Low)
- Test Type (positive/negative/boundary/edge/security/performance)

{"Also include a brief Karate/Playwright/Selenium/Cypress automation script for each test case." if request.include_automation else ""}
"""

    result = await _call_agent(request.agent, prompt)

    await save_prompt_history(
        db,
        prompt=request.requirement,
        response=result["response"],
        agent_name=request.agent,
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "requirement": request.requirement,
        "agent": result["agent"],
        "test_cases": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }


@router.post("/test-cases/stream")
async def stream_test_cases(
    request: TestCaseRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
):
    """Stream test case generation via Server-Sent Events."""
    prompt = f"""Generate comprehensive test cases for this requirement.

Requirement:
{request.requirement}

Include: {", ".join(request.test_types)} tests.
Format each with ID, Title, Steps, Expected Result, Priority.
"""

    async def event_generator():
        try:
            messages = [
                {"role": "system", "content": _agents["tester"].system_prompt},
                {"role": "user", "content": prompt},
            ]
            async for chunk in llm_client.stream_chat(messages, max_tokens=4096):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/sql/review")
async def review_sql(
    request: SQLReviewRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Review SQL query for correctness, performance, and security using the SQL agent."""
    prompt = f"""Review the following SQL query and provide:
1. Correctness analysis
2. Performance optimization suggestions (indexes, query rewriting, execution plan hints)
3. Security issues (SQL injection risks, privilege escalation)
4. Rewritten optimized version
5. Estimated complexity (O notation if applicable)

Dialect: {request.dialect}
SQL Query:
```sql
{request.sql_query}
```
"""
    result = await _call_agent("sql", prompt)

    await save_prompt_history(
        db,
        prompt=request.sql_query,
        response=result["response"],
        agent_name="sql",
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "sql_query": request.sql_query,
        "dialect": request.dialect,
        "agent": result["agent"],
        "review": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }


@router.post("/security/review")
async def review_security(
    request: SecurityReviewRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Review code for security vulnerabilities using the Security Reviewer agent."""
    focus_str = ", ".join(request.focus)
    prompt = f"""Perform a comprehensive security review of the following {request.language} code.

Focus areas: {focus_str}

For each issue found, provide:
- Vulnerability type (OWASP category if applicable)
- Severity: Critical / High / Medium / Low / Informational
- Line reference (if identifiable)
- Detailed description
- Proof of concept (how it could be exploited)
- Remediation with corrected code snippet

Code:
```{request.language}
{request.code}
```

End with an overall security score (0-100) and a summary table of all findings.
"""
    result = await _call_agent("security_reviewer", prompt)

    await save_prompt_history(
        db,
        prompt=f"Security review ({request.language})",
        response=result["response"],
        agent_name="security_reviewer",
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "language": request.language,
        "agent": result["agent"],
        "review": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }


@router.post("/bug/investigate")
async def investigate_bug(
    request: BugInvestigationRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Investigate a bug using all available evidence through the Bug Investigator agent."""
    evidence_parts = [f"Bug Description:\n{request.description}"]
    if request.logs:
        evidence_parts.append(f"Logs:\n```\n{request.logs}\n```")
    if request.stack_trace:
        evidence_parts.append(f"Stack Trace:\n```\n{request.stack_trace}\n```")
    if request.sql_queries:
        evidence_parts.append(f"SQL Queries:\n```sql\n{request.sql_queries}\n```")
    if request.api_response:
        evidence_parts.append(f"API Response:\n```json\n{request.api_response}\n```")
    if request.screenshots_descriptions:
        evidence_parts.append(f"Screenshot Observations:\n{request.screenshots_descriptions}")

    prompt = f"""Investigate the following bug and provide a comprehensive root cause analysis.

{"=== EVIDENCE ===".join(['']) }
{chr(10).join(evidence_parts)}

Provide:
1. **Probable Root Cause** — primary technical reason for the bug
2. **Affected Services/Components** — which layers/microservices are impacted
3. **Reproduction Steps** — how to reproduce the issue
4. **Immediate Fix** — quick remediation with code example if applicable
5. **Long-Term Fix** — architectural or design-level solution
6. **Severity** — Critical/High/Medium/Low with justification
7. **Confidence Score** — your confidence in this diagnosis (0.0–1.0) with reasoning
8. **Prevention** — how to prevent this class of bug in the future
"""
    result = await _call_agent("bug_investigator", prompt)

    await save_prompt_history(
        db,
        prompt=request.description,
        response=result["response"],
        agent_name="bug_investigator",
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "description": request.description,
        "agent": result["agent"],
        "investigation": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }


@router.post("/automation/generate")
async def generate_automation(
    request: AutomationRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Generate automation scripts in a specified framework."""
    framework_details = {
        "karate": "Karate DSL (BDD-style .feature files with * keyword steps)",
        "playwright": "Playwright with TypeScript (async/await, page object model)",
        "cypress": "Cypress with JavaScript (cy. commands, fixtures)",
        "selenium": "Selenium WebDriver with Java (Page Object Model, TestNG)",
        "rest_assured": "Rest Assured with Java (BDD given/when/then)",
        "postman": "Postman Collection JSON (v2.1 format with tests)",
    }

    framework_desc = framework_details.get(request.framework, request.framework)
    base_url_hint = f"\nBase URL: {request.base_url}" if request.base_url else ""
    endpoints_hint = f"\nEndpoints to test: {', '.join(request.endpoints)}" if request.endpoints else ""

    prompt = f"""Generate production-ready automation scripts in {framework_desc}.

Requirement:
{request.requirement}
{base_url_hint}
{endpoints_hint}

Requirements for the scripts:
- Complete, runnable code (not pseudocode)
- Proper setup/teardown
- Clear assertions
- Error handling
- Comments explaining key steps
- Follow {request.framework} best practices

Generate at minimum 3 test scenarios covering happy path, error handling, and edge cases.
"""
    result = await _call_agent("automation", prompt)

    await save_prompt_history(
        db,
        prompt=f"Automation ({request.framework}): {request.requirement[:100]}",
        response=result["response"],
        agent_name="automation",
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "framework": request.framework,
        "requirement": request.requirement,
        "agent": result["agent"],
        "automation_code": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }


@router.post("/analyze")
async def analyze(
    request: AnalysisRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze content using the Analyst agent."""
    type_prompts = {
        "requirements": "Analyze these requirements for completeness, ambiguity, testability, and risks.",
        "api": "Analyze this API specification for design issues, missing endpoints, and test coverage gaps.",
        "performance": "Analyze this for performance bottlenecks, scalability risks, and optimization opportunities.",
        "general": "Provide a comprehensive QA-focused analysis.",
    }
    type_instruction = type_prompts.get(request.analysis_type, type_prompts["general"])

    prompt = f"""{type_instruction}

Content:
{request.content}

Provide:
1. Executive summary
2. Key findings (categorized by severity)
3. Risks identified
4. Recommended test coverage areas
5. Actionable recommendations
"""
    result = await _call_agent("analyst", prompt)

    await save_prompt_history(
        db,
        prompt=f"Analysis ({request.analysis_type})",
        response=result["response"],
        agent_name="analyst",
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "analysis_type": request.analysis_type,
        "agent": result["agent"],
        "analysis": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for analysis and knowledge base ingestion."""
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{suffix}' not supported. Allowed: {settings.allowed_upload_extensions}",
        )

    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.max_upload_bytes // 1024 // 1024}MB",
        )

    # Save to uploads directory
    upload_dir = settings.uploads_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4().hex}_{file.filename}"
    dest.write_bytes(content)

    # Record in DB
    doc = await create_document(
        db,
        filename=file.filename,
        file_type=suffix.lstrip("."),
        file_size=file_size,
        file_path=str(dest),
        uploaded_by=current_user.id,
    )
    await db.commit()

    # Ingest into knowledge base (async, best-effort)
    try:
        from knowledge import KnowledgeBase
        kb = KnowledgeBase()
        if suffix == ".pdf":
            chunks = kb.ingest_pdf(str(dest))
        elif suffix == ".docx":
            chunks = kb.ingest_docx(str(dest))
        else:
            chunks = kb.ingest_text(str(dest))
        await update_document_status(db, doc.id, "indexed", chunk_count=chunks)
        await db.commit()
        logger.info("Ingested '%s' into knowledge base: %d chunks", file.filename, chunks)
    except Exception as exc:
        logger.warning("Knowledge base ingestion failed for '%s': %s", file.filename, exc)
        await update_document_status(db, doc.id, "failed")
        await db.commit()

    return {
        "id": doc.id,
        "filename": file.filename,
        "size_bytes": file_size,
        "file_type": suffix.lstrip("."),
        "status": doc.status,
    }


@router.get("/analysis/status")
async def get_analysis_status(
    current_user: UserDB = Depends(require_permission("read:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics about recent QA analysis activity."""
    from backend.db.crud import list_documents
    from sqlalchemy import select, func
    from backend.db.models import PromptHistoryDB

    docs = await list_documents(db)
    result = await db.execute(
        select(func.count(PromptHistoryDB.id)).where(
            PromptHistoryDB.user_id == current_user.id
        )
    )
    prompt_count = result.scalar() or 0

    return {
        "documents_indexed": sum(1 for d in docs if d.status == "indexed"),
        "documents_failed": sum(1 for d in docs if d.status == "failed"),
        "total_prompts": prompt_count,
        "agents_available": list(_agents.keys()),
    }


@router.post("/performance/analyze")
async def analyze_performance(
    request: AnalysisRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze performance characteristics using the Performance Engineer agent."""
    prompt = f"""Perform a detailed performance analysis.

Content to analyze:
{request.content}

Provide:
1. Performance bottlenecks identified
2. Latency analysis
3. Throughput estimates
4. Scalability concerns
5. Resource utilization patterns
6. Load testing recommendations (tools: k6, JMeter, Locust)
7. Specific optimization recommendations with expected improvements
8. SLO/SLA recommendations
"""
    result = await _call_agent("performance_engineer", prompt)

    await save_prompt_history(
        db,
        prompt="Performance analysis",
        response=result["response"],
        agent_name="performance_engineer",
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "agent": result["agent"],
        "analysis": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }


@router.post("/documentation/generate")
async def generate_documentation(
    request: AnalysisRequest,
    current_user: UserDB = Depends(require_permission("write:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Generate technical documentation from code or specifications."""
    prompt = f"""Generate comprehensive technical documentation for the following content.

Content:
{request.content}

Include:
1. Overview / Purpose
2. Architecture diagram (ASCII)
3. Setup and installation steps
4. API reference (if applicable)
5. Usage examples
6. Configuration options
7. Troubleshooting guide
8. Changelog / Release notes template

Format in clean Markdown.
"""
    result = await _call_agent("documentation", prompt)

    await save_prompt_history(
        db,
        prompt="Documentation generation",
        response=result["response"],
        agent_name="documentation",
        user_id=current_user.id,
        duration_ms=result["duration_ms"],
    )
    await db.commit()

    return {
        "agent": result["agent"],
        "documentation": result["response"],
        "confidence": result["confidence"],
        "duration_ms": result["duration_ms"],
    }
