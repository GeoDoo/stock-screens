import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ForensicRedFlags } from './ForensicRedFlags';

describe('ForensicRedFlags Component', () => {
  it('renders loading state correctly', () => {
    const { container } = render(<ForensicRedFlags analysis="" loading={true} />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders "No findings" state for empty analysis', () => {
    render(<ForensicRedFlags analysis="" />);
    expect(screen.getByText(/No critical red flags detected/i)).toBeTruthy();
  });

  it('correctly displays markdown analysis', () => {
    const mockAnalysis = `
# Forensic Audit
## Accounting Forensics
**High Risk: Revenue Recognition Shift**
Management has changed wording in Note 3 from 'shipment' to 'estimates of progress'.
    `;
    
    render(<ForensicRedFlags analysis={mockAnalysis} />);
    
    expect(screen.getByText(/Forensic Audit/i)).toBeTruthy();
    expect(screen.getByText(/Accounting Forensics/i)).toBeTruthy();
    expect(screen.getByText(/Revenue Recognition Shift/i)).toBeTruthy();
  });
});
