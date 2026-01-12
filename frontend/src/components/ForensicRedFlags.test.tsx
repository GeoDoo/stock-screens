import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ForensicRedFlags } from './ForensicRedFlags';

describe('ForensicRedFlags Component', () => {
  it('renders loading state correctly', () => {
    const { container } = render(<ForensicRedFlags analysis="" loading={true} />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders "No findings" state for empty or benign analysis', () => {
    render(<ForensicRedFlags analysis="The filing looks clean." />);
    expect(screen.getByText(/No critical red flags detected/i)).toBeTruthy();
  });

  it('correctly parses and displays high-severity findings', () => {
    const mockAnalysis = `
      SECTION ACCOUNTING_FORENSICS:
      **High Risk: Revenue Recognition Shift**
      Management has changed wording in Note 3 from 'shipment' to 'estimates of progress'. This is a detailed description that is long enough to pass the filter.
      
      **Sloan Ratio Warning**
      The Sloan ratio is 12%, indicating poor earnings quality. This is another long description to ensure it gets picked up.
    `;
    
    render(<ForensicRedFlags analysis={mockAnalysis} />);
    
    expect(screen.getByText(/Revenue Recognition Shift/i)).toBeTruthy();
    expect(screen.getAllByText(/ACCOUNTING_FORENSICS/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Sloan ratio is 12%/i)).toBeTruthy();
  });

  it('assigns correct severity based on keywords', () => {
    const mockAnalysis = `
      SECTION TEXTUAL_ALPHA:
      **Potential Warning: Tone Shift**
      Language became more legalistic in Item 1A. This is a long enough description for the parser.
    `;
    
    const { container } = render(<ForensicRedFlags analysis={mockAnalysis} />);
    // amber-500 is used for medium severity (triggered by 'warning')
    const card = container.querySelector('.bg-amber-50');
    expect(card).toBeTruthy();
  });
});
