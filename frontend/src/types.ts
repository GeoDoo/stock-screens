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
}

