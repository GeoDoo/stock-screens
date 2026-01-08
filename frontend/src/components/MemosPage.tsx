import { useState, useEffect } from 'react';
import type { InvestmentMemo, MemoStatus } from '../types';

interface MemosPageProps {
  onSelectMemo: (memo: InvestmentMemo) => void;
  onClose: () => void;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const STATUS_LABELS: Record<MemoStatus, string> = {
  active: 'Active',
  closed_win: 'Win',
  closed_loss: 'Loss',
  closed_neutral: 'Closed',
};

const STATUS_COLORS: Record<MemoStatus, string> = {
  active: 'bg-blue-100 text-blue-700',
  closed_win: 'bg-emerald-100 text-emerald-700',
  closed_loss: 'bg-red-100 text-red-700',
  closed_neutral: 'bg-gray-100 text-gray-700',
};

const CONVICTION_COLORS = {
  low: 'bg-gray-200 text-gray-700',
  medium: 'bg-amber-200 text-amber-800',
  high: 'bg-emerald-200 text-emerald-800',
};

export function MemosPage({ onSelectMemo, onClose }: MemosPageProps) {
  const [memos, setMemos] = useState<InvestmentMemo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<MemoStatus | 'all'>('all');

  useEffect(() => {
    fetchMemos();
  }, [filter]);

  const fetchMemos = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = filter === 'all' 
        ? `${API_BASE}/api/memos`
        : `${API_BASE}/api/memos?status=${filter}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch memos');
      const data = await res.json();
      setMemos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load memos');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getThesisProgress = (memo: InvestmentMemo) => {
    const realized = memo.current_performance.thesis_realized_percent;
    if (realized >= 100) return { label: 'Target Reached', color: 'text-emerald-600' };
    if (realized >= 50) return { label: 'On Track', color: 'text-blue-600' };
    if (realized >= 0) return { label: 'In Progress', color: 'text-amber-600' };
    return { label: 'Underwater', color: 'text-red-600' };
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 text-white px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">Investment Memos</h2>
              <p className="text-slate-300 text-sm mt-1">
                Track your thesis evolution and performance
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-slate-300 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Filters */}
          <div className="flex gap-2 mt-4">
            {(['all', 'active', 'closed_win', 'closed_loss', 'closed_neutral'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                  filter === status
                    ? 'bg-white text-slate-800'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {status === 'all' ? 'All' : STATUS_LABELS[status]}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
            </div>
          ) : error ? (
            <div className="bg-red-50 text-red-600 px-4 py-3 rounded-xl text-center">
              {error}
            </div>
          ) : memos.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">📝</div>
              <h3 className="text-xl font-semibold text-gray-700 mb-2">No memos yet</h3>
              <p className="text-gray-500">
                Create your first investment memo after running an analysis
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {memos.map((memo) => {
                const progress = getThesisProgress(memo);
                return (
                  <button
                    key={memo.id}
                    onClick={() => onSelectMemo(memo)}
                    className="w-full text-left bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition-all group"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        {/* Title & Symbol */}
                        <div className="flex items-center gap-3 mb-2">
                          <span className="font-mono text-lg font-bold text-blue-600">
                            {memo.symbol}
                          </span>
                          <span className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                            {memo.title}
                          </span>
                        </div>

                        {/* Badges */}
                        <div className="flex items-center gap-2 mb-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[memo.status]}`}>
                            {STATUS_LABELS[memo.status]}
                          </span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CONVICTION_COLORS[memo.conviction]}`}>
                            {memo.conviction.charAt(0).toUpperCase() + memo.conviction.slice(1)} Conviction
                          </span>
                          <span className="text-xs text-gray-400">
                            {formatDate(memo.created_at)}
                          </span>
                        </div>

                        {/* Thesis Preview */}
                        <p className="text-sm text-gray-600 line-clamp-2">
                          {memo.thesis}
                        </p>
                      </div>

                      {/* Performance */}
                      <div className="ml-6 text-right">
                        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Performance</div>
                        <div className={`font-mono font-bold text-lg ${
                          memo.current_performance.price_change_percent >= 0 
                            ? 'text-emerald-600' 
                            : 'text-red-600'
                        }`}>
                          {memo.current_performance.price_change_percent >= 0 ? '+' : ''}
                          {memo.current_performance.price_change_percent.toFixed(1)}%
                        </div>
                        <div className={`text-xs font-medium ${progress.color}`}>
                          {progress.label}
                        </div>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-4">
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                        <span>Thesis Progress</span>
                        <span>{Math.min(100, Math.max(0, memo.current_performance.thesis_realized_percent)).toFixed(0)}%</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            memo.current_performance.thesis_realized_percent >= 100
                              ? 'bg-emerald-500'
                              : memo.current_performance.thesis_realized_percent >= 0
                              ? 'bg-blue-500'
                              : 'bg-red-500'
                          }`}
                          style={{ 
                            width: `${Math.min(100, Math.max(0, memo.current_performance.thesis_realized_percent))}%` 
                          }}
                        />
                      </div>
                    </div>

                    {/* Post-mortems indicator */}
                    {memo.post_mortems.length > 0 && (
                      <div className="mt-3 flex items-center gap-1 text-xs text-gray-500">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        {memo.post_mortems.length} post-mortem{memo.post_mortems.length > 1 ? 's' : ''}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
