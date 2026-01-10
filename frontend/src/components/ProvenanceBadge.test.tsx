import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProvenanceBadge, ProvenanceDisplay } from './ProvenanceBadge';

describe('ProvenanceBadge', () => {
  it('renders high confidence badge with green styling', () => {
    render(
      <ProvenanceBadge
        source="ttm"
        description="From TTM income statement"
        confidence="high"
      />
    );
    
    const badge = screen.getByText('TTM');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-emerald');
  });

  it('renders medium confidence badge with yellow styling', () => {
    render(
      <ProvenanceBadge
        source="fy_average"
        description="3-year average"
        confidence="medium"
      />
    );
    
    const badge = screen.getByText('FY AVG');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-amber');
  });

  it('renders low confidence badge with red styling', () => {
    render(
      <ProvenanceBadge
        source="fallback"
        description="Using default value"
        confidence="low"
      />
    );
    
    const badge = screen.getByText('FALLBACK');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-red');
  });

  it('shows description on hover via title attribute', () => {
    render(
      <ProvenanceBadge
        source="ttm"
        description="From TTM income statement"
        confidence="high"
      />
    );
    
    const badge = screen.getByText('TTM');
    expect(badge).toHaveAttribute('title', 'From TTM income statement');
  });
});

describe('ProvenanceDisplay', () => {
  it('renders all provenance items for a metric', () => {
    const provenance = {
      tax_rate: { source: 'ttm', description: 'TTM effective tax rate', confidence: 'high' as const },
      shares_outstanding: { source: 'diluted', description: 'Diluted shares', confidence: 'high' as const },
      revenue_source: { source: 'fy_average', description: '3-year average', confidence: 'medium' as const },
      cost_of_debt: { source: 'fallback', description: 'Default 5%', confidence: 'low' as const },
    };

    render(<ProvenanceDisplay provenance={provenance} />);

    expect(screen.getByText('Tax Rate')).toBeInTheDocument();
    expect(screen.getByText('Shares')).toBeInTheDocument();
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('Cost of Debt')).toBeInTheDocument();
  });

  it('handles null provenance items gracefully', () => {
    const provenance = {
      tax_rate: { source: 'ttm', description: 'TTM effective tax rate', confidence: 'high' as const },
      shares_outstanding: null,
      revenue_source: null,
      cost_of_debt: null,
    };

    render(<ProvenanceDisplay provenance={provenance} />);

    expect(screen.getByText('Tax Rate')).toBeInTheDocument();
    // Should only render 1 item
    expect(screen.queryByText('Shares')).not.toBeInTheDocument();
  });

  it('returns null when provenance is undefined', () => {
    const { container } = render(<ProvenanceDisplay provenance={undefined} />);
    expect(container.firstChild).toBeNull();
  });
});
