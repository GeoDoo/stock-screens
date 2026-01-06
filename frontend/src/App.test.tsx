import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'
import type { ComparableResult } from './types'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock responses
const mockProviders = {
  fundamental: [
    { id: 'yahoo', name: 'Yahoo Finance', available: true, recommended: true },
    { id: 'fmp', name: 'FMP', available: true, recommended: false },
  ],
  technical: [
    { id: 'yahoo', name: 'Yahoo Finance', available: true, recommended: true },
    { id: 'massive', name: 'Massive/Polygon', available: true, recommended: false },
  ],
}

const mockStockDataWithWACC = {
  symbol: 'AAPL',
  company_name: 'Apple Inc.',
  industry: 'Technology Hardware',
  sector: 'Technology',
  data_provider: 'yahoo',
  data: {
    market_cap: 3000000000000,
    beta: 1.2,
    shares_outstanding: 15000000000,
    total_debt: 100000000000,
    cash: 60000000000,
    tax_rate: 0.21,
    cost_of_debt: 0.04,
    wacc: 0.0945,
  },
  hints: {
    revenue_growth: 0.05,
    operating_margin: 0.30,
  },
  validation: {
    is_valid: true,
    has_errors: false,
    has_warnings: false,
    issues: [],
  },
}

const mockStockDataWithoutWACC = {
  symbol: 'VSNTV',
  company_name: 'Versant Media Group',
  industry: 'Media',
  sector: 'Communication Services',
  data_provider: 'yahoo',
  data: {
    market_cap: 10000000,
    beta: null,
    shares_outstanding: 1000000,
    total_debt: 500000,
    cash: 200000,
    tax_rate: 0.21,
    cost_of_debt: null,
    wacc: null,
  },
  hints: {
    revenue_growth: 0.10,
    operating_margin: 0.15,
  },
  validation: {
    is_valid: false,
    has_errors: true,
    has_warnings: false,
    issues: [
      { field: 'beta', message: 'Beta is missing. WACC cannot be calculated.', severity: 'error', impacts: 'wacc' },
      { field: 'cost_of_debt', message: 'Cost of debt is missing.', severity: 'error', impacts: 'wacc' },
    ],
  },
}

const mockValuationResult = {
  intrinsic_value: 185.50,
  current_price: 178.00,
  upside: 0.042,
  wacc: 0.0945,
  terminal_value: 5000000000000,
  enterprise_value: 3200000000000,
  equity_value: 3160000000000,
  using_custom_discount_rate: false,
  discount_rate: 0.0945,
  sensitivity: {
    discount_rates: [0.08, 0.09, 0.10],
    terminal_rates: [0.02, 0.03, 0.04],
    matrix: [[200, 190, 180], [185, 175, 165], [170, 160, 150]],
    current_discount: 0.09,
    current_terminal: 0.03,
  },
}

const mockRatios = { 
  valuation: { pe_ratio: 30, earnings_yield: 0.033, ps_ratio: 8, pb_ratio: 45, ev_to_ebitda: 25, ev_to_revenue: 8 }, 
  dividend: { dividend_yield: 0.005, payout_ratio: 0.15 }, 
  profitability: { gross_margin: 0.43, operating_margin: 0.30, net_margin: 0.25, roe: 1.5, roa: 0.30, roic: 0.45 }, 
  liquidity: { current_ratio: 1.0, quick_ratio: 0.9, debt_to_equity: 1.5, interest_coverage: 25 }, 
  efficiency: { asset_turnover: 1.1, inventory_turnover: 40, receivables_turnover: 15, payables_turnover: 12 } 
}
const mockDividends = { symbol: 'AAPL', has_dividends: true, current_annual_dividend: 0.96, current_yield: 0.005, payout_ratio: 0.15, dividend_cagr: 0.08, consecutive_years: 10, annual_dividends: { '2023': 0.96 }, payments: [] }
const mockHistorical = { 
  symbol: 'AAPL',
  current: { pe: 30, ps: 8, pb: 45, ev_ebitda: 25 },
  average_5yr: { pe: 28, ps: 7, pb: 40, ev_ebitda: 23 },
  premium_discount: { pe: 0.07, ps: 0.14, pb: 0.125, ev_ebitda: 0.087 },
  assessment: { pe: 'fair', ps: 'fair', pb: 'fair', ev_ebitda: 'fair' },
}
const mockComparables: ComparableResult = { 
  symbol: 'AAPL',
  company_name: 'Apple Inc.',
  current_price: 178,
  sector: 'Technology',
  industry: 'Consumer Electronics',
  target_metrics: { pe_ratio: 30, ev_to_ebitda: 25, price_to_sales: 8, price_to_book: 45 },
  peer_medians: { pe_ratio: 25, ev_to_ebitda: 20, price_to_sales: 7, price_to_book: 40 },
  peers: [],
  implied_valuations: [],
  summary: { average_implied_price: 182.5, average_upside_percent: 2.5 },
}
const mockScenarios = { bear: { revenue_growth: 0.02, operating_margin: 0.25, intrinsic_value: 150 }, base: { revenue_growth: 0.05, operating_margin: 0.30, intrinsic_value: 185 }, bull: { revenue_growth: 0.10, operating_margin: 0.35, intrinsic_value: 220 }, probability_weighted_value: 180, current_price: 178, upside_range: { low: -10, high: 20 } }
const mockTechnical = { symbol: 'AAPL', period_days: 365, current_price: 178, price_change: 0.05, signals: [], prices: [], indicators: { sma_20: [], sma_50: [], rsi_14: [], macd: { macd_line: [], signal_line: [], histogram: [] } } }

