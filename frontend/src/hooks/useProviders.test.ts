import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useProviders } from './useProviders';

// Mock fetch
const mockFetch = vi.fn();
(globalThis as typeof globalThis & { fetch: typeof fetch }).fetch = mockFetch;

// Mock localStorage
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key: string) => localStorageMock.store[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    localStorageMock.store[key] = value;
  }),
  clear: vi.fn(() => {
    localStorageMock.store = {};
  }),
};
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });

describe('useProviders', () => {
  const mockProvidersResponse = {
    fundamental: [
      { id: 'fmp', name: 'FMP', description: 'Financial Modeling Prep', available: true, recommended: true },
      { id: 'yahoo', name: 'Yahoo', description: 'Yahoo Finance', available: true, recommended: false },
    ],
    technical: [
      { id: 'yahoo', name: 'Yahoo', description: 'Yahoo Finance', available: true, recommended: true },
      { id: 'massive', name: 'Massive', description: 'Polygon.io', available: true, recommended: false },
    ],
  };

  const mockRateLimits = {
    fmp: { limit: 250, remaining: 200, percentage: 20, reset_schedule: 'daily', api_limited: false, reset_in_seconds: null },
    yahoo: { limit: 100, remaining: 100, percentage: 0, reset_schedule: 'per_minute', api_limited: false, reset_in_seconds: null },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProvidersResponse),
        });
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockRateLimits),
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('fetches providers on mount', async () => {
    const { result } = renderHook(() => useProviders());

    expect(result.current.providersLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.providersLoading).toBe(false);
    });

    expect(result.current.fundamentalProviders).toHaveLength(2);
    expect(result.current.technicalProviders).toHaveLength(2);
  });

  it('selects recommended provider by default', async () => {
    const { result } = renderHook(() => useProviders());

    await waitFor(() => {
      expect(result.current.providersLoading).toBe(false);
    });

    // FMP is recommended for fundamental
    expect(result.current.selectedFundamentalProvider).toBe('fmp');
    // Yahoo is recommended for technical
    expect(result.current.selectedTechnicalProvider).toBe('yahoo');
  });

  it('fetches rate limits on mount', async () => {
    const { result } = renderHook(() => useProviders());

    await waitFor(() => {
      expect(result.current.rateLimitsLoading).toBe(false);
    });

    expect(result.current.rateLimits).toEqual(mockRateLimits);
  });

  it('correctly identifies provider at limit', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProvidersResponse),
        });
      }
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            fmp: { ...mockRateLimits.fmp, remaining: 0, api_limited: true },
            yahoo: mockRateLimits.yahoo,
          }),
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });

    const { result } = renderHook(() => useProviders());

    await waitFor(() => {
      expect(result.current.rateLimitsLoading).toBe(false);
    });

    expect(result.current.isProviderAtLimit('fmp')).toBe(true);
    expect(result.current.isProviderAtLimit('yahoo')).toBe(false);
  });

  it('restores saved provider from localStorage', async () => {
    localStorageMock.store.selectedFundamentalProvider = 'yahoo';
    localStorageMock.store.selectedTechnicalProvider = 'massive';

    const { result } = renderHook(() => useProviders());

    await waitFor(() => {
      expect(result.current.providersLoading).toBe(false);
    });

    // Should use saved provider (yahoo) instead of recommended (fmp)
    expect(result.current.selectedFundamentalProvider).toBe('yahoo');
    expect(result.current.selectedTechnicalProvider).toBe('massive');
  });

  it('allows changing selected provider', async () => {
    const { result } = renderHook(() => useProviders());

    await waitFor(() => {
      expect(result.current.providersLoading).toBe(false);
    });

    act(() => {
      result.current.setSelectedFundamentalProvider('yahoo');
    });

    expect(result.current.selectedFundamentalProvider).toBe('yahoo');
  });

  it('returns correct provider name', async () => {
    const { result } = renderHook(() => useProviders());

    await waitFor(() => {
      expect(result.current.providersLoading).toBe(false);
    });

    expect(result.current.getProviderName('fmp', 'fundamental')).toBe('FMP');
    expect(result.current.getProviderName('yahoo', 'technical')).toBe('Yahoo');
    expect(result.current.getProviderName('unknown', 'fundamental')).toBe('unknown');
  });

  it('auto-switches to available provider when current hits limit', async () => {
    // Start with both providers available
    const { result } = renderHook(() => useProviders());

    await waitFor(() => {
      expect(result.current.providersLoading).toBe(false);
    });

    // Initially FMP is selected (recommended)
    expect(result.current.selectedFundamentalProvider).toBe('fmp');

    // Now simulate FMP hitting rate limit
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/rate-limits')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            fmp: { limit: 250, remaining: 0, percentage: 100, reset_schedule: 'daily', api_limited: true, reset_in_seconds: 3600 },
            yahoo: mockRateLimits.yahoo,
          }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });

    // Trigger rate limit refresh
    await act(async () => {
      await result.current.refreshRateLimits();
    });

    // Should auto-switch to yahoo
    await waitFor(() => {
      expect(result.current.selectedFundamentalProvider).toBe('yahoo');
    });
  });
});
