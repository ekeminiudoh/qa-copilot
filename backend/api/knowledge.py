"""Knowledge base management API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user_db, require_permission
from backend.db import get_db
from backend.db.crud import list_documents
from backend.db.models import UserDB

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


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
