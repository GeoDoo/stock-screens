/**
 * Centralized API layer for all backend calls.
 * 
 * All network requests go through here to ensure:
 * - Consistent error handling
 * - Response normalization at the boundary
 * - Type safety
 */
import { API_BASE } from '../config';
import type {
  ProvidersResponse,
  RateLimitStats,
  StockDataResponse,
  ComparableResult,
  ValuationResult,
  ScenarioAnalysisResult,
  TechnicalAnalysisResult,
  CreateMemoRequest,
  ValuationRequest,
  GrowthStage,
  SensitivityMatrixResponse,
  InvestmentMemo,
  PostMortemAction,
} from '../types';
import {
  normalizeStockData,
  normalizeValuationResult,
  normalizeScenarioResult,
  normalizeComparableResult,
  normalizeTechnicalResult,
} from '../normalizers';

// ============================================================================
// Error handling
// ============================================================================

export interface ApiError {
  message: string;
  statusCode: number;
  detail?: string;
}

export function createApiError(
  message: string,
  statusCode: number,
  detail?: string
): ApiError {
  return { message, statusCode, detail };
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      // Response body wasn't JSON
    }
    const error = createApiError(
      detail || `Request failed with status ${response.status}`,
      response.status,
      detail
    );
    throw error;
  }
  return response.json();
}

// ============================================================================
// Provider endpoints
// ============================================================================

export async function fetchProviders(): Promise<ProvidersResponse> {
  const res = await fetch(`${API_BASE}/api/providers`);
  return handleResponse<ProvidersResponse>(res);
}

export async function fetchRateLimits(): Promise<Record<string, RateLimitStats>> {
  const res = await fetch(`${API_BASE}/api/rate-limits`);
  return handleResponse<Record<string, RateLimitStats>>(res);
}

// ============================================================================
// Stock data endpoints
// ============================================================================

export interface BatchAnalyzeResponse {
  stock: StockDataResponse;
  ratios: {
    annual: unknown;
    ttm: unknown | null;
  };
  dividends: unknown;
  historical_valuation: unknown;
  rate_limit: RateLimitStats;
}

export async function fetchStockAnalysis(
  symbol: string,
  provider: string
): Promise<BatchAnalyzeResponse> {
  const res = await fetch(
    `${API_BASE}/api/stock/${symbol}/analyze?provider=${provider}`
  );
  const data = await handleResponse<BatchAnalyzeResponse>(res);
  
  // Normalize at the boundary
  const normalizedStock = normalizeStockData(data.stock);
  if (!normalizedStock) {
    throw createApiError('Invalid stock data received', 500);
  }
  
  return {
    ...data,
    stock: normalizedStock,
  };
}

export async function fetchComparables(
  symbol: string,
  provider: string
): Promise<ComparableResult> {
  const res = await fetch(
    `${API_BASE}/api/stock/${symbol}/comparables?provider=${provider}`
  );
  const data = await handleResponse<ComparableResult>(res);
  const normalized = normalizeComparableResult(data);
  if (!normalized) {
    throw createApiError('Invalid comparable data received', 500);
  }
  return normalized;
}

export async function fetchTechnicalAnalysis(
  symbol: string,
  provider: string,
  days: number = 365
): Promise<TechnicalAnalysisResult> {
  const res = await fetch(
    `${API_BASE}/api/stock/${symbol}/technical?provider=${provider}&days=${days}`
  );
  const data = await handleResponse<TechnicalAnalysisResult>(res);
  const normalized = normalizeTechnicalResult(data);
  if (!normalized) {
    throw createApiError('Invalid technical data received', 500);
  }
  return normalized;
}

// ============================================================================
// Valuation endpoints
// ============================================================================

export interface RunValuationParams {
  symbol: string;
  provider: string;
  revenueGrowth: number;
  operatingMargin: number;
  terminalGrowthRate: number;
  marketRiskPremium: number;
  projectionYears: number;
  discountRateOverride?: number;
  daRatio?: number;
  capexRatio?: number;
  wcRatio?: number;
  useMidYearDiscounting?: boolean;
  wcMode?: 'level' | 'incremental';
  growthStages?: GrowthStage[];
  annualDilutionRate?: number;  // SBC dilution - e.g. 0.02 for 2% annual share issuance
  sectorEvEbitdaMultiple?: number;  // Exit Multiple cross-check - sector/peer median
}

