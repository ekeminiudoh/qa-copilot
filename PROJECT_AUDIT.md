# QA Copilot — Project Audit

**Date:** 2026-06-28  
**Auditor:** Lead Software Architect & Senior AI Engineer  
**Status:** Pre-implementation audit (MVP exists, completion required)

---

## 1. What Is Already Implemented

### Backend (FastAPI)
| Component | File | Status |
|-----------|------|--------|
| FastAPI app entry | `backend/main.py` | Complete |
| CORS middleware | `backend/main.py` | Complete |
| Configuration management | `backend/config.py` | Complete |
| JWT authentication | `backend/security.py` | Partial (plaintext passwords) |
| Auth endpoints (login/register/me) | `backend/api/auth.py` | Complete |
| Agent base classes | `backend/agents/base.py` | Complete |
| 9 specialized agents | `backend/agents/specialized.py` | Complete |
| Agent registry | `backend/agents/specialized.py` | Complete |
| LLM client (multi-provider) | `backend/llm.py` | Complete |
| Query router | `backend/router.py` | Complete |
| Conversation memory | `backend/memory/__init__.py` | Partial (duplicate method) |
| Knowledge base (in-memory) | `knowledge/manager.py` | Partial (no vector search) |
| Report generator (MD/JSON/HTML/CSV) | `backend/reporting/generator.py` | Complete |
| User models | `backend/models/user.py` | Complete |
| User service (in-memory) | `backend/services/user.py` | Complete |
| Test execution engine | `backend/execution/engine.py` | Stub (always passes) |
| Main query endpoint | `backend/api/__init__.py` | Complete |
| Discord bot | `backend/discord_bot.py` | Partial (duplicate bot.run()) |
| Logging | `backend/core/logger.py` | Complete |
| GitHub Actions CI | `.github/workflows/ci.yml` | Complete |

### Frontend
| Component | File | Status |
|-----------|------|--------|
| Streamlit app | `frontend/app.py` | Partial (no real API calls) |
| Static HTML dashboard | `frontend/index.html` | Partial |

### Infrastructure
| Component | Status |
|-----------|--------|
| docker-compose.yml | Partial (backend only, no DB) |
| .env.example | Complete |
| requirements.txt | Partial (missing python-multipart, bcrypt) |

---

## 2. What Is Partially Implemented

### QA Operations Endpoints (`backend/api/qa_operations.py`)
All 5 endpoints return **hardcoded responses** with `# TODO` comments:
- `POST /api/qa/test-cases/generate` → returns 2 fixed test cases
- `POST /api/qa/sql/review` → returns hardcoded suggestions
- `POST /api/qa/security/review` → returns hardcoded issues
- `POST /api/qa/bug/investigate` → returns hardcoded results
- `POST /api/qa/files/upload` → accepts file but doesn't process it

### Knowledge Base (`knowledge/manager.py`)
- Document ingestion works for PDF, DOCX, TXT, MD
- Search uses simple BM25-like term matching (not semantic)
- **ChromaDB is installed but never used**
- No vector embeddings generated
- No metadata filtering

### Test Execution Engine (`backend/execution/engine.py`)
- Structure is complete (TestStatus, TestResult, ExecutionReport)
- `_execute_single_test` only sleeps 100ms and returns PASSED
- No subprocess execution for real frameworks (Karate, Playwright, pytest)

### Discord Bot (`backend/discord_bot.py`)
- Slash commands exist: `/analyze`, `/testcases`, `/sql`, `/automation`
- Has duplicate `bot.run(token)` call (bug)
- No streaming responses
- No `/upload`, `/report`, `/history`, `/help`

### Authentication (`backend/security.py`)
- JWT creation and decoding works
- `CryptContext` set to `"plaintext"` scheme — no real hashing
- No refresh tokens
- No API key management

---

## 3. What Is Missing

