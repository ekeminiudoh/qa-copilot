# Contributing to QA Copilot

## Development Setup

```bash
git clone <repo-url>
cd QA-COPILOT
cp .env.example .env
pip install -r requirements.txt
```

## Running Tests

```bash
# All tests with coverage
pytest tests/ -v --cov=backend --cov=knowledge --cov-report=term-missing

# Specific module
pytest tests/test_auth.py -v

# With detailed output
pytest tests/ -v -s
```

## Project Structure

```
backend/
├── agents/         # One file per agent (inherit from BaseAgent)
├── api/            # FastAPI routers (auth.py, qa_operations.py, reports.py, knowledge.py)
├── db/             # SQLAlchemy models, session, CRUD functions
├── execution/      # Test runner (engine.py)
├── memory/         # Conversation memory
├── models/         # Pydantic request/response models
├── reporting/      # Report generators (generator.py)
├── auth.py         # FastAPI dependencies (get_current_user_db)
├── config.py       # Settings (pydantic-settings)
├── llm.py          # LLM client (OpenRouter / OpenAI / Anthropic)
├── router.py       # Agent selection and orchestration
└── security.py     # JWT, bcrypt, API keys
```

## Adding a New Agent

1. Create `backend/agents/my_agent.py`:

```python
from backend.agents.base import Agent

class MyAgent(Agent):
    name = "my_agent"
    description = "What this agent does"

    @property
    def system_prompt(self) -> str:
        return "You are a specialist in..."
```

2. Register in `backend/agents/__init__.py`:

```python
from backend.agents.my_agent import MyAgent

def create_agents() -> dict:
    agents = {
        ...
        "my_agent": MyAgent(llm_client),
    }
    return agents
```

3. Add routing keywords in `backend/router.py`.

4. Add a prompt file: `prompts/my_agent.txt`

5. Write tests in `tests/test_agents.py`.

## Adding a New API Endpoint

1. Add to the appropriate router in `backend/api/`.
2. Add request/response Pydantic models to `backend/models/`.
3. Add CRUD functions to `backend/db/crud.py` if DB persistence is needed.
4. Write tests in the appropriate `tests/test_*.py` file.

## Code Style

- Python 3.11+, async/await throughout
- Type hints on all function signatures
- No bare `except:` clauses — catch specific exceptions
- Loguru for logging: `from loguru import logger`
- Pydantic v2 for all models

## Pull Request Guidelines

1. All tests must pass: `pytest tests/ -v`
2. No new Pydantic deprecation warnings
3. New features need tests
4. Keep PRs focused — one feature or fix per PR
5. Update relevant docs if adding features

## Environment Variables

Add new settings to `backend/config.py` using pydantic-settings field declarations (no `Field(env=...)` — just declare the field with its default value; the field name maps to the env var automatically).

## Database Migrations

The project uses SQLAlchemy with `create_all` for simplicity. For production schema changes:

```bash
# Initialize alembic (first time)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "add my_table"

# Apply
alembic upgrade head
```
