import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CEOEfficiencyWarning } from './CEOEfficiencyWarning';

describe('CEOEfficiencyWarning', () => {
  it('shows VALUE CREATOR when Inc. ROIC significantly exceeds WACC', () => {
    render(
      <CEOEfficiencyWarning
        incrementalRoic={0.15}  // 15%
        wacc={0.10}  // 10%
      />
    );
    
    expect(screen.getByText('VALUE CREATOR')).toBeInTheDocument();
    expect(screen.getByText('Management earns above cost of capital on new investments')).toBeInTheDocument();
    expect(screen.getByText('+5.0%')).toBeInTheDocument();  // Spread
  });
  
  it('shows VALUE DESTROYER when Inc. ROIC significantly below WACC', () => {
    render(
      <CEOEfficiencyWarning
        incrementalRoic={0.06}  // 6%
        wacc={0.10}  // 10%
      />
    );
    
    expect(screen.getByText('VALUE DESTROYER')).toBeInTheDocument();
    expect(screen.getByText('Growth is destroying value — each new $ invested loses money')).toBeInTheDocument();
    expect(screen.getByText('-4.0%')).toBeInTheDocument();  // Spread
  });
  
  it('shows VALUE NEUTRAL when Inc. ROIC approximately equals WACC', () => {
    render(
      <CEOEfficiencyWarning
        incrementalRoic={0.11}  // 11%
        wacc={0.10}  // 10%
      />
    );
    
    expect(screen.getByText('VALUE NEUTRAL')).toBeInTheDocument();
    expect(screen.getByText('New investments roughly break even vs cost of capital')).toBeInTheDocument();
  });
  
  it('returns null when incrementalRoic is null', () => {
    const { container } = render(
      <CEOEfficiencyWarning
        incrementalRoic={null}
        wacc={0.10}
      />
    );
    
    expect(container.firstChild).toBeNull();
  });
  
  it('returns null when wacc is null', () => {
    const { container } = render(
      <CEOEfficiencyWarning
        incrementalRoic={0.15}
        wacc={null}
      />
    );
    
    expect(container.firstChild).toBeNull();
  });
  
  it('displays Inc. ROIC and WACC values correctly', () => {
    render(
      <CEOEfficiencyWarning
        incrementalRoic={0.125}  // 12.5%
        wacc={0.085}  // 8.5%
      />
    );
    
    expect(screen.getByText('12.5%')).toBeInTheDocument();
    expect(screen.getByText('8.5%')).toBeInTheDocument();
    expect(screen.getByText('+4.0%')).toBeInTheDocument();
  });
  
  it('shows distortion warning when Inc. ROIC exceeds 100%', () => {
    render(
      <CEOEfficiencyWarning
        incrementalRoic={2.676}  // 267.6% (like Apple)
        wacc={0.109}  // 10.9%
      />
    );
    
    expect(screen.getByText('267.6%')).toBeInTheDocument();
    expect(screen.getByText(/Potentially misleading/)).toBeInTheDocument();
    expect(screen.getByText(/buybacks/)).toBeInTheDocument();
  });
  
  it('does not show distortion warning for normal values', () => {
    render(
      <CEOEfficiencyWarning
        incrementalRoic={0.15}  // 15%
        wacc={0.10}  // 10%
      />
    );
    
    expect(screen.queryByText(/Potentially misleading/)).not.toBeInTheDocument();
  });
});
