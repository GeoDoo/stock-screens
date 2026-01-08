# DCF Valuation Model

> **Auto-generated** from source code docstrings.
> 
> Last updated: 2026-01-08 18:59
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Overview

This application implements a **Discounted Cash Flow (DCF)** model for intrinsic value estimation.

## DCF Calculator

Discounted Cash Flow calculator with optional mid-year discounting.

Mid-year convention assumes cash flows are received at the middle of each year
rather than at the end. This is more realistic for most businesses and produces
slightly higher valuations (since cash is received sooner on average).

## WACC Calculator

Weighted Average Cost of Capital calculator.

WACC = (E/V) * Re + (D/V) * Rd * (1 - T)

Where:
- E = Market cap (equity value)
- D = Total debt
- V = E + D (total firm value)
- Re = Cost of equity
- Rd = Cost of debt
- T = Tax rate

## FCF Projector

Projects Free Cash Flow from first principles.

FCF = NOPAT + D&A - CapEx - ΔWorking Capital

Where:
- NOPAT = EBIT × (1 - Tax Rate)
- D&A = Depreciation & Amortization
- CapEx = Capital Expenditures
- ΔWC = Change in Working Capital

Working Capital Modes:
- "level" (default): WC_t = Revenue_t × WC_ratio, ΔWC = WC_t - WC_{t-1}
  This maintains WC as a % of revenue (traditional approach)

- "incremental": ΔWC = ΔRevenue × WC_intensity
  This ties WC investment directly to revenue growth (institutional approach)
  Better for high-growth companies and more realistic for stable businesses

## Multi-Stage Growth

A single growth phase in a multi-stage model.

If end_growth_rate is provided, the stage will fade linearly
from growth_rate to end_growth_rate over the years.

## Monte Carlo Simulation

Configuration for a single Monte Carlo input variable.

Can sample from either:
- Normal distribution (if std_dev is provided)
- Uniform distribution (if min_value and max_value are provided)

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
