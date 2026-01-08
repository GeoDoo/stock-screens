import { useState, useEffect } from 'react';
import type { InvestmentMemo } from '../types';
import { Layout } from './Layout';

import { API_BASE } from '../config';

export function MemosPage() {
  const [memos, setMemos] = useState<InvestmentMemo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'closed'>('all');

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
    if (filter === 'active') return memo.status === 'active';
    if (filter === 'closed') return memo.status !== 'active';
    return true;
  });

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Investment Memos</h1>
        <p className="text-sm text-gray-400 mt-1">Track your investment theses and outcomes</p>
      </div>

      {/* Filters */}
      <div className="flex gap-6 mb-8 border-b border-gray-200">
        {(['all', 'active', 'closed'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`pb-3 text-sm transition-colors ${
              filter === f
                ? 'text-gray-900 border-b-2 border-gray-900 -mb-px'
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f === 'all' && memos.length > 0 && (
              <span className="ml-1.5 text-gray-400">({memos.length})</span>
            )}
          </button>
        ))}
      </div>
      
      {/* Content */}
      {loading ? (
        <p className="text-gray-400 py-12 text-center">Loading...</p>
      ) : error ? (
        <p className="text-red-600 text-sm">{error}</p>
      ) : filteredMemos.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-400 text-lg">No memos yet</p>
          <p className="text-sm text-gray-400 mt-2">
            Run a valuation and click "Create Memo" to save your thesis
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredMemos.map((memo) => (
            <a
              key={memo.id}
              href={`/memos/${memo.id}`}
              className="block border border-gray-200 rounded-lg p-5 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs text-gray-400">{memo.symbol}</span>
                    <span className="text-gray-200">·</span>
                    <span className="font-medium text-gray-900">{memo.title}</span>
                  </div>
                  <p className="text-sm text-gray-500 line-clamp-2">{memo.thesis}</p>
                  <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
                    <span>{formatDate(memo.created_at)}</span>
                    <span>·</span>
                    <span>{memo.conviction} conviction</span>
                    <span>·</span>
                    <span>{memo.time_horizon_months}mo horizon</span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  {memo.current_performance && (
                    <div className={`font-mono text-lg ${
                      memo.current_performance.price_change_percent >= 0 
                        ? 'text-emerald-600' 
                        : 'text-red-600'
                    }`}>
                      {memo.current_performance.price_change_percent >= 0 ? '+' : ''}
                      {memo.current_performance.price_change_percent.toFixed(1)}%
                    </div>
                  )}
                  <span className={`text-xs px-2 py-0.5 rounded mt-1 inline-block ${
                    memo.status === 'active' 
                      ? 'bg-emerald-50 text-emerald-600' 
                      : 'bg-gray-100 text-gray-500'
                  }`}>
                    {memo.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </Layout>
  );
}
