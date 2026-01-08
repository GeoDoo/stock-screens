# Development Guide

## Prerequisites

- Python 3.12+
- Node.js 18+
- Git

## Environment Setup

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FMP_API_KEY=your_fmp_api_key
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install
```

## Running Locally

### Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

API documentation at `http://localhost:8000/docs`

### Start Frontend

```bash
cd frontend
npm run dev
```

App runs at `http://localhost:5173`

## Project Structure

```
stock-screens/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app and routes
│   │   ├── constants.py
│   │   ├── models/           # Data classes
│   │   └── services/         # Business logic
│   ├── tests/                # Pytest tests
│   ├── requirements.txt
│   └── stock_screens.db      # SQLite database
├── frontend/
│   ├── src/
│   │   ├── main.tsx          # Entry point
│   │   ├── App.tsx           # Main page
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   └── types.ts          # TypeScript types
│   ├── package.json
│   └── vite.config.ts
└── docs/                     # Documentation
```

## Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_dcf_calculator.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

**Test categories:**

| File | Coverage |
|------|----------|
| `test_dcf_calculator.py` | DCF calculation logic |
| `test_wacc_calculator.py` | WACC components |
| `test_fcf_projector.py` | FCF projections |
| `test_scenario_calculator.py` | Scenario analysis |
| `test_sensitivity_calculator.py` | Sensitivity matrix |
| `test_valuation_service.py` | Full valuation flow |
| `test_ratio_calculator.py` | Financial ratios |
| `test_technical_indicators.py` | Technical analysis |
| `test_memo.py` | Memo repository and API |
| `test_assumption_audit.py` | Audit trail |
| `test_api.py` | API endpoints |
| `test_database.py` | Database operations |
| `test_rate_limiter_sqlite.py` | Rate limiting |

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

## Development Workflow

### Test-Driven Development (TDD)

This project follows TDD. When adding new features:

1. **Write failing tests first**
   ```python
   def test_new_feature():
       result = new_feature(input)
       assert result == expected
   ```

2. **Implement the feature**
   ```python
   def new_feature(input):
       # Implementation
       return result
   ```

3. **Refactor while tests pass**

### Adding a New API Endpoint

1. **Write test in `tests/test_api.py`**
   ```python
   def test_new_endpoint(test_client):
       response = test_client.get("/api/new-endpoint")
       assert response.status_code == 200
   ```

2. **Add endpoint in `app/main.py`**
   ```python
   @app.get("/api/new-endpoint")
   async def new_endpoint():
       return {"data": "value"}
   ```

3. **Add TypeScript types in `frontend/src/types.ts`**
   ```typescript
   export interface NewEndpointResponse {
     data: string;
   }
   ```

4. **Call from frontend**
   ```typescript
   const response = await fetch('/api/new-endpoint');
   const data: NewEndpointResponse = await response.json();
   ```

### Adding a New Service

1. **Create service file**
   ```bash
   touch backend/app/services/new_service.py
   ```

2. **Create test file**
   ```bash
   touch backend/tests/test_new_service.py
   ```

3. **Write tests first, then implement**

### Adding a New Component

1. **Create component file**
   ```bash
   touch frontend/src/components/NewComponent.tsx
   ```

2. **Create test file (optional)**
   ```bash
   touch frontend/src/components/NewComponent.test.tsx
   ```

3. **Add to appropriate page/layout**

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Docstrings for public functions

```python
def calculate_wacc(
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float,
    weight_equity: float,
    weight_debt: float,
) -> float:
    """
    Calculate Weighted Average Cost of Capital.
    
    Args:
        cost_of_equity: Required return on equity (e.g., 0.12 for 12%)
        cost_of_debt: Pre-tax cost of debt (e.g., 0.05 for 5%)
        tax_rate: Corporate tax rate (e.g., 0.21 for 21%)
        weight_equity: Equity weight in capital structure
        weight_debt: Debt weight in capital structure
    
    Returns:
        WACC as a decimal (e.g., 0.095 for 9.5%)
    """
    after_tax_debt = cost_of_debt * (1 - tax_rate)
    return (weight_equity * cost_of_equity) + (weight_debt * after_tax_debt)
```

### TypeScript

- Strict mode enabled
- Explicit type annotations
- Use `interface` for object shapes
- Use `type` for unions/primitives

```typescript
interface ValuationResult {
  intrinsic_value_per_share: number;
  current_price: number;
  upside_percent: number;
}

type ConvictionLevel = 'low' | 'medium' | 'high';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}
```

### React Components

- Functional components with hooks
- Props interface defined
- Minimal state, lift when needed

```typescript
interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

export function Button({ label, onClick, disabled = false }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-4 py-2 bg-gray-900 text-white rounded"
    >
      {label}
    </button>
  );
}
```

## Database

### Location

```
backend/stock_screens.db
```

### Viewing Data

```bash
cd backend
sqlite3 stock_screens.db

# List tables
.tables

# View schema
.schema memos

# Query data
SELECT * FROM memos LIMIT 5;
```

### Resetting Database

```bash
rm backend/stock_screens.db
# Restart server - tables are auto-created
```

## Environment Variables

### Backend

| Variable | Required | Description |
|----------|----------|-------------|
| `FMP_API_KEY` | Yes | Financial Modeling Prep API key |

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_BASE` | No | Backend URL (default: `http://localhost:8000`) |

## Common Issues

### CORS Errors

Backend has CORS configured for `localhost:5173`. If using a different port:

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:YOUR_PORT"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limits

FMP has daily limits. Use Yahoo fallback for development:

```typescript
// Force Yahoo provider
const response = await fetch(`/api/stock/${symbol}/analyze?provider=yahoo`);
```

### Database Locked

If you see "database is locked" errors:

1. Ensure only one server instance is running
2. Close any SQLite browser tools
3. Restart the server

## Git Workflow

### Branch Naming

- `feat/feature-name` — New features
- `fix/bug-description` — Bug fixes
- `docs/documentation-topic` — Documentation
- `refactor/area` — Code refactoring

### Commit Messages

```
type: short description

Longer description if needed.

- Bullet points for details
- Another point
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Process

1. Create feature branch
2. Make changes with tests
3. Push and create PR
4. Ensure tests pass
5. Merge to main
