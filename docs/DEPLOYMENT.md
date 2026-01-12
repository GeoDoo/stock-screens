# Deployment Guide

> **Auto-generated** from source code configuration.
> 
> Last updated: 2026-01-12 20:19
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Prerequisites

- Python 3.12+
- Node.js 18+
- SQLite (included with Python)

## Environment Variables

Environment variables read from `backend/app/main.py`:

| Variable | Required | Description |
|----------|----------|-------------|
| `CORS_ORIGINS` | Prod | Comma-separated allowed origins (default: `*`) |
| `FMP_API_KEY` | Yes | Financial Modeling Prep API key |
| `POLYGON_API_KEY` | No | Polygon.io API key for Massive provider |


## Database

- **Path**: `backend/stock_screens.db` (hardcoded in `database.py`)
- **Type**: SQLite
- **Tables**: See `database.py` module docstring

## Health & Monitoring

Endpoints available for monitoring (from `main.py`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check - returns `{"status": "ok"}` |
| `/api/rate-limits` | GET | Current API rate limit stats |
| `/api/rate-limits/reset` | POST | Reset rate limit counters |

## Production Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set required environment variables
export FMP_API_KEY=your_key_here
export CORS_ORIGINS=https://yourapp.com

# Run with production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
cd frontend
npm ci
npm run build

# dist/ folder contains static files for nginx/caddy
```

## Production Checklist

### Security (from `validate_configuration()`)
- [ ] Set `FMP_API_KEY` - FMP provider unavailable without it
- [ ] Set `CORS_ORIGINS` explicitly - wildcard `*` is dev-only
- [ ] Use HTTPS/TLS in production
- [ ] Secure API keys with secrets management (not .env files)

### Operations
- [ ] Set up database backups (see Troubleshooting section)
- [ ] Configure rate limits per provider (check `/api/rate-limits`)
- [ ] Add monitoring (Sentry, Datadog, or Prometheus `GET /metrics`)

## Docker

### Backend

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app

# Database persists at /app/stock_screens.db
VOLUME ["/app"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

## Troubleshooting

### Warnings on startup

The `validate_configuration()` function logs warnings for:
- Missing `FMP_API_KEY` - provider will be unavailable
- Missing `CORS_ORIGINS` - defaults to wildcard (insecure for prod)
- Missing `POLYGON_API_KEY` - Massive provider unavailable (optional)

### Rate limit errors

Check current usage:
```bash
curl http://localhost:8000/api/rate-limits
```

Reset counters:
```bash
curl -X POST http://localhost:8000/api/rate-limits/reset
```
