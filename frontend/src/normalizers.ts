/**
 * Data normalizers for API responses.
 * 
 * Normalize data at the boundary (when it arrives from API) to ensure consistent shape.
 * This prevents "cannot read property of undefined" errors throughout the app.
 * 
 * DRY: Single source of truth for data normalization.
 * KISS: Simple functions that ensure arrays exist and critical fields are present.
 */

import type {
  StockDataResponse,
  ValuationResult,
  ScenarioAnalysisResult,
  ComparableResult,
  TechnicalAnalysisResult,
  HistoricalValuationResult,
} from './types';

export function normalizeStockData(data: StockDataResponse | null): StockDataResponse | null {
  if (!data) return null;
  return {
    ...data,
    validation: {
      ...data.validation,
      errors: data.validation?.errors ?? [],
      warnings: data.validation?.warnings ?? [],
      issues: data.validation?.issues ?? [],
    },
  };
}

export function normalizeValuationResult(data: ValuationResult | null): ValuationResult | null {
  if (!data) return null;
  // If critical values are missing, don't render partial data
  if (data.intrinsic_value_per_share == null) return null;
  return {
    ...data,
    projections: data.projections ?? [],
    sensitivity: data.sensitivity ? {
      ...data.sensitivity,
      terminal_growth_rates: data.sensitivity.terminal_growth_rates ?? [],
      discount_rates: data.sensitivity.discount_rates ?? [],
      matrix: data.sensitivity.matrix ?? [],
    } : null,
  };
}

export function normalizeScenarioResult(data: ScenarioAnalysisResult | null): ScenarioAnalysisResult | null {
  if (!data) return null;
  // If critical value is missing, don't render
  if (data.probability_weighted_value == null) return null;
  return {
    ...data,
    scenarios: data.scenarios ?? [],
  };
}

export function normalizeComparableResult(data: ComparableResult | null): ComparableResult | null {
  if (!data) return null;
  return {
    ...data,
    peers: data.peers ?? [],
    implied_valuations: data.implied_valuations ?? [],
    summary: {
      ...data.summary,
      average_implied_price: data.summary?.average_implied_price ?? null,
      average_upside_percent: data.summary?.average_upside_percent ?? null,
    },
    target_metrics: {
      pe_ratio: data.target_metrics?.pe_ratio ?? null,
      ev_to_ebitda: data.target_metrics?.ev_to_ebitda ?? null,
      price_to_sales: data.target_metrics?.price_to_sales ?? null,
      price_to_book: data.target_metrics?.price_to_book ?? null,
    },
    peer_medians: {
      pe_ratio: data.peer_medians?.pe_ratio ?? null,
      ev_to_ebitda: data.peer_medians?.ev_to_ebitda ?? null,
      price_to_sales: data.peer_medians?.price_to_sales ?? null,
      price_to_book: data.peer_medians?.price_to_book ?? null,
    },
  };
}

export function normalizeTechnicalResult(data: TechnicalAnalysisResult | null): TechnicalAnalysisResult | null {
  if (!data) return null;
  return {
    ...data,
    prices: data.prices ?? [],
    indicators: data.indicators ? {
      ...data.indicators,
      sma_20: data.indicators.sma_20 ?? [],
      sma_50: data.indicators.sma_50 ?? [],
      rsi_14: data.indicators.rsi_14 ?? [],
      macd: data.indicators.macd ?? [],
    } : {
      sma_20: [],
      sma_50: [],
      rsi_14: [],
      macd: [],
    },
  };
}

export function normalizeHistoricalValuation(data: HistoricalValuationResult | null): HistoricalValuationResult | null {
  if (!data) return null;
  // Ensure all nested objects exist
  if (!data.current || !data.average_5yr || !data.premium_discount || !data.assessment) {
    return null; // Incomplete data - don't render partial
  }
  return data;
}

/**
 * Helper for displaying nullable metrics.
 * Replaces scattered `value?.toFixed(1) || '—'` patterns.
 */
export function formatMetric(value: number | null | undefined, decimals: number = 1, suffix: string = ''): string {
  if (value == null) return '—';
  return `${value.toFixed(decimals)}${suffix}`;
}