// Batch analyze response combines multiple data sources
const mockBatchAnalyzeResponse = {
  stock: mockStockDataWithWACC,
  ratios: mockRatios,
  dividends: mockDividends,
  historical_valuation: mockHistorical,
  rate_limit: { used: 1, limit: 250, remaining: 249, percentage: 0.4 },
}

const mockBatchAnalyzeWithoutWACC = {
  stock: mockStockDataWithoutWACC,
  ratios: mockRatios,
  dividends: mockDividends,
  historical_valuation: mockHistorical,
  rate_limit: { used: 1, limit: 250, remaining: 249, percentage: 0.4 },
}

const mockRateLimits = {
  fmp: { used: 10, limit: 250, remaining: 240, percentage: 4.0 },
  yahoo: { used: 5, limit: 2000, remaining: 1995, percentage: 0.25 },
  massive: { used: 1, limit: 5, remaining: 4, percentage: 20.0 },
}

describe('App - Unified Analyze Flow', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    // Default: return providers and rate limits
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProviders),
        })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockRateLimits),
        })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows single "Analyze" button instead of multiple buttons', async () => {
    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })
    
    // Should NOT have separate Run buttons
    expect(screen.queryByRole('button', { name: /Run Valuation/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Run Scenarios/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Run Comparables/i })).not.toBeInTheDocument()
  })

  it('auto-runs all analyses when WACC is available', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockRateLimits) })
      }
      // Batch analyze endpoint - DRY: one call for stock + ratios + dividends + historical
      if (url.includes('/api/stock/AAPL/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBatchAnalyzeResponse) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockComparables) })
      }
      if (url.includes('/valuation')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockValuationResult) })
      }
      if (url.includes('/scenarios')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockScenarios) })
      }
      if (url.includes('/technical')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTechnical) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    // Enter ticker
    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    // Click Analyze
    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i })
    fireEvent.click(analyzeBtn)
    
    // Should auto-run valuation (no modal)
    await waitFor(() => {
      // Check that valuation endpoint was called
      const valuationCalls = mockFetch.mock.calls.filter(
        (call: string[]) => call[0].includes('/valuation')
      )
      expect(valuationCalls.length).toBeGreaterThan(0)
    }, { timeout: 3000 })
  })

  it('shows discount rate modal when WACC is missing', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockRateLimits) })
      }
      // Batch analyze returns data without WACC
      if (url.includes('/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBatchAnalyzeWithoutWACC) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockComparables) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    // Enter ticker
    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'VSNTV' } })
    
    // Click Analyze
    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i })
    fireEvent.click(analyzeBtn)
    
    // Should show discount rate modal
    await waitFor(() => {
      expect(screen.getByText(/Discount Rate Required/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('runs valuation with custom rate after modal submit', async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockRateLimits) })
      }
      // Batch analyze returns data without WACC
      if (url.includes('/api/stock/VSNTV/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBatchAnalyzeWithoutWACC) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockComparables) })
      }
      if (url.includes('/valuation') && options?.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...mockValuationResult, using_custom_discount_rate: true }) })
      }
      if (url.includes('/scenarios')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockScenarios) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    // Enter ticker and click Analyze
    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'VSNTV' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze/i }))
    
    // Wait for modal
    await waitFor(() => {
      expect(screen.getByText(/Discount Rate Required/i)).toBeInTheDocument()
    })
    
    // Enter discount rate and submit
    const rateInput = screen.getByLabelText(/Your Discount Rate/i)
    fireEvent.change(rateInput, { target: { value: '12' } })
    fireEvent.click(screen.getByRole('button', { name: /Continue/i }))
    
    // Verify valuation was called with custom rate
    await waitFor(() => {
      const valuationCalls = mockFetch.mock.calls.filter(
        (call: string[]) => call[0].includes('/valuation')
      )
      expect(valuationCalls.length).toBeGreaterThan(0)
      
      // Check the request body contains discount_rate_override
      const valuationCall = valuationCalls[0]
      const body = JSON.parse(valuationCall[1].body)
      expect(body.discount_rate_override).toBe(0.12) // 12% as decimal
    }, { timeout: 3000 })
  })

  it('skips DCF when Skip is clicked in modal', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockRateLimits) })
      }
      // Batch analyze returns data without WACC
      if (url.includes('/api/stock/VSNTV/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBatchAnalyzeWithoutWACC) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockComparables) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    // Enter ticker and click Analyze
    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'VSNTV' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze/i }))
    
    // Wait for modal
    await waitFor(() => {
      expect(screen.getByText(/Discount Rate Required/i)).toBeInTheDocument()
    })
    
    // Click Skip
    fireEvent.click(screen.getByRole('button', { name: /Skip DCF/i }))
    
    // Modal should close
    await waitFor(() => {
      expect(screen.queryByText(/Discount Rate Required/i)).not.toBeInTheDocument()
    })
    
    // Valuation should NOT have been called
    const valuationCalls = mockFetch.mock.calls.filter(
      (call: string[]) => call[0].includes('/valuation')
    )
    expect(valuationCalls.length).toBe(0)
  })

  it('auto-runs comparables analysis', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockRateLimits) })
      }
      // Batch analyze - DRY: one call for stock + ratios + dividends + historical
      if (url.includes('/api/stock/AAPL/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBatchAnalyzeResponse) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockComparables) })
      }
      if (url.includes('/valuation')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockValuationResult) })
      }
      if (url.includes('/scenarios')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockScenarios) })
      }
      if (url.includes('/technical')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTechnical) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'AAPL' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze/i }))
    
    // Comparables should be auto-fetched
    await waitFor(() => {
      const comparablesCalls = mockFetch.mock.calls.filter(
        (call: string[]) => call[0].includes('/comparables')
      )
      expect(comparablesCalls.length).toBeGreaterThan(0)
    }, { timeout: 3000 })
  })
})

