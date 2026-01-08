// Provider Types
export interface Provider {
  id: string;
  name: string;
  description: string;
  available: boolean;
  recommended?: boolean;
}

export interface ProvidersResponse {
  fundamental: Provider[];
  technical: Provider[];
}

// Rate Limit Types (accurate time-based tracking)
export interface RateLimitStats {
  provider: string;
  used: number;
  limit: number;
  remaining: number;
  percentage: number;
  reset_schedule: 'daily' | 'minute';  // When limit resets
  api_limited: boolean;  // True if API returned 429 (auto-clears when window resets)
  reset_in_seconds: number | null;  // Seconds until can try again (null if not limited)
}

export interface CompanyData {
  beta: number | null;
  market_cap: number | null;
  total_debt: number | null;
  cash: number | null;
  tax_rate: number | null;
  cost_of_debt: number | null;
  shares_outstanding: number | null;
  risk_free_rate: number;
  wacc: number | null;
}

export interface HistoricalHints {
  revenue_growth: number | null;
  operating_margin: number | null;
  da_ratio: number | null;
  capex_ratio: number | null;
  wc_ratio: number | null;
}

// Same structure for both annual and TTM hints
export type PeriodHints = HistoricalHints;

export interface ValidationIssue {
  field: string;
  message: string;
  impacts: 'wacc' | 'dcf' | 'per_share';
}

