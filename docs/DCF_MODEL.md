# DCF Valuation Model

This document explains the Discounted Cash Flow (DCF) methodology used in this platform.

## Overview

DCF valuation estimates a company's intrinsic value by projecting future free cash flows and discounting them to present value.

```
Intrinsic Value = Present Value of FCFs + Present Value of Terminal Value - Net Debt
                  ────────────────────────────────────────────────────────────────────
                                       Shares Outstanding
```

## Free Cash Flow (FCF)

### Formula

```
FCF = NOPAT + D&A - CapEx - ΔWorking Capital
```

Where:
- **NOPAT** = Net Operating Profit After Tax = EBIT × (1 - Tax Rate)
- **D&A** = Depreciation & Amortization (non-cash, added back)
- **CapEx** = Capital Expenditures (cash outflow, subtracted)
- **ΔWC** = Change in Working Capital (increase = cash use, decrease = cash source)

### Implementation

```python
# fcf_projector.py
def project_fcf(
    revenue: float,
    operating_margin: float,
    tax_rate: float,
    da_ratio: float,
    capex_ratio: float,
    wc_ratio: float,
    prior_wc: float,
) -> dict:
    ebit = revenue * operating_margin
    nopat = ebit * (1 - tax_rate)
    da = revenue * da_ratio
    capex = revenue * capex_ratio
    wc = revenue * wc_ratio
    delta_wc = wc - prior_wc
    
    fcf = nopat + da - capex - delta_wc
    
    return {
        "revenue": revenue,
        "ebit": ebit,
        "nopat": nopat,
        "da": da,
        "capex": capex,
        "working_capital": wc,
        "delta_wc": delta_wc,
        "fcf": fcf,
    }
```

## Weighted Average Cost of Capital (WACC)

WACC is the discount rate used to calculate present value.

### Formula

```
WACC = (E/V × Re) + (D/V × Rd × (1 - T))
```

Where:
- **E** = Market value of equity
- **D** = Market value of debt
- **V** = E + D (total value)
- **Re** = Cost of equity
- **Rd** = Cost of debt
- **T** = Tax rate

### Cost of Equity (CAPM)

```
Re = Rf + β × (Rm - Rf)
```

