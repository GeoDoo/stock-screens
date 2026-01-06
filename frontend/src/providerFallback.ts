/**
 * Provider fallback utilities.
 * 
 * Handles automatic fallback to alternative providers when the primary fails.
 * DRY: Single source of truth for fallback logic.
 * KISS: Simple, focused functions.
 */

import type { Provider } from './types';

/**
 * Error messages that should trigger auto-fallback to another provider.
 * These indicate the data is unavailable from this provider specifically,
 * not a transient error.
 */
const FALLBACK_TRIGGERS = [
  'premium',
  'subscription',
  'not found',
  'ticker not found',
  'no data available',
] as const;

/**
 * Determine if an error should trigger fallback to another provider.
 * 
 * Rate limit errors (429) should NOT trigger fallback - they're transient
 * and the provider might work for other tickers.
 */
export function shouldFallback(errorMsg: string): boolean {
  const lowerMsg = errorMsg.toLowerCase();
  return FALLBACK_TRIGGERS.some(trigger => lowerMsg.includes(trigger));
}

/**
 * Get an alternative provider when the current one fails.
 * Returns null if no alternative is available.
 * Works for both Fundamental and Technical providers.
 */
export function getAlternativeProvider(
  currentProvider: string,
  availableProviders: Provider[]
): string | null {
  if (!availableProviders || availableProviders.length === 0) return null;
  const alternatives = availableProviders.filter(
    p => p.id !== currentProvider && p.available
  );
  return alternatives.length > 0 ? alternatives[0].id : null;
}

/**
 * Get display name for a provider ID.
 */
export function getProviderDisplayName(
  providerId: string,
  providers: Provider[]
): string {
  return providers.find(p => p.id === providerId)?.name || providerId;
}

