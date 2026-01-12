#!/usr/bin/env python3
"""
Auto-generate ALL documentation from source code.
Run: python scripts/generate_all_docs.py
"""

import os
import sys
import ast
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add backend to path
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DOCS_DIR = PROJECT_ROOT / "docs"

sys.path.insert(0, str(BACKEND_DIR))


def generate_api_docs():
    """Generate API.md from FastAPI OpenAPI schema."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_api_docs.py")],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(f"Warning: API docs generation had issues: {result.stderr}")


def extract_class_info(filepath: Path) -> list:
    """Extract class names and docstrings from a Python file."""
    classes = []
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                        method_doc = ast.get_docstring(item) or ""
                        methods.append({
                            "name": item.name,
                            "docstring": method_doc.split('\n')[0] if method_doc else ""
                        })
                classes.append({
                    "name": node.name,
                    "docstring": docstring.split('\n')[0] if docstring else "",
                    "methods": methods[:5]  # Top 5 methods
                })
    except:
        pass
    return classes


def generate_architecture_docs():
    """Generate ARCHITECTURE.md from codebase structure."""
    
    # Scan backend services
    services_dir = BACKEND_DIR / "app" / "services"
    services = []
    for f in sorted(services_dir.glob("*.py")):
        if f.name.startswith("__"):
            continue
        classes = extract_class_info(f)
        services.append({
            "file": f.name,
            "classes": classes
        })
    
    # Scan frontend components
    components_dir = FRONTEND_DIR / "src" / "components"
    components = [f.name for f in sorted(components_dir.glob("*.tsx")) if not f.name.endswith(".test.tsx")]
    
    # Scan hooks
    hooks_dir = FRONTEND_DIR / "src" / "hooks"
    hooks = [f.name for f in sorted(hooks_dir.glob("*.ts")) if not f.name.endswith(".test.ts")]
    
    # Count tests
    backend_tests = len(list((BACKEND_DIR / "tests").glob("test_*.py")))
    frontend_tests = len(list((FRONTEND_DIR / "src").rglob("*.test.ts*")))
    
    # Generate markdown
    content = f"""# Architecture

> **Auto-generated** from source code structure.
> 
> Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Overview

Stock Screens is a full-stack stock analysis application with:
- **Backend**: FastAPI (Python) - DCF valuation, financial analysis
- **Frontend**: React + TypeScript + Vite - Interactive UI
- **Database**: SQLite - Rate limits, audit trails, memos

## Backend Architecture

### Services (`backend/app/services/`)

| Service | Purpose |
|---------|---------|
"""
    
    for svc in services:
        name = svc["file"].replace(".py", "").replace("_", " ").title()
        if svc["classes"]:
            purpose = svc["classes"][0]["docstring"] or "—"
        else:
            purpose = "—"
        content += f"| `{svc['file']}` | {purpose[:60]} |\n"
    
    content += """
### Key Services Detail

"""
    
    # Detail key services
    key_services = ["valuation_service.py", "dcf_calculator.py", "wacc_calculator.py", 
                    "fcf_projector.py", "monte_carlo.py", "data_extractor.py"]
    
    for svc in services:
        if svc["file"] in key_services and svc["classes"]:
            cls = svc["classes"][0]
            content += f"#### `{svc['file']}` - {cls['name']}\n\n"
            if cls["docstring"]:
                content += f"{cls['docstring']}\n\n"
            if cls["methods"]:
                content += "**Key Methods:**\n"
                for m in cls["methods"]:
                    content += f"- `{m['name']}()` - {m['docstring']}\n"
                content += "\n"
    
    content += f"""## Frontend Architecture

### Components (`frontend/src/components/`)

| Component | Description |
|-----------|-------------|
"""
    
    for comp in components:
        name = comp.replace(".tsx", "")
        content += f"| `{comp}` | {name} |\n"
    
    content += f"""
### Hooks (`frontend/src/hooks/`)

| Hook | Purpose |
|------|---------|
"""
    
    for hook in hooks:
        name = hook.replace(".ts", "")
        content += f"| `{hook}` | {name.replace('use', '').replace('-', ' ').title()} |\n"
    
    content += f"""
## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│  Providers  │
│   (React)   │◀────│   Backend   │◀────│ (FMP/Yahoo) │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌─────────┐  ┌─────────────┐
              │ SQLite  │  │ Calculators │
              │   DB    │  │  & Models   │
              └─────────┘  └─────────────┘
```

## Database Schema

The application uses a single SQLite database (`stock_screens.db`) with the following tables:

| Table | Purpose |
|-------|---------|
| `api_calls` | Rate limiting call records |
| `api_limited` | Rate limiting status flags |
| `audit_entries` | Assumption audit trail entries |
| `audit_changes` | Individual field changes per audit entry |
| `memos` | Investment memos with thesis and assumptions |
| `memo_scenarios` | Scenarios at memo creation time |
| `memo_market_snapshots` | Periodic market tracking |
| `memo_post_mortems` | Post-mortem reviews |
| `filing_pdfs` | Cached SEC filing PDFs |

## Test Coverage

| Layer | Test Files | Framework |
|-------|------------|-----------|
| Backend | {backend_tests} test files | pytest |
| Frontend | {frontend_tests} test files | vitest |

## Constants (`backend/app/constants.py`)

All magic numbers are centralized:
- `DEFAULT_TREASURY_RATE` - Risk-free rate fallback
- `DEFAULT_TAX_RATE` - Tax rate when data missing
- `DEFAULT_MARKET_RISK_PREMIUM` - Historical market premium
- `DEFAULT_TERMINAL_GROWTH` - Long-term GDP growth
"""
    
    # Write file
    output_path = DOCS_DIR / "ARCHITECTURE.md"
    with open(output_path, "w") as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")
    print(f"  {len(content.splitlines())} lines")


def generate_dcf_docs():
    """Generate DCF_MODEL.md from valuation service docstrings."""
    
    # Extract docstrings from key files
    dcf_calc = BACKEND_DIR / "app" / "services" / "dcf_calculator.py"
    wacc_calc = BACKEND_DIR / "app" / "services" / "wacc_calculator.py"
    fcf_proj = BACKEND_DIR / "app" / "services" / "fcf_projector.py"
    monte_carlo = BACKEND_DIR / "app" / "services" / "monte_carlo.py"
    multi_stage = BACKEND_DIR / "app" / "services" / "multi_stage_growth.py"
    
    def get_file_docstring(filepath):
        try:
            with open(filepath) as f:
                tree = ast.parse(f.read())
            return ast.get_docstring(tree) or ""
        except:
            return ""
    
    def get_class_full_doc(filepath):
        try:
            with open(filepath) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    return ast.get_docstring(node) or ""
        except:
            return ""
    
    dcf_doc = get_class_full_doc(dcf_calc)
    wacc_doc = get_class_full_doc(wacc_calc)
    fcf_doc = get_class_full_doc(fcf_proj)
    monte_doc = get_class_full_doc(monte_carlo)
    multi_doc = get_class_full_doc(multi_stage)
    
    content = f"""# DCF Valuation Model

> **Auto-generated** from source code docstrings.
> 
> Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Overview

This application implements a **Discounted Cash Flow (DCF)** model for intrinsic value estimation.

## DCF Calculator

{dcf_doc}

## WACC Calculator

{wacc_doc}

## FCF Projector

{fcf_doc}

## Multi-Stage Growth

{multi_doc}

## Monte Carlo Simulation

{monte_doc}

## Key Formulas

### Intrinsic Value
```
Intrinsic Value = Σ(FCF_t / (1 + WACC)^t) + Terminal Value / (1 + WACC)^n
```

### WACC (Weighted Average Cost of Capital)
```
WACC = (E/V) × Re + (D/V) × Rd × (1 - Tc)

Where:
  E = Market value of equity
  D = Market value of debt
  V = E + D (total firm value)
  Re = Cost of equity (from CAPM)
  Rd = Cost of debt
  Tc = Corporate tax rate
```

### Cost of Equity (CAPM)
```
Re = Rf + β × (Rm - Rf)

Where:
  Rf = Risk-free rate
  β = Beta (systematic risk)
  Rm - Rf = Market risk premium
