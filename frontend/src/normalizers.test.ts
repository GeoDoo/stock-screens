import { describe, it, expect } from 'vitest';
import { normalizeStockData } from './normalizers';
import type { StockDataResponse } from './types';

describe('normalizeStockData', () => {
  it('maps backend hint property names to frontend expected names', () => {
    // Backend sends da_to_revenue, capex_to_revenue, wc_to_revenue
    const backendData = {
      symbol: 'ATRA',
      company_name: 'Atara Biotherapeutics',
      industry: 'Biotechnology',
      sector: 'Healthcare',
      data_provider: 'yahoo',
      data: {
        beta: -0.401,
        market_cap: 105053120,
        total_debt: 43831000,
        cash: 25030000,
        tax_rate: 0.00014,
        cost_of_debt: 0.1053,
        shares_outstanding: 7210235,
        risk_free_rate: 0.0414,
        wacc: 0.0433,
      },
      hints: {
        revenue_growth: 0.8507,
        operating_margin: -13.498,
        da_to_revenue: 0.2877,      // Backend name
        capex_to_revenue: 0.1827,   // Backend name
        wc_to_revenue: 2.965,       // Backend name
      },
      validation: {
        has_errors: false,
        has_warnings: false,
        errors: [],
        warnings: [],
      },
    } as unknown as StockDataResponse;

    const normalized = normalizeStockData(backendData);

    // Frontend expects da_ratio, capex_ratio, wc_ratio
    expect(normalized?.hints.da_ratio).toBe(0.2877);
    expect(normalized?.hints.capex_ratio).toBe(0.1827);
    expect(normalized?.hints.wc_ratio).toBe(2.965);
    expect(normalized?.hints.revenue_growth).toBe(0.8507);
    expect(normalized?.hints.operating_margin).toBe(-13.498);
  });

  it('handles missing hint properties gracefully', () => {
    const backendData = {
      symbol: 'TEST',
      company_name: 'Test Corp',
      industry: 'Tech',
      sector: 'Technology',
      data_provider: 'yahoo',
      data: {},
      hints: {
        revenue_growth: 0.1,
        operating_margin: 0.2,
        // Missing da_to_revenue, capex_to_revenue, wc_to_revenue
      },
      validation: {
        has_errors: false,
        has_warnings: false,
        errors: [],
        warnings: [],
      },
    } as unknown as StockDataResponse;

    const normalized = normalizeStockData(backendData);

    expect(normalized?.hints.da_ratio).toBeNull();
    expect(normalized?.hints.capex_ratio).toBeNull();
    expect(normalized?.hints.wc_ratio).toBeNull();
  });

  it('returns null for null input', () => {
    expect(normalizeStockData(null)).toBeNull();
  });
});

