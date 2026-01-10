import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VolumeSignals } from './VolumeSignals';
import type { TechnicalAnalysisResult } from '../types';

const mockTechnicalResult: Partial<TechnicalAnalysisResult> = {
  signals: {
    trend: 'bullish',
    rsi: 'neutral',
    macd: 'bullish',
    mfi_signal: 'overbought',
    obv_trend: 'accumulation',
  },
  indicators: {
    sma_20: [],
    sma_50: [],
    ema_12: [],
    ema_26: [],
    rsi_14: [],
    macd: [],
    mfi_14: [
      { timestamp: '2026-01-10', value: 75 },
      { timestamp: '2026-01-09', value: 72 },
    ],
    obv: [
      { timestamp: '2026-01-10', value: 1500000 },
      { timestamp: '2026-01-09', value: 1400000 },
    ],
    vwma_20: [
      { timestamp: '2026-01-10', value: 150.5 },
      { timestamp: '2026-01-09', value: 149.2 },
    ],
  },
};

describe('VolumeSignals', () => {
  it('renders MFI signal with correct styling for overbought', () => {
    render(<VolumeSignals technicalResult={mockTechnicalResult as TechnicalAnalysisResult} />);
    
    const mfiLabel = screen.getByText('MFI');
    expect(mfiLabel).toBeInTheDocument();
    
    const mfiValue = screen.getByText('overbought');
    expect(mfiValue).toBeInTheDocument();
    expect(mfiValue.className).toContain('text-red');
  });

  it('renders OBV trend with correct styling for accumulation', () => {
    render(<VolumeSignals technicalResult={mockTechnicalResult as TechnicalAnalysisResult} />);
    
    const obvLabel = screen.getByText('OBV Trend');
    expect(obvLabel).toBeInTheDocument();
    
    const obvValue = screen.getByText('accumulation');
    expect(obvValue).toBeInTheDocument();
    expect(obvValue.className).toContain('text-emerald');
  });

  it('renders oversold MFI with green styling', () => {
    const oversoldResult = {
      ...mockTechnicalResult,
      signals: {
        ...mockTechnicalResult.signals!,
        mfi_signal: 'oversold' as const,
      },
    };
    
    render(<VolumeSignals technicalResult={oversoldResult as TechnicalAnalysisResult} />);
    
    const mfiValue = screen.getByText('oversold');
    expect(mfiValue.className).toContain('text-emerald');
  });

  it('renders distribution OBV trend with red styling', () => {
    const distributionResult = {
      ...mockTechnicalResult,
      signals: {
        ...mockTechnicalResult.signals!,
        obv_trend: 'distribution' as const,
      },
    };
    
    render(<VolumeSignals technicalResult={distributionResult as TechnicalAnalysisResult} />);
    
    const obvValue = screen.getByText('distribution');
    expect(obvValue.className).toContain('text-red');
  });

  it('renders neutral signals with gray styling', () => {
    const neutralResult = {
      ...mockTechnicalResult,
      signals: {
        ...mockTechnicalResult.signals!,
        mfi_signal: 'neutral' as const,
        obv_trend: 'neutral' as const,
      },
    };
    
    render(<VolumeSignals technicalResult={neutralResult as TechnicalAnalysisResult} />);
    
    // Both MFI and OBV show "neutral" - check that all neutral values have gray styling
    const neutralValues = screen.getAllByText('neutral');
    expect(neutralValues.length).toBe(2);
    neutralValues.forEach(el => {
      expect(el.className).toContain('text-gray');
    });
  });

  it('shows current MFI value when available', () => {
    render(<VolumeSignals technicalResult={mockTechnicalResult as TechnicalAnalysisResult} />);
    
    // Should show the latest MFI value
    expect(screen.getByText(/75/)).toBeInTheDocument();
  });

  it('handles missing MFI signal gracefully', () => {
    const noMfiResult = {
      ...mockTechnicalResult,
      signals: {
        trend: 'bullish' as const,
        rsi: 'neutral' as const,
        macd: 'bullish' as const,
        // No mfi or obv_trend
      },
    };
    
    render(<VolumeSignals technicalResult={noMfiResult as TechnicalAnalysisResult} />);
    
    // Should show dashes for missing data
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('handles missing indicator data gracefully', () => {
    const noIndicatorDataResult = {
      ...mockTechnicalResult,
      indicators: {
        sma_20: [],
        sma_50: [],
        ema_12: [],
        ema_26: [],
        rsi_14: [],
        macd: [],
        // No mfi_14, obv, or vwma_20
      },
    };
    
    const { container } = render(
      <VolumeSignals technicalResult={noIndicatorDataResult as TechnicalAnalysisResult} />
    );
    
    // Should still render without crashing
    expect(container).toBeTruthy();
  });
});
