"""CRUD operations for all database models."""

import hashlib
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    APIKeyDB,
    ChatMessageDB,
    ChatSessionDB,
    DocumentDB,
    ExecutionRunDB,
    PromptHistoryDB,
    ReportDB,
    UserDB,
)
from backend.security import generate_api_key, get_password_hash, verify_password


# ─── Users ────────────────────────────────────────────────────────────────────

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[UserDB]:
    result = await db.execute(select(UserDB).where(UserDB.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserDB]:
    result = await db.execute(select(UserDB).where(UserDB.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[UserDB]:
    result = await db.execute(select(UserDB).where(UserDB.id == user_id))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession) -> List[UserDB]:
    result = await db.execute(select(UserDB).order_by(UserDB.created_at))
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    full_name: str = None,
    roles: list = None,
    permissions: list = None,
) -> UserDB:
    user = UserDB(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        roles=roles or ["viewer"],
        permissions=permissions or ["read:queries", "view:reports"],
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[UserDB]:
    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user(db: AsyncSession, user_id: str, **kwargs) -> Optional[UserDB]:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    for key, value in kwargs.items():
        if key == "password":
            user.hashed_password = get_password_hash(value)
        elif hasattr(user, key):
            setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.flush()
    return True


# ─── API Keys ─────────────────────────────────────────────────────────────────

async def create_api_key(
    db: AsyncSession, user_id: str, name: str, expires_at: Optional[datetime] = None
) -> tuple[APIKeyDB, str]:
    """Create an API key. Returns (db_record, raw_key) — raw_key shown once."""
    raw_key = generate_api_key()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12]

    record = APIKeyDB(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()
    return record, raw_key


async def get_api_key_by_raw(db: AsyncSession, raw_key: str) -> Optional[APIKeyDB]:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(APIKeyDB).where(APIKeyDB.key_hash == key_hash, APIKeyDB.is_active == True)
    )
    record = result.scalar_one_or_none()
    if record and record.expires_at and record.expires_at < datetime.utcnow():
        return None
    return record


async def list_api_keys(db: AsyncSession, user_id: str) -> List[APIKeyDB]:
    result = await db.execute(
        select(APIKeyDB).where(APIKeyDB.user_id == user_id).order_by(APIKeyDB.created_at)
    )
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: str, user_id: str) -> bool:
    result = await db.execute(
        select(APIKeyDB).where(APIKeyDB.id == key_id, APIKeyDB.user_id == user_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    record.is_active = False
    await db.flush()
    return True


# ─── Chat Sessions ─────────────────────────────────────────────────────────────

async def create_chat_session(
    db: AsyncSession, user_id: str = None, title: str = None, channel_id: str = None
) -> ChatSessionDB:
    session = ChatSessionDB(user_id=user_id, title=title, channel_id=channel_id)
    db.add(session)
    await db.flush()
    return session


async def get_chat_session(db: AsyncSession, session_id: str) -> Optional[ChatSessionDB]:
    result = await db.execute(
        select(ChatSessionDB).where(ChatSessionDB.id == session_id)
    )
    return result.scalar_one_or_none()


async def list_chat_sessions(db: AsyncSession, user_id: str) -> List[ChatSessionDB]:
    result = await db.execute(
        select(ChatSessionDB).where(ChatSessionDB.user_id == user_id).order_by(ChatSessionDB.updated_at.desc())
    )
    return list(result.scalars().all())


async def add_chat_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    agent_name: str = None,
    tokens_used: int = None,
) -> ChatMessageDB:
    msg = ChatMessageDB(
        session_id=session_id,
        role=role,
        content=content,
        agent_name=agent_name,
        tokens_used=tokens_used,
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_chat_history(db: AsyncSession, session_id: str) -> List[ChatMessageDB]:
    result = await db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(ChatMessageDB.created_at)
    )
    return list(result.scalars().all())


# ─── Documents ────────────────────────────────────────────────────────────────

async def create_document(
    db: AsyncSession,
    filename: str,
    file_type: str,
    file_size: int,
    file_path: str = None,
    uploaded_by: str = None,
    metadata: dict = None,
) -> DocumentDB:
    doc = DocumentDB(
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        file_path=file_path,
        uploaded_by=uploaded_by,
        metadata_=metadata or {},
    )
    db.add(doc)
    await db.flush()
    return doc


async def update_document_status(
    db: AsyncSession, doc_id: str, status: str, chunk_count: int = None
) -> Optional[DocumentDB]:
    result = await db.execute(select(DocumentDB).where(DocumentDB.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return None
    doc.status = status
    if chunk_count is not None:
        doc.chunk_count = chunk_count
    await db.flush()
    return doc


async def list_documents(db: AsyncSession) -> List[DocumentDB]:
    result = await db.execute(select(DocumentDB).order_by(DocumentDB.created_at.desc()))
    return list(result.scalars().all())


# ─── Execution Runs ───────────────────────────────────────────────────────────

async def save_execution_run(
    db: AsyncSession,
    run_id: str,
    framework: str,
    total_tests: int,
    passed: int,
    failed: int,
    skipped: int,
    success_rate: float,
    duration: float,
    start_time: datetime,
    end_time: datetime,
    results_json: dict,
    created_by: str = None,
) -> ExecutionRunDB:
    run = ExecutionRunDB(
        run_id=run_id,
        framework=framework,
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        skipped=skipped,
        success_rate=success_rate,
        duration=duration,
        start_time=start_time,
        end_time=end_time,
        status="completed",
        results_json=results_json,
        created_by=created_by,
    )
    db.add(run)
    await db.flush()
    return run


async def list_execution_runs(db: AsyncSession, limit: int = 50) -> List[ExecutionRunDB]:
    result = await db.execute(
        select(ExecutionRunDB).order_by(ExecutionRunDB.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ─── Prompt History ───────────────────────────────────────────────────────────

async def save_prompt_history(
    db: AsyncSession,
    prompt: str,
    response: str,
    agent_name: str = None,
    user_id: str = None,
    tokens_used: int = None,
    cost_usd: float = None,
    duration_ms: int = None,
) -> PromptHistoryDB:
    record = PromptHistoryDB(
        user_id=user_id,
        agent_name=agent_name,
        prompt=prompt,
        response=response,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        duration_ms=duration_ms,
    )
    db.add(record)
    await db.flush()
    return record
