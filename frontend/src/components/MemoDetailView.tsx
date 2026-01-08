import { useState } from 'react';
import type { InvestmentMemo, PostMortemAction, MemoStatus } from '../types';

interface MemoDetailViewProps {
  memo: InvestmentMemo;
  onClose: () => void;
  onAddPostMortem: (note: string, action: PostMortemAction, price: number, iv: number) => Promise<void>;
  onCloseMemo: (status: MemoStatus, reason: string) => Promise<void>;
  onRefresh: () => void;
}

// API_BASE not needed here - API calls are handled by parent

const ACTION_LABELS: Record<PostMortemAction, string> = {
  hold: '📊 Hold',
  add: '📈 Add',
  trim: '📉 Trim',
  close: '🚪 Close',
  review: '🔍 Review',
};

const ACTION_COLORS: Record<PostMortemAction, string> = {
  hold: 'bg-blue-100 text-blue-700 border-blue-200',
  add: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  trim: 'bg-amber-100 text-amber-700 border-amber-200',
  close: 'bg-red-100 text-red-700 border-red-200',
  review: 'bg-gray-100 text-gray-700 border-gray-200',
};

export function MemoDetailView({ 
  memo, 
  onClose, 
  onAddPostMortem,
  onCloseMemo,
  onRefresh,
}: MemoDetailViewProps) {
  const [showPostMortemForm, setShowPostMortemForm] = useState(false);
  const [showCloseForm, setShowCloseForm] = useState(false);
  const [pmNote, setPmNote] = useState('');
  const [pmAction, setPmAction] = useState<PostMortemAction>('review');
  const [pmPrice, setPmPrice] = useState('');
  const [pmIv, setPmIv] = useState('');
  const [closeStatus, setCloseStatus] = useState<MemoStatus>('closed_neutral');
  const [closeReason, setCloseReason] = useState('');
  const [saving, setSaving] = useState(false);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPercent = (val: number) => {
    return `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`;
  };

  const handleAddPostMortem = async () => {
    if (!pmNote.trim()) return;
    setSaving(true);
    try {
      await onAddPostMortem(
        pmNote.trim(),
        pmAction,
        parseFloat(pmPrice) || memo.current_performance.latest_price,
        parseFloat(pmIv) || memo.current_performance.latest_iv
      );
      setPmNote('');
      setPmPrice('');
      setPmIv('');
      setShowPostMortemForm(false);
      onRefresh();
    } finally {
      setSaving(false);
    }
  };

  const handleCloseMemo = async () => {
    if (!closeReason.trim()) return;
    setSaving(true);
    try {
      await onCloseMemo(closeStatus, closeReason.trim());
      setShowCloseForm(false);
      onRefresh();
    } finally {
      setSaving(false);
    }
  };

  const perf = memo.current_performance;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 text-white px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-2xl font-bold">{memo.symbol}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  memo.status === 'active' ? 'bg-blue-500' :
                  memo.status === 'closed_win' ? 'bg-emerald-500' :
                  memo.status === 'closed_loss' ? 'bg-red-500' :
                  'bg-gray-500'
                }`}>
                  {memo.status === 'active' ? 'Active' :
                   memo.status === 'closed_win' ? 'Win' :
                   memo.status === 'closed_loss' ? 'Loss' : 'Closed'}
                </span>
              </div>
              <h2 className="text-xl font-semibold mt-1">{memo.title}</h2>
              <p className="text-slate-400 text-sm mt-1">
                Created {formatDate(memo.created_at)} • {memo.time_horizon_months} month horizon
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
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Performance Summary */}
          <div className="bg-gradient-to-r from-slate-50 to-gray-50 px-6 py-4 border-b">
            <div className="grid grid-cols-5 gap-4">
              <div className="text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider">Entry Price</div>
                <div className="font-mono font-semibold text-gray-900">${memo.initial_market.price.toFixed(2)}</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider">Current</div>
                <div className="font-mono font-semibold text-gray-900">${perf.latest_price.toFixed(2)}</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider">Price Change</div>
                <div className={`font-mono font-semibold ${perf.price_change_percent >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {formatPercent(perf.price_change_percent)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider">Target</div>
                <div className="font-mono font-semibold text-blue-600">
                  ${memo.target_price?.toFixed(2) || memo.initial_market.intrinsic_value.toFixed(2)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider">Thesis Progress</div>
                <div className={`font-mono font-semibold ${
                  perf.thesis_realized_percent >= 100 ? 'text-emerald-600' :
                  perf.thesis_realized_percent >= 0 ? 'text-blue-600' : 'text-red-600'
                }`}>
                  {perf.thesis_realized_percent.toFixed(0)}%
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 space-y-6">
            {/* Thesis */}
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Thesis</h3>
              <p className="text-gray-800 leading-relaxed">{memo.thesis}</p>
            </div>

            {/* Grid: Catalysts, Risks, Exit Criteria */}
            <div className="grid grid-cols-3 gap-4">
              {memo.catalysts && (
                <div className="bg-emerald-50 rounded-xl p-4">
                  <h4 className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-2">Catalysts</h4>
                  <p className="text-sm text-emerald-900">{memo.catalysts}</p>
                </div>
              )}
              {memo.risks && (
                <div className="bg-red-50 rounded-xl p-4">
                  <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wider mb-2">Risks</h4>
                  <p className="text-sm text-red-900">{memo.risks}</p>
                </div>
              )}
              {memo.what_would_change_mind && (
                <div className="bg-amber-50 rounded-xl p-4">
                  <h4 className="text-xs font-semibold text-amber-700 uppercase tracking-wider mb-2">Exit Criteria</h4>
                  <p className="text-sm text-amber-900">{memo.what_would_change_mind}</p>
                </div>
              )}
            </div>

            {/* Scenarios */}
            {memo.scenarios.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Original Scenarios</h3>
                <div className="grid grid-cols-3 gap-3">
                  {memo.scenarios.map((s) => (
                    <div
                      key={s.name}
                      className={`p-4 rounded-xl text-center ${
                        s.name.toLowerCase() === 'bull' ? 'bg-emerald-50 border border-emerald-200' :
                        s.name.toLowerCase() === 'bear' ? 'bg-red-50 border border-red-200' :
                        'bg-blue-50 border border-blue-200'
                      }`}
                    >
                      <div className="text-xs font-semibold uppercase tracking-wider opacity-75">{s.name}</div>
                      <div className="font-mono font-bold text-xl mt-1">${s.intrinsic_value.toFixed(0)}</div>
                      <div className="text-sm mt-1">
                        {s.upside_percent >= 0 ? '+' : ''}{s.upside_percent.toFixed(0)}% upside
                      </div>
                      <div className="text-xs text-gray-500 mt-2">
                        {(s.revenue_growth * 100).toFixed(0)}% growth • {(s.operating_margin * 100).toFixed(0)}% margin
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Post-Mortem Timeline */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Post-Mortem Timeline</h3>
                {memo.status === 'active' && (
                  <button
                    onClick={() => setShowPostMortemForm(true)}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Add Post-Mortem
                  </button>
                )}
              </div>

              {memo.post_mortems.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-xl">
                  <div className="text-4xl mb-2">📝</div>
                  <p className="text-gray-500">No post-mortems yet</p>
                  {memo.status === 'active' && (
                    <button
                      onClick={() => setShowPostMortemForm(true)}
                      className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Add your first review
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {memo.post_mortems.map((pm, idx) => (
                    <div
                      key={pm.id}
                      className={`relative pl-6 pb-4 ${idx < memo.post_mortems.length - 1 ? 'border-l-2 border-gray-200' : ''}`}
                    >
                      {/* Timeline dot */}
                      <div className="absolute left-0 top-0 -translate-x-1/2 w-3 h-3 rounded-full bg-blue-500 border-2 border-white shadow" />
                      
                      <div className={`rounded-xl p-4 border ${ACTION_COLORS[pm.action]}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">{ACTION_LABELS[pm.action]}</span>
                          <span className="text-xs text-gray-500">{formatDate(pm.created_at)}</span>
                        </div>
                        <p className="text-sm text-gray-800">{pm.note}</p>
                        <div className="flex gap-4 mt-2 text-xs text-gray-500">
                          <span>Price: ${pm.price_at_time.toFixed(2)}</span>
                          <span>IV: ${pm.iv_at_time.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Add Post-Mortem Form */}
            {showPostMortemForm && (
              <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
                <h4 className="font-medium text-blue-900 mb-3">Add Post-Mortem</h4>
                <textarea
                  value={pmNote}
                  onChange={(e) => setPmNote(e.target.value)}
                  placeholder="How is the thesis tracking? What's changed?"
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-blue-200 focus:border-blue-400 outline-none mb-3"
                />
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="text-xs text-gray-600 mb-1 block">Action</label>
                    <select
                      value={pmAction}
                      onChange={(e) => setPmAction(e.target.value as PostMortemAction)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200"
                    >
                      {Object.entries(ACTION_LABELS).map(([val, label]) => (
                        <option key={val} value={val}>{label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 mb-1 block">Current Price</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pmPrice}
                      onChange={(e) => setPmPrice(e.target.value)}
                      placeholder={perf.latest_price.toFixed(2)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 mb-1 block">Current IV</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pmIv}
                      onChange={(e) => setPmIv(e.target.value)}
                      placeholder={perf.latest_iv.toFixed(2)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setShowPostMortemForm(false)}
                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddPostMortem}
                    disabled={saving || !pmNote.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            )}

            {/* Close Memo Form */}
            {showCloseForm && (
              <div className="bg-amber-50 rounded-xl p-4 border border-amber-200">
                <h4 className="font-medium text-amber-900 mb-3">Close Memo</h4>
                <div className="mb-3">
                  <label className="text-xs text-gray-600 mb-1 block">Outcome</label>
                  <div className="flex gap-2">
                    {(['closed_win', 'closed_loss', 'closed_neutral'] as MemoStatus[]).map((status) => (
                      <button
                        key={status}
                        onClick={() => setCloseStatus(status)}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                          closeStatus === status
                            ? status === 'closed_win' ? 'bg-emerald-500 text-white'
                              : status === 'closed_loss' ? 'bg-red-500 text-white'
                              : 'bg-gray-500 text-white'
                            : 'bg-white border text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        {status === 'closed_win' ? '✅ Win' : 
                         status === 'closed_loss' ? '❌ Loss' : '➖ Neutral'}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  value={closeReason}
                  onChange={(e) => setCloseReason(e.target.value)}
                  placeholder="Why are you closing this memo?"
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-amber-200 focus:border-amber-400 outline-none mb-3"
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setShowCloseForm(false)}
                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCloseMemo}
                    disabled={saving || !closeReason.trim()}
                    className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
                  >
                    {saving ? 'Closing...' : 'Close Memo'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        {memo.status === 'active' && !showPostMortemForm && !showCloseForm && (
          <div className="border-t border-gray-100 px-6 py-4 flex justify-between">
            <button
              onClick={() => setShowCloseForm(true)}
              className="px-4 py-2 text-amber-600 hover:bg-amber-50 rounded-lg font-medium"
            >
              Close Memo
            </button>
            <button
              onClick={() => setShowPostMortemForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              Add Post-Mortem
            </button>
          </div>
        )}

        {/* Closed Memo Banner */}
        {memo.status !== 'active' && memo.closed_reason && (
          <div className={`border-t px-6 py-4 ${
            memo.status === 'closed_win' ? 'bg-emerald-50 border-emerald-200' :
            memo.status === 'closed_loss' ? 'bg-red-50 border-red-200' :
            'bg-gray-50 border-gray-200'
          }`}>
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium">
                {memo.status === 'closed_win' ? '✅ Closed as Win' :
                 memo.status === 'closed_loss' ? '❌ Closed as Loss' : '➖ Closed'}
              </span>
              <span className="text-gray-500">•</span>
              <span className="text-gray-600">{memo.closed_reason}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