describe('App - Provider Changes', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    // Default: return providers and rate limits
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProviders),
        })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockRateLimits),
        })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows "no data" message when stockData is null', async () => {
    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })
    
    // Should show no data message (tabs only show after data is loaded)
    await waitFor(() => {
      expect(screen.getByText(/No stock data available/i)).toBeInTheDocument()
    })
  })
})

// Provider switching behavior tests are in:
// - src/hooks/useProviderState.test.ts (logic documentation)
// - The "shows 'no data' message" test above (integration)

describe('App - Rate Limit Handling', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows error message when rate limit exceeded', async () => {
    // Mock rate limits showing provider at limit
    const mockRateLimitsAtLimit = {
      fmp: { provider: 'fmp', used: 250, limit: 250, remaining: 0, percentage: 100, reset_schedule: 'daily', api_limited: true },
      yahoo: { provider: 'yahoo', used: 2000, limit: 2000, remaining: 0, percentage: 100, reset_schedule: 'daily', api_limited: true },
      massive: { provider: 'massive', used: 5, limit: 5, remaining: 0, percentage: 100, reset_schedule: 'minute', api_limited: false },
    }

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      // Return rate limits showing provider at limit
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockRateLimitsAtLimit) })
      }
      // Simulate rate limit error from API
      if (url.includes('/analyze')) {
        return Promise.resolve({ 
          ok: false, 
          status: 429,
          json: () => Promise.resolve({ detail: 'Rate limit exceeded for yahoo. Try again later.' }) 
        })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    // Wait for providers to load and be auto-selected
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })
    
    // Wait for auto-selection to complete
    await waitFor(() => {
      expect(screen.getByPlaceholderText('AAPL')).toBeInTheDocument()
    })

    // Enter ticker and click Analyze
    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'AAPL' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze/i }))
    
    // Should show rate limit error in error area
    const errorElement = await screen.findByText(/Rate limit exceeded for yahoo/i)
    expect(errorElement).toBeInTheDocument()
  })
})

