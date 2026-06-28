"""Tests for knowledge base ingestion and search."""

import pytest
import tempfile
from pathlib import Path


def test_knowledge_base_init():
    from knowledge.manager import KnowledgeBase
    kb = KnowledgeBase()
    assert kb.chunk_size > 0
    assert kb.overlap > 0


def test_ingest_text_file():
    from knowledge.manager import KnowledgeBase

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("This is a test document. It contains information about APIs. "
                             "The API uses REST protocol. Authentication uses JWT tokens.")

        kb = KnowledgeBase()
        count = kb.ingest_text(str(test_file))
        assert count >= 1


def test_ingest_markdown_file():
    from knowledge.manager import KnowledgeBase

    with tempfile.TemporaryDirectory() as tmpdir:
        md_file = Path(tmpdir) / "docs.md"
        md_file.write_text("# API Documentation\n\n## Authentication\nUse Bearer tokens.\n\n## Endpoints\nGET /users")

        kb = KnowledgeBase()
        count = kb.ingest_text(str(md_file))
        assert count >= 1


def test_bm25_search_returns_results():
    from knowledge.manager import KnowledgeBase

    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "data.txt"
        f.write_text("The login endpoint accepts username and password. "
                     "The logout endpoint invalidates the JWT token. "
                     "Authentication is required for all protected routes.")

        kb = KnowledgeBase()
        kb.ingest_text(str(f))
        results = kb.search("login authentication", top_k=3)
        assert len(results) >= 1


def test_search_returns_empty_for_unknown():
    from knowledge.manager import KnowledgeBase
    kb = KnowledgeBase()
    # Empty KB should return empty results
    if not kb.chunks and (kb._collection is None or kb._collection.count() == 0):
        results = kb.search("xyzzy frobozz quux")
        assert results == []


def test_context_for_returns_string():
    from knowledge.manager import KnowledgeBase

    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "info.txt"
        f.write_text("Performance testing uses JMeter or k6. Load tests simulate user traffic.")

        kb = KnowledgeBase()
        kb.ingest_text(str(f))
        ctx = kb.context_for("load testing tools", top_k=2)
        assert isinstance(ctx, str)


def test_get_statistics():
    from knowledge.manager import KnowledgeBase

    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "stats.txt"
        f.write_text("Statistics test document with enough content to chunk properly. " * 5)

        kb = KnowledgeBase()
        kb.ingest_text(str(f))
        stats = kb.get_statistics()
        assert "total_chunks_in_memory" in stats
        assert "total_sources" in stats
        assert stats["total_sources"] >= 1


def test_ingest_nonexistent_file():
    from knowledge.manager import KnowledgeBase
    kb = KnowledgeBase()
    count = kb.ingest_text("/nonexistent/path/file.txt")
    assert count == 0


def test_delete_source():
    from knowledge.manager import KnowledgeBase

    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "deleteme.txt"
        f.write_text("Content to be deleted from the knowledge base after testing.")

        kb = KnowledgeBase()
        kb.ingest_text(str(f))
        assert str(f) in kb._indexed_sources

        kb.delete_source(str(f))
        assert str(f) not in kb._indexed_sources
        # Chunks for this source should be removed
        assert all(c.source != str(f) for c in kb.chunks)


def test_ingest_json_file():
    from knowledge.manager import KnowledgeBase
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "api.json"
        data = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "paths": {
                "/users": {"get": {"summary": "List users"}},
                "/login": {"post": {"summary": "Login endpoint"}},
            }
        }
        f.write_text(json.dumps(data))

        kb = KnowledgeBase()
        count = kb.ingest_text(str(f))
        assert count >= 1
