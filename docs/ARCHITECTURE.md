# QA Copilot — Architecture

## Overview

QA Copilot is a multi-agent AI system for the software testing lifecycle. It combines a FastAPI backend, a Streamlit web UI, a Discord bot, and a ChromaDB-powered knowledge base to deliver AI-assisted QA capabilities.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │  Streamlit UI   │  │ Discord Bot  │  │  External API Client│ │
│  │  (port 8501)    │  │ (slash cmds) │  │  (REST / API Key)   │ │
│  └────────┬────────┘  └──────┬───────┘  └──────────┬──────────┘ │
└───────────┼─────────────────┼───────────────────────┼────────────┘
            │ HTTP            │ aiohttp               │ HTTP/Bearer
            ▼                 ▼                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (port 8000)                  │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Auth Layer │  │ Rate Limiting│  │    CORS Middleware      │   │
│  │ JWT + API  │  │ (slowapi)    │  │                        │   │
│  │ Keys       │  └──────────────┘  └────────────────────────┘   │
│  └────────────┘                                                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    API Routers                           │    │
│  │  /auth  │  /api/query  │  /api/qa/*  │  /api/reports/*  │    │
│  │  /api/knowledge/*                                        │    │
│  └─────────────────────────┬────────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐   │
│  │                  Agent Orchestration Layer                 │   │
│  │  ┌──────────────┐   Query Router   ┌───────────────────┐  │   │
│  │  │ RouterService│──────────────────►   Agent Registry  │  │   │
│  │  └──────────────┘                  └──────────┬────────┘  │   │
│  │                                               │           │   │
│  │  ┌────────────────────────────────────────────▼────────┐  │   │
│  │  │              9 Specialized Agents                    │  │   │
│  │  │  Analyst │ Tester │ Developer │ Automation │ SQL    │  │   │
│  │  │  Documentation │ BugInvestigator │ Security │ Perf  │  │   │
│  │  └────────────────────────────────────┬────────────────┘  │   │
│  └───────────────────────────────────────┼────────────────────┘   │
│                                          │                       │
│  ┌───────────────────────────────────────▼────────────────────┐  │
│  │                      LLM Client                            │  │
│  │  OpenRouter (primary) │ OpenAI │ Anthropic (failover)     │  │
│  │  Streaming SSE │ Retry logic │ Token tracking             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────┐   ┌────────────────────────────────┐   │
│  │   Knowledge Base    │   │      Test Execution Engine     │   │
│  │  ChromaDB (vector)  │   │  pytest │ Playwright │ Karate  │   │
│  │  BM25 (fallback)    │   │  Postman/Newman                │   │
│  │  Document ingestion │   │  Screenshot capture            │   │
│  └─────────────────────┘   └────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────┐   ┌────────────────────────────────┐   │
│  │   Report Generator  │   │     SQLAlchemy DB Layer        │   │
│  │  MD│HTML│JSON│CSV   │   │  Users │ API Keys │ Chats      │   │
│  │  Excel│PDF│DOCX     │   │  Documents │ Execution Runs    │   │
│  └─────────────────────┘   └────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │           Database              │
                    │   SQLite (dev) / PostgreSQL     │
                    │   (production via DATABASE_URL) │
                    └────────────────────────────────┘
```

## Component Details

### Backend (`backend/`)

| Module | Purpose |
|--------|---------|
| `main.py` | FastAPI app, lifespan, middleware, route registration |
| `config.py` | Pydantic settings, environment variables |
| `auth.py` | FastAPI dependencies: JWT + API key auth |
| `security.py` | bcrypt hashing, JWT create/decode, token revocation |
| `llm.py` | Multi-provider LLM client with retry and streaming |
| `router.py` | Intent-based agent routing and response merging |
| `agents/base.py` | Abstract `Agent` and `SimpleAgent` base classes |
| `agents/specialized.py` | 9 concrete agent implementations + registry |
| `agents/tools.py` | Tool definitions for agents |
| `memory/__init__.py` | In-memory conversation history with sliding window |
| `db/session.py` | Async SQLAlchemy engine + session factory |
| `db/models.py` | ORM models: User, APIKey, ChatSession, Document, etc. |
| `db/crud.py` | All database CRUD operations |
| `api/auth.py` | Auth endpoints: login, register, refresh, API keys |
| `api/__init__.py` | Main query endpoint with RAG context injection |
| `api/qa_operations.py` | QA endpoints: test cases, SQL, security, bugs |
| `api/reports.py` | Test execution + report export in 8 formats |
| `api/knowledge.py` | Knowledge base search and statistics |
| `execution/engine.py` | Multi-framework test runner (subprocess-based) |
| `reporting/generator.py` | Report generation: MD, HTML, JSON, CSV, Excel, PDF, DOCX |
| `discord_bot.py` | Discord slash commands with aiohttp backend calls |
| `core/logger.py` | Loguru-based structured logging |

### Knowledge Base (`knowledge/`)

| Module | Purpose |
|--------|---------|
| `manager.py` | Document ingestion, ChromaDB vector store, BM25 fallback |

Supported ingestion formats:
- PDF (via PyMuPDF or PyPDF2)
- DOCX (via python-docx)
- TXT, MD, JSON, YAML, SQL, .feature
- Swagger/OpenAPI (JSON/YAML)
- Postman collections
- Images (OCR via pytesseract)

### Frontend (`frontend/`)

| File | Purpose |
|------|---------|
| `app.py` | Full Streamlit app with 12+ pages |
| `index.html` | Static HTML dashboard (lightweight alternative) |

## Data Flow

### Chat Query
```
User → Streamlit → POST /api/query
  → Auth middleware (JWT/API key)
  → RAG context lookup (ChromaDB)
  → Intent routing (RouterService)
  → Agent(s).process() → LLM API
  → Response merge → DB persist → Return
```

### Document Upload
```
User → POST /api/qa/files/upload
  → File validation (size, extension)
  → Save to /uploads/
  → Create DocumentDB record
  → KnowledgeBase.ingest_*() → ChromaDB
  → Update document status
```

### Test Execution
```
User → POST /api/reports/execute
  → TestExecutor.execute_tests()
  → Framework-specific runner (subprocess)
  → Result parsing → ExecutionRunDB record
  → GET /api/reports/execute/{run_id}/export/{fmt}
  → ReportGenerator.generate_*() → Response
```

## Database Schema

```
users
  id (PK), username, email, hashed_password
  full_name, roles[], permissions[], is_active
  created_at, updated_at

api_keys
  id (PK), user_id (FK→users)
  name, key_hash, key_prefix
  is_active, created_at, last_used_at, expires_at

chat_sessions
  id (PK), user_id (FK→users), title, channel_id
  created_at, updated_at

chat_messages
  id (PK), session_id (FK→chat_sessions)
  role, content, agent_name, tokens_used, created_at

documents
  id (PK), filename, file_type, file_size
  file_path, chunk_count, status
  uploaded_by (FK→users), created_at, metadata

execution_runs
  id (PK), run_id (unique), framework
  total_tests, passed, failed, skipped
  success_rate, duration
  start_time, end_time, status
  results_json, created_by (FK→users), created_at

reports
  id (PK), run_id, format, file_path
  content, created_by (FK→users), created_at

prompt_history
  id (PK), user_id (FK→users), agent_name
  prompt, response, tokens_used, cost_usd
  duration_ms, created_at
```

## Security Model

- **Authentication**: JWT Bearer tokens (short-lived, 60min) + refresh tokens (7 days)
- **API Keys**: `qac_*` prefix, SHA-256 hashed in DB, revocable
- **Passwords**: bcrypt with automatic salting
- **Authorization**: Role-based (admin/analyst/developer/tester/viewer) + permission-based
- **Token Revocation**: In-memory blacklist (extend to Redis for multi-instance)

## Agent System

Agents are `SimpleAgent` subclasses with specialized system prompts. The `RouterService` uses keyword matching to route queries:

| Keyword Set | Agent |
|-------------|-------|
| test, qa, assert, regression | Tester |
| sql, database, query, optimize | SQL |
| security, vulnerability, owasp | Security Reviewer |
| automation, playwright, karate | Automation |
| bug, crash, root cause, trace | Bug Investigator |
| api, swagger, endpoint, code | Developer |
| document, readme, architecture | Documentation |
| performance, latency, load | Performance Engineer |
| analysis, risk, requirements | Analyst |
