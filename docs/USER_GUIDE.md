# QA Copilot — User Guide

## Overview

QA Copilot is an AI-powered assistant for the full software testing lifecycle. It uses 9 specialized AI agents to help you generate test cases, review code and SQL, investigate bugs, generate automation scripts, and execute tests.

---

## Getting Started

### 1. Log In

Open http://localhost:8501 in your browser.

Enter your credentials (default: `admin` / `admin`) and click **Login**.

### 2. Dashboard

The Dashboard shows:
- Total queries processed
- Active knowledge base documents
- Recent test execution results
- System health status

---

## Core Features

### Chat (AI Assistant)

Navigate to **Chat** in the sidebar.

1. Select an **Agent** from the dropdown (or leave on "Auto" for automatic routing):
   - **Analyst** — Requirements analysis, feature breakdown
   - **Tester** — Test case generation, test strategy
   - **Developer** — Code review, implementation guidance
   - **SQL** — SQL query analysis, optimization, security review
   - **Automation** — Karate/Playwright/Cypress/Selenium code generation
   - **Documentation** — API documentation, user guides
   - **Bug Investigator** — Root cause analysis from logs/traces
   - **Security Reviewer** — OWASP vulnerability review
   - **Performance Engineer** — Load test design, bottleneck analysis

2. Type your question or paste content into the text area.
3. Click **Send** to get the AI response.

**Tips:**
- Paste requirements, code, SQL, logs, or API specs directly into the chat
- The AI remembers conversation context for follow-up questions
- Upload documents first (see Knowledge Base) for context-aware answers

---

### Test Cases

Navigate to **Test Cases**.

**Generate test cases:**
1. Select the test type (API, Mobile, Web, Regression, Smoke, Sanity, Security, Performance, SQL Validation, Edge, Negative, Boundary)
2. Paste your requirement, API spec, or feature description
3. Click **Generate Test Cases**
4. Review the generated test cases
5. Click **Generate Automation** to convert them to executable scripts

**Generate automation scripts:**
1. Paste your requirements
2. Select framework: Karate, Playwright, Cypress, Selenium, Rest Assured, Postman
3. Click **Generate Automation Code**

---

### SQL Review

Navigate to **SQL Review**.

Paste a SQL query and click **Review SQL**. The SQL agent analyzes:
- Query performance (missing indexes, full table scans)
- Security vulnerabilities (SQL injection risks)
- Best practices violations
- Optimization suggestions

---

### Security Review

Navigate to **Security Review**.

Paste code, API endpoints, or configuration and click **Security Review**. The security agent checks:
- OWASP Top 10 vulnerabilities
- Authentication/authorization issues
- Input validation gaps
- Sensitive data exposure
- Insecure dependencies

---

### Bug Investigation

Navigate to **Bug Investigation**.

Describe the bug or paste:
- Error messages and stack traces
- Relevant log excerpts
- API request/response payloads
- Screenshots (upload to knowledge base first)
- SQL query results

Click **Investigate Bug** to get:
- Root cause analysis
- Confidence score
- Suggested fix
- Severity assessment

---

### Knowledge Base

Navigate to **Knowledge Base**.

**Upload documents:**
Supported formats: PDF, DOCX, Markdown, JSON, YAML, SQL, PNG/JPG (OCR)

1. Click **Upload Document**
2. Select your file(s)
3. Wait for ingestion (status shows "indexed")

The knowledge base is automatically searched for context when you ask questions. Upload:
- API specifications (Swagger/OpenAPI JSON/YAML)
- Postman collections
- System architecture documents
- Database schemas
- Previous bug reports
- Test plans

**Search the knowledge base:**
Type a query in the search box to find relevant documents.

---

### Test Execution

Navigate to **Execution**.

1. Define test cases (paste JSON or use generated test cases)
2. Select framework: pytest, Playwright, Karate, Postman
3. Click **Execute Tests**
4. View real-time results
5. Export report in your chosen format

**Export formats:**
- Markdown (`.md`)
- HTML (`.html`)
- JSON (`.json`)
- CSV (`.csv`)
- Excel (`.xlsx`)
- PDF (`.pdf`)
- DOCX (`.docx`)
- Confluence wiki markup

---

### Reports

Navigate to **Reports**.

View execution history, search past runs, and download reports. Each report shows:
- Pass/fail counts and success rate
- Individual test results with error details
- Execution duration
- Framework used

---

### Settings

Navigate to **Settings**.

**Profile:** Update your display name and email.

**API Keys:** Generate API keys for programmatic access:
1. Click **Generate API Key**
2. Give it a name
3. Copy the key (shown only once)
4. Use as `Authorization: Bearer qac_...` header

**Health:** View backend service status and connected components.

---

### User Management (Admin Only)

Navigate to **User Management**.

Admins can:
- View all users
- Create new users with specific roles
- Deactivate users

**Roles:**
| Role | Access Level |
|------|-------------|
| `admin` | Full access, user management |
| `analyst` | Read queries, view reports |
| `developer` | Queries, code review |
| `tester` | Test cases, execution, reports |
| `viewer` | Read-only access |

---

## Discord Bot

If the Discord bot is configured, use these slash commands in any channel:

| Command | Usage |
|---------|-------|
| `/analyze <content>` | Analyze requirements |
| `/testcases <requirement>` | Generate test cases |
| `/sql <query>` | Review SQL query |
| `/automation <req> <framework>` | Generate automation code |
| `/security <code>` | Security vulnerability scan |
| `/bug <description>` | Root cause analysis |
| `/report` | Latest test execution summary |
| `/history` | Your recent query history |
| `/upload` | Get instructions for uploading documents |
| `/help` | List all commands |

---

## API Access

Use the REST API directly:

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Save the access_token from the response
TOKEN="eyJ..."

# Query the AI
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Generate smoke tests for a login API"}'

# Upload a document
curl -X POST http://localhost:8000/api/qa/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@openapi.json"
```

Full API reference: [API.md](API.md)

---

## Tips and Best Practices

1. **Upload context first** — Uploading your API spec, DB schema, or requirements document dramatically improves response quality.

2. **Use specific agents** — For SQL queries, explicitly select the SQL agent. For test cases, select the Tester agent. Auto-routing works but explicit selection is faster.

3. **Iterative refinement** — Follow up in the chat: "Add edge cases", "Generate negative tests", "Convert to Playwright syntax".

4. **Batch uploads** — Upload all relevant documents at project start: API spec + DB schema + existing test plan = rich context for all future queries.

5. **Save reports** — Export and archive execution reports in Excel or PDF for compliance and audit trails.
