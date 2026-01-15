/**
 * Utility functions for formatting values in the UI.
 * All functions handle null AND undefined (common when API data is missing).
 */

export function formatCurrency(value: number | null | undefined, currency: string = 'USD'): string {
  if (value == null) return '—';  // Catches both null and undefined
  const abs = Math.abs(value);
  const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : currency === 'JPY' ? '¥' : `${currency} `;
  
  if (abs >= 1e12) return `${symbol}${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${symbol}${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${symbol}${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${symbol}${(value / 1e3).toFixed(2)}K`;
  return `${symbol}${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—';  // Catches both null and undefined
  return `${(value * 100).toFixed(2)}%`;
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '—';  // Catches both null and undefined
  return value.toFixed(decimals);
}

export function formatShareCount(value: number | null | undefined): string {
  if (value == null) return '—';  // Catches both null and undefined
  const abs = Math.abs(value);
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toLocaleString('en-US');
}

