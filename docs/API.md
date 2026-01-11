# API Reference

> **Auto-generated** from FastAPI OpenAPI schema.
> 
> Do not edit manually. Run `python scripts/generate_api_docs.py` to regenerate.

Base URL: `http://localhost:8000`

## Other

### Health Check

```
GET /health
```




---

### Get Providers

Get list of available data providers with their capabilities.

Returns providers for:
- Fundamental analysis (financials, DCF, comparables)
- Technical analysis (price charts, indicators)

User picks one provider for each analysis type.

```
GET /api/providers
```




---

### Get Rate Limits

Get current rate limit statistics for all providers.

```
GET /api/rate-limits
```




---

### Reset Rate Limits

Reset all rate limit counters (e.g., for a new day).

```
POST /api/rate-limits/reset
```




---

### Analyze Capital Efficiency

Analyze capital efficiency and value creation.

Key metrics:
- ROIC: Return on Invested Capital (profitability of capital)
- Reinvestment Rate: % of earnings needed to fund growth
- Value Spread: ROIC - WACC (positive = value creation)
- Economic Profit (EVA): Dollar value created/destroyed

Interpretation:
- ROIC > WACC: Growth creates shareholder value
- ROIC < WACC: Growth destroys shareholder value (despite earnings!)
- High ROIC + Low reinvestment = Excellent capital efficiency

```
POST /api/capital-efficiency
```


**Request Body**

```json
{
  "nopat": 0.0,
  "invested_capital": 0.0,
  "revenue_growth": 0.0,
  "wacc": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nopat` | number | Yes |  |
| `invested_capital` | number | Yes |  |
| `revenue_growth` | number | Yes |  |
| `wacc` | number | Yes |  |


---

## audit

### Record Assumptions

Record assumption changes for a stock.

Args:
    symbol: Stock ticker symbol
    request: New assumptions and optional note

On first call for a symbol, creates an initial entry (baseline).
On subsequent calls, only records fields that changed from previous snapshot.

Returns:
    - 201 with saved audit entry when changes recorded
    - 200 with empty changes if nothing changed

