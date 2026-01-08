/**
 * Inline indicator showing a field has change history.
 * 
 * Shows 🕐 icon that, on hover, displays:
 * - Number of changes
 * - Most recent change summary
 * - Click to open full history
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
    return `${value} years`;
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
        className="text-gray-400 hover:text-blue-600 transition-colors p-1 rounded hover:bg-blue-50"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={onShowHistory}
        aria-label={`View ${changeCount} change${changeCount !== 1 ? 's' : ''} to ${fieldLabel}`}
      >
        <span className="text-sm">🕐</span>
        {changeCount > 1 && (
          <span className="absolute -top-1 -right-1 bg-blue-600 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
            {changeCount}
          </span>
        )}
      </button>
      
      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-lg">
          <div className="font-medium mb-1">
            {changeCount} change{changeCount !== 1 ? 's' : ''}
          </div>
          <div className="text-gray-300">
            Latest: {formatValue(field, latestChange.old_value)} → {formatValue(field, latestChange.new_value)}
          </div>
          <div className="text-gray-400 mt-1">
            Click to view history
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  );
}