```

### Free Cash Flow
```
FCF = NOPAT + D&A - CapEx - ΔWC

Where:
  NOPAT = EBIT × (1 - Tax Rate)
  D&A = Depreciation & Amortization
  CapEx = Capital Expenditures
  ΔWC = Change in Working Capital
```

### Terminal Value (Gordon Growth)
```
TV = FCF_n × (1 + g) / (WACC - g)

Where:
  FCF_n = Final year FCF
  g = Terminal growth rate (must be < WACC)
```

## Working Capital Modes

1. **Level Mode**: `WC = Revenue × WC_ratio`
2. **Incremental Mode**: `ΔWC = (Revenue_t - Revenue_t-1) × WC_intensity`

## Mid-Year Discounting

Optional adjustment that assumes cash flows occur mid-year rather than year-end:
```
Discount Factor = 1 / (1 + WACC)^(t - 0.5)
```

## Guardrails

- WACC must be greater than terminal growth rate
- Shares outstanding must be positive
- Warnings for negative FCF projections
- Warnings for distressed companies (negative equity)
"""
    
    # Write file
    output_path = DOCS_DIR / "DCF_MODEL.md"
    with open(output_path, "w") as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")
    print(f"  {len(content.splitlines())} lines")


def generate_deployment_docs():
    """Generate DEPLOYMENT.md from code configuration."""
    import re
    
    main_py = BACKEND_DIR / "app" / "main.py"
    database_py = BACKEND_DIR / "app" / "services" / "database.py"
    
    # Known env var metadata (description and required status)
    ENV_VAR_METADATA = {
        "FMP_API_KEY": ("Yes", "Financial Modeling Prep API key"),
        "CORS_ORIGINS": ("Prod", "Comma-separated allowed origins (default: `*`)"),
        "POLYGON_API_KEY": ("No", "Polygon.io API key for Massive provider"),
    }
    
    # Extract environment variables from main.py
    env_vars = []
    try:
        with open(main_py) as f:
            content = f.read()
        
        # Find os.getenv calls
        for match in re.finditer(r'os\.getenv\(["\'](\w+)["\']', content):
            env_vars.append(match.group(1))
        env_vars = sorted(set(env_vars))
    except:
        env_vars = list(ENV_VAR_METADATA.keys())
    
    # Build env vars table dynamically
    env_vars_table = "| Variable | Required | Description |\n|----------|----------|-------------|\n"
    for var in env_vars:
        if var in ENV_VAR_METADATA:
            required, desc = ENV_VAR_METADATA[var]
        else:
            # Unknown variable found in code - flag it
            required, desc = "?", f"Found in code (add to ENV_VAR_METADATA)"
        env_vars_table += f"| `{var}` | {required} | {desc} |\n"
    
    # Extract database path from database.py
    db_path = "stock_screens.db"
    try:
        with open(database_py) as f:
            db_content = f.read()
        # Extract actual path from DEFAULT_DB_PATH line
        match = re.search(r'["\']([^"\']+\.db)["\']', db_content)
        if match:
            db_path = match.group(1)
    except:
        pass
    
    # Extract health endpoint
    health_endpoint = "/health"
    rate_limits_endpoint = "/api/rate-limits"
    
    content = f"""# Deployment Guide

> **Auto-generated** from source code configuration.
> 
> Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Prerequisites

- Python 3.12+
- Node.js 18+
- SQLite (included with Python)

## Environment Variables

Environment variables read from `backend/app/main.py`:

{env_vars_table}

## Database

- **Path**: `backend/{db_path}` (hardcoded in `database.py`)
- **Type**: SQLite
- **Tables**: See `database.py` module docstring

## Health & Monitoring

Endpoints available for monitoring (from `main.py`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `{health_endpoint}` | GET | Health check - returns `{{"status": "ok"}}` |
| `{rate_limits_endpoint}` | GET | Current API rate limit stats |
| `{rate_limits_endpoint}/reset` | POST | Reset rate limit counters |

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
- [ ] Configure rate limits per provider (check `{rate_limits_endpoint}`)
- [ ] Add monitoring (Sentry, Datadog, or Prometheus `GET /metrics`)

## Docker

### Backend

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app

# Database persists at /app/{db_path}
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
curl http://localhost:8000{rate_limits_endpoint}
```

