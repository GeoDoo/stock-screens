# Architecture

> **Auto-generated** from source code structure.
> 
> Last updated: 2026-01-16 12:40
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
| `audit_repository.py` | Asynchronous SQLite-based repository for assumption audit en |
| `base_provider.py` | Standardized company profile data. |
| `cache.py` | Simple in-memory cache with TTL and size limits. |
| `capital_efficiency.py` | Calculator for capital efficiency metrics. |
| `comparable_analyzer.py` | Key valuation metrics for a company. |
| `data_adapter.py` | — |
| `data_extractor.py` | Tracks the source/derivation of a financial metric. |
| `data_validator.py` | Severity levels for validation issues. |
| `database.py` | — |
| `dcf_calculator.py` | Discounted Cash Flow calculator with optional mid-year disco |
| `dividend_analyzer.py` | A single dividend payment. |
| `fcf_projector.py` | Projects Free Cash Flow from first principles. |
| `filing_analyzer.py` | Error during filing analysis. |
| `filing_parser.py` | Parses SEC HTML filings to extract specific sections (Items) |
| `filings_repository.py` | A cached SEC filing PDF. |
| `financial_audit.py` | Performs quantitative forensic analysis on financial stateme |
| `fmp_client.py` | Custom exception for FMP API errors. |
| `fmp_provider.py` | Financial Modeling Prep data provider. |
| `fx_service.py` | Service for fetching and managing exchange rates. |
| `historical_valuation.py` | Valuation metrics for a single year. |
| `logging_config.py` | — |
| `ltm_calculator.py` | Calculates LTM (Trailing Twelve Months) values by merging fa |
| `massive_provider.py` | Massive (Polygon.io) data provider. |
| `memo_repository.py` | Asynchronous SQLite-based repository for investment memos. |
| `monte_carlo.py` | Configuration for a single Monte Carlo input variable. |
| `monte_carlo_full.py` | Input parameter with bounded distribution. |
| `multi_stage_growth.py` | How values transition from start to end over a growth stage. |
| `rate_limiter_sqlite.py` | When the rate limit resets. |
| `ratio_calculator.py` | Valuation metrics. |
| `resilience.py` | Simple Circuit Breaker to prevent cascading failures. |
| `scenario_calculator.py` | A single scenario with its assumptions. |
| `sec_filings.py` | Error fetching or processing SEC filings. |
| `sensitivity_calculator.py` | Calculates sensitivity matrix for DCF valuation. |
| `stock_data_client.py` | Smart stock data client with automatic fallback between prov |
| `technical_indicators.py` | Single indicator data point. |
| `technical_service.py` | Service for running technical analysis on a stock. |
| `telemetry_repository.py` | Asynchronous repository for recording system telemetry. |
| `valuation_service.py` | Orchestrates the full DCF valuation: |
| `wacc_calculator.py` | Weighted Average Cost of Capital calculator. |
| `yahoo_provider.py` | Yahoo Finance data provider using yfinance library. |

### Key Services Detail

#### `data_extractor.py` - ProvenanceInfo

Tracks the source/derivation of a financial metric.

**Key Methods:**
- `to_dict()` - 

#### `dcf_calculator.py` - DCFCalculator

Discounted Cash Flow calculator with optional mid-year discounting.

**Key Methods:**
- `calculate()` - Calculate intrinsic value per share using DCF model.

#### `fcf_projector.py` - FCFProjector

Projects Free Cash Flow from first principles.

**Key Methods:**
- `effective_tax_rate()` - Return tax rate or default if not available.
- `revenue_cagr()` - Calculate Compound Annual Growth Rate of revenue.
- `operating_margin()` - Calculate average operating margin (EBIT / Revenue).
- `da_to_revenue_ratio()` - Calculate average D&A as percentage of revenue.
- `capex_to_revenue_ratio()` - Calculate average CapEx as percentage of revenue.

#### `monte_carlo.py` - MonteCarloInput

Configuration for a single Monte Carlo input variable.

**Key Methods:**
- `sample()` - Draw a random sample for this input.

#### `valuation_service.py` - ValuationService

Orchestrates the full DCF valuation:

#### `wacc_calculator.py` - WACCCalculator

Weighted Average Cost of Capital calculator.

**Key Methods:**
- `size_premium()` - Get size premium for this company based on market cap.
- `size_category()` - Get size category description (e.g., 'Small Cap (5)').
- `cost_of_equity()` - Calculate cost of equity using CAPM with Size Premium.
- `after_tax_cost_of_debt()` - Calculate after-tax cost of debt.
- `calculate()` - Calculate WACC.

## Frontend Architecture

### Components (`frontend/src/components/`)

| Component | Description |
|-----------|-------------|
| `AssumptionCommitModal.tsx` | AssumptionCommitModal |
| `AssumptionHistoryDrawer.tsx` | AssumptionHistoryDrawer |
| `AssumptionHistoryIndicator.tsx` | AssumptionHistoryIndicator |
| `CEOEfficiencyWarning.tsx` | CEOEfficiencyWarning |
| `CapitalEfficiencyPanel.tsx` | CapitalEfficiencyPanel |
| `DiscountRateModal.tsx` | DiscountRateModal |
| `ExecutionRiskMatrix.tsx` | ExecutionRiskMatrix |
| `FilingsPage.tsx` | FilingsPage |
| `FinancialAuditGrid.tsx` | FinancialAuditGrid |
| `FinancialRatiosTable.tsx` | FinancialRatiosTable |
| `ForensicRedFlags.tsx` | ForensicRedFlags |
| `ForensicTimeline.tsx` | ForensicTimeline |
| `GlossaryPage.tsx` | GlossaryPage |
| `GlossaryRef.tsx` | GlossaryRef |
| `InstitutionalTechnicals.tsx` | InstitutionalTechnicals |
| `Layout.tsx` | Layout |
| `MemoCreateModal.tsx` | MemoCreateModal |
| `MemoDetailPage.tsx` | MemoDetailPage |
| `MemoDetailView.tsx` | MemoDetailView |
| `MemosPage.tsx` | MemosPage |
| `MomentumBridge.tsx` | MomentumBridge |
| `MonteCarloPanel.tsx` | MonteCarloPanel |
| `MultiStageGrowth.tsx` | MultiStageGrowth |
| `ProvenanceBadge.tsx` | ProvenanceBadge |
| `RedFlagHeatmap.tsx` | RedFlagHeatmap |
| `SensitivityMatrixPanel.tsx` | SensitivityMatrixPanel |
| `TruthBridge.tsx` | TruthBridge |
| `ValuationTrustStrip.tsx` | ValuationTrustStrip |
| `ValueDrivers.tsx` | ValueDrivers |
| `VolumeSignals.tsx` | VolumeSignals |

### Hooks (`frontend/src/hooks/`)

| Hook | Purpose |
|------|---------|
| `useAssumptionTracker.ts` | Assumptiontracker |
| `useProviders.ts` | Providers |
| `useStockAnalysis.ts` | Stockanalysis |

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
| Backend | 56 test files | pytest |
| Frontend | 24 test files | vitest |

## Constants (`backend/app/constants.py`)

All magic numbers are centralized:
- `DEFAULT_TREASURY_RATE` - Risk-free rate fallback
- `DEFAULT_TAX_RATE` - Tax rate when data missing
- `DEFAULT_MARKET_RISK_PREMIUM` - Historical market premium
- `DEFAULT_TERMINAL_GROWTH` - Long-term GDP growth
