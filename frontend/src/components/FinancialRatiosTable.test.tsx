import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FinancialRatiosTable } from './FinancialRatiosTable';
import type { FinancialRatiosPeriod } from '../types';
import { BrowserRouter } from 'react-router-dom';

// Wrap component in BrowserRouter for GlossaryRef links
const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

const createMockRatios = (overrides?: Partial<FinancialRatiosPeriod>): FinancialRatiosPeriod => ({
  symbol: 'AAPL',
  period: 'annual',
  valuation: {
    pe_ratio: 25.5,
    earnings_yield: 0.04,
    ps_ratio: 6.5,
    pb_ratio: 40.0,
    ev_to_ebitda: 22.0,
    ev_to_revenue: 7.5,
  },
  profitability: {
    gross_margin: 0.45,
    operating_margin: 0.30,
    net_margin: 0.25,
    roe: 0.35,
    roa: 0.15,
    roic: 0.22,
    rotic: 0.28,
    incremental_roic: 0.18,
    incremental_roic_unavailable_reason: null,
  },
  liquidity: {
    current_ratio: 1.5,
    quick_ratio: 1.2,
    debt_to_equity: 0.8,
    interest_coverage: 15.0,
  },
  efficiency: {
    asset_turnover: 0.9,
    inventory_turnover: 8.0,
    days_sales_outstanding: 35,
    days_inventory_outstanding: 45,
    days_payables_outstanding: 60,
    cash_conversion_cycle: 20,
  },
  dividend: {
    dividend_yield: 0.015,
    payout_ratio: 0.30,
    buyback_yield: 0.02,
    total_shareholder_yield: 0.035,
    is_debt_funded_returns: null,
    capital_returns_coverage: null,
  },
  risk: {
    altman_z_score: 5.5,
    z_score_zone: 'safe',
    beneish_m_score: -2.5,
    m_score_zone: 'low_risk',
    accrual_ratio: 0.03,
    accrual_quality: 'good',
  },
  sbc: {
    sbc_percent_revenue: 0.05,
    sbc_level: 'normal',
    fcf_adjusted: 80_000_000_000,
  },
  ...overrides,
});

describe('FinancialRatiosTable', () => {
  describe('Debt-Funded Returns Warning', () => {
    it('shows warning when returns are debt-funded', () => {
      const ratios = createMockRatios({
        dividend: {
          dividend_yield: 0.04,
          payout_ratio: 0.50,
          buyback_yield: 0.02,
          total_shareholder_yield: 0.06,
          is_debt_funded_returns: true,
          capital_returns_coverage: 0.5,
        },
      });

      renderWithRouter(<FinancialRatiosTable ratios={ratios} />);

      expect(screen.getByText('Debt-Funded Returns')).toBeInTheDocument();
      expect(screen.getByText(/Dividends \+ Buybacks exceed Free Cash Flow/)).toBeInTheDocument();
    });

    it('does not show warning when returns are healthy', () => {
      const ratios = createMockRatios({
        dividend: {
          dividend_yield: 0.02,
          payout_ratio: 0.30,
          buyback_yield: 0.01,
          total_shareholder_yield: 0.03,
          is_debt_funded_returns: false,
          capital_returns_coverage: 1.5,
        },
      });

      renderWithRouter(<FinancialRatiosTable ratios={ratios} />);

      expect(screen.queryByText('Debt-Funded Returns')).not.toBeInTheDocument();
    });

    it('shows FCF coverage ratio with color coding', () => {
      const ratios = createMockRatios({
        dividend: {
          dividend_yield: 0.02,
          payout_ratio: 0.30,
          buyback_yield: 0.01,
          total_shareholder_yield: 0.03,
          is_debt_funded_returns: false,
          capital_returns_coverage: 1.33,
        },
      });

      renderWithRouter(<FinancialRatiosTable ratios={ratios} />);

      expect(screen.getByText('1.33x')).toBeInTheDocument();
      // Should be green (healthy coverage)
      expect(screen.getByText('1.33x')).toHaveClass('text-green-600');
    });

    it('shows amber coverage for borderline cases', () => {
      const ratios = createMockRatios({
        dividend: {
          dividend_yield: 0.02,
          payout_ratio: 0.30,
          buyback_yield: 0.01,
          total_shareholder_yield: 0.03,
          is_debt_funded_returns: true,
          capital_returns_coverage: 0.75,
        },
      });

      renderWithRouter(<FinancialRatiosTable ratios={ratios} />);

      expect(screen.getByText('0.75x')).toBeInTheDocument();
      expect(screen.getByText('0.75x')).toHaveClass('text-amber-600');
    });

    it('shows red coverage for severely debt-funded returns', () => {
      const ratios = createMockRatios({
        dividend: {
          dividend_yield: 0.04,
          payout_ratio: 0.80,
          buyback_yield: 0.02,
          total_shareholder_yield: 0.06,
          is_debt_funded_returns: true,
          capital_returns_coverage: 0.3,
        },
      });

      renderWithRouter(<FinancialRatiosTable ratios={ratios} />);

      expect(screen.getByText('0.30x')).toBeInTheDocument();
      expect(screen.getByText('0.30x')).toHaveClass('text-red-600');
    });
  });
});
