# QA Copilot — Deployment Guide

## Docker Compose (Recommended)

### Prerequisites
- Docker 24+
- Docker Compose v2+

### Steps

```bash
# 1. Clone and configure
git clone <repo-url>
cd QA-COPILOT
cp .env.example .env

# 2. Edit .env — set at minimum:
#   OPENROUTER_API_KEY=sk-...
#   JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
#   ADMIN_PASSWORD=your-secure-password

# 3. Build and start
docker-compose up --build -d

# 4. Verify
curl http://localhost:8000/health
```

Services:
- **Backend API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **Web UI**: http://localhost:8501

### Volumes

| Volume | Purpose |
|--------|---------|
| `qa-copilot-db` | SQLite database (persists between restarts) |
| `chroma-data` | ChromaDB vector store |

### Health checks

Docker Compose waits for the backend health check before starting the frontend:
```yaml
depends_on:
  backend:
    condition: service_healthy
```

Backend health check: `GET /health` → must return `{"status": "ok"}` within 30s.

---

## Production: PostgreSQL

Switch from SQLite to PostgreSQL for multi-instance deployments:

```env
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/qa_copilot
```

Add to `docker-compose.yml`:
```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: qa_user
    POSTGRES_PASSWORD: qa_pass
    POSTGRES_DB: qa_copilot
  volumes:
    - pg-data:/var/lib/postgresql/data

volumes:
  pg-data:
```

Install driver: `pip install asyncpg`

---

## Kubernetes (Helm-style)

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: qa-copilot-config
data:
  ENVIRONMENT: production
  MODEL: deepseek/deepseek-chat
  DATABASE_URL: postgresql+asyncpg://user:pass@postgres-svc:5432/qa_copilot
  LOG_LEVEL: INFO
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: qa-copilot-secrets
type: Opaque
stringData:
  OPENROUTER_API_KEY: "sk-..."
  JWT_SECRET_KEY: "your-32-char-secret"
  ADMIN_PASSWORD: "secure-password"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qa-copilot-backend
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: backend
          image: qa-copilot:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: qa-copilot-config
            - secretRef:
                name: qa-copilot-secrets
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

---

## CI/CD: GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=backend --cov=knowledge --cov-report=xml
      - uses: codecov/codecov-action@v4

  build-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
```

---

## SSL / Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name qa-copilot.example.com;

    ssl_certificate /etc/letsencrypt/live/qa-copilot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qa-copilot.example.com/privkey.pem;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Environment Checklist (Production)

- [ ] `JWT_SECRET_KEY` is at least 32 random characters
- [ ] `ADMIN_PASSWORD` is changed from default
- [ ] `DATABASE_URL` points to PostgreSQL (not SQLite)
- [ ] `ENVIRONMENT=production`
- [ ] `CORS_ORIGINS` is restricted to your domain
- [ ] SSL/TLS is configured
- [ ] Logs are shipped to a log aggregator
- [ ] Health check alerts are configured
- [ ] Backups for the database volume
