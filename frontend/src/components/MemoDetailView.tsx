import { useState } from 'react';
import type { InvestmentMemo, MemoPostMortem, PostMortemAction } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface MemoDetailViewProps {
  memo: InvestmentMemo;
  onBack: () => void;
  onUpdate: (updated: InvestmentMemo) => void;
}

export function MemoDetailView({ memo, onBack, onUpdate }: MemoDetailViewProps) {
  const [showPostMortem, setShowPostMortem] = useState(false);
  const [postMortemContent, setPostMortemContent] = useState('');
  const [postMortemAction, setPostMortemAction] = useState<PostMortemAction>('hold');
  const [saving, setSaving] = useState(false);

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
    if (!postMortemContent.trim()) return;

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/memos/${memo.id}/post-mortems`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: postMortemContent.trim(),
          action_taken: postMortemAction,
        }),
      });

      if (!response.ok) throw new Error('Failed to add post-mortem');

      const postMortem: MemoPostMortem = await response.json();
      const updated = {
        ...memo,
        post_mortems: [...(memo.post_mortems || []), postMortem],
      };
      onUpdate(updated);
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
    if (!reason) return;

    try {
      const response = await fetch(`${API_BASE}/api/memos/${memo.id}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });

      if (!response.ok) throw new Error('Failed to close memo');

      const updated = await response.json();
      onUpdate(updated);
    } catch (err) {
      console.error('Failed to close memo:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Back
            </button>
            <span className="text-gray-200">|</span>
            <span className="font-mono text-sm text-gray-500">{memo.symbol}</span>
          </div>
          {memo.status === 'open' && (
            <button
              onClick={handleCloseMemo}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Close Memo
            </button>
          )}
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Title & Thesis */}
        <div>
          <h1 className="text-xl font-medium text-gray-900">{memo.title}</h1>
          <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
            <span>{formatDate(memo.created_at)}</span>
            <span className="text-gray-200">·</span>
            <span>{memo.conviction} conviction</span>
            <span className="text-gray-200">·</span>
            <span>{memo.time_horizon_months}mo horizon</span>
            {memo.status === 'closed' && (
              <>
                <span className="text-gray-200">·</span>
                <span className="text-gray-400">closed</span>
              </>
            )}
          </div>
          <p className="mt-4 text-gray-700 leading-relaxed">{memo.thesis}</p>
        </div>

        {/* Performance */}
        {memo.current_performance && (
          <div className="border border-gray-200 rounded p-5 bg-white">
            <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Performance</h2>
            <div className="grid grid-cols-4 gap-6 text-center">
              <div>
                <div className="text-xs text-gray-400">Entry</div>
                <div className="font-mono mt-1">${memo.initial_market.price.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">Current</div>
                <div className="font-mono mt-1">
                  ${memo.current_performance.current_price?.toFixed(2) || '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400">Return</div>
                <div className={`font-mono mt-1 ${
                  memo.current_performance.return_percent >= 0 ? 'text-gray-900' : 'text-gray-500'
                }`}>
                  {memo.current_performance.return_percent >= 0 ? '+' : ''}
                  {memo.current_performance.return_percent.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400">Target</div>
                <div className="font-mono mt-1">
                  {memo.target_price ? `$${memo.target_price.toFixed(2)}` : '—'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Initial Snapshot */}
        <div className="border border-gray-200 rounded p-5 bg-white">
          <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Assumptions at Creation</h2>
          <div className="grid grid-cols-5 gap-4 text-center text-sm">
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
          <div className="border border-gray-200 rounded p-5 bg-white">
            <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Scenario Analysis</h2>
            <div className="grid grid-cols-3 gap-4">
              {memo.scenarios.map((scenario) => (
                <div key={scenario.name} className="border border-gray-100 rounded p-4 text-center">
                  <div className="text-xs text-gray-400 uppercase">{scenario.name}</div>
                  <div className="font-mono text-lg mt-2">${scenario.intrinsic_value.toFixed(0)}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {scenario.upside_percent >= 0 ? '+' : ''}{scenario.upside_percent.toFixed(0)}% upside
                  </div>
                  <div className="text-xs text-gray-400 mt-2">
                    {formatPercent(scenario.revenue_growth)} rev / {formatPercent(scenario.operating_margin)} margin
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Details */}
        {(memo.catalysts || memo.risks || memo.what_would_change_mind) && (
          <div className="border border-gray-200 rounded p-5 bg-white space-y-4">
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

        {/* Post-Mortems */}
        <div className="border border-gray-200 rounded p-5 bg-white">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs text-gray-400 uppercase tracking-wider">Timeline</h2>
            {memo.status === 'open' && (
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
                  {(['hold', 'add', 'trim', 'exit'] as PostMortemAction[]).map((action) => (
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

          {/* Timeline */}
          <div className="space-y-4">
            {/* Initial entry */}
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

            {/* Post-mortems */}
            {memo.post_mortems?.map((pm) => (
              <div key={pm.id} className="flex gap-4">
                <div className="w-24 flex-shrink-0 text-xs text-gray-400 pt-0.5">
                  {formatDate(pm.timestamp)}
                </div>
                <div className="flex-1 border-l border-gray-100 pl-4 pb-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                    {pm.action_taken}
                  </div>
                  <p className="text-sm text-gray-700">{pm.content}</p>
                  {pm.market_snapshot && (
                    <div className="text-xs text-gray-400 mt-2">
                      Price: ${pm.market_snapshot.price.toFixed(2)}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Closed entry */}
            {memo.status === 'closed' && memo.closed_at && (
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

            {/* Empty state */}
            {(!memo.post_mortems || memo.post_mortems.length === 0) && memo.status === 'open' && (
              <div className="text-center py-4 text-sm text-gray-400">
                No updates yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
