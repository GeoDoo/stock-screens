# API Reference

Base URL: `http://localhost:8000`

## Stock Analysis

### Get Basic Stock Data

Returns basic company data (lightweight endpoint).

```
GET /api/stock/{symbol}
```

**Response**

```json
{
  "symbol": "AAPL",
  "company_name": "Apple Inc.",
  "profile": {
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "price": 178.50,
    "market_cap": 2800000000000
  }
}
```

---

### Get Full Analysis Data

Fetches company fundamentals and historical hints for DCF inputs.

```
GET /api/stock/{symbol}/analyze
```

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | string | `fmp` | Data provider (`fmp`, `yahoo`, `massive`) |

**Response**

```json
{
  "symbol": "AAPL",
  "company_name": "Apple Inc.",
  "profile": {
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "description": "...",
    "price": 178.50,
    "market_cap": 2800000000000
  },
  "data": {
    "beta": 1.25,
    "market_cap": 2800000000000,
    "total_debt": 111088000000,
    "cash": 29965000000,
    "shares_outstanding": 15700000000,
    "tax_rate": 0.147,
    "risk_free_rate": 0.045,
    "historical_revenue": [394328000000, 383285000000, 365817000000],
    "historical_ebit": [119437000000, 114301000000, 111852000000],
    "historical_da": [11519000000, 11104000000, 11284000000],
    "historical_capex": [-10708000000, -10959000000, -11085000000],
    "historical_working_capital": [-1234000000, -1456000000, -1678000000]
  },
  "hints_annual": {
    "revenue_growth": 0.024,
    "operating_margin": 0.298,
    "da_ratio": 0.029,
    "capex_ratio": 0.027,
    "wc_ratio": -0.003
  },
  "hints_ttm": {
    "revenue_growth": 0.031,
    "operating_margin": 0.305,
    "da_ratio": 0.028,
    "capex_ratio": 0.026,
    "wc_ratio": -0.002
  },
  "provider_used": "fmp",
  "fallback_reason": null
}
```

---

### Run DCF Valuation

Calculates intrinsic value using provided assumptions.

```
POST /api/stock/{symbol}/valuation
```

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | string | `fmp` | Data provider |

**Request Body**

