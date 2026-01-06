import { describe, it, expect } from 'vitest';
import { shouldFallback, getAlternativeProvider, getProviderDisplayName } from './providerFallback';
import type { Provider } from './types';

describe('shouldFallback', () => {
  it('returns true for premium errors', () => {
    expect(shouldFallback('Data requires premium FMP subscription')).toBe(true);
    expect(shouldFallback('Premium data required')).toBe(true);
  });

  it('returns true for subscription errors', () => {
    expect(shouldFallback('This requires a subscription')).toBe(true);
  });

  it('returns true for not found errors', () => {
    expect(shouldFallback('Ticker not found')).toBe(true);
    expect(shouldFallback('Symbol NOT FOUND in database')).toBe(true);
    expect(shouldFallback('No data available for this ticker')).toBe(true);
  });

  it('returns false for rate limit errors (should not fallback)', () => {
    expect(shouldFallback('Rate limit exceeded')).toBe(false);
    expect(shouldFallback('Too many requests')).toBe(false);
    expect(shouldFallback('429 Too Many Requests')).toBe(false);
  });

  it('returns false for server errors (transient)', () => {
    expect(shouldFallback('Internal server error')).toBe(false);
    expect(shouldFallback('Service unavailable')).toBe(false);
  });

  it('is case-insensitive', () => {
    expect(shouldFallback('PREMIUM REQUIRED')).toBe(true);
    expect(shouldFallback('Ticker NOT FOUND')).toBe(true);
  });
});

describe('getAlternativeProvider', () => {
  const mockProviders: Provider[] = [
    { id: 'fmp', name: 'FMP', available: true, recommended: true },
    { id: 'yahoo', name: 'Yahoo Finance', available: true, recommended: false },
    { id: 'disabled', name: 'Disabled Provider', available: false, recommended: false },
  ];

  it('returns first available alternative', () => {
    expect(getAlternativeProvider('fmp', mockProviders)).toBe('yahoo');
    expect(getAlternativeProvider('yahoo', mockProviders)).toBe('fmp');
  });

  it('skips unavailable providers', () => {
    const providers: Provider[] = [
      { id: 'fmp', name: 'FMP', available: true, recommended: true },
      { id: 'yahoo', name: 'Yahoo', available: false, recommended: false },
      { id: 'massive', name: 'Massive', available: true, recommended: false },
    ];
    expect(getAlternativeProvider('fmp', providers)).toBe('massive');
  });

  it('returns null when no alternatives available', () => {
    const singleProvider: Provider[] = [
      { id: 'fmp', name: 'FMP', available: true, recommended: true },
    ];
    expect(getAlternativeProvider('fmp', singleProvider)).toBe(null);
  });

  it('returns null when providers array is empty', () => {
    expect(getAlternativeProvider('fmp', [])).toBe(null);
  });

  it('handles undefined/null providers gracefully', () => {
    expect(getAlternativeProvider('fmp', undefined as unknown as Provider[])).toBe(null);
    expect(getAlternativeProvider('fmp', null as unknown as Provider[])).toBe(null);
  });
});

describe('getProviderDisplayName', () => {
  const mockProviders: Provider[] = [
    { id: 'fmp', name: 'FMP', available: true, recommended: true },
    { id: 'yahoo', name: 'Yahoo Finance', available: true, recommended: false },
  ];

  it('returns display name for known provider', () => {
    expect(getProviderDisplayName('fmp', mockProviders)).toBe('FMP');
    expect(getProviderDisplayName('yahoo', mockProviders)).toBe('Yahoo Finance');
  });

  it('returns provider ID when not found', () => {
    expect(getProviderDisplayName('unknown', mockProviders)).toBe('unknown');
  });

  it('returns provider ID when providers array is empty', () => {
    expect(getProviderDisplayName('fmp', [])).toBe('fmp');
  });
});
