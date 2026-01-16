import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStockAnalysis } from './useStockAnalysis';

// Mock fetch
const mockFetch = vi.fn();
(globalThis as typeof globalThis & { fetch: typeof fetch }).fetch = mockFetch;

// Mock normalizers
vi.mock('../normalizers', () => ({
  normalizeStockData: vi.fn((data) => data),
  normalizeComparableResult: vi.fn((data) => data),
  normalizeTechnicalResult: vi.fn((data) => data),
  normalizeHistoricalValuation: vi.fn((data) => data),
}));

// Mock providerFallback - disable fallback by default to simplify tests
vi.mock('../providerFallback', () => ({
  shouldFallback: vi.fn(() => false),
  getAlternativeProvider: vi.fn(() => null),
  getProviderDisplayName: vi.fn((id: string) => id),
}));

describe('useStockAnalysis', () => {
  const mockStockResponse = {
    stock: {
      symbol: 'AAPL',
      data: {
        company_name: 'Apple Inc.',
        sector: 'Technology',
        market_cap: 3000000000000,
        shares_outstanding: 15000000000,
        wacc: 0.10,
      },
      hints_annual: {
        revenue_growth: 0.08,
        operating_margin: 0.30,
      },
      hints_ttm: {
        revenue_growth: 0.05,
        operating_margin: 0.28,
      },
      validation: {
        errors: [],
        warnings: [],
      },
    },
    ratios: { annual: {}, ttm: {} },
    dividends: { history: [], metrics: null },
    historical_valuation: { multiples: [] },
  };

  const mockProviders = [
    { id: 'fmp', name: 'FMP', description: 'FMP', available: true, recommended: true },
    { id: 'yahoo', name: 'Yahoo', description: 'Yahoo', available: true, recommended: false },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with empty state', () => {
    const { result } = renderHook(() => useStockAnalysis());

    expect(result.current.stockData).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.hasAttemptedAnalysis).toBe(false);
  });

  it('fetches and stores stock data', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStockResponse),
    });

    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.analyzeStock('AAPL', 'fmp', mockProviders);
    });

    expect(result.current.stockData).toEqual(mockStockResponse.stock);
    expect(result.current.loading).toBe(false);
    expect(result.current.hasAttemptedAnalysis).toBe(true);
  });

  it('handles fetch errors', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: 'Stock not found' }),
    });

    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.analyzeStock('INVALID', 'fmp', mockProviders);
    });

    expect(result.current.stockData).toBeNull();
    expect(result.current.error).toBe('Stock not found');
  });

  it('clears data on new analysis', async () => {
    // First fetch succeeds
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStockResponse),
    });

    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.analyzeStock('AAPL', 'fmp', mockProviders);
    });

    expect(result.current.stockData).not.toBeNull();

    // Second fetch starts - should clear previous data
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        ...mockStockResponse,
        stock: { ...mockStockResponse.stock, symbol: 'MSFT' },
      }),
    });

    // Start the analysis (don't await yet)
    const analysisPromise = act(async () => {
      await result.current.analyzeStock('MSFT', 'fmp', mockProviders);
    });

    // Complete the analysis
    await analysisPromise;

    expect(result.current.stockData?.symbol).toBe('MSFT');
  });

  it('calls onSuccess callback with stock data and provider', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStockResponse),
    });

    const onSuccess = vi.fn();
    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.analyzeStock('AAPL', 'fmp', mockProviders, 'USD', onSuccess);
    });

    // onSuccess receives both the stock data and the actual provider used
    expect(onSuccess).toHaveBeenCalledWith(mockStockResponse.stock, 'fmp');
  });

  it('awaits async onSuccess callback', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStockResponse),
    });

    let callbackCompleted = false;
    const asyncOnSuccess = vi.fn(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
      callbackCompleted = true;
    });
    
    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.analyzeStock('AAPL', 'fmp', mockProviders, 'USD', asyncOnSuccess);
    });

    // The hook should wait for the async callback to complete
    expect(callbackCompleted).toBe(true);
  });

  it('fetches comparables', async () => {
    const mockComparables = {
      sector: 'Technology',
      peers: [{ symbol: 'MSFT', name: 'Microsoft' }],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockComparables),
    });

    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.fetchComparables('AAPL', 'fmp');
    });

    expect(result.current.comparableResult).toEqual(mockComparables);
    expect(result.current.comparableLoading).toBe(false);
  });

  it('fetches technical analysis', async () => {
    const mockTechnical = {
      provider: 'fmp',
      current_price: 180,
      prices: [],
      indicators: {},
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockTechnical),
    });

    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.fetchTechnical('AAPL', 'fmp', mockProviders);
    });

    expect(result.current.technicalResult).toEqual(mockTechnical);
    expect(result.current.technicalLoading).toBe(false);
  });

  it('clears error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: 'Error' }),
    });

    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.analyzeStock('INVALID', 'fmp', mockProviders);
    });

    expect(result.current.error).toBe('Error');

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });

  it('clears all data', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStockResponse),
    });

    const { result } = renderHook(() => useStockAnalysis());

    await act(async () => {
      await result.current.analyzeStock('AAPL', 'fmp', mockProviders);
    });

    expect(result.current.stockData).not.toBeNull();

    act(() => {
      result.current.clearData();
    });

    expect(result.current.stockData).toBeNull();
    expect(result.current.ratiosResult).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
