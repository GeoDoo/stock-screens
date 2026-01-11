import { GlossaryRef } from './GlossaryRef';

interface CEOEfficiencyWarningProps {
  incrementalRoic: number | null | undefined;
  wacc: number | null | undefined;
}

/**
 * CEO Efficiency Warning (Alpha Layer)
 * 
 * Compares Incremental ROIC to WACC to determine if management
 * is creating or destroying value with new investments.
 * 
 * - Value Creator: Inc. ROIC > WACC (every new $ invested earns above cost)
 * - Value Neutral: Inc. ROIC ≈ WACC (breaking even on new investments)
 * - Value Destroyer: Inc. ROIC < WACC (burning capital with growth)
 */
export function CEOEfficiencyWarning({ incrementalRoic, wacc }: CEOEfficiencyWarningProps) {
  // Need both values to assess
  if (incrementalRoic == null || wacc == null) {
    return null;
  }
  
  const spread = incrementalRoic - wacc;
  const spreadPct = (spread * 100).toFixed(1);
  
  // Determine status
  let statusLabel: string;
  let statusColor: string;
  let bgColor: string;
  let borderColor: string;
  let description: string;
  
  if (spread > 0.02) {
    // Inc. ROIC > WACC + 2%: Value Creator
    statusLabel = 'VALUE CREATOR';
    statusColor = 'text-emerald-700';
    bgColor = 'bg-emerald-50';
    borderColor = 'border-emerald-200';
    description = 'Management earns above cost of capital on new investments';
  } else if (spread < -0.02) {
    // Inc. ROIC < WACC - 2%: Value Destroyer
    statusLabel = 'VALUE DESTROYER';
    statusColor = 'text-red-700';
    bgColor = 'bg-red-50';
    borderColor = 'border-red-200';
    description = 'Growth is destroying value — each new $ invested loses money';
  } else {
    // Within ±2%: Neutral
    statusLabel = 'VALUE NEUTRAL';
    statusColor = 'text-amber-700';
    bgColor = 'bg-amber-50';
    borderColor = 'border-amber-200';
    description = 'New investments roughly break even vs cost of capital';
  }
  
  // Flag extreme values that may be distorted
  const isDistorted = Math.abs(incrementalRoic) > 1.0;  // > 100% or < -100%
  
  return (
    <div className={`p-4 rounded-lg border ${borderColor} ${bgColor}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          CEO Efficiency
          <GlossaryRef id="ceo-efficiency" />
        </div>
        <span className={`text-sm font-bold ${statusColor}`}>
          {statusLabel}
        </span>
      </div>
      
      <div className="text-sm text-gray-600 mb-3">
        {description}
      </div>
      
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <div className="text-xs text-gray-400 uppercase">Inc. ROIC</div>
          <div className="font-medium font-mono">
            {(incrementalRoic * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 uppercase">WACC</div>
          <div className="font-medium font-mono">
            {(wacc * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 uppercase">Spread</div>
          <div className={`font-medium font-mono ${spread > 0 ? 'text-emerald-600' : spread < 0 ? 'text-red-600' : ''}`}>
            {spread > 0 ? '+' : ''}{spreadPct}%
          </div>
        </div>
      </div>
      
      {/* Warning for distorted metrics */}
      {isDistorted && (
        <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
          <span className="font-semibold">⚠️ Potentially misleading:</span>{' '}
          Incremental ROIC above 100% often occurs when a company returns massive capital via buybacks, 
          causing invested capital to shrink while profits grow. This mathematically inflates the ratio 
          but doesn't reflect true reinvestment efficiency. Consider alongside other metrics.
        </div>
      )}
    </div>
  );
}