// CRITICAL: Tests with INCOMPLETE data - real APIs return missing fields!
describe('App - Handles Incomplete API Data (Regression)', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // Mock data with MISSING fields - like real APIs return
  const mockIncompleteHistorical = {
    symbol: 'TEST',
    // current is MISSING - this caused the crash!
    average_5yr: { pe: 28 },
    premium_discount: {},
    assessment: {},
  }

  const mockIncompleteRatios = {
    valuation: { pe_ratio: null, earnings_yield: undefined },  // Some fields missing
    // Other sections might be missing entirely
  }

  const mockIncompleteDividends = {
    symbol: 'TEST',
    has_dividends: false,  // No dividend data
    // Rest is missing
  }

  const mockBatchWithIncompleteData = {
    stock: {
      symbol: 'TEST',
      company_name: 'Test Company',
      industry: null,  // Missing
      sector: null,    // Missing
      data_provider: 'yahoo',
      data: {
        market_cap: null,  // Missing
        beta: null,        // Missing
        shares_outstanding: 1000000,
        total_debt: null,
        cash: null,
        tax_rate: null,
        cost_of_debt: null,
        wacc: null,        // Missing - triggers modal
      },
      hints: {
        revenue_growth: null,
        operating_margin: null,
      },
      validation: {
        is_valid: false,
        has_errors: true,
        has_warnings: false,
        issues: [],
      },
    },
    ratios: mockIncompleteRatios,
    dividends: mockIncompleteDividends,
    historical_valuation: mockIncompleteHistorical,
    rate_limit: { provider: 'yahoo', used: 1, limit: 2000, remaining: 1999, percentage: 0.05, reset_schedule: 'daily', api_limited: false, reset_in_seconds: null },
  }

  it('renders without crashing when historical_valuation.current is missing', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
      }
      if (url.includes('/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBatchWithIncompleteData) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...mockComparables, peers: [], implied_valuations: [] }) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    // This should NOT crash
    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'TEST' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze/i }))
    
    // Should show modal (WACC is null) or company name - but NOT crash
    await waitFor(() => {
      // Either modal appears (WACC missing) or stock data loads
      const modalOrCompany = screen.queryByText(/Discount Rate Required/i) || screen.queryByText(/Test Company/i)
      expect(modalOrCompany).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('handles historical_valuation with missing premium_discount and assessment', async () => {
    // REGRESSION: Bug at App.tsx:1032 - guard checked current/average_5yr but not premium_discount/assessment
    const mockHistoricalMissingPremiumAssessment = {
      ...mockBatchWithIncompleteData,
      historical_valuation: {
        symbol: 'TEST',
        current: { pe: 25, ps: 5, pb: 3, ev_ebitda: 12 },      // Present
        average_5yr: { pe: 28, ps: 6, pb: 4, ev_ebitda: 14 },  // Present
        // premium_discount: MISSING - this crashed!
        // assessment: MISSING - this crashed!
      },
    }

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
      }
      if (url.includes('/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockHistoricalMissingPremiumAssessment) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...mockComparables, peers: [], implied_valuations: [] }) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'TEST' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze/i }))
    
    // Should NOT crash - would have thrown "Cannot read properties of undefined (reading 'pe')"
    await waitFor(() => {
      const modalOrCompany = screen.queryByText(/Discount Rate Required/i) || screen.queryByText(/Test Company/i)
      expect(modalOrCompany).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('handles completely empty historical_valuation gracefully', async () => {
    const mockWithNullHistorical = {
      ...mockBatchWithIncompleteData,
      historical_valuation: null,  // Completely missing
    }

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProviders) })
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
      }
      if (url.includes('/analyze')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockWithNullHistorical) })
      }
      if (url.includes('/comparables')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...mockComparables, peers: [], implied_valuations: [] }) })
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
    })

    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText('AAPL')
    fireEvent.change(input, { target: { value: 'TEST' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze/i }))
    
    // Should NOT crash - modal or data should appear
    await waitFor(() => {
      const modalOrCompany = screen.queryByText(/Discount Rate Required/i) || screen.queryByText(/Test Company/i)
      expect(modalOrCompany).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})

