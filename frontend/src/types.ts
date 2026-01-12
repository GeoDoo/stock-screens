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

// Provenance shows the source/confidence for key metrics
export interface ProvenanceItem {
  source: string;  // "ttm", "fy_average", "fallback", etc.
  description: string;  // Human-readable explanation
  confidence: 'high' | 'medium' | 'low';
}

export interface DataProvenance {
  tax_rate: ProvenanceItem | null;
  shares_outstanding: ProvenanceItem | null;
  revenue_source: ProvenanceItem | null;
  cost_of_debt: ProvenanceItem | null;
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
  is_using_ltm?: boolean;  // True if using Last Twelve Months (more current) data
  validation: ValidationResult;
  provenance?: DataProvenance;  // Source/confidence for key metrics
  // Data freshness indicator (NOTES2.md enhancement)
  latest_statement_date?: string;  // Date of most recent financial statement (YYYY-MM-DD)
  data_freshness_days?: number;  // Days since latest statement
  data_is_stale?: boolean;  // True if >120 days old (post-earnings update required)
}

// Fade mode for economics schedules
export type FadeMode = 'linear' | 'step';

export interface GrowthStage {
  name: string;
  years: number;
  growth_rate: number;  // e.g., 0.20 for 20%
  end_growth_rate?: number | null;  // If set, fade linearly to this rate
  
  // Multi-stage economics - fade operating margin as company matures
  operating_margin?: number | null;  // e.g., 0.15 for 15% margin
  end_operating_margin?: number | null;  // If set, fade to this margin
  // Operating leverage mode: 'linear' = smooth fade, 'step' = jump at step_at_year
  margin_fade_mode?: FadeMode | null;
  margin_step_at_year?: number | null;  // For 'step' mode: year when margin jumps
  
  // CapEx ratio (as % of revenue) - typically declines as growth slows
  capex_ratio?: number | null;  // e.g., 0.10 for 10%
  end_capex_ratio?: number | null;  // If set, fade to this ratio
  
  // Working capital ratio - efficiency often improves with scale
  wc_ratio?: number | null;  // e.g., 0.15 for 15%
  end_wc_ratio?: number | null;  // If set, fade to this ratio
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
  // SBC dilution - annual share growth rate from stock-based compensation
  // E.g., 0.02 means 2% more shares issued each year (dilutes per-share value)
  annual_dilution_rate?: number;
  // Exit Multiple cross-check - sector/peer median EV/EBITDA multiple
  // If provided, compares Gordon Growth TV with Exit Multiple TV and warns if >20% divergence
  sector_ev_ebitda_multiple?: number | null;
  // Conservative FCF: SBC as % of revenue to subtract from FCF (NOTES2.md)
  // When provided, treats SBC as a real expense: FCF = NOPAT + D&A - CapEx - ΔWC - SBC
  sbc_ratio?: number | null;
}

export interface SensitivityMatrix {
  discount_rates: number[];
  terminal_growth_rates: number[];
  matrix: (number | null)[][];
  roic_flags?: boolean[][];  // True if cell is economically suspect (implied ROIC > 2× WACC)
  base_discount_rate: number;
  base_terminal_growth: number;
}

// Institutional-grade Equity Bridge
export interface EquityBridge {
  net_debt: number;
  minority_interest: number;
  preferred_stock: number;
  deferred_tax_assets: number;  // NOLs/tax shields (adds value)
  pension_deficit: number;
}

// Terminal Value cross-check (Exit Multiple vs Gordon Growth)
export interface TerminalValueCheck {
  terminal_ebitda: number;
  implied_exit_multiple: number | null;
  terminal_value_pct: number;  // PV(Terminal) / EV - dominance check
  gordon_growth_tv?: number;  // TV via Gordon Growth Model
  exit_multiple_tv?: number;  // TV via Exit Multiple Method (if sector multiple provided)
  sector_ev_ebitda_multiple?: number;  // The sector multiple used
  method_divergence_pct?: number;  // (Gordon - Exit Multiple) / Exit Multiple
  warning?: string;  // High implied multiple warning
  dominance_warning?: string;  // Terminal value dominance warning
  method_divergence_warning?: string;  // Gordon vs Exit Multiple divergence warning
  // P0 Economic Terminal State (ROIC convergence)
  implied_terminal_roic?: number | null;  // Implied ROIC in perpetuity
  terminal_roic_warning?: string;  // Warning if ROIC >> WACC
  // P1 CapEx convergence (Maintenance vs Growth)
  terminal_capex_to_da?: number;  // CapEx/D&A ratio in terminal year
  capex_convergence_warning?: string;  // Warning if CapEx >> D&A
}

// Value driver impact - shows which inputs have the largest effect on intrinsic value
export interface ValueDriver {
  input: 'discount_rate' | 'terminal_growth' | 'revenue_growth' | 'operating_margin';
  impact_percent: number;  // Percentage change in value from ±10% input change
  description: string;     // Human-readable description of the sensitivity
}

