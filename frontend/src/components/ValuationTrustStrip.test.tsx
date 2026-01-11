import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ValuationTrustStrip } from './ValuationTrustStrip';
import type { ValuationResult, DataProvenance } from '../types';

const createMockResult = (overrides: Partial<ValuationResult> = {}): ValuationResult => ({
  symbol: 'AAPL',
  enterprise_value: 3000000000000,
  equity_value: 2900000000000,
  intrinsic_value_per_share: 200,
  discount_rate: 0.10,
  terminal_value: 2000000000000,
  projections: [],
  market_cap: 2500000000000,
  net_debt: 100000000000,
  using_custom_discount_rate: false,
  wacc: 0.10,
  sensitivity: { 
    discount_rates: [0.08, 0.10, 0.12], 
    terminal_growth_rates: [0.02, 0.03, 0.04], 
    matrix: [[100, 90, 80], [110, 100, 90], [120, 110, 100]],
    base_discount_rate: 0.10,
    base_terminal_growth: 0.03,
  },
  inputs: {
    revenue_growth: 0.10,
    operating_margin: 0.25,
    terminal_growth_rate: 0.03,
    projection_years: 10,
    discount_rate_override: null,
    shares_outstanding: 15000000000,
    shares_type: 'diluted',
    annual_dilution_rate: 0.02,
    terminal_shares: 18000000000,
  },
  terminal_value_check: {
    terminal_ebitda: 200000000000,
    implied_exit_multiple: 10,
    terminal_value_pct: 70,
    gordon_growth_tv: 2000000000000,
  },
  ...overrides,
});

describe('ValuationTrustStrip', () => {
  it('shows period indicator', () => {
    render(
      <ValuationTrustStrip 
        result={createMockResult()} 
        period="ttm"
      />
    );
    expect(screen.getByText('TTM')).toBeInTheDocument();
  });

  it('shows Annual period when selected', () => {
    render(
      <ValuationTrustStrip 
        result={createMockResult()} 
        period="annual"
      />
    );
    expect(screen.getByText('Annual')).toBeInTheDocument();
  });

  it('shows WACC discount rate when not custom', () => {
    render(
      <ValuationTrustStrip 
        result={createMockResult({ using_custom_discount_rate: false, discount_rate: 0.10 })} 
        period="ttm"
      />
    );
    expect(screen.getByText('10.0% (WACC)')).toBeInTheDocument();
  });

  it('shows custom discount rate when overridden', () => {
    render(
      <ValuationTrustStrip 
        result={createMockResult({ using_custom_discount_rate: true, discount_rate: 0.12 })} 
        period="ttm"
      />
    );
    expect(screen.getByText('12.0% (Custom)')).toBeInTheDocument();
  });

  it('shows diluted shares type', () => {
    const result = createMockResult();
    result.inputs.shares_type = 'diluted';
    render(<ValuationTrustStrip result={result} period="ttm" />);
    expect(screen.getByText(/Diluted/)).toBeInTheDocument();
  });

  it('shows basic shares type with warning styling', () => {
    const result = createMockResult();
    result.inputs.shares_type = 'basic';
    result.inputs.annual_dilution_rate = 0;
    render(<ValuationTrustStrip result={result} period="ttm" />);
    expect(screen.getByText('Basic')).toBeInTheDocument();
  });

  it('shows dilution rate when applied', () => {
    const result = createMockResult();
    result.inputs.shares_type = 'diluted';
    result.inputs.annual_dilution_rate = 0.03;
    render(<ValuationTrustStrip result={result} period="ttm" />);
    expect(screen.getByText('Diluted +3.0%/yr')).toBeInTheDocument();
  });

  it('shows terminal value percentage', () => {
    render(
      <ValuationTrustStrip 
        result={createMockResult()} 
        period="ttm"
      />
    );
    expect(screen.getByText('70% of EV')).toBeInTheDocument();
  });

  it('shows warning when terminal dominates', () => {
    const result = createMockResult();
    result.terminal_value_check!.terminal_value_pct = 85;
    render(<ValuationTrustStrip result={result} period="ttm" />);
    expect(screen.getByText('85% of EV')).toBeInTheDocument();
    // Should have warning styling (amber)
    const terminalBadge = screen.getByText('85% of EV').closest('span');
    expect(terminalBadge?.className).toContain('amber');
  });

  it('shows fallback warning when provenance has fallbacks', () => {
    const provenance: DataProvenance = {
      tax_rate: { source: 'fallback', description: 'Using fallback tax rate', confidence: 'low' },
      shares_outstanding: null,
      revenue_source: null,
      cost_of_debt: null,
    };
    render(
      <ValuationTrustStrip 
        result={createMockResult()} 
        period="ttm"
        provenance={provenance}
      />
    );
    expect(screen.getByText('Has Fallbacks')).toBeInTheDocument();
  });

  it('does not show fallback warning when no fallbacks', () => {
    const provenance: DataProvenance = {
      tax_rate: { source: 'ttm', description: 'From TTM data', confidence: 'high' },
      shares_outstanding: null,
      revenue_source: null,
      cost_of_debt: null,
    };
    render(
      <ValuationTrustStrip 
        result={createMockResult()} 
        period="ttm"
        provenance={provenance}
      />
    );
    expect(screen.queryByText('Has Fallbacks')).not.toBeInTheDocument();
  });
});