export interface ValidationResult {
  has_errors: boolean;
  has_warnings: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface StockDataResponse {
  symbol: string;
  company_name: string | null;
  industry: string | null;
  sector: string | null;
  data_provider: string;
  data: CompanyData;
  hints_annual: HistoricalHints;
  hints_ttm: HistoricalHints | null;  // Null if TTM data not available
  validation: ValidationResult;
}

export interface ValuationRequest {
  revenue_growth: number;
  operating_margin: number;
  terminal_growth_rate: number;
  market_risk_premium: number;
  projection_years: number;
  discount_rate_override?: number | null;
  // FCF ratios - passed from frontend for clean TTM/Annual separation
  da_ratio?: number | null;
  capex_ratio?: number | null;
  wc_ratio?: number | null;
}

export interface SensitivityMatrix {
  discount_rates: number[];
  terminal_growth_rates: number[];
  matrix: (number | null)[][];
  base_discount_rate: number;
  base_terminal_growth: number;
}

export interface ValuationResult {
  symbol: string;
  intrinsic_value_per_share: number;
  enterprise_value: number;
  equity_value: number;
  market_cap: number | null;
  net_debt: number;
  wacc: number;
  discount_rate: number;
  using_custom_discount_rate: boolean;
  terminal_value: number;
  projections: Array<{
    revenue: number;
    ebit: number;
    nopat: number;
    da: number;
    capex: number;
    working_capital: number;
    delta_wc: number;
    fcf: number;
  }>;
  inputs: Record<string, unknown>;
  sensitivity: SensitivityMatrix;
}

// Scenario Analysis Types
export interface ScenarioInput {
  name: string;
  revenue_growth: number;
  operating_margin: number;
  terminal_growth: number;
  probability: number;
  description: string;
}

export interface ScenarioRequest {
  scenarios?: ScenarioInput[];
  projection_years: number;
  market_risk_premium: number;
  discount_rate_override?: number | null;
  // FCF ratios - passed from frontend for clean TTM/Annual separation
  da_ratio?: number | null;
  capex_ratio?: number | null;
  wc_ratio?: number | null;
}

export interface ScenarioResultItem {
  name: string;
  intrinsic_value: number;
  upside_percent: number | null;
  enterprise_value: number;
  equity_value: number;
  probability: number;
  assumptions: {
    revenue_growth: number;
    operating_margin: number;
    terminal_growth: number;
    discount_rate: number;
  };
  description: string;
}

export interface ScenarioAnalysisResult {
  symbol: string;
  current_price: number | null;
  wacc: number;
  projection_years: number;
  scenarios: ScenarioResultItem[];
  probability_weighted_value: number | null;
  upside_range: {
    min_percent: number;
    max_percent: number;
  };
}

// Comparable Analysis Types
export interface PeerCompany {
  symbol: string;
  name: string;
  market_cap: number | null;
  pe_ratio: number | null;
  ev_to_ebitda: number | null;
  price_to_sales: number | null;
  price_to_book: number | null;
}

export interface ImpliedValuation {
  metric: string;
  peer_median: number | null;
  company_value: number | null;
  implied_price: number | null;
  upside_percent: number | null;
}

export interface ComparableResult {
  symbol: string;
  company_name: string;
  current_price: number | null;
  sector: string;
  industry: string;
  target_metrics: {
    pe_ratio: number | null;
    ev_to_ebitda: number | null;
    price_to_sales: number | null;
    price_to_book: number | null;
  };
  peer_medians: {
    pe_ratio: number | null;
    ev_to_ebitda: number | null;
    price_to_sales: number | null;
    price_to_book: number | null;
  };
  peers: PeerCompany[];
  implied_valuations: ImpliedValuation[];
  summary: {
    average_implied_price: number | null;
    average_upside_percent: number | null;
  };
}

// Technical Analysis Types
export interface PriceBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorValue {
  timestamp: string;
  value: number;
}

export interface MACDValue {
  timestamp: string;
  macd: number;
  signal: number;
  histogram: number;
}

export interface TechnicalAnalysisResult {
  symbol: string;
  provider: string;
  period_days: number;
  current_price: number;
  price_change_pct: number;
  prices: PriceBar[];
  indicators: {
    sma_20: IndicatorValue[];
    sma_50: IndicatorValue[];
    ema_12: IndicatorValue[];
    ema_26: IndicatorValue[];
    rsi_14: IndicatorValue[];
    macd: MACDValue[];
  };
  signals: {
    trend: 'bullish' | 'bearish' | 'neutral';
    rsi: 'overbought' | 'oversold' | 'neutral';
    macd: 'bullish' | 'bearish' | 'neutral';
  };
}

// Financial Ratios Types (single period)
export interface FinancialRatiosPeriod {
  symbol: string;
  period: 'annual' | 'ttm';
  valuation: {
    pe_ratio: number | null;
    earnings_yield: number | null;
    ps_ratio: number | null;
    pb_ratio: number | null;
    ev_to_ebitda: number | null;
    ev_to_revenue: number | null;
  };
  dividend?: {
    dividend_yield: number | null;
    payout_ratio: number | null;
  };
  profitability: {
    gross_margin: number | null;
    operating_margin: number | null;
    net_margin: number | null;
    roe: number | null;
    roa: number | null;
    roic: number | null;
  };
  liquidity: {
    current_ratio: number | null;
    quick_ratio: number | null;
    debt_to_equity: number | null;
    interest_coverage: number | null;
  };
  efficiency: {
    asset_turnover: number | null;
    inventory_turnover: number | null;
  };
}

// Financial Ratios Result (contains both annual and TTM)
export interface FinancialRatiosResult {
  annual: FinancialRatiosPeriod;
  ttm: FinancialRatiosPeriod | null;
}

// Dividend History Types
export interface DividendPayment {
  date: string;
  amount: number;
}

export interface DividendHistoryResult {
  symbol: string;
  has_dividends: boolean;
  current_annual_dividend: number | null;
  current_yield: number | null;
  payout_ratio: number | null;
  dividend_cagr: number | null;
  consecutive_years: number;
  annual_dividends: Record<string, number>;
  payments: DividendPayment[];
}

// Historical Valuation Types
export interface YearlyMetrics {
  year: number;
  revenue: number | null;
  net_income: number | null;
  ebitda: number | null;
  pe: number | null;
  ps: number | null;
  pb: number | null;
  ev_ebitda: number | null;
}

export interface HistoricalValuationResult {
  symbol: string;
  current: {
    pe: number | null;
    ps: number | null;
    pb: number | null;
    ev_ebitda: number | null;
  };
  average_5yr: {
    pe: number | null;
    ps: number | null;
    pb: number | null;
    ev_ebitda: number | null;
  };
  premium_discount: {
    pe: number | null;
    ps: number | null;
    pb: number | null;
    ev_ebitda: number | null;
  };
  assessment: {
    pe: 'cheap' | 'fair' | 'expensive';
    ps: 'cheap' | 'fair' | 'expensive';
    pb: 'cheap' | 'fair' | 'expensive';
    ev_ebitda: 'cheap' | 'fair' | 'expensive';
  };
  yearly_metrics: YearlyMetrics[];
}