### Authentication
- [ ] Bcrypt password hashing (currently plaintext)
- [ ] Refresh tokens endpoint and rotation
- [ ] API key generation and management
- [ ] Token revocation / blacklist

### Database
- [ ] SQLAlchemy ORM models (User, Chat, Document, Report, etc.)
- [ ] Alembic migrations
- [ ] Database initialization on startup
- [ ] Persistent chat history
- [ ] Persistent execution history

### RAG
- [ ] ChromaDB vector store integration
- [ ] Sentence-transformers embedding pipeline
- [ ] Semantic search (cosine similarity)
- [ ] Metadata filtering
- [ ] Swagger/OpenAPI ingestion
- [ ] Postman collection ingestion
- [ ] SQL file ingestion
- [ ] OCR for images
- [ ] Confluence export ingestion

### AI Orchestration
- [ ] Confidence scoring on agent responses
- [ ] Streaming responses in API endpoints
- [ ] Model failover between providers
- [ ] Response validation
- [ ] Token tracking per conversation

### QA Feature Endpoints (wired to agents)
- [ ] Real test case generation (API, Mobile, Web, Regression, Smoke, Sanity)
- [ ] Security test generation
- [ ] Performance test generation
- [ ] SQL validation queries
- [ ] Edge case / negative / boundary test generation

### Automation Code Generation
- [ ] Karate DSL scripts
- [ ] Playwright scripts
- [ ] Cypress scripts
- [ ] Selenium scripts
- [ ] Rest Assured scripts
- [ ] Postman collections

### Test Execution Engine
- [ ] Subprocess-based pytest execution
- [ ] Playwright execution
- [ ] Karate execution
- [ ] Screenshot capture
- [ ] Log capture
- [ ] Report parsing
- [ ] Retry on failure
- [ ] Execution history persistence

### Bug Investigation
- [ ] Log file upload and parsing
- [ ] Stack trace parsing
- [ ] Screenshot analysis
- [ ] Severity classification
- [ ] Confidence scoring

### Report Generation
- [ ] Excel (`.xlsx`) export
- [ ] PDF export
- [ ] DOCX export
- [ ] Confluence-ready format

### Web UI
- [ ] Production-quality React/Next.js or improved Streamlit
- [ ] Dashboard with live metrics
- [ ] Chat interface with streaming
- [ ] Knowledge Base management page
- [ ] Prompt Library page
- [ ] Document upload page
- [ ] Swagger upload page
- [ ] SQL upload page
- [ ] Automation code generation page
- [ ] Test execution page
- [ ] Reports page
- [ ] Settings page
- [ ] Dark/Light mode
- [ ] User management page

### Discord Bot
- [ ] `/upload` command
- [ ] `/report` command
- [ ] `/history` command
- [ ] `/help` command
- [ ] Streaming responses
- [ ] Fix duplicate `bot.run()` bug

### Docker
- [ ] `docker/Dockerfile` for backend
- [ ] `docker/Dockerfile.frontend` for frontend
- [ ] PostgreSQL service in docker-compose
- [ ] Health checks
- [ ] Environment validation

### CI/CD
- [ ] Environment validation step
- [ ] Coverage reporting

### Documentation
- [ ] `docs/ARCHITECTURE.md`
- [ ] `docs/API.md`
- [ ] `docs/INSTALL.md`
- [ ] `docs/DEPLOYMENT.md`
- [ ] `docs/USER_GUIDE.md`
- [ ] `docs/CONTRIBUTING.md`
- [ ] Updated `README.md`

### Tests
- [ ] Test database fixtures
- [ ] Auth endpoint tests
- [ ] Agent unit tests
- [ ] QA operation endpoint tests
- [ ] Knowledge base tests
- [ ] Report generation tests
- [ ] Router logic tests
- [ ] Target: >90% coverage

---

## 4. Technical Debt

