"""QA Copilot — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import router as api_router
from backend.api.auth import router as auth_router
from backend.api.qa_operations import router as qa_router
from backend.api.reports import router as reports_router
from backend.api.knowledge import router as knowledge_router
from backend.api.gaming import router as gaming_router
from backend.api.fintech import router as fintech_router
from backend.config import settings
from backend.core.logger import logger, setup_logger
from backend.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    setup_logger(settings.log_level)
    logger.info("Starting QA Copilot backend [%s]", settings.environment)

    # Create required directories
    for d in (settings.uploads_path, settings.logs_path, settings.reports_path):
        d.mkdir(parents=True, exist_ok=True)

    # Bootstrap database
    await init_db()
    await _bootstrap_admin()
    logger.info("Database initialized")

    yield

    logger.info("QA Copilot backend shutting down")


async def _bootstrap_admin() -> None:
    """Ensure the default admin user exists in the DB."""
    from backend.db.session import AsyncSessionLocal
    from backend.db.crud import get_user_by_username, create_user

    async with AsyncSessionLocal() as db:
        existing = await get_user_by_username(db, settings.admin_username)
        if not existing:
            await create_user(
                db,
                username=settings.admin_username,
                email=settings.admin_email,
                password=settings.admin_password,
                full_name="Administrator",
                roles=["admin"],
                permissions=[p.value if hasattr(p, "value") else p for p in __import__(
                    "backend.models.user", fromlist=["UserPermission"]
                ).UserPermission],
            )
            await db.commit()
            logger.info("Admin user '%s' bootstrapped", settings.admin_username)


app = FastAPI(
    title="QA Copilot",
    version="1.0.0",
    description="AI-powered QA assistant for the full software testing lifecycle.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)
app.include_router(qa_router)
app.include_router(reports_router)
app.include_router(knowledge_router)
app.include_router(gaming_router)
app.include_router(fintech_router)

frontend_dir = Path(settings.frontend_path)
if frontend_dir.exists():
    app.mount(
        "/app",
        StaticFiles(directory=str(frontend_dir), html=True),
        name="frontend",
    )


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Health check — validates DB connectivity."""
    from backend.db.session import AsyncSessionLocal
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "environment": settings.environment,
        "database": db_status,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not settings.is_production,
    )
