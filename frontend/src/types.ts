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
  total_equity: number | null;
  cash: number | null;
  tax_rate: number | null;
  cost_of_debt: number | null;
  shares_outstanding: number | null;
  risk_free_rate: number;
  wacc: number | null;
  revenue: number | null;
  working_capital: number | null;
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

export interface GrowthStage {
  name: string;
  years: number;
  growth_rate: number;  // e.g., 0.20 for 20%
  end_growth_rate?: number | null;  // If set, fade linearly to this rate
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
  // Advanced DCF options
  use_mid_year_discounting?: boolean;
  wc_mode?: 'level' | 'incremental';
  // Multi-stage growth - if provided, overrides revenue_growth and projection_years
  growth_stages?: GrowthStage[] | null;
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
  // Hints for default scenario generation - clean TTM/Annual separation
  revenue_growth_hint?: number | null;
  operating_margin_hint?: number | null;
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

// =============================================================================
// Investment Memo Types
// =============================================================================

export type MemoConviction = 'low' | 'medium' | 'high';
export type MemoStatus = 'active' | 'closed_win' | 'closed_loss' | 'closed_neutral';
export type PostMortemAction = 'hold' | 'add' | 'trim' | 'close' | 'review';

export interface MemoAssumptions {
  revenue_growth: number;
  operating_margin: number;
  terminal_growth_rate: number;
  discount_rate: number;
  projection_years: number;
  da_ratio?: number | null;
  capex_ratio?: number | null;
  wc_ratio?: number | null;
}

export interface MemoScenario {
  name: string;
  revenue_growth: number;
  operating_margin: number;
  intrinsic_value: number;
  upside_percent: number;
}

export interface MemoMarketSnapshot {
  price: number;
  intrinsic_value: number;
  pe_ratio?: number | null;
  captured_at: string;
}

export interface MemoPostMortem {
  id: number;
  memo_id: number;
  created_at: string;
  note: string;
  action: PostMortemAction;
  price_at_time: number;
  iv_at_time: number;
}

export interface MemoPerformance {
  price_change_percent: number;
  iv_change_percent: number;
  original_upside_percent: number;
  thesis_realized_percent: number;
  latest_price: number;
  latest_iv: number;
}

export interface InvestmentMemo {
  id: number;
  symbol: string;
  title: string;
  thesis: string;
  conviction: MemoConviction;
  time_horizon_months: number;
  created_at: string;
  
  // Snapshots at creation
  assumptions: MemoAssumptions;
  scenarios: MemoScenario[];
  initial_market: MemoMarketSnapshot;
  
  // Optional fields
  target_price?: number | null;
  risks?: string | null;
  catalysts?: string | null;
  what_would_change_mind?: string | null;
  
  // Status
  status: MemoStatus;
  closed_at?: string | null;
  closed_reason?: string | null;
  
  // Tracking data
  market_snapshots: MemoMarketSnapshot[];
  post_mortems: MemoPostMortem[];
  
  // Computed
  current_performance: MemoPerformance;
}

export interface CreateMemoRequest {
  symbol: string;
  title: string;
  thesis: string;
  conviction: MemoConviction;
  time_horizon_months: number;
  assumptions: MemoAssumptions;
  scenarios: MemoScenario[];
  initial_market: {
    price: number;
    intrinsic_value: number;
    pe_ratio?: number | null;
  };
  target_price?: number | null;
  risks?: string | null;
  catalysts?: string | null;
  what_would_change_mind?: string | null;
}

// =============================================================================
// Monte Carlo Simulation Types
// =============================================================================

export interface MonteCarloRequest {
  base_growth: number;
  growth_std: number;
  base_margin: number;
  margin_std: number;
  base_discount_rate: number;
  discount_std: number;
  terminal_growth: number;
  projection_years: number;
  iterations: number;
}

export interface MonteCarloPercentiles {
  p5: number;
  p10: number;
  p25: number;
  p50: number;  // Median
  p75: number;
  p90: number;
  p95: number;
  min: number;
  max: number;
}

export interface MonteCarloResult {
  symbol: string;
  iterations: number;
  valid_simulations: number;
  enterprise_value: {
    mean: number;
    std_dev: number;
    percentiles: MonteCarloPercentiles;
  };
  per_share: {
    mean: number;
    percentiles: MonteCarloPercentiles;
  };
  inputs: {
    base_revenue: number;
    base_growth: number;
    growth_std: number;
    base_margin: number;
    margin_std: number;
    base_discount_rate: number;
    discount_std: number;
    terminal_growth: number;
    projection_years: number;
  };
}

// Full-Model Monte Carlo (Decision-Grade)
export interface FullMonteCarloRequest {
  base_growth: number;
  base_margin: number;
  base_da_ratio: number;
  base_capex_ratio: number;
  base_wc_ratio: number;
  base_tax_rate?: number;
  base_discount_rate: number;
  base_terminal_growth?: number;
  growth_std?: number;
  margin_std?: number;
  da_ratio_std?: number;
  capex_ratio_std?: number;
  wc_ratio_std?: number;
  discount_std?: number;
  terminal_growth_std?: number;
  projection_years?: number;
  iterations?: number;
  growth_margin_correlation?: number;
  growth_capex_correlation?: number;
}

export interface FullMonteCarloDecisionMetrics {
  probability_positive_upside: number;  // P(IV > price)
  probability_20pct_upside: number;     // P(IV > price * 1.2)
  probability_20pct_downside: number;   // P(IV < price * 0.8)
  cvar_10: number;                      // Expected value of worst 10%
  margin_of_safety_mean: number;
  margin_of_safety_median: number;
}

export interface FullMonteCarloResult {
  symbol: string;
  mode: 'full';
  current_price: number;
  iterations: number;
  valid_simulations: number;
  per_share: {
    mean: number;
    median: number;
    std_dev: number;
    percentiles: MonteCarloPercentiles;
  };
  decision_metrics: FullMonteCarloDecisionMetrics;
  inputs: {
    base_growth: number;
    base_margin: number;
    base_da_ratio: number;
    base_capex_ratio: number;
    base_wc_ratio: number;
    base_tax_rate: number;
    base_discount_rate: number;
    base_terminal_growth: number;
    projection_years: number;
    correlations: {
      growth_margin: number;
      growth_capex: number;
    };
  };
}

// =============================================================================
// Capital Efficiency Types
// =============================================================================

export interface CapitalEfficiencyRequest {
  nopat: number;
  invested_capital: number;
  revenue_growth: number;
  wacc: number;
}

export interface CapitalEfficiencyResult {
  roic: number | null;
  roic_formatted: string | null;
  reinvestment_rate: number | null;
  reinvestment_rate_formatted: string | null;
  value_spread: number | null;
  value_spread_formatted: string | null;
  economic_profit: number | null;
  is_value_creating: boolean;
  assessment: string;
}
