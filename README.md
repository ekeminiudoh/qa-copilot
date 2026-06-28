# QA Copilot

**AI-Powered QA Assistant for the Full Software Testing Lifecycle**

QA Copilot is a production-ready multi-agent AI system that helps QA engineers, developers, and analysts generate test cases, review code, investigate bugs, generate automation scripts, and execute tests — all driven by large language models.

---

## Features

| Feature | Description |
|---------|-------------|
| **9 Specialized AI Agents** | Analyst, Tester, Developer, Automation, SQL, Documentation, Bug Investigator, Security Reviewer, Performance Engineer |
| **Multi-Provider LLM** | OpenRouter (primary), OpenAI, Anthropic — with automatic retry and streaming |
| **RAG Knowledge Base** | ChromaDB vector search, BM25 fallback, PDF/DOCX/MD/JSON/SQL ingestion |
| **Test Execution** | Real subprocess runners for pytest, Playwright, Karate, Postman/Newman |
| **8 Report Formats** | Markdown, HTML, JSON, CSV, Excel, PDF, DOCX, Confluence |
| **JWT + API Key Auth** | Refresh tokens, role-based access, API key management |
| **Streamlit Web UI** | 12-page production UI: Chat, Test Cases, SQL Review, Bug Investigation, Reports, and more |
| **Discord Bot** | Slash commands: /analyze /testcases /sql /automation /bug /security /report /help |
| **Docker** | Full Docker Compose setup with health checks |

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd QA-COPILOT

# 2. Configure
cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY and JWT_SECRET_KEY

# 3. Install
pip install -r requirements.txt

# 4. Start backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Start web UI (new terminal)
streamlit run frontend/app.py

# 6. Open browser → http://localhost:8501
# Login: admin / admin
```

Or with Docker:
```bash
docker-compose up --build -d
# Backend: http://localhost:8000
# Frontend: http://localhost:8501
```

---

## Project Structure

```
QA-COPILOT/
├── backend/
│   ├── agents/           # 9 specialized AI agents
│   ├── api/              # REST endpoints (auth, qa, reports, knowledge)
│   ├── core/             # Logging
│   ├── db/               # SQLAlchemy models, session, CRUD
│   ├── execution/        # Multi-framework test runner
│   ├── memory/           # Conversation memory
│   ├── models/           # Pydantic models
│   ├── reporting/        # Multi-format report generation
│   ├── services/         # Legacy service layer
│   ├── auth.py           # FastAPI auth dependencies
│   ├── config.py         # Settings management
│   ├── discord_bot.py    # Discord slash commands
│   ├── llm.py            # LLM client (multi-provider)
│   ├── main.py           # App entry point
│   ├── router.py         # Agent orchestration
│   └── security.py       # JWT, bcrypt, API keys
├── docker/
│   ├── Dockerfile        # Backend image
│   └── Dockerfile.frontend # Streamlit image
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── INSTALL.md
├── frontend/
│   └── app.py            # Streamlit web app (12 pages)
├── knowledge/
│   └── manager.py        # ChromaDB + BM25 knowledge base
├── prompts/              # Agent system prompts
├── tests/                # Test suite (~90%+ coverage target)
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/login | Login → access + refresh tokens |
| POST | /auth/refresh | Rotate refresh token |
| POST | /auth/register | Register new user |
| GET | /auth/me | Current user profile |
| POST | /auth/api-keys | Generate API key |
| POST | /api/query | Chat with auto-routed or named agent |
| POST | /api/qa/test-cases/generate | Generate test cases |
| POST | /api/qa/test-cases/stream | Streaming test case generation (SSE) |
| POST | /api/qa/sql/review | SQL performance + security review |
| POST | /api/qa/security/review | OWASP security analysis |
| POST | /api/qa/bug/investigate | Root cause analysis |
| POST | /api/qa/automation/generate | Generate Karate/Playwright/Cypress scripts |
| POST | /api/qa/files/upload | Upload document to knowledge base |
| POST | /api/reports/execute | Execute tests |
| GET | /api/reports/execute/{run_id}/export/{fmt} | Download report |
| POST | /api/knowledge/search | Semantic search |
| GET | /health | Health check |

Full API reference: [docs/API.md](docs/API.md)

---

## Discord Commands

| Command | Description |
|---------|-------------|
| `/analyze <content>` | Requirements analysis |
| `/testcases <requirement>` | Generate test cases |
| `/sql <query>` | SQL review |
| `/automation <req> <framework>` | Generate automation scripts |
| `/security <code>` | Security vulnerability review |
| `/bug <description>` | Bug investigation |
| `/report` | Latest execution report summary |
| `/history` | Recent query history |
| `/upload` | Upload instructions |
| `/help` | All commands |

---

## Configuration

Set these in `.env`:

```env
OPENROUTER_API_KEY=your_key
MODEL=deepseek/deepseek-chat
JWT_SECRET_KEY=your-secret-key-min-32-chars
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me
DISCORD_TOKEN=optional
DATABASE_URL=sqlite+aiosqlite:///./qa_copilot.db
```

See [docs/INSTALL.md](docs/INSTALL.md) for complete configuration reference.

---

## Running Tests

```bash
pytest tests/ -v --cov=backend --cov=knowledge --cov-report=term-missing
```

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Installation Guide](docs/INSTALL.md)
- [Project Audit](PROJECT_AUDIT.md)

---

## License

MIT
