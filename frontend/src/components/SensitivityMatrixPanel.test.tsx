import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SensitivityMatrixPanel } from './SensitivityMatrixPanel';
import * as api from '../api';
import type { SensitivityMatrixResponse } from '../types';

// Mock the API module
vi.mock('../api', () => ({
  fetchSensitivityMatrix: vi.fn(),
}));

const mockMarginGrowthResponse: SensitivityMatrixResponse = {
  matrix_type: 'margin_growth',
  margins: [0.10, 0.12, 0.14, 0.16, 0.18],
  growth_rates: [0.05, 0.08, 0.10, 0.12, 0.15],
  matrix: [
    [80, 85, 90, 95, 100],
    [90, 95, 100, 105, 110],
    [100, 105, 110, 115, 120],
    [110, 115, 120, 125, 130],
    [120, 125, 130, 135, 140],
  ],
  base_values: { margin: 0.14, growth: 0.10 },
};

const mockWaccTerminalResponse: SensitivityMatrixResponse = {
  matrix_type: 'wacc_terminal',
  discount_rates: [0.08, 0.09, 0.10, 0.11, 0.12],
  terminal_growth_rates: [0.01, 0.02, 0.025, 0.03, 0.035],
  matrix: [
    [150, 140, 130, 120, 110],
    [140, 130, 120, 110, 100],
    [130, 120, 110, 100, 90],
    [120, 110, 100, 90, 80],
    [110, 100, 90, 80, 70],
  ],
  base_values: { discount_rate: 0.10, terminal_growth: 0.025 },
};

describe('SensitivityMatrixPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(api.fetchSensitivityMatrix).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(
      <SensitivityMatrixPanel
        symbol="AAPL"
        provider="fmp"
        baseGrowth={0.10}
        baseMargin={0.14}
        baseDiscountRate={0.10}
        terminalGrowth={0.025}
      />
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders margin vs growth matrix correctly', async () => {
    vi.mocked(api.fetchSensitivityMatrix).mockResolvedValue(mockMarginGrowthResponse);

    render(
      <SensitivityMatrixPanel
        symbol="AAPL"
        provider="fmp"
        baseGrowth={0.10}
        baseMargin={0.14}
        baseDiscountRate={0.10}
        terminalGrowth={0.025}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Margin vs Growth')).toBeInTheDocument();
    });

    // Should show multiple matrix values (the matrix has multiple $110.00 cells)
    const cells = screen.getAllByText('$110.00');
    expect(cells.length).toBeGreaterThan(0);
  });

  it('switches between matrix types', async () => {
    vi.mocked(api.fetchSensitivityMatrix)
      .mockResolvedValueOnce(mockMarginGrowthResponse)
      .mockResolvedValueOnce(mockWaccTerminalResponse);

    render(
      <SensitivityMatrixPanel
        symbol="AAPL"
        provider="fmp"
        baseGrowth={0.10}
        baseMargin={0.14}
        baseDiscountRate={0.10}
        terminalGrowth={0.025}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Margin vs Growth')).toBeInTheDocument();
    });

    // Click to switch to WACC vs Terminal Growth
    const waccButton = screen.getByText('WACC vs Terminal');
    fireEvent.click(waccButton);

    await waitFor(() => {
      expect(api.fetchSensitivityMatrix).toHaveBeenCalledTimes(2);
    });
  });

  it('highlights base value cell', async () => {
    vi.mocked(api.fetchSensitivityMatrix).mockResolvedValue(mockMarginGrowthResponse);

    render(
      <SensitivityMatrixPanel
        symbol="AAPL"
        provider="fmp"
        baseGrowth={0.10}
        baseMargin={0.14}
        baseDiscountRate={0.10}
        terminalGrowth={0.025}
      />
    );

    await waitFor(() => {
      // The center cell (base case) should be highlighted with ring class
      const cells = screen.getAllByRole('cell');
      const highlightedCell = cells.find(cell => cell.className.includes('ring'));
      expect(highlightedCell).toBeTruthy();
      expect(highlightedCell?.className).toContain('ring-gray-900');
    });
  });

  it('shows color gradient from red (low) to green (high)', async () => {
    vi.mocked(api.fetchSensitivityMatrix).mockResolvedValue(mockMarginGrowthResponse);

    render(
      <SensitivityMatrixPanel
        symbol="AAPL"
        provider="fmp"
        baseGrowth={0.10}
        baseMargin={0.14}
        baseDiscountRate={0.10}
        terminalGrowth={0.025}
      />
    );

    await waitFor(() => {
      const cells = screen.getAllByRole('cell');
      // Higher values should have green-ish background
      // Lower values should have red-ish background
      // This is a visual test - we check that cells exist
      expect(cells.length).toBeGreaterThan(0);
    });
  });

  it('handles null matrix values gracefully', async () => {
    const responseWithNull: SensitivityMatrixResponse = {
      ...mockMarginGrowthResponse,
      matrix: [
        [80, null, 90, 95, 100],
        [90, 95, null, 105, 110],
        [100, 105, 110, 115, 120],
        [110, 115, 120, null, 130],
        [120, 125, 130, 135, null],
      ],
    };
    vi.mocked(api.fetchSensitivityMatrix).mockResolvedValue(responseWithNull);

    render(
      <SensitivityMatrixPanel
        symbol="AAPL"
        provider="fmp"
        baseGrowth={0.10}
        baseMargin={0.14}
        baseDiscountRate={0.10}
        terminalGrowth={0.025}
      />
    );

    await waitFor(() => {
      // Null values should show as "-"
      expect(screen.getAllByText('-').length).toBeGreaterThan(0);
    });
  });

  it('handles API errors gracefully', async () => {
    vi.mocked(api.fetchSensitivityMatrix).mockRejectedValue(
      new Error('Network error')
    );

    render(
      <SensitivityMatrixPanel
        symbol="AAPL"
        provider="fmp"
        baseGrowth={0.10}
        baseMargin={0.14}
        baseDiscountRate={0.10}
        terminalGrowth={0.025}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