// Capital Efficiency metrics - NOTES4
export interface CapitalEfficiency {
  roic: number | null;  // Return on Invested Capital
  value_spread: number | null;  // ROIC - WACC (positive = value creation)
  economic_profit: number | null;  // Value Spread × Invested Capital
  is_value_creating: boolean | null;  // ROIC > WACC
  invested_capital?: number | null;  // Total invested capital
  nopat?: number | null;  // Net Operating Profit After Tax
  assessment?: string;  // Human-readable interpretation
  incremental_assessment?: string | null;  // Incremental ROIC assessment
  reinvestment_rate?: number | null;  // % of earnings needed for growth
  data_issue?: string;  // Why metrics couldn't be calculated
}

export interface ValuationResult {
  symbol: string;
  intrinsic_value_per_share: number;
  enterprise_value: number;
  equity_value: number;
  market_cap: number | null;
  net_debt: number;
  equity_bridge?: EquityBridge;  // Full institutional bridge
  wacc: number | null;  // Can be null if WACC calculation fails
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
  inputs: {
    revenue_growth?: number;
    operating_margin?: number;
    terminal_growth_rate?: number;
    projection_years?: number;
    discount_rate_override?: number | null;
    shares_outstanding?: number;
    shares_type?: 'diluted' | 'basic';
    annual_dilution_rate?: number;
    terminal_shares?: number;
    da_ratio?: number;
    capex_ratio?: number;
    wc_ratio?: number;
    sbc_ratio?: number | null;  // Conservative FCF: SBC as % of revenue
    [key: string]: unknown;  // Allow other properties
  };
  sensitivity: SensitivityMatrix;
  terminal_value_check?: TerminalValueCheck;  // Exit Multiple cross-check and dominance warnings
  value_drivers?: ValueDriver[];  // Ranked list of inputs by impact on valuation
  business_type_warning?: string | null;  // P2.8: Warning for financial companies where DCF is less appropriate
  capital_efficiency?: CapitalEfficiency;  // NOTES4: ROIC, Value Spread, Economic Profit
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
  probabilities_normalized?: boolean;  // True if probabilities were auto-adjusted to sum to 1
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
  currency?: string;  // Reporting currency (e.g., "USD", "JPY", "EUR")
}

// Currency conversion tracking for cross-currency peer comparisons
export interface CurrencyConversion {
  symbol: string;
  original_currency: string;
  converted_to: string;
  rate: number;  // Units of original currency per unit of target currency
  is_approximate?: boolean;  // P1.3: True if using hardcoded fallback rates
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
  // Currency normalization info
  base_currency?: string;  // Currency all values are normalized to (target's currency)
  currency_conversions?: CurrencyConversion[] | null;  // Peers that required currency conversion
  fx_rates_approximate?: boolean;  // P1.3: True if any FX rates were approximate
  // P2 #8: Business-type valuation notes for financials/cyclicals
  valuation_notes?: string[];  // Notes about metric applicability for this business type
  // P2 #9: Peer selection transparency (market cap filtering info)
  // NOTES2.md: Added 'fmp_dynamic' source for dynamic peer discovery
  peer_selection_info?: {
    source: 'industry' | 'sector' | 'fmp_dynamic';  // fmp_dynamic = FMP API peers
    total_candidates: number;
    after_market_cap_filter: number;
    market_cap_range: string;
    filter_note?: string;  // Shown when peers were filtered out
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
    vwap?: IndicatorValue[];  // Volume Weighted Average Price
    // NEW: Enhanced volume-weighted indicators
    vwma_20?: IndicatorValue[];  // Volume Weighted Moving Average
    obv?: IndicatorValue[];  // On-Balance Volume
    mfi_14?: IndicatorValue[];  // Money Flow Index (volume-weighted RSI)
  };
  // Volume metrics (institutional-grade)
  volume?: {
    average_volume: number | null;  // 20-day average
    relative_volume: number | null;  // Current vs average (multiplier)
  };
  signals: {
    trend: 'bullish' | 'bearish' | 'neutral';
    rsi: 'overbought' | 'oversold' | 'neutral';
    macd: 'bullish' | 'bearish' | 'neutral';
    volume_confirmation?: 'confirmed' | 'weak' | 'neutral';  // Volume validates signal
    mfi_signal?: 'overbought' | 'oversold' | 'neutral';  // MFI signal (matches backend field name)
    obv_trend?: 'accumulation' | 'distribution' | 'neutral';  // Smart money flow
    // NEW: Momentum Bridge (Value + Momentum convergence)
    vwma_trend?: 'uptrend' | 'downtrend' | 'flat';  // 200-day VWMA trend
  };
}

// Sensitivity Matrix Types
export interface SensitivityMatrixRequest {
  matrix_type: 'margin_growth' | 'wacc_terminal';
  base_growth?: number;
  base_margin?: number;
  base_discount_rate?: number;
  terminal_growth?: number;
  projection_years?: number;
}

