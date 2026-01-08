/**
 * Inline indicator showing a field has change history.
 */
import { useState } from 'react';
import type { AssumptionChange } from '../hooks/useAssumptionTracker';

interface AssumptionHistoryIndicatorProps {
  field: string;
  fieldLabel: string;
  changes: AssumptionChange[];
  onShowHistory: () => void;
}

function formatValue(field: string, value: number | null): string {
  if (value === null) return '—';
  
  if (['revenue_growth', 'operating_margin', 'terminal_growth', 'discount_rate', 'market_risk_premium'].includes(field)) {
    return `${(value * 100).toFixed(1)}%`;
  }
  
  if (field === 'projection_years') {
    return `${value}y`;
  }
  
  return value.toString();
}

export function AssumptionHistoryIndicator({
  field,
  fieldLabel,
  changes,
  onShowHistory,
}: AssumptionHistoryIndicatorProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  
  if (changes.length === 0) return null;
  
  const latestChange = changes[0];
  const changeCount = changes.length;
  
  return (
    <div className="relative inline-block ml-2">
      <button
        className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={onShowHistory}
        aria-label={`View ${changeCount} change${changeCount !== 1 ? 's' : ''} to ${fieldLabel}`}
      >
        {changeCount}×
      </button>
      
      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-40 bg-gray-900 text-white text-xs rounded p-2 shadow-lg">
          <div className="mb-1">
            {changeCount} change{changeCount !== 1 ? 's' : ''}
          </div>
          <div className="text-gray-400 font-mono">
            {formatValue(field, latestChange.old_value)} → {formatValue(field, latestChange.new_value)}
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  );
}