Reset counters:
```bash
curl -X POST http://localhost:8000{rate_limits_endpoint}/reset
```
"""
    
    # Write file
    output_path = DOCS_DIR / "DEPLOYMENT.md"
    with open(output_path, "w") as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")
    print(f"  {len(content.splitlines())} lines")


def generate_development_docs():
    """Generate DEVELOPMENT.md from package files."""
    
    # Read requirements.txt
    requirements = []
    req_file = BACKEND_DIR / "requirements.txt"
    if req_file.exists():
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    requirements.append(line)
    
    # Read package.json
    pkg_file = FRONTEND_DIR / "package.json"
    frontend_deps = {}
    frontend_dev_deps = {}
    if pkg_file.exists():
        with open(pkg_file) as f:
            pkg = json.load(f)
            frontend_deps = pkg.get("dependencies", {})
            frontend_dev_deps = pkg.get("devDependencies", {})
    
    # Count tests
    backend_tests = list((BACKEND_DIR / "tests").glob("test_*.py"))
    frontend_tests = list((FRONTEND_DIR / "src").rglob("*.test.ts*"))
    
    content = f"""# Development Guide

> **Auto-generated** from package files.
> 
> Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Prerequisites

- Python 3.12+
- Node.js 18+
- npm 9+

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\\Scripts\\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Backend Dependencies

| Package | Version |
|---------|---------|
"""
    
    for req in requirements[:20]:  # Top 20
        parts = req.split("==")
        name = parts[0].split(">=")[0].split("[")[0]
        version = parts[1] if len(parts) > 1 else "latest"
        content += f"| `{name}` | {version} |\n"
    
    if len(requirements) > 20:
        content += f"| ... | ({len(requirements) - 20} more) |\n"
    
    content += """
## Frontend Dependencies

| Package | Version |
|---------|---------|
"""
    
    for name, version in list(frontend_deps.items())[:15]:
        content += f"| `{name}` | {version} |\n"
    
    content += f"""
## Running Tests

### Backend Tests ({len(backend_tests)} test files)

```bash
cd backend
source venv/bin/activate
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --tb=short -q      # Quick summary
pytest tests/test_api.py  # Specific file
```

### Frontend Tests ({len(frontend_tests)} test files)

```bash
cd frontend
npm test                  # Watch mode
npm test -- --run         # Single run
npm test -- --coverage    # With coverage
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FMP_API_KEY` | Optional | Financial Modeling Prep API key |

## Database

SQLite database at `backend/stock_screens.db`:
- `rate_limits` - API call tracking
- `audit_trail` - Assumption change history
- `memos` - Investment memos

## Documentation

All docs are auto-generated:

```bash
python scripts/generate_all_docs.py
```

This regenerates:
- `docs/API.md` - API endpoints
- `docs/ARCHITECTURE.md` - Code structure
- `docs/DCF_MODEL.md` - Valuation math
- `docs/DEVELOPMENT.md` - This file

## Pre-commit Hook

Documentation auto-updates on every commit:

```bash
# .git/hooks/pre-commit runs:
python scripts/generate_all_docs.py
git add docs/*.md
```

## Code Style

- **Backend**: Python with type hints, docstrings required
- **Frontend**: TypeScript strict mode, ESLint
- **Tests**: TDD approach, all new code must have tests
"""
    
    # Write file
    output_path = DOCS_DIR / "DEVELOPMENT.md"
    with open(output_path, "w") as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")
    print(f"  {len(content.splitlines())} lines")


def main():
    print("📚 Generating ALL documentation...\n")
    
    # Ensure docs directory exists
    DOCS_DIR.mkdir(exist_ok=True)
    
    # Generate all docs
    generate_api_docs()
    generate_architecture_docs()
    generate_dcf_docs()
    generate_development_docs()
    generate_deployment_docs()
    
    print("\n✅ All documentation generated!")


if __name__ == "__main__":
    main()
