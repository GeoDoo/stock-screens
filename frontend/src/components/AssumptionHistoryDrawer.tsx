/**
 * Drawer component showing assumption change history.
 * 
 * Displays audit trail in a commit-log style format:
 * - Grouped by timestamp (like git commits)
 * - Shows what changed (field, old → new)
 * - Includes user notes explaining why
 */
import type { AuditEntry } from '../hooks/useAssumptionTracker';

interface AssumptionHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  symbol: string;
  history: AuditEntry[];
  isLoading: boolean;
}

const FIELD_LABELS: Record<string, string> = {
  revenue_growth: 'Revenue Growth',
  operating_margin: 'Operating Margin',
  terminal_growth: 'Terminal Growth',
  discount_rate: 'Discount Rate',
  projection_years: 'Projection Years',
  market_risk_premium: 'Market Risk Premium',
};

function formatValue(field: string, value: number | null): string {
  if (value === null) return '—';
  
  // Percentage fields
  if (['revenue_growth', 'operating_margin', 'terminal_growth', 'discount_rate', 'market_risk_premium'].includes(field)) {
    return `${(value * 100).toFixed(1)}%`;
  }
  
  // Integer fields
  if (field === 'projection_years') {
    return `${value} years`;
  }
  
  return value.toString();
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatTimestamp(timestamp);
}

export function AssumptionHistoryDrawer({
  isOpen,
  onClose,
  symbol,
  history,
  isLoading,
}: AssumptionHistoryDrawerProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl z-50 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Assumption History
            </h2>
            <p className="text-sm text-gray-500">{symbol}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-full transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-3">📝</div>
              <p>No history yet</p>
              <p className="text-sm mt-1">Run a valuation to start tracking</p>
            </div>
          ) : (
            <div className="space-y-6">
              {history.map((entry, index) => (
                <div key={entry.id} className="relative">
                  {/* Timeline connector */}
                  {index < history.length - 1 && (
                    <div className="absolute left-3 top-8 bottom-0 w-0.5 bg-gray-200" />
                  )}
                  
                  {/* Entry */}
                  <div className="flex gap-4">
                    {/* Timeline dot */}
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                      entry.is_initial 
                        ? 'bg-green-100 text-green-600' 
                        : 'bg-blue-100 text-blue-600'
                    }`}>
                      {entry.is_initial ? (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {/* Header */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          entry.is_initial 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-blue-100 text-blue-700'
                        }`}>
                          {entry.is_initial ? 'Initial' : 'Update'}
                        </span>
                        <span className="text-sm text-gray-500" title={formatTimestamp(entry.timestamp)}>
                          {getRelativeTime(entry.timestamp)}
                        </span>
                      </div>
                      
                      {/* Market Context */}
                      {(entry.price_at_time || entry.intrinsic_value_at_time || entry.pe_ratio_at_time) && (
                        <div className="mb-2 flex flex-wrap gap-2">
                          {entry.price_at_time && (
                            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                              Price: ${entry.price_at_time.toFixed(2)}
                            </span>
                          )}
                          {entry.intrinsic_value_at_time && (
                            <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded">
                              Fair Value: ${entry.intrinsic_value_at_time.toFixed(2)}
                            </span>
                          )}
                          {entry.pe_ratio_at_time && (
                            <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                              P/E: {entry.pe_ratio_at_time.toFixed(1)}x
                            </span>
                          )}
                          {entry.price_at_time && entry.intrinsic_value_at_time && (
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              entry.intrinsic_value_at_time > entry.price_at_time 
                                ? 'bg-green-50 text-green-700' 
                                : 'bg-red-50 text-red-700'
                            }`}>
                              {entry.intrinsic_value_at_time > entry.price_at_time ? '▲' : '▼'} 
                              {Math.abs(((entry.intrinsic_value_at_time - entry.price_at_time) / entry.price_at_time) * 100).toFixed(0)}% 
                              {entry.intrinsic_value_at_time > entry.price_at_time ? 'undervalued' : 'overvalued'}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Note */}
                      {entry.note && (
                        <p className="text-sm text-gray-700 mb-2 italic">
                          "{entry.note}"
                        </p>
                      )}
                      
                      {/* Changes */}
                      <div className="space-y-1">
                        {entry.changes.map((change, i) => (
                          <div key={i} className="text-sm flex items-center gap-2">
                            <span className="font-medium text-gray-700">
                              {FIELD_LABELS[change.field] || change.field}
                            </span>
                            <span className="text-gray-400">:</span>
                            {change.old_value !== null && (
                              <>
                                <span className="text-red-600 line-through">
                                  {formatValue(change.field, change.old_value)}
                                </span>
                                <span className="text-gray-400">→</span>
                              </>
                            )}
                            <span className="text-green-600 font-medium">
                              {formatValue(change.field, change.new_value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <p className="text-xs text-gray-500 text-center">
            {history.length} {history.length === 1 ? 'entry' : 'entries'} recorded
          </p>
        </div>
      </div>
    </>
  );
}
