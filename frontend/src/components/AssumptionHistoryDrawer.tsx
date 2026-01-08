/**
 * Drawer component showing assumption change history.
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
  
  if (['revenue_growth', 'operating_margin', 'terminal_growth', 'discount_rate', 'market_risk_premium'].includes(field)) {
    return `${(value * 100).toFixed(1)}%`;
  }
  
  if (field === 'projection_years') {
    return `${value}y`;
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
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-xl z-50 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium text-gray-900">Assumption History</h2>
            <p className="text-sm text-gray-400">{symbol}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <p className="text-gray-400">Loading...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400">No history yet</p>
              <p className="text-sm text-gray-400 mt-1">Run a valuation to start tracking</p>
            </div>
          ) : (
            <div className="space-y-6">
              {history.map((entry, index) => (
                <div key={entry.id} className="relative">
                  {/* Timeline connector */}
                  {index < history.length - 1 && (
                    <div className="absolute left-1.5 top-6 bottom-0 w-px bg-gray-100" />
                  )}
                  
                  {/* Entry */}
                  <div className="flex gap-4">
                    {/* Timeline dot */}
                    <div className="w-3 h-3 rounded-full bg-gray-200 flex-shrink-0 mt-1.5" />
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {/* Header */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs text-gray-400 uppercase tracking-wider">
                          {entry.is_initial ? 'Initial' : 'Update'}
                        </span>
                        <span className="text-gray-200">·</span>
                        <span className="text-xs text-gray-400" title={formatTimestamp(entry.timestamp)}>
                          {getRelativeTime(entry.timestamp)}
                        </span>
                      </div>
                      
                      {/* Market Context */}
                      {(entry.price_at_time || entry.intrinsic_value_at_time || entry.pe_ratio_at_time) && (
                        <div className="mb-2 text-xs text-gray-400 font-mono">
                          {entry.price_at_time && <span className="mr-3">${entry.price_at_time.toFixed(2)}</span>}
                          {entry.intrinsic_value_at_time && (
                            <span className="mr-3">IV: ${entry.intrinsic_value_at_time.toFixed(2)}</span>
                          )}
                          {entry.pe_ratio_at_time && <span>P/E: {entry.pe_ratio_at_time.toFixed(1)}</span>}
                        </div>
                      )}

                      {/* Note */}
                      {entry.note && (
                        <p className="text-sm text-gray-600 mb-2">
                          {entry.note}
                        </p>
                      )}
                      
                      {/* Changes */}
                      <div className="space-y-1">
                        {entry.changes.map((change, i) => (
                          <div key={i} className="text-sm font-mono">
                            <span className="text-gray-500">
                              {FIELD_LABELS[change.field] || change.field}
                            </span>
                            <span className="text-gray-300 mx-2">:</span>
                            {change.old_value !== null && (
                              <>
                                <span className="text-gray-400">
                                  {formatValue(change.field, change.old_value)}
                                </span>
                                <span className="text-gray-300 mx-1">→</span>
                              </>
                            )}
                            <span className="text-gray-900">
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
        <div className="px-6 py-4 border-t border-gray-100">
          <p className="text-xs text-gray-400 text-center">
            {history.length} {history.length === 1 ? 'entry' : 'entries'}
          </p>
        </div>
      </div>
    </>
  );
}
