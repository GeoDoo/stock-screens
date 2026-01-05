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

export interface ValidationIssue {
  field: string;
  message: string;
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
  data_provider: string;
  data: CompanyData;
  hints: HistoricalHints;
  validation: ValidationResult;
}

export interface ValuationRequest {
  revenue_growth: number;
  operating_margin: number;
  terminal_growth_rate: number;
  market_risk_premium: number;
  projection_years: number;
  discount_rate_override?: number | null;
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

