"""Knowledge base management API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user_db, require_permission
from backend.db import get_db
from backend.db.crud import create_document, list_documents, update_document_status
from backend.db.models import UserDB

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class IngestTextRequest(BaseModel):
    title: str
    content: str
    category: str = "general"   # gaming | fintech | requirements | test-cases | jira | general
    source: Optional[str] = None


@router.get("/documents")
async def list_knowledge_documents(
    current_user: UserDB = Depends(require_permission("read:queries")),
    db: AsyncSession = Depends(get_db),
):
    """List all documents in the knowledge base."""
    docs = await list_documents(db)
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "chunk_count": d.chunk_count,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.get("/stats")
async def knowledge_stats(
    current_user: UserDB = Depends(require_permission("read:queries")),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge base statistics."""
    docs = await list_documents(db)
    total_chunks = sum(d.chunk_count for d in docs)

    from knowledge import KnowledgeBase
    kb = KnowledgeBase()
    kb_stats = kb.get_statistics()

    return {
        "total_documents": len(docs),
        "indexed_documents": sum(1 for d in docs if d.status == "indexed"),
        "total_chunks": total_chunks,
        "kb_in_memory_chunks": kb_stats.get("total_chunks", 0),
        "by_file_type": _count_by_type(docs),
    }


def _count_by_type(docs) -> dict:
    counts: dict = {}
    for d in docs:
        counts[d.file_type] = counts.get(d.file_type, 0) + 1
    return counts


@router.post("/ingest-text")
async def ingest_text(
    request: IngestTextRequest,
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Paste any text directly into the knowledge base for AI training."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    from knowledge import KnowledgeBase
    kb = KnowledgeBase()

    source_id = f"{request.category}::{request.title}::{datetime.utcnow().isoformat()}"
    tagged_content = (
        f"[CATEGORY: {request.category.upper()}]\n"
        f"[TITLE: {request.title}]\n"
        f"[ADDED BY: {current_user.username}]\n\n"
        f"{request.content}"
    )

    chunks = kb.ingest_text(tagged_content, source=source_id)

    doc = await create_document(
        db,
        filename=request.title,
        file_type=request.category,
        file_size=len(request.content.encode()),
        uploaded_by=current_user.id,
    )
    await update_document_status(db, doc.id, "indexed", chunk_count=chunks)
    await db.commit()

    return {
        "status": "indexed",
        "title": request.title,
        "category": request.category,
        "chunks": chunks,
        "message": f"'{request.title}' ingested. AI will now use this as context for future queries.",
    }


@router.post("/save-chat-training")
async def save_chat_as_training(
    body: dict,
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Save a chat conversation as a training example in the knowledge base."""
    messages = body.get("messages", [])
    label = body.get("label", "chat-training")
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    from knowledge import KnowledgeBase
    kb = KnowledgeBase()

    conversation = "\n".join(
        f"[{m.get('role','').upper()}]: {m.get('content','')}" for m in messages
    )
    source_id = f"chat-training::{label}::{datetime.utcnow().isoformat()}"
    tagged = (
        f"[CATEGORY: CHAT-TRAINING]\n"
        f"[LABEL: {label}]\n"
        f"[SAVED BY: {current_user.username}]\n\n"
        f"{conversation}"
    )
    chunks = kb.ingest_text(tagged, source=source_id)

    doc = await create_document(
        db, filename=label, file_type="chat-training",
        file_size=len(conversation.encode()), uploaded_by=current_user.id,
    )
    await update_document_status(db, doc.id, "indexed", chunk_count=chunks)
    await db.commit()

    return {"status": "saved", "chunks": chunks,
            "message": "Chat saved as training example. AI will learn from this conversation."}


@router.post("/search")
async def search_knowledge(
    query: str,
    top_k: int = 5,
    current_user: UserDB = Depends(require_permission("read:queries")),
):
    """Search the knowledge base for relevant content."""
    from knowledge import KnowledgeBase
    kb = KnowledgeBase()
    results = kb.search(query, top_k=top_k)
    return {"query": query, "results": results, "count": len(results)}
