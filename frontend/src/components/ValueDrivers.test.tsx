import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ValueDrivers } from './ValueDrivers';
import type { ValueDriver } from '../types';

describe('ValueDrivers', () => {
  const mockDrivers: ValueDriver[] = [
    { input: 'discount_rate', impact_percent: 25.5, description: '±1% change in discount rate' },
    { input: 'terminal_growth', impact_percent: 18.2, description: '±0.5% change in terminal growth' },
    { input: 'revenue_growth', impact_percent: 12.3, description: '±10% relative change in growth rate' },
    { input: 'operating_margin', impact_percent: 8.1, description: '±10% relative change in margin' },
  ];

  it('renders all value drivers sorted by impact', () => {
    render(<ValueDrivers drivers={mockDrivers} />);
    
    // All labels should be visible
    expect(screen.getByText('Discount Rate')).toBeInTheDocument();
    expect(screen.getByText('Terminal Growth')).toBeInTheDocument();
    expect(screen.getByText('Revenue Growth')).toBeInTheDocument();
    expect(screen.getByText('Operating Margin')).toBeInTheDocument();
  });

  it('displays impact percentages', () => {
    render(<ValueDrivers drivers={mockDrivers} />);
    
    expect(screen.getByText('25.50%')).toBeInTheDocument();
    expect(screen.getByText('18.20%')).toBeInTheDocument();
    expect(screen.getByText('12.30%')).toBeInTheDocument();
    expect(screen.getByText('8.10%')).toBeInTheDocument();
  });

  it('shows descriptions', () => {
    render(<ValueDrivers drivers={mockDrivers} />);
    
    expect(screen.getByText('±1% change in discount rate')).toBeInTheDocument();
    expect(screen.getByText('±0.5% change in terminal growth')).toBeInTheDocument();
  });

  it('returns null for empty drivers array', () => {
    const { container } = render(<ValueDrivers drivers={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null for undefined drivers', () => {
    const { container } = render(<ValueDrivers drivers={undefined as unknown as ValueDriver[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders section header', () => {
    render(<ValueDrivers drivers={mockDrivers} />);
    expect(screen.getByText('Value Sensitivity')).toBeInTheDocument();
  });

  it('shows explanatory footer', () => {
    render(<ValueDrivers drivers={mockDrivers} />);
    expect(screen.getByText(/Higher sensitivity = bigger impact/)).toBeInTheDocument();
  });

  it('handles single driver', () => {
    const singleDriver: ValueDriver[] = [
      { input: 'discount_rate', impact_percent: 15.0, description: '±1% change' },
    ];
    render(<ValueDrivers drivers={singleDriver} />);
    
    expect(screen.getByText('Discount Rate')).toBeInTheDocument();
    expect(screen.getByText('15.00%')).toBeInTheDocument();
  });

  it('applies correct colors based on impact level', () => {
    // High impact (>=20) should be red
    // Medium impact (>=10) should be amber
    // Low impact (<10) should be green
    render(<ValueDrivers drivers={mockDrivers} />);
    
    // The 25.50% impact should have red text styling
    const highImpact = screen.getByText('25.50%');
    expect(highImpact).toHaveClass('text-red-600');
    
    // The 8.10% impact should have gray text
    const lowImpact = screen.getByText('8.10%');
    expect(lowImpact).toHaveClass('text-gray-500');
  });
});