| Issue | Location | Severity |
|-------|----------|----------|
| Plaintext password hashing | `backend/security.py:13` | CRITICAL |
| Duplicate `get_context` method | `backend/memory/__init__.py:34,46` | MEDIUM |
| Hardcoded `"change-me"` JWT secret | `backend/config.py:23` | HIGH |
| Hardcoded `admin/admin` credentials | `backend/config.py:26-27` | HIGH |
| Duplicate `bot.run()` call | `backend/discord_bot.py:196,201` | HIGH |
| In-memory user store (no persistence) | `backend/services/user.py` | HIGH |
| ChromaDB unused (installed but not wired) | `knowledge/manager.py` | MEDIUM |
| `allows_origins=["*"]` in production | `backend/main.py:26` | MEDIUM |
| Missing `python-multipart` in requirements | `requirements.txt` | HIGH |
| Missing `bcrypt` in requirements | `requirements.txt` | MEDIUM |
| No rate limiting on API endpoints | `backend/api/` | MEDIUM |
| Execution engine always returns PASSED | `backend/execution/engine.py:121` | HIGH |

---

## 5. Duplicate Logic

| Duplication | Files | Action |
|-------------|-------|--------|
| `get_context` defined twice | `backend/memory/__init__.py:34` and `:46` | Remove duplicate |
| `bot.run(token)` called twice | `backend/discord_bot.py:196` and `:201` | Remove second call |
| Router keyword sets overlap with agent prompts | `backend/router.py` | Acceptable, minor |

---

## 6. Performance Issues

| Issue | Impact |
|-------|--------|
| Knowledge base search is O(n*m) per query | Slow at scale, fix with ChromaDB vector search |
| All agents created at startup (9 class instantiations) | Minor, acceptable |
| No connection pooling for LLM client | Mitigated by single client instance |
| No caching of repeated queries | Future improvement |
| In-memory conversation storage | Lost on restart, fix with DB |

---

## 7. Security Issues

| Issue | Severity | Fix |
|-------|----------|-----|
| Plaintext password storage | CRITICAL | Switch to bcrypt |
| `JWT_SECRET_KEY` defaults to "change-me" | HIGH | Validate non-default in production |
| `ADMIN_PASSWORD` defaults to "admin" | HIGH | Validate non-default or force change |
| `allow_origins=["*"]` | MEDIUM | Restrict in production |
| No rate limiting | MEDIUM | Add slowapi middleware |
| File upload with no size limit | MEDIUM | Add max file size validation |
| No token revocation | MEDIUM | Add refresh token blacklist |
| Stack traces exposed in HTTP 500 responses | MEDIUM | Sanitize in production |

---

## 8. Architecture Improvements

| Improvement | Priority |
|-------------|----------|
| Replace in-memory user store with SQLAlchemy + DB | HIGH |
| Replace BM25 knowledge search with ChromaDB semantic search | HIGH |
| Wire QA endpoints to actual agent calls | HIGH |
| Add refresh token + API key auth | HIGH |
| Add real subprocess-based test execution | HIGH |
| Add Excel/PDF/DOCX report export | MEDIUM |
| Add streaming SSE endpoint for chat | MEDIUM |
| Add confidence scoring to agent responses | MEDIUM |
| Add request/response logging middleware | LOW |
| Add health check that validates DB/LLM connectivity | LOW |

---

## Implementation Plan

The implementation will proceed in this order:

1. **Fix critical security debt** (bcrypt, duplicate methods)
2. **Database layer** (SQLAlchemy models + migrations)
3. **Wire QA endpoints to agents** (remove all TODO stubs)
4. **ChromaDB RAG pipeline** (semantic search, document ingestion)
5. **Refresh tokens + API keys**
6. **Real test execution engine** (subprocess + framework runners)
7. **Report generation** (Excel, PDF, DOCX)
8. **Web UI** (production Streamlit upgrade or Next.js)
9. **Discord bot upgrade** (all commands + streaming)
10. **Docker** (Dockerfile + full compose)
11. **Tests** (>90% coverage)
12. **Documentation** (all docs files)
