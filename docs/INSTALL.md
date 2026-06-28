# QA Copilot — Installation Guide

## Prerequisites

- Python 3.11+
- pip or uv
- (Optional) Docker + Docker Compose
- (Optional) Java 11+ for Karate test execution
- (Optional) Node.js 18+ for Playwright/Cypress/Newman
- (Optional) Tesseract OCR for image text extraction

---

## Quick Start (Local)

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd QA-COPILOT
cp .env.example .env
```

Edit `.env` and set your API key:
```
OPENROUTER_API_KEY=your_key_here
JWT_SECRET_KEY=generate-a-secure-random-string
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or with uv (faster):
```bash
pip install uv
uv pip install -r requirements.txt
```

### 3. Start the backend

```bash
python -m backend.main
# or
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: http://localhost:8000

API docs: http://localhost:8000/docs

### 4. Start the web UI

```bash
streamlit run frontend/app.py
```

UI will be at: http://localhost:8501

### 5. Default credentials

- Username: `admin`
- Password: `admin`

**Change these in production** via `.env`:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
```

---

## Docker Compose (Recommended)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 2. Build and start

```bash
docker-compose up --build -d
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:8501

### 3. View logs

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. Stop

```bash
docker-compose down
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *(required)* | OpenRouter API key for LLM access |
| `OPENAI_API_KEY` | *(optional)* | OpenAI API key (fallback) |
| `ANTHROPIC_API_KEY` | *(optional)* | Anthropic API key (fallback) |
| `MODEL` | `deepseek/deepseek-chat` | LLM model to use |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `DATABASE_URL` | `sqlite+aiosqlite:///./qa_copilot.db` | Database connection |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | `admin` | Initial admin password |
| `ADMIN_EMAIL` | `admin@example.com` | Initial admin email |
| `DISCORD_TOKEN` | *(optional)* | Discord bot token |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | `development`, `qa`, or `production` |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `MAX_UPLOAD_BYTES` | `52428800` | Max file upload size (50MB) |

---

## Optional: Discord Bot

1. Create a Discord application at https://discord.com/developers
2. Create a bot and copy the token
3. Enable "Message Content Intent" under "Privileged Gateway Intents"
4. Set `DISCORD_TOKEN=your_token` in `.env`
5. Invite the bot to your server with scopes: `bot`, `applications.commands`
6. Start the bot:
```bash
python -m backend.discord_bot
```

---

## Optional: OCR for Images

Install Tesseract:
- **Windows**: Download installer from https://github.com/UB-Mannheim/tesseract/wiki
- **macOS**: `brew install tesseract`
- **Ubuntu**: `sudo apt-get install tesseract-ocr`

---

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=backend --cov=knowledge --cov-report=html

# Specific test file
pytest tests/test_auth.py -v
```

---

## Troubleshooting

**Backend won't start:**
- Check that `OPENROUTER_API_KEY` is set (or any LLM key)
- Ensure port 8000 is free: `netstat -an | grep 8000`

**Database errors:**
- Delete `qa_copilot.db` to reset: `rm qa_copilot.db`
- Check `DATABASE_URL` format

**ChromaDB errors:**
- Delete `.chroma_db/` directory to reset the vector store
- Ensure `chromadb` is installed: `pip install chromadb`

**Import errors:**
- Ensure you're running from the project root
- Check that `PYTHONPATH` includes the project root

**Discord bot slash commands not appearing:**
- Wait up to 1 hour for global command sync
- For immediate testing, sync to a specific guild
