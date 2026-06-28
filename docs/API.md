# QA Copilot — API Reference

Base URL: `http://localhost:8000`

All protected endpoints require: `Authorization: Bearer <token>`

---

## Authentication

### POST /auth/login
```json
Request:  { "username": "admin", "password": "admin" }
Response: { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "user": {...} }
```

### POST /auth/refresh
```json
Request:  { "refresh_token": "<refresh_token>" }
Response: { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
```

### POST /auth/logout
Revokes the current access token.

### POST /auth/register
```json
Request:  { "username": "...", "email": "...", "password": "...", "roles": ["viewer"] }
Response: { "access_token": "...", "refresh_token": "...", "user": {...} }
```

### GET /auth/me
Returns current user profile.

### GET /auth/users *(admin only)*
Returns list of all users.

### PUT /auth/users/{username} *(admin or self)*
Update user profile (email, full_name, roles, is_active).

### DELETE /auth/users/{username} *(admin only)*
Delete a user.

### POST /auth/api-keys
```json
Request:  { "name": "my-key", "expires_days": 30 }
Response: { "id": "...", "key": "qac_...", "prefix": "qac_abc123", ... }
```
**Note:** The `key` field is only shown once.

### GET /auth/api-keys
List API keys for current user (without raw values).

### DELETE /auth/api-keys/{key_id}
Revoke an API key.

---

## Core Query

### POST /api/query *(requires write:queries)*
```json
Request:  { "query": "generate test cases for login", "agent": "tester", "context": "..." }
Response: { "agent": "tester", "response": "...", "confidence": 0.87 }
```
If `agent` is omitted, auto-routing selects the best agent(s).

---

## QA Operations

### POST /api/qa/test-cases/generate
```json
Request: {
  "requirement": "User can login with email and password",
  "test_types": ["positive", "negative", "boundary", "edge"],
  "framework": "karate",
  "include_automation": false
}
Response: { "agent": "tester", "test_cases": "...", "confidence": 0.92, "duration_ms": 1200 }
```

### POST /api/qa/test-cases/stream
Same as above but returns Server-Sent Events (text/event-stream).

### POST /api/qa/sql/review
```json
Request:  { "sql_query": "SELECT * FROM users", "dialect": "postgresql" }
Response: { "review": "...", "confidence": 0.88 }
```

### POST /api/qa/security/review
```json
Request:  { "code": "...", "language": "python", "focus": ["owasp", "injection"] }
Response: { "review": "...", "confidence": 0.85 }
```

### POST /api/qa/bug/investigate
```json
Request: {
  "description": "Users can't login after 6pm",
  "logs": "...",
  "stack_trace": "...",
  "sql_queries": "...",
  "api_response": "..."
}
Response: { "investigation": "...", "confidence": 0.79 }
```

### POST /api/qa/automation/generate
```json
Request: {
  "requirement": "Test login endpoint",
  "framework": "karate",
  "base_url": "https://api.example.com",
  "endpoints": ["/auth/login", "/auth/logout"]
}
Response: { "automation_code": "...", "framework": "karate", "confidence": 0.91 }
```

### POST /api/qa/analyze
```json
Request:  { "content": "...", "analysis_type": "requirements" }
Response: { "analysis": "...", "confidence": 0.83 }
```

### POST /api/qa/files/upload
Multipart form upload. Field: `file`.
```json
Response: { "id": "...", "filename": "spec.pdf", "size_bytes": 12345, "status": "indexed" }
```

### GET /api/qa/analysis/status
```json
Response: { "documents_indexed": 5, "total_prompts": 42, "agents_available": [...] }
```

### POST /api/qa/performance/analyze
```json
Request:  { "content": "..." }
Response: { "analysis": "..." }
```

### POST /api/qa/documentation/generate
```json
Request:  { "content": "..." }
Response: { "documentation": "..." }
```

---

## Test Execution & Reports

### POST /api/reports/execute *(requires execute:tests)*
```json
Request: {
  "test_cases": [{ "id": "TC001", "name": "Login test", "steps": ["..."] }],
  "framework": "generic",
  "timeout": 300,
  "retry_failed": 1
}
Response: { "run_id": "abc123", "total_tests": 5, "passed": 4, "failed": 1, "success_rate": 80.0, ... }
```

Supported frameworks: `generic`, `pytest`, `playwright`, `karate`, `postman`

### GET /api/reports/execute/{run_id}
Returns full execution report with individual test results.

### GET /api/reports/execute/{run_id}/export/{format} *(requires export:reports)*
Download report in specified format.

Supported formats: `markdown`, `json`, `html`, `csv`, `excel`, `pdf`, `docx`, `confluence`

### GET /api/reports/history
```json
Response: [{ "run_id": "...", "framework": "...", "success_rate": 80.0, ... }]
```

### GET /api/reports/summary
Aggregate statistics across all in-memory runs.

---

## Knowledge Base

### POST /api/knowledge/search
```
Query params: query=<string>, top_k=<int>
Response: { "query": "...", "results": ["chunk1", "chunk2", ...], "count": 3 }
```

### GET /api/knowledge/documents
List all documents in the knowledge base.

### GET /api/knowledge/stats
```json
Response: {
  "total_documents": 10,
  "indexed_documents": 9,
  "total_chunks": 450,
  "by_file_type": { "pdf": 5, "md": 3, "docx": 2 }
}
```

---

## System

### GET /health
```json
Response: { "status": "ok", "environment": "development", "database": "ok", "version": "1.0.0" }
```

---

## Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request (validation error, missing field) |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not found (agent, report, user) |
| 413 | File too large (max 50MB) |
| 422 | Unprocessable entity (Pydantic validation) |
| 500 | Internal server error |
| 502 | Agent/LLM error |

---

## Authentication Schemes

### Bearer JWT
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

### Bearer API Key
```http
Authorization: Bearer qac_abc123def456...
```

API keys are generated via `POST /auth/api-keys` and work identically to JWT tokens but don't expire by default (configurable).
