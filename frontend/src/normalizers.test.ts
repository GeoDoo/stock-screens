import { describe, it, expect } from 'vitest';
import { normalizeStockData } from './normalizers';
import type { StockDataResponse } from './types';

describe('normalizeStockData', () => {
  it('maps backend hint property names to frontend expected names (annual)', () => {
    // Backend sends da_to_revenue, capex_to_revenue, wc_to_revenue in hints_annual
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
      hints_annual: {
        revenue_growth: 0.8507,
        operating_margin: -13.498,
        da_to_revenue: 0.2877,      // Backend name
        capex_to_revenue: 0.1827,   // Backend name
        wc_to_revenue: 2.965,       // Backend name
      },
      hints_ttm: null,
      validation: {
        has_errors: false,
        has_warnings: false,
        errors: [],
        warnings: [],
      },
    } as unknown as StockDataResponse;

    const normalized = normalizeStockData(backendData);

    // Frontend expects da_ratio, capex_ratio, wc_ratio
    expect(normalized?.hints_annual.da_ratio).toBe(0.2877);
    expect(normalized?.hints_annual.capex_ratio).toBe(0.1827);
    expect(normalized?.hints_annual.wc_ratio).toBe(2.965);
    expect(normalized?.hints_annual.revenue_growth).toBe(0.8507);
    expect(normalized?.hints_annual.operating_margin).toBe(-13.498);
  });

  it('maps backend hint property names for TTM data', () => {
    const backendData = {
      symbol: 'AAPL',
      company_name: 'Apple Inc.',
      industry: 'Consumer Electronics',
      sector: 'Technology',
      data_provider: 'yahoo',
      data: {},
      hints_annual: {
        revenue_growth: 0.05,
        operating_margin: 0.30,
        da_to_revenue: 0.03,
        capex_to_revenue: 0.03,
        wc_to_revenue: -0.03,
      },
      hints_ttm: {
        revenue_growth: 0.06,
        operating_margin: 0.32,
        da_to_revenue: 0.025,
        capex_to_revenue: 0.028,
        wc_to_revenue: -0.025,
      },
      validation: {
        has_errors: false,
        has_warnings: false,
        errors: [],
        warnings: [],
      },
    } as unknown as StockDataResponse;

    const normalized = normalizeStockData(backendData);

    // TTM hints should be normalized
    expect(normalized?.hints_ttm?.da_ratio).toBe(0.025);
    expect(normalized?.hints_ttm?.capex_ratio).toBe(0.028);
    expect(normalized?.hints_ttm?.wc_ratio).toBe(-0.025);
    expect(normalized?.hints_ttm?.operating_margin).toBe(0.32);
  });

  it('handles missing hint properties gracefully', () => {
    const backendData = {
      symbol: 'TEST',
      company_name: 'Test Corp',
      industry: 'Tech',
      sector: 'Technology',
      data_provider: 'yahoo',
      data: {},
      hints_annual: {
        revenue_growth: 0.1,
        operating_margin: 0.2,
        // Missing da_to_revenue, capex_to_revenue, wc_to_revenue
      },
      hints_ttm: null,
      validation: {
        has_errors: false,
        has_warnings: false,
        errors: [],
        warnings: [],
      },
    } as unknown as StockDataResponse;

    const normalized = normalizeStockData(backendData);

    expect(normalized?.hints_annual.da_ratio).toBeNull();
    expect(normalized?.hints_annual.capex_ratio).toBeNull();
    expect(normalized?.hints_annual.wc_ratio).toBeNull();
    expect(normalized?.hints_ttm).toBeNull();
  });

  it('returns null for null input', () => {
    expect(normalizeStockData(null)).toBeNull();
  });

  it('handles legacy "hints" field for backward compatibility', () => {
    // Some old code might send "hints" instead of "hints_annual"
    const backendData = {
      symbol: 'TEST',
      company_name: 'Test Corp',
      industry: 'Tech',
      sector: 'Technology',
      data_provider: 'yahoo',
      data: {},
      hints: {  // Legacy field name
        revenue_growth: 0.1,
        operating_margin: 0.2,
        da_to_revenue: 0.05,
        capex_to_revenue: 0.04,
        wc_to_revenue: -0.02,
      },
      validation: {
        has_errors: false,
        has_warnings: false,
        errors: [],
        warnings: [],
      },
    } as unknown as StockDataResponse;

    const normalized = normalizeStockData(backendData);

    // Should fall back to "hints" and use it as annual
    expect(normalized?.hints_annual.revenue_growth).toBe(0.1);
    expect(normalized?.hints_annual.da_ratio).toBe(0.05);
  });
});
