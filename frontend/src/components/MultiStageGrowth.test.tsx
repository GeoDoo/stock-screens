import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MultiStageGrowth } from './MultiStageGrowth';
import type { GrowthStage } from '../types';

describe('MultiStageGrowth', () => {
  const mockOnChange = vi.fn();
  
  beforeEach(() => {
    mockOnChange.mockClear();
  });

  const defaultProps = {
    stages: [] as GrowthStage[],
    onChange: mockOnChange,
    terminalGrowth: 0.025,
  };

  describe('Basic functionality', () => {
    it('renders with expand/collapse toggle', () => {
      render(<MultiStageGrowth {...defaultProps} />);
      expect(screen.getByText('Multi-Stage Growth')).toBeInTheDocument();
      expect(screen.getByText('Expand')).toBeInTheDocument();
    });

    it('shows templates when expanded', () => {
      render(<MultiStageGrowth {...defaultProps} />);
      fireEvent.click(screen.getByText('Expand'));
      expect(screen.getByText('High Growth Tech')).toBeInTheDocument();
      expect(screen.getByText('Stable Company')).toBeInTheDocument();
      expect(screen.getByText('Turnaround')).toBeInTheDocument();
    });

    it('applies High Growth Tech template with economics', () => {
      render(<MultiStageGrowth {...defaultProps} />);
      fireEvent.click(screen.getByText('Expand'));
      fireEvent.click(screen.getByText('High Growth Tech'));
      
      expect(mockOnChange).toHaveBeenCalledTimes(1);
      const stages = mockOnChange.mock.calls[0][0];
      expect(stages.length).toBe(4);
      
      // Verify first stage has economics
      expect(stages[0].name).toBe('Hypergrowth');
      expect(stages[0].operating_margin).toBe(0.10);
      expect(stages[0].capex_ratio).toBe(0.15);
      expect(stages[0].wc_ratio).toBe(0.20);
    });

    it('adds new stage with default values', () => {
      render(<MultiStageGrowth {...defaultProps} />);
      fireEvent.click(screen.getByText('Expand'));
      fireEvent.click(screen.getByText('+ Add Stage'));
      
      expect(mockOnChange).toHaveBeenCalledWith([
        { name: 'Stage 1', years: 3, growth_rate: 0.10 },
      ]);
    });
  });

  describe('Economics UI', () => {
    const stagesWithEconomics: GrowthStage[] = [
      { 
        name: 'Growth', 
        years: 3, 
        growth_rate: 0.20,
        operating_margin: 0.15,
        capex_ratio: 0.10,
        wc_ratio: 0.12,
      },
    ];

    it('shows economics toggle button on each stage', () => {
      render(<MultiStageGrowth {...defaultProps} stages={stagesWithEconomics} />);
      expect(screen.getByText(/Econ/)).toBeInTheDocument();
    });

    it('toggles economics panel visibility', () => {
      render(<MultiStageGrowth {...defaultProps} stages={stagesWithEconomics} />);
      
      // Initially collapsed
      expect(screen.queryByText('Op. Margin')).not.toBeInTheDocument();
      
      // Click to expand
      fireEvent.click(screen.getByText(/Econ/));
      expect(screen.getByText('Op. Margin')).toBeInTheDocument();
      expect(screen.getByText('CapEx Ratio')).toBeInTheDocument();
      expect(screen.getByText('WC Ratio')).toBeInTheDocument();
    });

    it('shows economics values in inputs when expanded', () => {
      render(<MultiStageGrowth {...defaultProps} stages={stagesWithEconomics} />);
      fireEvent.click(screen.getByText(/Econ/));
      
      // Find inputs by their values (15%, 10%, 12%)
      const inputs = screen.getAllByRole('spinbutton');
      const values = inputs.map(input => (input as HTMLInputElement).value);
      
      // Should include economics values (15.00, 10.00, 12.00)
      expect(values).toContain('15.00');
      expect(values).toContain('10.00');
      expect(values).toContain('12.00');
    });

    it('updates operating margin when changed', () => {
      render(<MultiStageGrowth {...defaultProps} stages={stagesWithEconomics} />);
      fireEvent.click(screen.getByText(/Econ/));
      
      // Find the first economics input (operating margin start value)
      const inputs = screen.getAllByRole('spinbutton');
      // The margin input should have value "15.00" (15%)
      const marginInput = inputs.find(i => (i as HTMLInputElement).value === '15.00');
      expect(marginInput).toBeTruthy();
      
      fireEvent.change(marginInput!, { target: { value: '20' } });
      
      expect(mockOnChange).toHaveBeenCalled();
      const updatedStages = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
      expect(updatedStages[0].operating_margin).toBe(0.20);
    });

    it('highlights economics button when stage has economics defined', () => {
      render(<MultiStageGrowth {...defaultProps} stages={stagesWithEconomics} />);
      
      const econButton = screen.getByText(/Econ/).closest('button');
      expect(econButton).toHaveClass('bg-blue-50');
    });

    it('shows plain button when no economics defined', () => {
      const stagesNoEcon: GrowthStage[] = [
        { name: 'Simple', years: 3, growth_rate: 0.10 },
      ];
      render(<MultiStageGrowth {...defaultProps} stages={stagesNoEcon} />);
      
      const econButton = screen.getByText(/Econ/).closest('button');
      expect(econButton).not.toHaveClass('bg-blue-50');
    });
  });

  describe('Templates with economics', () => {
    it('Stable Company template includes economics', () => {
      render(<MultiStageGrowth {...defaultProps} />);
      fireEvent.click(screen.getByText('Expand'));
      fireEvent.click(screen.getByText('Stable Company'));
      
      const stages = mockOnChange.mock.calls[0][0];
      expect(stages[0].operating_margin).toBe(0.15);
      expect(stages[0].capex_ratio).toBe(0.05);
    });

    it('Turnaround template has negative margin in recovery phase', () => {
      render(<MultiStageGrowth {...defaultProps} />);
      fireEvent.click(screen.getByText('Expand'));
      fireEvent.click(screen.getByText('Turnaround'));
      
      const stages = mockOnChange.mock.calls[0][0];
      expect(stages[0].name).toBe('Recovery');
      expect(stages[0].operating_margin).toBe(-0.05);
      expect(stages[0].end_operating_margin).toBe(0.02);
    });
  });

  describe('Fading economics', () => {
    it('supports end values for margin fading', () => {
      const fadingStages: GrowthStage[] = [
        { 
          name: 'Expansion', 
          years: 5, 
          growth_rate: 0.15,
          operating_margin: 0.10,
          end_operating_margin: 0.20,
        },
      ];
      render(<MultiStageGrowth {...defaultProps} stages={fadingStages} />);
      fireEvent.click(screen.getByText(/Econ/));
      
      // Should see both start (10%) and end (20%) margin values
      const inputs = screen.getAllByRole('spinbutton');
      const values = inputs.map(i => (i as HTMLInputElement).value);
      expect(values).toContain('10.00');
      expect(values).toContain('20.00');
    });

    it('clears end value when empty string entered', () => {
      const fadingStages: GrowthStage[] = [
        { 
          name: 'Test', 
          years: 3, 
          growth_rate: 0.10,
          capex_ratio: 0.08,
          end_capex_ratio: 0.05,
        },
      ];
      render(<MultiStageGrowth {...defaultProps} stages={fadingStages} />);
      fireEvent.click(screen.getByText(/Econ/));
      
      // Find end_capex_ratio input (value "5.00")
      const inputs = screen.getAllByRole('spinbutton');
      const endCapexInput = inputs.find(i => (i as HTMLInputElement).value === '5.00');
      expect(endCapexInput).toBeTruthy();
      
      fireEvent.change(endCapexInput!, { target: { value: '' } });
      
      const updatedStages = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
      expect(updatedStages[0].end_capex_ratio).toBeNull();
    });
  });

  describe('Growth schedule preview', () => {
    it('shows preview with stages defined', () => {
      const stages: GrowthStage[] = [
        { name: 'High', years: 2, growth_rate: 0.20 },
        { name: 'Fade', years: 3, growth_rate: 0.15, end_growth_rate: 0.05 },
      ];
      render(<MultiStageGrowth {...defaultProps} stages={stages} />);
      
      expect(screen.getByText('Growth schedule preview:')).toBeInTheDocument();
      expect(screen.getByText('Year 1')).toBeInTheDocument();
      expect(screen.getByText('Year 5 + Terminal')).toBeInTheDocument();
    });
  });

  describe('Disabled state', () => {
    it('disables all inputs when disabled prop is true', () => {
      const stages: GrowthStage[] = [
        { name: 'Test', years: 3, growth_rate: 0.10, operating_margin: 0.15 },
      ];
      render(<MultiStageGrowth {...defaultProps} stages={stages} disabled={true} />);
      
      // Expand economics
      fireEvent.click(screen.getByText(/Econ/));
      
      const inputs = screen.getAllByRole('spinbutton');
      inputs.forEach(input => {
        expect(input).toBeDisabled();
      });
    });
  });
});