```
POST /api/audit/{symbol}
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |

**Request Body**

```json
{
  "assumptions": {},
  "note": "string",
  "price_at_time": 0.0,
  "intrinsic_value_at_time": 0.0,
  "pe_ratio_at_time": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assumptions` | object | Yes |  |
| `note` | string | null | No |  |
| `price_at_time` | number | null | No |  |
| `intrinsic_value_at_time` | number | null | No |  |
| `pe_ratio_at_time` | number | null | No |  |


---

### Get Audit History

Get assumption change history for a stock.

Args:
    symbol: Stock ticker symbol
    limit: Maximum entries to return (default 50)

Returns:
    List of audit entries, most recent first.

```
GET /api/audit/{symbol}/history
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `limit` | integer | No |  (default: `50`) |



---

### Get Audit Snapshot

Get the current assumption snapshot for a stock.

Reconstructs the current state by replaying all changes.

Returns:
    Current assumption values, or 404 if no history exists.

```
GET /api/audit/{symbol}/snapshot
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |



---

### Get Field History

Get change history for a specific assumption field.

Args:
    symbol: Stock ticker symbol
    field: Field name (revenue_growth, operating_margin, etc.)

Returns:
    List of changes for that field, most recent first.

```
GET /api/audit/{symbol}/field/{field}
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `field` | string | Yes |  |



---

## memos

### Create Memo

Create a new investment memo.

Captures thesis, assumptions, scenarios, and market context at creation time.

```
POST /api/memos
```


**Request Body**

```json
{
  "symbol": "string",
  "title": "string",
  "thesis": "string",
  "conviction": "string",
  "time_horizon_months": 0,
  "assumptions": {
    "revenue_growth": 0.0,
    "operating_margin": 0.0,
    "terminal_growth_rate": 0.0,
    "discount_rate": 0.0,
    "projection_years": 0,
    "da_ratio": 0.0,
    "capex_ratio": 0.0,
    "wc_ratio": 0.0
  },
  "scenarios": [
    {
      "name": "string",
      "revenue_growth": 0.0,
      "operating_margin": 0.0,
      "intrinsic_value": 0.0,
      "upside_percent": 0.0
    }
  ],
  "initial_market": {
    "price": 0.0,
    "intrinsic_value": 0.0,
    "pe_ratio": 0.0
  },
  "target_price": 0.0,
  "risks": "string",
  "catalysts": "string",
  "what_would_change_mind": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `title` | string | Yes |  |
| `thesis` | string | Yes |  |
| `conviction` | string | Yes |  |
| `time_horizon_months` | integer | Yes |  |
| `assumptions` | MemoAssumptions | Yes |  |
| `scenarios` | array | Yes |  |
| `initial_market` | MemoMarket | Yes |  |
| `target_price` | number | null | No |  |
| `risks` | string | null | No |  |
| `catalysts` | string | null | No |  |
| `what_would_change_mind` | string | null | No |  |


---

### List Memos

List investment memos with optional filtering.

Args:
    symbol: Filter by stock symbol
    status: Filter by status (active, closed_win, closed_loss, closed_neutral)

```
GET /api/memos
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | null | No |  |
| `status` | string | null | No |  |



---

### Get Memo

Get a single investment memo by ID.

```
GET /api/memos/{memo_id}
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `memo_id` | integer | Yes |  |



---

### Update Memo

Update an existing memo.

```
PUT /api/memos/{memo_id}
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `memo_id` | integer | Yes |  |

**Request Body**

```json
{
  "symbol": "string",
  "title": "string",
  "thesis": "string",
  "conviction": "string",
  "time_horizon_months": 0,
  "assumptions": {
    "revenue_growth": 0.0,
    "operating_margin": 0.0,
    "terminal_growth_rate": 0.0,
    "discount_rate": 0.0,
    "projection_years": 0,
    "da_ratio": 0.0,
    "capex_ratio": 0.0,
    "wc_ratio": 0.0
  },
  "scenarios": [
    {
      "name": "string",
      "revenue_growth": 0.0,
      "operating_margin": 0.0,
      "intrinsic_value": 0.0,
      "upside_percent": 0.0
    }
  ],
  "initial_market": {
    "price": 0.0,
    "intrinsic_value": 0.0,
    "pe_ratio": 0.0
  },
  "target_price": 0.0,
  "risks": "string",
  "catalysts": "string",
  "what_would_change_mind": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `title` | string | Yes |  |
| `thesis` | string | Yes |  |
| `conviction` | string | Yes |  |
| `time_horizon_months` | integer | Yes |  |
| `assumptions` | MemoAssumptions | Yes |  |
| `scenarios` | array | Yes |  |
| `initial_market` | MemoMarket | Yes |  |
| `target_price` | number | null | No |  |
| `risks` | string | null | No |  |
| `catalysts` | string | null | No |  |
| `what_would_change_mind` | string | null | No |  |


---

### Delete Memo

Delete an investment memo.

```
DELETE /api/memos/{memo_id}
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `memo_id` | integer | Yes |  |



---

### Add Post Mortem

Add a post-mortem review to a memo.

Post-mortems track how reality is unfolding vs the original thesis.

```
POST /api/memos/{memo_id}/post-mortems
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `memo_id` | integer | Yes |  |

**Request Body**

```json
{
  "note": "string",
  "action": "string",
  "price_at_time": 0.0,
  "iv_at_time": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `note` | string | Yes |  |
| `action` | string | Yes |  |
| `price_at_time` | number | Yes |  |
| `iv_at_time` | number | Yes |  |


---

### Close Memo

Close a memo with final status and reason.

Status should reflect whether the thesis played out:
- closed_win: Thesis was correct
- closed_loss: Thesis was wrong
- closed_neutral: Closed for other reasons

```
POST /api/memos/{memo_id}/close
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `memo_id` | integer | Yes |  |

**Request Body**

```json
{
  "status": "string",
  "reason": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes |  |
| `reason` | string | Yes |  |


---

### Add Market Snapshot

Add a market snapshot to track performance over time.

Call this periodically to track how price and intrinsic value evolve.

```
POST /api/memos/{memo_id}/snapshots
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `memo_id` | integer | Yes |  |

**Request Body**

```json
{
  "price": 0.0,
  "intrinsic_value": 0.0,
  "pe_ratio": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `price` | number | Yes |  |
| `intrinsic_value` | number | Yes |  |
| `pe_ratio` | number | null | No |  |


---

## stock

### Get Stock

Get stock data and historical hints.

Args:
    symbol: Stock ticker symbol
    provider: Data provider to use (fmp or yahoo) - REQUIRED

Returns:
- data: Read-only values (beta, debt, cash, etc.)
- hints: Historical averages for reference (user decides what to use)

```
GET /api/stock/{symbol}
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |


**Response**

```json
{
  "symbol": "string",
  "company_name": "string",
  "industry": "string",
  "sector": "string",
  "data_provider": "string",
  "data": {
    "beta": 0.0,
    "market_cap": 0.0,
    "total_debt": 0.0,
    "total_equity": 0.0,
    "cash": 0.0,
    "tax_rate": 0.0,
    "cost_of_debt": 0.0,
    "shares_outstanding": 0.0,
    "risk_free_rate": 0.0,
    "wacc": 0.0,
    "revenue": 0.0,
    "working_capital": 0.0
  },
  "hints_annual": {
    "revenue_growth": 0.0,
    "operating_margin": 0.0,
    "da_ratio": 0.0,
    "capex_ratio": 0.0,
    "wc_ratio": 0.0
  },
  "hints_ttm": {
    "revenue_growth": 0.0,
    "operating_margin": 0.0,
    "da_ratio": 0.0,
    "capex_ratio": 0.0,
    "wc_ratio": 0.0
  },
  "validation": {
    "has_errors": true,
    "has_warnings": true,
    "errors": [
      {
        "field": "string",
        "message": "string"
      }
    ],
    "warnings": [
      {
        "field": "string",
        "message": "string"
      }
    ]
  },
  "is_using_ltm": true,
  "provenance": {
    "tax_rate": {
      "source": "string",
      "description": "string",
      "confidence": "string"
    },
    "shares_outstanding": {
      "source": "string",
      "description": "string",
      "confidence": "string"
    },
    "revenue_source": {
      "source": "string",
      "description": "string",
      "confidence": "string"
    },
    "cost_of_debt": {
      "source": "string",
      "description": "string",
      "confidence": "string"
    }
  }
}
```

---

### Run Valuation

Run DCF valuation with user-provided assumptions.

Supports two modes:
1. Single growth rate: Uses revenue_growth for all projection_years
2. Multi-stage growth: Uses growth_stages to define phases with fading economics

Multi-stage economics (institutional modeling):
- margin_schedule: Fade from high-growth margins to mature margins
- capex_schedule: Fade from growth-phase CapEx to maintenance CapEx
- wc_schedule: Model working capital efficiency improvements

```
POST /api/stock/{symbol}/valuation
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |

**Request Body**

```json
{
  "revenue_growth": 0.0,
  "operating_margin": 0.0,
  "terminal_growth_rate": 0.0,
  "market_risk_premium": 0.0,
  "projection_years": 0,
  "discount_rate_override": 0.0,
  "da_ratio": 0.0,
  "capex_ratio": 0.0,
  "wc_ratio": 0.0,
  "use_mid_year_discounting": true,
  "wc_mode": "string",
  "growth_stages": [
    {
      "name": "string",
      "years": 0,
      "growth_rate": 0.0,
      "end_growth_rate": 0.0,
      "operating_margin": 0.0,
      "end_operating_margin": 0.0,
      "capex_ratio": 0.0,
      "end_capex_ratio": 0.0,
      "wc_ratio": 0.0,
      "end_wc_ratio": 0.0
    }
  ],
  "annual_dilution_rate": 0.0,
  "sector_ev_ebitda_multiple": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `revenue_growth` | number | Yes |  |
| `operating_margin` | number | Yes |  |
| `terminal_growth_rate` | number | Yes |  |
| `market_risk_premium` | number | Yes |  |
| `projection_years` | integer | Yes |  |
| `discount_rate_override` | number | null | No |  |
| `da_ratio` | number | null | No |  |
| `capex_ratio` | number | null | No |  |
| `wc_ratio` | number | null | No |  |
| `use_mid_year_discounting` | boolean | No |  |
| `wc_mode` | string | No |  |
| `growth_stages` | array | null | No |  |
| `annual_dilution_rate` | number | No |  |
| `sector_ev_ebitda_multiple` | number | null | No |  |


---

### Run Scenarios

Run scenario analysis (Bear/Base/Bull cases).

If no scenarios provided, generates smart defaults based on historical data.
Returns intrinsic values for each scenario and probability-weighted average.

```
POST /api/stock/{symbol}/scenarios
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |

**Request Body**

```json
{
  "scenarios": [
    {
      "name": "string",
      "revenue_growth": 0.0,
      "operating_margin": 0.0,
      "terminal_growth": 0.0,
      "probability": 0.0,
      "description": "string"
    }
  ],
  "projection_years": 0,
  "market_risk_premium": 0.0,
  "discount_rate_override": 0.0,
  "revenue_growth_hint": 0.0,
  "operating_margin_hint": 0.0,
  "da_ratio": 0.0,
  "capex_ratio": 0.0,
  "wc_ratio": 0.0,
  "annual_dilution_rate": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scenarios` | array | null | No |  |
| `projection_years` | integer | No |  |
| `market_risk_premium` | number | No |  |
| `discount_rate_override` | number | null | No |  |
| `revenue_growth_hint` | number | null | No |  |
| `operating_margin_hint` | number | null | No |  |
| `da_ratio` | number | null | No |  |
| `capex_ratio` | number | null | No |  |
| `wc_ratio` | number | null | No |  |
| `annual_dilution_rate` | number | No |  |


---

### Get Comparables

Run comparable company analysis.

Compares the stock against sector peers using valuation multiples.
Returns implied fair value based on peer median multiples.

```
GET /api/stock/{symbol}/comparables
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |
| `max_peers` | integer | No |  (default: `5`) |



---

### Get Ratios

Get comprehensive financial ratios for a stock.

Returns ratios organized by category:
- Valuation: P/E, Earnings Yield, P/S, P/B, EV/EBITDA, EV/Revenue
- Dividend: Dividend Yield, Payout Ratio
- Profitability: Gross/Operating/Net Margins, ROE, ROA, ROIC
- Liquidity: Current Ratio, Quick Ratio, Debt/Equity, Interest Coverage
- Efficiency: Asset Turnover, Inventory Turnover

```
GET /api/stock/{symbol}/ratios
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |



---

### Get Dividends

Get dividend history and metrics for a stock.

Returns dividend analysis including:
- Current annual dividend and yield
- Dividend growth rate (CAGR)
- Consecutive years of payments
- Annual dividend history

```
GET /api/stock/{symbol}/dividends
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |



---

### Get Historical Valuation

Get historical valuation context for a stock.

Compares current valuation multiples (P/E, P/S, P/B, EV/EBITDA)
to 5-year averages to assess if stock is cheap or expensive
relative to its own history.

Uses true historical prices when available for accurate historical
multiples, falling back to current market cap proxy if historical
prices cannot be fetched.

```
GET /api/stock/{symbol}/historical-valuation
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |



---

### Get Technical Analysis

Run technical analysis on a stock.

Returns:
    Price data, moving averages, RSI, MACD, and trend signals.

```
GET /api/stock/{symbol}/technical
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | No |  (default: `massive`) |
| `days` | integer | No |  (default: `365`) |



---

### Batch Analyze

Batch analyze endpoint - returns all fundamental data in a single call.

This reduces API calls by fetching stock data once and computing all
derived metrics (ratios, dividends, historical valuation) from that data.

Note: All blocking I/O (yfinance calls) is run via run_in_executor()
to avoid blocking the event loop.

```
GET /api/stock/{symbol}/analyze
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |



---

### Run Monte Carlo

Run Monte Carlo simulation on DCF valuation (simplified/quick mode).

Varies growth, margin, and discount rate to produce a probability
distribution of intrinsic values.

```
POST /api/stock/{symbol}/monte-carlo
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | No |  (default: `yahoo`) |

**Request Body**

```json
{
  "base_growth": 0.0,
  "growth_std": 0.0,
  "base_margin": 0.0,
  "margin_std": 0.0,
  "base_discount_rate": 0.0,
  "discount_std": 0.0,
  "terminal_growth": 0.0,
  "projection_years": 0,
  "iterations": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_growth` | number | Yes |  |
| `growth_std` | number | No |  |
| `base_margin` | number | Yes |  |
| `margin_std` | number | No |  |
| `base_discount_rate` | number | Yes |  |
| `discount_std` | number | No |  |
| `terminal_growth` | number | No |  |
| `projection_years` | integer | No |  |
| `iterations` | integer | No |  |


---

### Run Full Monte Carlo Endpoint

Run Full-Model Monte Carlo simulation using complete DCF engine.

This is the DECISION-GRADE Monte Carlo that:
1. Uses FCFProjector for proper FCF calculations (NOPAT + D&A - CapEx - ΔWC)
2. Samples ALL DCF inputs with bounded distributions
3. Implements correlations between inputs (growth↔margin, growth↔reinvestment)
4. Computes comprehensive decision-support outputs

Use this for actual investment decisions.
Use /monte-carlo (simplified) for quick intuition only.

```
POST /api/stock/{symbol}/monte-carlo-full
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | No |  (default: `yahoo`) |

**Request Body**

```json
{
  "base_growth": 0.0,
  "base_margin": 0.0,
  "base_da_ratio": 0.0,
  "base_capex_ratio": 0.0,
  "base_wc_ratio": 0.0,
  "base_tax_rate": 0.0,
  "base_discount_rate": 0.0,
  "base_terminal_growth": 0.0,
  "growth_std": 0.0,
  "margin_std": 0.0,
  "da_ratio_std": 0.0,
  "capex_ratio_std": 0.0,
  "wc_ratio_std": 0.0,
  "discount_std": 0.0,
  "terminal_growth_std": 0.0,
  "projection_years": 0,
  "iterations": 0,
  "growth_margin_correlation": 0.0,
  "growth_capex_correlation": 0.0,
  "wacc_components": {
    "risk_free_rate": 0.0,
    "beta": 0.0,
    "market_risk_premium": 0.0,
    "cost_of_debt": 0.0,
    "market_cap": 0.0,
    "beta_std": 0.0,
    "market_risk_premium_std": 0.0
  },
  "growth_stages": [
    {
      "name": "string",
      "years": 0,
      "growth_rate": 0.0,
      "end_growth_rate": 0.0,
      "operating_margin": 0.0,
      "end_operating_margin": 0.0,
      "capex_ratio": 0.0,
      "end_capex_ratio": 0.0,
      "wc_ratio": 0.0,
      "end_wc_ratio": 0.0
    }
  ],
  "use_mid_year_discounting": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_growth` | number | null | No |  |
| `base_margin` | number | Yes |  |
| `base_da_ratio` | number | Yes |  |
| `base_capex_ratio` | number | Yes |  |
| `base_wc_ratio` | number | Yes |  |
| `base_tax_rate` | number | No |  |
| `base_discount_rate` | number | null | No |  |
| `base_terminal_growth` | number | No |  |
| `growth_std` | number | No |  |
| `margin_std` | number | No |  |
| `da_ratio_std` | number | No |  |
| `capex_ratio_std` | number | No |  |
| `wc_ratio_std` | number | No |  |
| `discount_std` | number | No |  |
| `terminal_growth_std` | number | No |  |
| `projection_years` | integer | No |  |
| `iterations` | integer | No |  |
| `growth_margin_correlation` | number | No |  |
| `growth_capex_correlation` | number | No |  |
| `wacc_components` | WACCComponentsInput | null | No |  |
| `growth_stages` | array | null | No |  |
| `use_mid_year_discounting` | boolean | No |  |


---

### Get Sensitivity Matrix

Generate 2D sensitivity matrix for valuation.

Supports two matrix types:

1. **margin_growth** (default): Varies operating margin and revenue growth.
   Shows how intrinsic value changes with execution (margin) and
   market size (growth) assumptions. Useful for understanding
   execution risk and upside potential.

2. **wacc_terminal**: Varies discount rate (WACC) and terminal growth.
   Classic DCF sensitivity showing value sensitivity to
   risk (WACC) and long-term growth assumptions.

Each cell shows intrinsic value per share for that parameter combination.
Matrix is 5×5 by default, centered on base values.

```
POST /api/stock/{symbol}/sensitivity-matrix
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `symbol` | string | Yes |  |
| `provider` | string | Yes |  |

**Request Body**

```json
{
  "matrix_type": "string",
  "base_growth": 0.0,
  "base_margin": 0.0,
  "base_discount_rate": 0.0,
  "terminal_growth": 0.0,
  "projection_years": 0,
  "growth_steps": [
    0.0
  ],
  "margin_steps": [
    0.0
  ],
  "discount_rate_steps": [
    0.0
  ],
  "terminal_growth_steps": [
    0.0
  ],
  "da_ratio": 0.0,
  "capex_ratio": 0.0,
  "wc_ratio": 0.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `matrix_type` | string | No |  |
| `base_growth` | number | null | No |  |
| `base_margin` | number | null | No |  |
| `base_discount_rate` | number | null | No |  |
| `terminal_growth` | number | No |  |
| `projection_years` | integer | No |  |
| `growth_steps` | array | No |  |
| `margin_steps` | array | No |  |
| `discount_rate_steps` | array | No |  |
| `terminal_growth_steps` | array | No |  |
| `da_ratio` | number | null | No |  |
| `capex_ratio` | number | null | No |  |
| `wc_ratio` | number | null | No |  |

**Response**

```json
{
  "matrix_type": "string",
  "margins": [
    0.0
  ],
  "growth_rates": [
    0.0
  ],
  "discount_rates": [
    0.0
  ],
  "terminal_growth_rates": [
    0.0
  ],
  "matrix": [
    [
      0.0
    ]
  ],
  "base_values": {},
  "base_discount_rate_used": 0.0
}
```

---
