# Deployment Guide

This guide covers deploying Stock Screens to production environments.

## Prerequisites

- Python 3.12+
- Node.js 18+
- SQLite (included with Python)

## Environment Variables

### Backend (Required)

| Variable | Description | Example |
|----------|-------------|---------|
| `FMP_API_KEY` | Financial Modeling Prep API key | `abc123...` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `https://app.example.com` |

### Backend (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `POLYGON_API_KEY` | Polygon.io API key for Massive provider | (none) |
| `DATABASE_PATH` | Path to SQLite database | `stock_screens.db` |

### Frontend

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_BASE` | Backend API URL | `https://api.example.com` |

## Production Checklist

### Security

- [ ] **Set `CORS_ORIGINS` explicitly** - Never use `*` in production
- [ ] **Configure SSL/TLS** - Use HTTPS for all traffic
- [ ] **Secure API keys** - Use secrets management (not env files in prod)
- [ ] **Review rate limits** - Adjust provider limits for expected traffic

### Backend

```bash
# Install dependencies
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
# Install and build
cd frontend
npm ci
npm run build

# Serve static files (dist/ folder) with nginx/caddy/etc.
```

### Database

- SQLite is suitable for single-server deployments
- For multi-server: migrate to PostgreSQL
- Set up daily backups:

```bash
#!/bin/bash
# scripts/backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp stock_screens.db backups/stock_screens_$DATE.db
find backups/ -name "stock_screens_*.db" -mtime +30 -delete
```

## Docker Deployment

### Backend Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### Docker Compose

```yaml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - FMP_API_KEY=${FMP_API_KEY}
      - CORS_ORIGINS=https://app.example.com
    volumes:
      - ./data:/app/data  # For SQLite persistence

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

## Monitoring

### Health Check

```bash
curl https://api.example.com/health
# Expected: {"status": "ok"}
```

### Rate Limits

```bash
curl https://api.example.com/api/rate-limits
# Shows current API usage per provider
```

### Recommended Monitoring

1. **Uptime monitoring** - Ping `/health` endpoint every minute
2. **Error tracking** - Add Sentry or similar:
   ```python
   import sentry_sdk
   sentry_sdk.init(dsn="your-dsn")
   ```
3. **Metrics** - Consider adding Prometheus `/metrics` endpoint

## Scaling Considerations

### Single Server (Recommended for < 100 users)

- SQLite works well
- 4 uvicorn workers
- nginx for static files

### Multi-Server

- Migrate to PostgreSQL
- Use Redis for caching (replace in-memory cache)
- Load balancer in front of backend instances
- CDN for frontend static files

## Troubleshooting

### "FMP_API_KEY not set" warning

Set the environment variable:
```bash
export FMP_API_KEY=your_key_here
```

### "CORS_ORIGINS not set" warning

Set explicit origins for production:
```bash
export CORS_ORIGINS=https://app.example.com,https://www.app.example.com
```

### Rate limit errors

Check current usage:
```bash
curl https://api.example.com/api/rate-limits
```

Reset if needed (e.g., for a new billing period):
```bash
curl -X POST https://api.example.com/api/rate-limits/reset
```

### Database locked errors

SQLite can only handle one writer at a time. Solutions:
1. Reduce concurrent requests
2. Enable WAL mode: `PRAGMA journal_mode=WAL;`
3. Migrate to PostgreSQL for high concurrency

## Backup & Recovery

### Database Backup

```bash
# Manual backup
cp stock_screens.db stock_screens_backup_$(date +%Y%m%d).db

# Automated daily backup (add to crontab)
0 2 * * * /path/to/scripts/backup_db.sh
```

### Recovery

```bash
# Stop the server first
cp stock_screens_backup_20240101.db stock_screens.db
# Restart the server
```

## Support

- **Issues**: https://github.com/GeoDoo/stock-screens/issues
- **Documentation**: See `/docs` folder for API and architecture guides
