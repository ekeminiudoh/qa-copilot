# QA Copilot - AI-Powered QA Assistant

A comprehensive AI-powered quality assurance platform that leverages multiple LLM providers to automate test case generation, SQL review, security analysis, bug investigation, and more.

## 🚀 Features

### Core Capabilities

- **Multi-Provider LLM Support**: Seamlessly switch between OpenRouter, OpenAI, Anthropic, Google, DeepSeek, Qwen, and Llama models
- **Specialized Agents**: 9 domain-specific agents for different QA tasks
- **JWT Authentication**: Secure user authentication with role-based permissions
- **Knowledge Base & RAG**: Document ingestion (PDF, DOCX, TXT, MD, JSON) with semantic search
- **Test Execution Engine**: Run and track test case execution with detailed reporting
- **Multi-Format Reporting**: Export reports as Markdown, JSON, HTML, and CSV

### QA Operations

- **Test Case Generation**: Automatically generate comprehensive test cases from requirements
- **SQL Review**: Analyze and optimize SQL queries for performance
- **Security Review**: Identify security vulnerabilities in code
- **Bug Investigation**: Analyze bugs and suggest fixes
- **Performance Analysis**: Monitor and analyze application performance
- **Automation Script Generation**: Create automation test scripts

### Interfaces

- **REST API**: FastAPI-based comprehensive REST API
- **Streamlit Web UI**: Interactive web application for all features
- **Discord Bot**: Slack-like slash commands for quick access
- **CLI Tools**: Command-line interface for automation

## 📋 System Requirements

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- LLM API Keys (OpenRouter, OpenAI, or other provider)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/qa-copilot.git
cd qa-copilot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

5. **Run backend**
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Run frontend** (in another terminal)
```bash
streamlit run frontend/app.py
```

### Docker Deployment

```bash
docker-compose up --build
```

## 📚 API Documentation

### Authentication

All API endpoints require JWT authentication. Get a token via:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### Core Endpoints

#### Query Agent
```bash
POST /api/query
{
  "query": "Generate test cases for user login",
  "agent": "tester",  # or null for auto-routing
  "context": ""
}
```

#### Test Case Generation
```bash
POST /api/qa/test-cases/generate
{
  "requirement": "User login with email and password",
  "agent": "tester"
}
```

#### SQL Review
```bash
POST /api/qa/sql/review
{
  "sql_query": "SELECT * FROM users WHERE id = 1"
}
```

#### Security Review
```bash
POST /api/qa/security/review
{
  "code": "password = request.form['password']"
}
```

#### Bug Investigation
```bash
POST /api/qa/bug/investigate
{
  "description": "Login fails intermittently",
  "logs": "... error logs ..."
}
```

#### Test Execution
```bash
POST /api/reports/execute
{
  "test_cases": [
    {"id": "TC001", "name": "Valid login"},
    {"id": "TC002", "name": "Invalid password"}
  ],
  "timeout": 300
}
```

#### Report Export
```bash
GET /api/reports/execute/{run_id}/export/{format}
# Formats: markdown, json, html, csv
```

## 🤖 Specialized Agents

| Agent | Purpose | Key Features |
|-------|---------|--------------|
| **Analyst** | Requirements analysis | Break down features, identify gaps |
| **Developer** | Code review & optimization | Performance, architecture review |
| **Tester** | Test case generation | Comprehensive test coverage |
| **Automation** | Automation script generation | Selenium, Cypress, API tests |
| **SQL** | Database query optimization | Query analysis, indexing advice |
| **Documentation** | API & feature documentation | Auto-doc generation |
| **Bug Investigator** | Root cause analysis | Bug investigation & fixes |
| **Security Reviewer** | Security vulnerability detection | OWASP, CWE analysis |
| **Performance Engineer** | Performance optimization | Bottleneck identification |

## 🔌 Discord Bot Commands

- `/analyze <content>` - Analyze code or requirements
- `/testcases <requirement>` - Generate test cases
- `/sqlreview <query>` - Review SQL query
- `/securityreview <code>` - Review code security
- `/bug <description> [logs]` - Investigate bug
- `/help` - Show available commands

## 🎨 Streamlit UI Features

### Dashboard
- Real-time metrics and statistics
- Recent analyses and reports
- System health status

### AI Chat
- Multi-turn conversation
- Agent selection
- Context-aware responses

### File Upload
- Document analysis
- Knowledge base integration
- Format detection

### Analysis Tools
- Test case generator
- SQL reviewer
- Security analyzer
- Performance profiler
- Bug investigator

### Reporting
- Real-time report generation
- Multiple export formats
- Historical tracking

## 🗄️ Knowledge Base

The system supports a multi-format knowledge base for context-aware responses:

### Supported Formats
- **PDF** (.pdf) - Via PyPDF2
- **DOCX** (.docx) - Via python-docx
- **Text** (.txt, .md, .json)

### Features
- Automatic document ingestion
- Text chunking with configurable overlap
- BM25-like semantic search
- Context enrichment for queries

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

## 📊 Project Structure

```
qa-copilot/
├── backend/
│   ├── agents/          # Specialized agent implementations
│   ├── api/             # REST API endpoints
│   ├── auth/            # Authentication & authorization
│   ├── config.py        # Configuration management
│   ├── core/            # Core utilities (logger, etc)
│   ├── execution/       # Test execution engine
│   ├── llm.py           # Multi-provider LLM client
│   ├── main.py          # FastAPI application
│   ├── memory/          # Conversation memory
│   ├── models/          # Data models
│   ├── reporting/       # Report generation
│   ├── router.py        # Agent routing logic
│   └── services/        # Business logic services
├── frontend/
│   └── app.py           # Streamlit web application
├── knowledge/           # Knowledge base files
├── prompts/             # Agent system prompts
├── tests/               # Test suites
├── docker/              # Docker configuration
├── .github/workflows/   # CI/CD pipelines
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker Compose config
└── README.md            # This file
```

## 🔐 Security

- JWT-based authentication with configurable expiration
- Role-based access control (RBAC)
- Permission-based endpoint authorization
- Input validation via Pydantic models
- Secure password hashing (passlib)
- Environment variable management
- CORS configuration for API security

## 🚀 Deployment

### Production Checklist

- [ ] Update `.env` with production API keys
- [ ] Enable HTTPS/SSL certificates
- [ ] Configure database (PostgreSQL recommended)
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Review security settings
- [ ] Load test the system
- [ ] Set up CI/CD pipeline

### Environment Variables

```
ENVIRONMENT=production
OPENROUTER_API_KEY=your_key
MODEL=deepseek/deepseek-chat
DISCORD_TOKEN=your_token
DATABASE_URL=postgresql://user:pass@host/db
JWT_SECRET_KEY=your_secret_key
LOG_LEVEL=INFO
```

## 📈 Performance

- Async/await architecture for scalability
- Connection pooling for database
- Caching for frequently accessed data
- Pagination for large datasets
- Request/response compression

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues, questions, or suggestions:
- Open a GitHub issue
- Check existing documentation
- Review the API docs at `/docs` (Swagger UI)

## 🎯 Roadmap

- [ ] Machine learning-based test case optimization
- [ ] Advanced analytics dashboard
- [ ] Jira & Confluence integration
- [ ] Automated performance regression detection
- [ ] Real-time collaboration features
- [ ] Custom agent development framework
- [ ] Mobile app
- [ ] Advanced caching strategies

---

**Version:** 1.0.0  
**Last Updated:** 2024  
**Status:** Production Ready
