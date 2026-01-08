import { useState, useEffect } from 'react';
import type { InvestmentMemo, PostMortemAction } from '../types';
import { Layout } from './Layout';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface MemoDetailPageProps {
  memoId: number;
}

export function MemoDetailPage({ memoId }: MemoDetailPageProps) {
  const [memo, setMemo] = useState<InvestmentMemo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPostMortem, setShowPostMortem] = useState(false);
  const [postMortemContent, setPostMortemContent] = useState('');
  const [postMortemAction, setPostMortemAction] = useState<PostMortemAction>('hold');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchMemo = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/memos/${memoId}`);
        if (!response.ok) throw new Error('Memo not found');
        const data = await response.json();
        setMemo(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading memo');
      } finally {
        setLoading(false);
      }
    };
    fetchMemo();
  }, [memoId]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${(value * 100).toFixed(1)}%`;
  };

  const handleAddPostMortem = async () => {
    if (!postMortemContent.trim() || !memo) return;

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/memos/${memo.id}/post-mortems`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          note: postMortemContent.trim(),
          action: postMortemAction,
          price_at_time: memo.current_performance?.latest_price || memo.initial_market.price,
          iv_at_time: memo.current_performance?.latest_iv || memo.initial_market.intrinsic_value,
        }),
      });

      if (!response.ok) throw new Error('Failed to add note');

      const refreshResponse = await fetch(`${API_BASE}/api/memos/${memoId}`);
      if (refreshResponse.ok) {
        setMemo(await refreshResponse.json());
      }
      setPostMortemContent('');
      setShowPostMortem(false);
    } catch (err) {
      console.error('Failed to add post-mortem:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCloseMemo = async () => {
    const reason = prompt('Why are you closing this memo?');
    if (!reason || !memo) return;

    try {
      const response = await fetch(`${API_BASE}/api/memos/${memo.id}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });

      if (!response.ok) throw new Error('Failed to close memo');

      const refreshResponse = await fetch(`${API_BASE}/api/memos/${memoId}`);
      if (refreshResponse.ok) {
        setMemo(await refreshResponse.json());
      }
    } catch (err) {
      console.error('Failed to close memo:', err);
    }
  };

  if (loading) {
    return (
      <Layout>
        <p className="text-gray-400 py-12 text-center">Loading...</p>
      </Layout>
    );
  }

  if (error || !memo) {
    return (
      <Layout>
        <p className="text-red-600">{error || 'Memo not found'}</p>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-sm text-gray-400">{memo.symbol}</span>
            <span className="text-gray-200">·</span>
            <h1 className="text-2xl font-semibold text-gray-900">{memo.title}</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-400">
            <span>{formatDate(memo.created_at)}</span>
            <span>·</span>
            <span>{memo.conviction} conviction</span>
            <span>·</span>
            <span>{memo.time_horizon_months}mo horizon</span>
            {memo.status !== 'active' && (
              <>
                <span>·</span>
                <span className="text-gray-500">{memo.status.replace('_', ' ')}</span>
              </>
            )}
          </div>
        </div>
        {memo.status === 'active' && (
          <button
            onClick={handleCloseMemo}
            className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            Close Memo
          </button>
        )}
      </div>

      {/* Thesis */}
      <p className="text-gray-700 leading-relaxed mb-8">{memo.thesis}</p>

      {/* Performance */}
      {memo.current_performance && (
        <div className="mb-8 grid grid-cols-4 gap-6 p-5 border border-gray-200 rounded-lg">
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Entry</div>
            <div className="font-mono text-lg">${memo.initial_market.price.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Current</div>
            <div className="font-mono text-lg">
              ${memo.current_performance.latest_price?.toFixed(2) || '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Return</div>
            <div className={`font-mono text-lg ${
              memo.current_performance.price_change_percent >= 0 ? 'text-emerald-600' : 'text-red-600'
            }`}>
              {memo.current_performance.price_change_percent >= 0 ? '+' : ''}
              {memo.current_performance.price_change_percent.toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Target</div>
            <div className="font-mono text-lg">
              {memo.target_price ? `$${memo.target_price.toFixed(2)}` : '—'}
            </div>
          </div>
        </div>
      )}

      {/* Assumptions */}
      <div className="mb-8 p-5 border border-gray-200 rounded-lg">
        <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Assumptions at Creation</h2>
        <div className="grid grid-cols-5 gap-4 text-center">
          <div>
            <div className="text-xs text-gray-400">Revenue Growth</div>
            <div className="font-mono mt-1">{formatPercent(memo.assumptions.revenue_growth)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400">Op. Margin</div>
            <div className="font-mono mt-1">{formatPercent(memo.assumptions.operating_margin)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400">Terminal Growth</div>
            <div className="font-mono mt-1">{formatPercent(memo.assumptions.terminal_growth_rate)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400">Discount Rate</div>
            <div className="font-mono mt-1">{formatPercent(memo.assumptions.discount_rate)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400">Projection</div>
            <div className="font-mono mt-1">{memo.assumptions.projection_years}y</div>
          </div>
        </div>
      </div>

      {/* Scenarios */}
      {memo.scenarios && memo.scenarios.length > 0 && (
        <div className="mb-8 p-5 border border-gray-200 rounded-lg">
          <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Scenarios</h2>
          <div className="grid grid-cols-3 gap-4">
            {memo.scenarios.map((scenario) => (
              <div key={scenario.name} className="text-center p-4 bg-gray-50 rounded">
                <div className="text-xs text-gray-400 uppercase">{scenario.name}</div>
                <div className="font-mono text-xl mt-2">${scenario.intrinsic_value.toFixed(0)}</div>
                <div className={`text-sm mt-1 ${
                  scenario.upside_percent >= 0 ? 'text-emerald-600' : 'text-red-600'
                }`}>
                  {scenario.upside_percent >= 0 ? '+' : ''}{scenario.upside_percent.toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Details */}
      {(memo.catalysts || memo.risks || memo.what_would_change_mind) && (
        <div className="mb-8 p-5 border border-gray-200 rounded-lg space-y-4">
          {memo.catalysts && (
            <div>
              <h3 className="text-xs text-gray-400 uppercase tracking-wider mb-2">Catalysts</h3>
              <p className="text-sm text-gray-700">{memo.catalysts}</p>
            </div>
          )}
          {memo.risks && (
            <div>
              <h3 className="text-xs text-gray-400 uppercase tracking-wider mb-2">Key Risks</h3>
              <p className="text-sm text-gray-700">{memo.risks}</p>
            </div>
          )}
          {memo.what_would_change_mind && (
            <div>
              <h3 className="text-xs text-gray-400 uppercase tracking-wider mb-2">Exit Criteria</h3>
              <p className="text-sm text-gray-700">{memo.what_would_change_mind}</p>
            </div>
          )}
        </div>
      )}

      {/* Timeline */}
      <div className="p-5 border border-gray-200 rounded-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs text-gray-400 uppercase tracking-wider">Timeline</h2>
          {memo.status === 'active' && (
            <button
              onClick={() => setShowPostMortem(!showPostMortem)}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              {showPostMortem ? 'Cancel' : 'Add Note'}
            </button>
          )}
        </div>

        {showPostMortem && (
          <div className="mb-6 space-y-3">
            <textarea
              value={postMortemContent}
              onChange={(e) => setPostMortemContent(e.target.value)}
              placeholder="What happened? What did you learn?"
              rows={3}
              className="w-full px-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none text-sm resize-none"
            />
            <div className="flex items-center justify-between">
              <div className="flex gap-1">
                {(['hold', 'add', 'trim', 'close', 'review'] as PostMortemAction[]).map((action) => (
                  <button
                    key={action}
                    onClick={() => setPostMortemAction(action)}
                    className={`px-3 py-1 text-xs rounded transition-colors ${
                      postMortemAction === action
                        ? 'bg-gray-900 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {action.charAt(0).toUpperCase() + action.slice(1)}
                  </button>
                ))}
              </div>
              <button
                onClick={handleAddPostMortem}
                disabled={saving || !postMortemContent.trim()}
                className="px-3 py-1 text-sm bg-gray-900 text-white rounded hover:bg-gray-800 transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="w-24 flex-shrink-0 text-xs text-gray-400 pt-0.5">
              {formatDate(memo.created_at)}
            </div>
            <div className="flex-1 border-l border-gray-100 pl-4 pb-4">
              <div className="text-sm text-gray-600">
                Created memo at ${memo.initial_market.price.toFixed(2)}
              </div>
            </div>
          </div>

          {memo.post_mortems?.map((pm) => (
            <div key={pm.id} className="flex gap-4">
              <div className="w-24 flex-shrink-0 text-xs text-gray-400 pt-0.5">
                {formatDate(pm.created_at)}
              </div>
              <div className="flex-1 border-l border-gray-100 pl-4 pb-4">
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                  {pm.action}
                </div>
                <p className="text-sm text-gray-700">{pm.note}</p>
                {pm.price_at_time && (
                  <div className="text-xs text-gray-400 mt-2">
                    Price: ${pm.price_at_time.toFixed(2)}
                  </div>
                )}
              </div>
            </div>
          ))}

          {memo.status !== 'active' && memo.closed_at && (
            <div className="flex gap-4">
              <div className="w-24 flex-shrink-0 text-xs text-gray-400 pt-0.5">
                {formatDate(memo.closed_at)}
              </div>
              <div className="flex-1 border-l border-gray-100 pl-4">
                <div className="text-sm text-gray-600">
                  Closed: {memo.closed_reason || 'No reason provided'}
                </div>
              </div>
            </div>
          )}

          {(!memo.post_mortems || memo.post_mortems.length === 0) && memo.status === 'active' && (
            <div className="text-center py-4 text-sm text-gray-400">
              No updates yet
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