export async function runValuation(
  params: RunValuationParams
): Promise<ValuationResult> {
  const body: ValuationRequest = {
    revenue_growth: params.revenueGrowth,
    operating_margin: params.operatingMargin,
    terminal_growth_rate: params.terminalGrowthRate,
    market_risk_premium: params.marketRiskPremium,
    projection_years: params.projectionYears,
    discount_rate_override: params.discountRateOverride,
    da_ratio: params.daRatio,
    capex_ratio: params.capexRatio,
    wc_ratio: params.wcRatio,
    use_mid_year_discounting: params.useMidYearDiscounting,
    wc_mode: params.wcMode,
    growth_stages: params.growthStages,
    annual_dilution_rate: params.annualDilutionRate,
    sector_ev_ebitda_multiple: params.sectorEvEbitdaMultiple,
  };

  const res = await fetch(
    `${API_BASE}/api/stock/${params.symbol}/valuation?provider=${params.provider}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }
  );
  const data = await handleResponse<ValuationResult>(res);
  const normalized = normalizeValuationResult(data);
  if (!normalized) {
    throw createApiError('Invalid valuation data received', 500);
  }
  return normalized;
}

export interface RunScenariosParams {
  symbol: string;
  provider: string;
  projectionYears: number;
  marketRiskPremium: number;
  discountRateOverride?: number;
  revenueGrowthHint?: number;
  operatingMarginHint?: number;
  daRatio?: number;
  capexRatio?: number;
  wcRatio?: number;
}

export async function runScenarios(
  params: RunScenariosParams
): Promise<ScenarioAnalysisResult> {
  const body = {
    projection_years: params.projectionYears,
    market_risk_premium: params.marketRiskPremium,
    discount_rate_override: params.discountRateOverride,
    revenue_growth_hint: params.revenueGrowthHint,
    operating_margin_hint: params.operatingMarginHint,
    da_ratio: params.daRatio,
    capex_ratio: params.capexRatio,
    wc_ratio: params.wcRatio,
  };

  const res = await fetch(
    `${API_BASE}/api/stock/${params.symbol}/scenarios?provider=${params.provider}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }
  );
  const data = await handleResponse<ScenarioAnalysisResult>(res);
  const normalized = normalizeScenarioResult(data);
  if (!normalized) {
    throw createApiError('Invalid scenario data received', 500);
  }
  return normalized;
}

// ============================================================================
// Sensitivity Matrix endpoint
// ============================================================================

export interface FetchSensitivityMatrixParams {
  symbol: string;
  provider: string;
  matrixType: 'margin_growth' | 'wacc_terminal';
  baseGrowth?: number;
  baseMargin?: number;
  baseDiscountRate?: number;
  terminalGrowth?: number;
  projectionYears?: number;
  daRatio?: number;
  capexRatio?: number;
  wcRatio?: number;
}

export async function fetchSensitivityMatrix(
  params: FetchSensitivityMatrixParams
): Promise<SensitivityMatrixResponse> {
  const body = {
    matrix_type: params.matrixType,
    base_growth: params.baseGrowth,
    base_margin: params.baseMargin,
    base_discount_rate: params.baseDiscountRate,
    terminal_growth: params.terminalGrowth,
    projection_years: params.projectionYears,
    da_ratio: params.daRatio,
    capex_ratio: params.capexRatio,
    wc_ratio: params.wcRatio,
  };

  const res = await fetch(
    `${API_BASE}/api/stock/${params.symbol}/sensitivity-matrix?provider=${params.provider}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }
  );
  return handleResponse<SensitivityMatrixResponse>(res);
}

// ============================================================================
// Memo endpoints
// P2 Fix: Centralize all memo fetch logic here (not scattered in components)
// ============================================================================

export async function createMemo(memo: CreateMemoRequest): Promise<{ id: number }> {
  const res = await fetch(`${API_BASE}/api/memos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(memo),
  });
  return handleResponse<{ id: number }>(res);
}

export async function fetchMemos(): Promise<InvestmentMemo[]> {
  const res = await fetch(`${API_BASE}/api/memos`);
  return handleResponse<InvestmentMemo[]>(res);
}

export async function fetchMemo(memoId: string | number): Promise<InvestmentMemo> {
  const res = await fetch(`${API_BASE}/api/memos/${memoId}`);
  return handleResponse<InvestmentMemo>(res);
}

export interface AddPostMortemParams {
  memoId: number;
  note: string;
  action: PostMortemAction;
  current_price?: number;
}

export async function addPostMortem(params: AddPostMortemParams): Promise<void> {
  const res = await fetch(`${API_BASE}/api/memos/${params.memoId}/post-mortems`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      note: params.note,
      action: params.action,
      current_price: params.current_price,
    }),
  });
  await handleResponse<void>(res);
}

export interface CloseMemoParams {
  memoId: number;
  status: 'closed_win' | 'closed_loss' | 'closed_neutral';
  reason: string;
}

export async function closeMemo(params: CloseMemoParams): Promise<void> {
  const res = await fetch(`${API_BASE}/api/memos/${params.memoId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: params.status, reason: params.reason }),
  });
  await handleResponse<void>(res);
}