export interface SensitivityMatrixResponse {
  matrix_type: 'margin_growth' | 'wacc_terminal';
  margins?: number[];  // For margin_growth
  growth_rates?: number[];  // For margin_growth
  discount_rates?: number[];  // For wacc_terminal
  terminal_growth_rates?: number[];  // For wacc_terminal
  matrix: (number | null)[][];  // 2D matrix of intrinsic values
  roic_flags?: boolean[][];  // True if cell is economically suspect (implied ROIC > 2× WACC)
  base_values: Record<string, number>;
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
    // NEW: Total Shareholder Yield (Alpha Layer)
    buyback_yield: number | null;  // Share Repurchases / Market Cap
    total_shareholder_yield: number | null;  // Dividend Yield + Buyback Yield
    // NOTES2.md P0: Debt-Funded Returns Check (Value Trap Detection)
    is_debt_funded_returns: boolean | null;  // True if (Dividends + Buybacks) > FCF
    capital_returns_coverage: number | null;  // FCF / (Dividends + Buybacks), >1 = healthy
  };
  profitability: {
    gross_margin: number | null;
    operating_margin: number | null;
    net_margin: number | null;
    roe: number | null;
    roa: number | null;
    roic: number | null;
    rotic: number | null;  // Return on Tangible Invested Capital
    incremental_roic: number | null;  // ΔNOPAT / ΔInvested Capital
    // Why incremental_roic is null: "capital_returned" = buybacks reduced capital base
    incremental_roic_unavailable_reason?: 'capital_returned' | null;
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
    days_sales_outstanding: number | null;  // DSO = (AR / Revenue) × 365
    days_inventory_outstanding: number | null;  // DIO = (Inventory / COGS) × 365
    days_payables_outstanding: number | null;  // DPO = (AP / COGS) × 365
    cash_conversion_cycle: number | null;  // CCC = DSO + DIO - DPO
  };
  // Institutional-grade risk metrics
  // P1.2: z_score_zone and m_score_zone can be "not_applicable" for financial companies
  risk?: {
    altman_z_score: number | null;
    z_score_zone: 'safe' | 'grey' | 'distress' | 'not_applicable' | null;
    accrual_ratio: number | null;
    accrual_quality: 'good' | 'elevated' | 'warning' | null;
    beneish_m_score: number | null;
    m_score_zone: 'low_risk' | 'high_risk' | 'not_applicable' | null;
  };
  // Stock-based compensation analysis
  sbc?: {
    fcf_adjusted: number | null;
    sbc_percent_revenue: number | null;
    sbc_level: 'normal' | 'elevated' | 'high' | null;
    // NOTES2.md P0: Net Buyback Efficiency (Defensive Buyback Detection)
    // Ratio = SBC Expense / Cash Spent on Buybacks
    // > 1.0: Dilutive (SBC exceeds buybacks - value trap)
    // < 1.0: Accretive (buybacks exceed SBC - genuine value return)
    net_buyback_efficiency?: number | null;
    is_defensive_buyback?: boolean | null;
  };
  // NOTES2.md III.1: Exit Liquidity for institutional position sizing
  exit_liquidity?: {
    average_daily_volume: number;  // 30-day ADV in shares
    average_daily_dollar_volume: number;  // ADV × Price
    days_to_liquidate_1m: number;  // Days to exit a $1M position at 10% participation
    liquidity_tier: 'highly_liquid' | 'liquid' | 'moderate' | 'illiquid';
    requires_liquidity_discount: boolean;  // True if > 5 days to exit
  } | null;
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
  fcf_payout_ratio: number | null;  // Dividends / Free Cash Flow (more accurate)
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
  uses_true_historical_prices: boolean;  // P1.7: True if actual historical prices used, false if proxy (current market cap)
  // NOTES2.md P0.2: Static price bias warning - when proxy used, comparison is disabled
  comparison_disabled_reason: string | null;
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
    pe: 'cheap' | 'fair' | 'expensive' | 'unavailable';
    ps: 'cheap' | 'fair' | 'expensive' | 'unavailable';
    pb: 'cheap' | 'fair' | 'expensive' | 'unavailable';
    ev_ebitda: 'cheap' | 'fair' | 'expensive' | 'unavailable';
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
  // P1: Full institutional equity bridge (not just net debt)
  equity_bridge?: EquityBridge;
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
  // Fat tails (Student's t-distribution)
  // None = Normal distribution, 3-4 = fat tails (recommended), 5-10 = moderate
  // Must be ≥3 for valid variance (math requirement)
  fat_tails_df?: number | null;
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
  // P2: Simulation quality metrics
  warnings?: string[];  // Warnings about simulation quality (negative terminal FCF, etc.)
  negative_terminal_fcf_count?: number;  // How many simulations were skipped
  zero_equity_count?: number;  // P0.3: How many simulations resulted in wipe-out (equity <= 0)
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