```json
{
  "revenue_growth": 0.10,
  "operating_margin": 0.30,
  "terminal_growth_rate": 0.03,
  "market_risk_premium": 0.06,
  "projection_years": 10,
  "da_ratio": 0.029,
  "capex_ratio": 0.027,
  "wc_ratio": -0.003,
  "discount_rate_override": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `revenue_growth` | float | Yes | Annual revenue growth rate (0.10 = 10%) |
| `operating_margin` | float | Yes | EBIT as % of revenue (0.30 = 30%) |
| `terminal_growth_rate` | float | Yes | Perpetual growth rate (0.03 = 3%) |
| `market_risk_premium` | float | Yes | Equity risk premium (0.06 = 6%) |
| `projection_years` | int | Yes | Years to project (typically 5-10) |
| `da_ratio` | float | No | D&A as % of revenue |
| `capex_ratio` | float | No | CapEx as % of revenue |
| `wc_ratio` | float | No | Working capital change as % of revenue |
| `discount_rate_override` | float | No | Custom WACC override |

**Response**

```json
{
  "intrinsic_value_per_share": 185.50,
  "current_price": 178.50,
  "upside_percent": 3.9,
  "enterprise_value": 3100000000000,
  "equity_value": 2920000000000,
  "terminal_value": 2500000000000,
  "discount_rate": 0.095,
  "projections": [
    {
      "revenue": 433760800000,
      "ebit": 130128240000,
      "nopat": 111079476000,
      "da": 12579064000,
      "capex": -11711542000,
      "working_capital": -1301282400,
      "delta_wc": 67174600,
      "fcf": 112014172600
    }
  ],
  "wacc_components": {
    "cost_of_equity": 0.1175,
    "cost_of_debt": 0.045,
    "weight_equity": 0.85,
    "weight_debt": 0.15,
    "tax_rate": 0.147
  }
}
```

---

### Run Scenario Analysis

Runs multiple scenarios (bull/base/bear) and returns comparison.

```
POST /api/stock/{symbol}/scenarios
```

**Request Body**

```json
{
  "scenarios": [
    {
      "name": "Bear",
      "revenue_growth": 0.05,
      "operating_margin": 0.25
    },
    {
      "name": "Base",
      "revenue_growth": 0.10,
      "operating_margin": 0.30
    },
    {
      "name": "Bull",
      "revenue_growth": 0.15,
      "operating_margin": 0.35
    }
  ],
  "projection_years": 10,
  "market_risk_premium": 0.06,
  "discount_rate_override": null,
  "revenue_growth_hint": 0.10,
  "operating_margin_hint": 0.30,
  "da_ratio": 0.029,
  "capex_ratio": 0.027,
  "wc_ratio": -0.003
}
```

If `scenarios` is null, default scenarios are generated from hints.

**Response**

```json
{
  "scenarios": [
    {
      "name": "Bear",
      "revenue_growth": 0.05,
      "operating_margin": 0.25,
      "intrinsic_value": 145.00,
      "upside_percent": -18.8,
      "terminal_value": 1800000000000
    },
    {
      "name": "Base",
      "revenue_growth": 0.10,
      "operating_margin": 0.30,
      "intrinsic_value": 185.50,
      "upside_percent": 3.9,
      "terminal_value": 2500000000000
    },
    {
      "name": "Bull",
      "revenue_growth": 0.15,
      "operating_margin": 0.35,
      "intrinsic_value": 245.00,
      "upside_percent": 37.3,
      "terminal_value": 3500000000000
    }
  ],
  "discount_rate": 0.095
}
```

---

### Get Financial Ratios

Returns comprehensive financial ratios.

```
GET /api/stock/{symbol}/ratios
```

**Response**

```json
{
  "annual": {
    "profitability": {
      "gross_margin": 0.438,
      "operating_margin": 0.298,
      "net_margin": 0.253,
      "roe": 1.472,
      "roa": 0.283
    },
    "liquidity": {
      "current_ratio": 0.988,
      "quick_ratio": 0.813
    },
    "leverage": {
      "debt_to_equity": 1.99,
      "debt_to_assets": 0.31,
      "interest_coverage": 29.5
    },
    "valuation": {
      "pe_ratio": 28.5,
      "price_to_book": 42.0,
      "price_to_sales": 7.2,
      "ev_to_ebitda": 21.5
    }
  },
  "ttm": {
    "profitability": {},
    "liquidity": {},
    "leverage": {},
    "valuation": {}
  }
}
```

---

### Get Comparable Analysis

Returns peer comparison data.

```
GET /api/stock/{symbol}/comparables
```

**Response**

```json
{
  "target": {
    "symbol": "AAPL",
    "pe_ratio": 28.5,
    "ev_ebitda": 21.5,
    "price_to_sales": 7.2,
    "price_to_book": 42.0
  },
  "peers": [
    {
      "symbol": "MSFT",
      "pe_ratio": 32.1,
      "ev_ebitda": 24.3,
      "price_to_sales": 11.5,
      "price_to_book": 10.8
    }
  ],
  "sector_median": {
    "pe_ratio": 25.0,
    "ev_ebitda": 18.0,
    "price_to_sales": 5.0,
    "price_to_book": 8.0
  }
}
```

---

### Get Dividend History

```
GET /api/stock/{symbol}/dividends
```

**Response**

```json
{
  "symbol": "AAPL",
  "dividends": [
    {
      "date": "2024-02-09",
      "amount": 0.24
    }
  ],
  "dividend_yield": 0.005,
  "payout_ratio": 0.15
}
```

---

### Get Historical Valuation

Returns historical P/E, P/B, and other multiples.

```
GET /api/stock/{symbol}/historical-valuation
```

**Response**

```json
{
  "symbol": "AAPL",
  "history": [
    {
      "date": "2024-01-15",
      "pe_ratio": 28.5,
      "pb_ratio": 42.0,
      "ps_ratio": 7.2
    }
  ]
}
```

---

## Technical Analysis

### Get Technical Indicators

```
GET /api/stock/{symbol}/technical
```

**Response**

```json
{
  "price_data": {
    "current": 178.50,
    "change_percent": 1.25,
    "high_52w": 199.62,
    "low_52w": 124.17,
    "volume": 52000000,
    "avg_volume": 58000000
  },
  "moving_averages": {
    "sma_20": 175.30,
    "sma_50": 172.50,
    "sma_200": 168.00,
    "ema_12": 176.80,
    "ema_26": 174.20
  },
  "momentum": {
    "rsi_14": 58.5,
    "macd": 2.6,
    "macd_signal": 1.8,
    "macd_histogram": 0.8
  },
  "trend": {
    "direction": "bullish",
    "strength": "moderate"
  }
}
```

---

## Investment Memos

### List Memos

```
GET /api/memos
```

**Response**

```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "title": "Apple Q4 2024 Thesis",
    "thesis": "Strong services growth offsetting hardware...",
    "conviction": "high",
    "time_horizon_months": 12,
    "created_at": "2024-01-15T10:30:00Z",
    "status": "open",
    "current_performance": {
      "current_price": 185.50,
      "return_percent": 3.9
    }
  }
]
```

---

### Create Memo

```
POST /api/memos
```

**Request Body**

```json
{
  "symbol": "AAPL",
  "title": "Apple Q4 2024 Thesis",
  "thesis": "Strong services growth offsetting hardware headwinds...",
  "conviction": "high",
  "time_horizon_months": 12,
  "target_price": 200.00,
  "catalysts": "iPhone 16 launch, AI features, services growth",
  "risks": "China exposure, regulatory pressure",
  "what_would_change_mind": "Services growth below 10%, margin compression",
  "assumptions": {
    "revenue_growth": 0.10,
    "operating_margin": 0.30,
    "terminal_growth_rate": 0.03,
    "discount_rate": 0.095,
    "projection_years": 10
  },
  "scenarios": [],
  "initial_market": {
    "price": 178.50,
    "intrinsic_value": 185.50,
    "pe_ratio": 28.5
  }
}
```

---

### Get Memo

```
GET /api/memos/{id}
```

---

### Update Memo

```
PUT /api/memos/{id}
```

**Request Body**

Same fields as Create Memo (partial updates supported).

---

### Delete Memo

```
DELETE /api/memos/{id}
```

---

### Add Market Snapshot

Records current market data for tracking.

```
POST /api/memos/{id}/snapshots
```

---

### Add Post-Mortem

```
POST /api/memos/{id}/post-mortems
```

**Request Body**

```json
{
  "content": "Q4 earnings beat expectations. Raising conviction.",
  "action_taken": "add"
}
```

| `action_taken` | Description |
|----------------|-------------|
| `hold` | Maintaining position |
| `add` | Adding to position |
| `trim` | Reducing position |
| `exit` | Exiting position |

---

### Close Memo

```
POST /api/memos/{id}/close
```

**Request Body**

```json
{
  "reason": "Thesis played out. Target reached."
}
```

---

## Assumption Audit Trail

### Get Audit History

```
GET /api/audit/{symbol}/history
```

**Response**

```json
{
  "symbol": "AAPL",
  "entries": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "changes": [
        {
          "field": "revenue_growth",
          "old_value": 0.08,
          "new_value": 0.10
        }
      ],
      "note": "Updated growth assumption after Q4 earnings",
      "is_initial": false,
      "price_at_time": 178.50,
      "intrinsic_value_at_time": 185.50,
      "pe_ratio_at_time": 28.5
    }
  ]
}
```

---

### Get Current Snapshot

```
GET /api/audit/{symbol}/snapshot
```

**Response**

```json
{
  "symbol": "AAPL",
  "revenue_growth": 0.10,
  "operating_margin": 0.30,
  "terminal_growth_rate": 0.03,
  "projection_years": 10
}
```

---

### Get Field History

```
GET /api/audit/{symbol}/field/{field}
```

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `field` | string | Field name (e.g., `revenue_growth`, `operating_margin`) |

**Response**

```json
{
  "field": "revenue_growth",
  "history": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "value": 0.10,
      "note": "Updated for Q4"
    },
    {
      "timestamp": "2024-01-01T09:00:00Z",
      "value": 0.08,
      "note": "Initial analysis"
    }
  ]
}
```

---

### Record Assumptions

```
POST /api/audit/{symbol}
```

**Request Body**

```json
{
  "assumptions": {
    "revenue_growth": 0.10,
    "operating_margin": 0.30,
    "terminal_growth_rate": 0.03,
    "projection_years": 10
  },
  "note": "Initial analysis",
  "price_at_time": 178.50,
  "intrinsic_value_at_time": 185.50,
  "pe_ratio_at_time": 28.5
}
```

---

## Providers

### List Providers

```
GET /api/providers
```

**Response**

```json
{
  "fundamental": [
    {
      "id": "fmp",
      "name": "Financial Modeling Prep",
      "description": "Professional financial data API"
    },
    {
      "id": "yahoo",
      "name": "Yahoo Finance",
      "description": "Free financial data from Yahoo"
    }
  ],
  "technical": [
    {
      "id": "massive",
      "name": "Massive",
      "description": "Technical analysis data"
    }
  ]
}
```

---

### Get Rate Limits

```
GET /api/rate-limits
```

**Response**

```json
{
  "fmp": {
    "calls_today": 150,
    "limit": 250,
    "reset_in_seconds": 43200
  },
  "yahoo": {
    "calls_today": 50,
    "limit": null,
    "reset_in_seconds": null
  }
}
```

---

### Reset Rate Limits

Clears rate limit counters (for testing/development).

```
POST /api/rate-limits/reset
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
