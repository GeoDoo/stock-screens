/**
 * Volume-weighted technical signals display
 * 
 * Shows MFI (Money Flow Index) and OBV (On-Balance Volume) trend signals.
 * These are institutional-grade volume indicators that help confirm price trends.
 */
import type { TechnicalAnalysisResult } from '../types';
import { GlossaryRef } from './GlossaryRef';

interface VolumeSignalsProps {
  technicalResult: TechnicalAnalysisResult;
}

export function VolumeSignals({ technicalResult }: VolumeSignalsProps) {
  const { signals, indicators } = technicalResult;
  
  // Get current MFI value (latest data point - first in array)
  const currentMfi = indicators.mfi_14?.length
    ? indicators.mfi_14[0]?.value
    : null;
    
  // Get current OBV value (latest data point - first in array)
  const currentObv = indicators.obv?.length
    ? indicators.obv[0]?.value
    : null;

  const getMfiColor = (signal: string | undefined): string => {
    if (signal === 'overbought') return 'text-red-600';
    if (signal === 'oversold') return 'text-emerald-600';
    return 'text-gray-400';
  };

  const getObvColor = (trend: string | undefined): string => {
    if (trend === 'accumulation') return 'text-emerald-600';
    if (trend === 'distribution') return 'text-red-600';
    return 'text-gray-400';
  };

  const formatObv = (value: number | null): string => {
    if (value === null) return '—';
    const absValue = Math.abs(value);
    if (absValue >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
    if (absValue >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
    if (absValue >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
    return value.toFixed(0);
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* MFI Signal */}
      <div className="p-4 rounded-lg border border-gray-100">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
          MFI
          <GlossaryRef id="mfi" />
        </div>
        <div className={`text-lg font-medium capitalize ${getMfiColor(signals.mfi_signal)}`}>
          {signals.mfi_signal || '—'}
        </div>
        {currentMfi !== null && (
          <div className="text-xs text-gray-400 mt-1">
            Value: {currentMfi.toFixed(0)}
          </div>
        )}
      </div>

      {/* OBV Trend */}
      <div className="p-4 rounded-lg border border-gray-100">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
          OBV Trend
          <GlossaryRef id="obv" />
        </div>
        <div className={`text-lg font-medium capitalize ${getObvColor(signals.obv_trend)}`}>
          {signals.obv_trend || '—'}
        </div>
        {currentObv !== null && (
          <div className="text-xs text-gray-400 mt-1">
            OBV: {formatObv(currentObv)}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * MFI Interpretation helper
 */
export function getMfiInterpretation(signal: string | undefined, value: number | null): string {
  if (!signal || signal === 'neutral') {
    if (value !== null) {
      if (value > 70) return 'Approaching overbought (>80)';
      if (value < 30) return 'Approaching oversold (<20)';
      return 'Normal money flow';
    }
    return 'Insufficient data';
  }
  
  if (signal === 'overbought') {
    return 'High buying pressure - potential reversal';
  }
  
  if (signal === 'oversold') {
    return 'High selling pressure - potential bounce';
  }
  
  return '';
}

/**
 * OBV Interpretation helper
 */
export function getObvInterpretation(trend: string | undefined): string {
  if (!trend || trend === 'neutral') {
    return 'No clear volume direction';
  }
  
  if (trend === 'accumulation') {
    return 'Smart money buying - bullish signal';
  }
  
  if (trend === 'distribution') {
    return 'Smart money selling - bearish signal';
  }
  
  return '';
}