Where:
- **Rf** = Risk-free rate (10-year Treasury yield)
- **β** = Beta (stock's volatility vs market)
- **Rm - Rf** = Market risk premium (typically 5-7%)

### Implementation

```python
# wacc_calculator.py
def calculate_wacc(
    beta: float,
    risk_free_rate: float,
    market_risk_premium: float,
    cost_of_debt: float,
    tax_rate: float,
    market_cap: float,
    total_debt: float,
) -> dict:
    # Cost of equity using CAPM
    cost_of_equity = risk_free_rate + (beta * market_risk_premium)
    
    # After-tax cost of debt
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
    
    # Capital structure weights
    total_value = market_cap + total_debt
    weight_equity = market_cap / total_value
    weight_debt = total_debt / total_value
    
    # WACC
    wacc = (weight_equity * cost_of_equity) + (weight_debt * after_tax_cost_of_debt)
    
    return {
        "wacc": wacc,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "after_tax_cost_of_debt": after_tax_cost_of_debt,
        "weight_equity": weight_equity,
        "weight_debt": weight_debt,
    }
```

## Terminal Value

Terminal value captures the company's value beyond the projection period.

### Gordon Growth Model

```
Terminal Value = FCF_final × (1 + g) / (WACC - g)
```

Where:
- **FCF_final** = Free cash flow in the final projection year
- **g** = Perpetual growth rate (typically 2-3%, should not exceed GDP growth)
- **WACC** = Discount rate

### Present Value of Terminal Value

```
PV of Terminal Value = Terminal Value / (1 + WACC)^n
```

Where **n** = number of projection years

### Implementation

```python
# dcf_calculator.py
def calculate_terminal_value(
    final_fcf: float,
    terminal_growth: float,
    wacc: float,
) -> float:
    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth rate")
    
    return final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
```

## Enterprise Value to Equity Value

### Formula

```
Equity Value = Enterprise Value - Net Debt
```

Where:
- **Enterprise Value** = PV of FCFs + PV of Terminal Value
- **Net Debt** = Total Debt - Cash

### Intrinsic Value Per Share

```
Intrinsic Value = Equity Value / Shares Outstanding
```

## Complete DCF Flow

```
                    User Inputs
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
  Revenue Growth   Operating Margin   Terminal Growth
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │ Project Revenue  │
              │ Years 1 through N│
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Calculate FCF    │
              │ for each year    │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Calculate WACC   │
              │ (discount rate)  │
              └────────┬─────────┘
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
   ┌──────────────┐      ┌──────────────┐
   │ PV of FCFs   │      │ Terminal     │
   │ Σ FCF/(1+r)^t│      │ Value        │
   └──────┬───────┘      └──────┬───────┘
          │                     │
          └──────────┬──────────┘
                     │
                     ▼
          ┌──────────────────┐
          │ Enterprise Value │
          │ = PV FCFs + PV TV│
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │ Equity Value     │
          │ = EV - Net Debt  │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │ Intrinsic Value  │
          │ = Equity / Shares│
          └──────────────────┘
```

## Key Assumptions & Sensitivities

### Revenue Growth

| Impact | High | Low |
|--------|------|-----|
| Higher growth → Higher revenue → Higher FCF → Higher value | ✓ | |
| Growth should reflect realistic market opportunity | | |
| Historical growth is a reference, not a guarantee | | |

### Operating Margin

| Impact | High | Low |
|--------|------|-----|
| Higher margin → More profit per dollar of revenue | ✓ | |
| Should reflect competitive position and scale | | |
| Consider industry benchmarks | | |

### Terminal Growth Rate

| Impact | High | Low |
|--------|------|-----|
| Higher terminal growth → Much higher terminal value | ✓ | |
| **Critical**: Should not exceed long-term GDP growth (2-3%) | | |
| Small changes have large impact (sensitivity) | | |

### Discount Rate (WACC)

| Impact | High | Low |
|--------|------|-----|
| Higher WACC → Lower present value | | ✓ |
| Reflects risk—riskier companies need higher rates | | |
| Driven by beta and capital structure | | |

## Scenario Analysis

Compare valuations under different assumptions:

| Scenario | Revenue Growth | Op. Margin | Result |
|----------|----------------|------------|--------|
| Bear | Low | Low | Downside case |
| Base | Moderate | Moderate | Expected case |
| Bull | High | High | Upside case |

### Default Scenario Generation

```python
def get_default_scenarios(hints: dict) -> list:
    base_growth = hints["revenue_growth"]
    base_margin = hints["operating_margin"]
    
    return [
        {
            "name": "Bear",
            "revenue_growth": base_growth * 0.5,
            "operating_margin": base_margin * 0.85,
        },
        {
            "name": "Base",
            "revenue_growth": base_growth,
            "operating_margin": base_margin,
        },
        {
            "name": "Bull",
            "revenue_growth": base_growth * 1.5,
            "operating_margin": base_margin * 1.15,
        },
    ]
```

## Sensitivity Analysis

Shows intrinsic value for combinations of WACC and terminal growth:

```
             Terminal Growth Rate
              1%    2%    3%    4%
         ┌─────────────────────────┐
    8%   │ 210   225   245   270   │
WACC 9%  │ 185   198   215   235   │
    10%  │ 165   176   190   208   │
    11%  │ 148   158   170   185   │
         └─────────────────────────┘
```

## Limitations

1. **Garbage In, Garbage Out**: Results depend entirely on assumption quality
2. **Terminal Value Dominance**: Often 60-80% of total value—highly sensitive
3. **Single Point Estimate**: DCF gives one number, not a range
4. **No Margin of Safety**: Doesn't account for execution risk
5. **Assumes Cash Flow**: May not suit early-stage or distressed companies

## Best Practices

1. **Use ranges, not point estimates** — Run scenarios
2. **Triangulate** — Compare with multiples (P/E, EV/EBITDA)
3. **Be conservative** — Err on lower growth, higher discount
4. **Update regularly** — Revisit assumptions quarterly
5. **Document reasoning** — Use memos to track why you chose assumptions
