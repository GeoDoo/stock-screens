import { useState, useEffect } from 'react';
import type { InvestmentMemo } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface MemosPageProps {
  onSelectMemo: (memo: InvestmentMemo) => void;
  onClose: () => void;
}

export function MemosPage({ onSelectMemo, onClose }: MemosPageProps) {
  const [memos, setMemos] = useState<InvestmentMemo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all');

  useEffect(() => {
    const fetchMemos = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/memos`);
        if (!response.ok) throw new Error('Failed to fetch memos');
        const data = await response.json();
        setMemos(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading memos');
      } finally {
        setLoading(false);
      }
    };
    fetchMemos();
  }, []);

  const filteredMemos = memos.filter(memo => {
    if (filter === 'open') return memo.status === 'open';
    if (filter === 'closed') return memo.status === 'closed';
    return true;
  });

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-white z-50 flex items-center justify-center">
        <p className="text-gray-400">Loading memos...</p>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-white z-50 overflow-auto">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-lg font-medium text-gray-900">Investment Memos</h1>
          <button
            onClick={onClose}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Back
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 text-red-600 text-sm">{error}</div>
        )}

        {/* Filters */}
        <div className="flex gap-4 mb-6 border-b border-gray-200">
          {(['all', 'open', 'closed'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`pb-2 text-sm transition-colors ${
                filter === f
                  ? 'text-gray-900 border-b-2 border-gray-900'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Empty State */}
        {filteredMemos.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-400">No memos yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Run a valuation and click "Create Memo" to save an investment thesis
            </p>
          </div>
        )}

        {/* Memos List */}
        <div className="space-y-3">
          {filteredMemos.map((memo) => (
            <button
              key={memo.id}
              onClick={() => onSelectMemo(memo)}
              className="w-full text-left bg-white border border-gray-200 rounded p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-gray-500">{memo.symbol}</span>
                    <span className="text-gray-300">·</span>
                    <span className="text-sm font-medium text-gray-900 truncate">{memo.title}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">{memo.thesis}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                    <span>{formatDate(memo.created_at)}</span>
                    <span className="text-gray-300">·</span>
                    <span>{memo.conviction} conviction</span>
                    <span className="text-gray-300">·</span>
                    <span>{memo.time_horizon_months}mo horizon</span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  {memo.current_performance && (
                    <>
                      <div className={`font-mono text-sm ${
                        memo.current_performance.return_percent >= 0 
                          ? 'text-emerald-600' 
                          : 'text-red-600'
                      }`}>
                        {memo.current_performance.return_percent >= 0 ? '+' : ''}
                        {memo.current_performance.return_percent.toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">
                        ${memo.current_performance.current_price?.toFixed(2) || '—'}
                      </div>
                    </>
                  )}
                  <div className="mt-2">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      memo.status === 'open' 
                        ? 'bg-gray-100 text-gray-600' 
                        : 'bg-gray-50 text-gray-400'
                    }`}>
                      {memo.status}
                    </span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
