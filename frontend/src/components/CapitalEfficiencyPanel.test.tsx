import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CapitalEfficiencyPanel } from './CapitalEfficiencyPanel';
import type { CapitalEfficiency } from '../types';
import { BrowserRouter } from 'react-router-dom';

// Wrap component with router for GlossaryRef links
const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('CapitalEfficiencyPanel', () => {
  const defaultData: CapitalEfficiency = {
    roic: 0.25,
    value_spread: 0.15,
    economic_profit: 5_000_000_000, // 5B
    is_value_creating: true,
    invested_capital: 20_000_000_000,
    nopat: 5_000_000_000,
    assessment: 'Strong value creator: ROIC (25.0%) significantly exceeds WACC (10.0%)',
    reinvestment_rate: 0.40,
  };

  it('displays ROIC percentage', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={0.10} />);
    expect(screen.getByText('25.0%')).toBeInTheDocument();
  });

  it('displays value spread with sign', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={0.10} />);
    expect(screen.getByText('+15.0%')).toBeInTheDocument();
  });

  it('displays economic profit formatted', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={0.10} />);
    expect(screen.getByText('$5.00B')).toBeInTheDocument();
  });

  it('shows Value Creator badge when ROIC > WACC', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={0.10} />);
    expect(screen.getByText('Value Creator')).toBeInTheDocument();
  });

  it('shows Value Destroyer badge when ROIC < WACC', () => {
    const destroyerData: CapitalEfficiency = {
      ...defaultData,
      roic: 0.05,
      value_spread: -0.05,
      economic_profit: -1_000_000_000,
      is_value_creating: false,
      assessment: 'Value destroyer: ROIC (5.0%) below WACC (10.0%)',
    };
    renderWithRouter(<CapitalEfficiencyPanel data={destroyerData} wacc={0.10} />);
    expect(screen.getByText('Value Destroyer')).toBeInTheDocument();
  });

  it('displays assessment text', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={0.10} />);
    expect(screen.getByText(/Strong value creator/)).toBeInTheDocument();
  });

  it('displays reinvestment rate when available', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={0.10} />);
    expect(screen.getByText('40.0%')).toBeInTheDocument();
  });

  it('warns when reinvestment rate exceeds 100%', () => {
    const highReinvestment: CapitalEfficiency = {
      ...defaultData,
      reinvestment_rate: 1.5, // 150%
    };
    renderWithRouter(<CapitalEfficiencyPanel data={highReinvestment} wacc={0.10} />);
    expect(screen.getByText(/unsustainable/)).toBeInTheDocument();
  });

  it('handles null ROIC gracefully', () => {
    const nullData: CapitalEfficiency = {
      roic: null,
      value_spread: null,
      economic_profit: null,
      is_value_creating: null,
    };
    renderWithRouter(<CapitalEfficiencyPanel data={nullData} wacc={0.10} />);
    expect(screen.getAllByText('N/A')).toHaveLength(3);
  });

  it('displays data issue message when present', () => {
    const issueData: CapitalEfficiency = {
      roic: null,
      value_spread: null,
      economic_profit: null,
      is_value_creating: null,
      data_issue: 'Missing operating income or invested capital data',
    };
    renderWithRouter(<CapitalEfficiencyPanel data={issueData} wacc={0.10} />);
    expect(screen.getByText(/Missing operating income/)).toBeInTheDocument();
  });

  it('formats millions correctly', () => {
    const smallEVA: CapitalEfficiency = {
      ...defaultData,
      economic_profit: 500_000_000, // 500M
    };
    renderWithRouter(<CapitalEfficiencyPanel data={smallEVA} wacc={0.10} />);
    expect(screen.getByText('$500.00M')).toBeInTheDocument();
  });

  it('displays WACC reference in footer', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={0.10} />);
    expect(screen.getByText(/ROIC.*WACC.*Growth creates value/)).toBeInTheDocument();
  });

  it('handles null WACC gracefully', () => {
    renderWithRouter(<CapitalEfficiencyPanel data={defaultData} wacc={null} />);
    // Should show N/A for WACC percentage
    expect(screen.getByText(/WACC \(N\/A%\)/)).toBeInTheDocument();
  });
});
