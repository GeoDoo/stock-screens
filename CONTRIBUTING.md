# Contributing

## Documentation-First Development

This project maintains documentation as a first-class citizen. **Documentation is code** — it should be accurate, tested, and versioned.

### The Golden Rule

> If you change the code, update the docs.

### Automated Enforcement

We use multiple layers to keep docs in sync:

| Layer | What it does |
|-------|--------------|
| **Pre-commit hooks** | Validates docs before every commit |
| **CI/CD** | Blocks PRs with broken doc links or stale generated docs |
| **Auto-generation** | API docs generated from FastAPI schema |
| **Validation scripts** | Check endpoints, links, code blocks |

### Setup

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Now docs are validated on every commit
```

## Documentation Structure

```
docs/
├── API.md              # Hand-written API guide with examples
├── API_GENERATED.md    # Auto-generated from OpenAPI (don't edit)
├── ARCHITECTURE.md     # System design and data flow
├── DEVELOPMENT.md      # Setup and workflow guide
└── DCF_MODEL.md        # Valuation methodology
```

### When to Update What

| You changed... | Update... |
|----------------|-----------|
| API endpoint | `docs/API.md` |
| New service/module | `docs/ARCHITECTURE.md` |
| Build/test process | `docs/DEVELOPMENT.md` |
| DCF calculation | `docs/DCF_MODEL.md` |
| Main features | `README.md` |

### Auto-Generated Docs

`API_GENERATED.md` is created from FastAPI's OpenAPI schema:

```bash
python scripts/generate_api_docs.py
```

This runs automatically in CI. If it changes, the PR will fail until you commit the updated file.

## Pull Request Checklist

Before submitting a PR:

- [ ] Tests pass (`pytest` / `npm test`)
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] Documentation updated if code changed
- [ ] New endpoints have examples in API.md

## Writing Good Documentation

### API Examples

Always include request AND response:

```markdown
### Get Stock Data

```
GET /api/stock/{symbol}/analyze
```

**Request**

```bash
curl http://localhost:8000/api/stock/AAPL/analyze
```

**Response**

```json
{
  "symbol": "AAPL",
  "company_name": "Apple Inc."
}
```
```

### Architecture Diagrams

Use ASCII for portability:

```
┌─────────┐     ┌─────────┐
│ Frontend│────▶│ Backend │
└─────────┘     └─────────┘
```

### Code Examples

Ensure they're syntactically valid — the validation script checks this:

```python
# Good - valid Python
def calculate_wacc(cost_of_equity: float) -> float:
    return cost_of_equity * 0.8
```

## Running Validation Manually

```bash
# Validate all documentation
python scripts/validate_docs.py

# Regenerate API docs
python scripts/generate_api_docs.py
```

## Questions?

Open an issue if docs are unclear. Unclear docs are bugs.
