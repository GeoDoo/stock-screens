import { useState } from 'react';
import type { 
  CreateMemoRequest, 
  MemoConviction, 
  MemoScenario,
  ScenarioAnalysisResult,
} from '../types';

interface MemoCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (memo: CreateMemoRequest) => Promise<void>;
  symbol: string;
  currentPrice: number;
  intrinsicValue: number;
  peRatio: number | null;
  assumptions: {
    revenue_growth: number;
    operating_margin: number;
    terminal_growth_rate: number;
    discount_rate: number;
    projection_years: number;
    da_ratio?: number | null;
    capex_ratio?: number | null;
    wc_ratio?: number | null;
  };
  scenarios?: ScenarioAnalysisResult | null;
}

export function MemoCreateModal({
  isOpen,
  onClose,
  onSave,
  symbol,
  currentPrice,
  intrinsicValue,
  peRatio,
  assumptions,
  scenarios,
}: MemoCreateModalProps) {
  const [title, setTitle] = useState('');
  const [thesis, setThesis] = useState('');
  const [conviction, setConviction] = useState<MemoConviction>('medium');
  const [timeHorizon, setTimeHorizon] = useState(12);
  const [targetPrice, setTargetPrice] = useState<string>(intrinsicValue.toFixed(2));
  const [risks, setRisks] = useState('');
  const [catalysts, setCatalysts] = useState('');
  const [whatWouldChangeMind, setWhatWouldChangeMind] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const upside = ((intrinsicValue - currentPrice) / currentPrice) * 100;

  // Convert scenario results to memo format
  const memoScenarios: MemoScenario[] = scenarios?.scenarios?.map((s) => ({
    name: s.name,
    revenue_growth: s.assumptions.revenue_growth,
    operating_margin: s.assumptions.operating_margin,
    intrinsic_value: s.intrinsic_value,
    upside_percent: s.upside_percent ?? 0,
  })) || [];

  const handleSave = async () => {
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (!thesis.trim()) {
      setError('Thesis is required');
      return;
    }

    setError(null);
    setSaving(true);

    try {
      const memo: CreateMemoRequest = {
        symbol,
        title: title.trim(),
        thesis: thesis.trim(),
        conviction,
        time_horizon_months: timeHorizon,
        assumptions: {
          revenue_growth: assumptions.revenue_growth,
          operating_margin: assumptions.operating_margin,
          terminal_growth_rate: assumptions.terminal_growth_rate,
          discount_rate: assumptions.discount_rate,
          projection_years: assumptions.projection_years,
          da_ratio: assumptions.da_ratio,
          capex_ratio: assumptions.capex_ratio,
          wc_ratio: assumptions.wc_ratio,
        },
        scenarios: memoScenarios,
        initial_market: {
          price: currentPrice,
          intrinsic_value: intrinsicValue,
          pe_ratio: peRatio,
        },
        target_price: targetPrice ? parseFloat(targetPrice) : null,
        risks: risks.trim() || null,
        catalysts: catalysts.trim() || null,
        what_would_change_mind: whatWouldChangeMind.trim() || null,
      };

      await onSave(memo);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save memo');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Create Investment Memo</h2>
            <p className="text-sm text-gray-500 mt-1">{symbol} • ${currentPrice.toFixed(2)}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Market Context Banner */}
          <div className="bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl p-4">
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider">Price</div>
                <div className="font-mono font-semibold text-gray-900">${currentPrice.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider">Intrinsic Value</div>
                <div className="font-mono font-semibold text-emerald-600">${intrinsicValue.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider">Upside</div>
                <div className={`font-mono font-semibold ${upside >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {upside >= 0 ? '+' : ''}{upside.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider">P/E Ratio</div>
                <div className="font-mono font-semibold text-gray-900">
                  {peRatio ? peRatio.toFixed(1) : 'N/A'}
                </div>
              </div>
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Memo Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., AI iPhone Cycle, Cloud Dominance Play"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all"
            />
          </div>

          {/* Thesis */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Investment Thesis <span className="text-red-500">*</span>
            </label>
            <textarea
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              placeholder="Why do you believe this stock is mispriced? What's your edge or insight?"
              rows={4}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all resize-none"
            />
          </div>

          {/* Conviction & Time Horizon */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Conviction</label>
              <div className="flex gap-2">
                {(['low', 'medium', 'high'] as MemoConviction[]).map((level) => (
                  <button
                    key={level}
                    onClick={() => setConviction(level)}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                      conviction === level
                        ? level === 'high' ? 'bg-emerald-500 text-white'
                          : level === 'medium' ? 'bg-amber-500 text-white'
                          : 'bg-gray-500 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Time Horizon</label>
              <select
                value={timeHorizon}
                onChange={(e) => setTimeHorizon(parseInt(e.target.value))}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 focus:border-blue-500 outline-none"
              >
                <option value={3}>3 months</option>
                <option value={6}>6 months</option>
                <option value={12}>12 months</option>
                <option value={18}>18 months</option>
                <option value={24}>2 years</option>
                <option value={36}>3 years</option>
              </select>
            </div>
          </div>

          {/* Target Price */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Target Price</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">$</span>
              <input
                type="number"
                step="0.01"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                className="w-full pl-8 pr-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all"
              />
            </div>
          </div>

          {/* Catalysts */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Catalysts</label>
            <textarea
              value={catalysts}
              onChange={(e) => setCatalysts(e.target.value)}
              placeholder="What events could drive the stock to your target?"
              rows={2}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all resize-none"
            />
          </div>

          {/* Risks */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Key Risks</label>
            <textarea
              value={risks}
              onChange={(e) => setRisks(e.target.value)}
              placeholder="What could go wrong with this thesis?"
              rows={2}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all resize-none"
            />
          </div>

          {/* What Would Change Mind */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">What Would Change Your Mind?</label>
            <textarea
              value={whatWouldChangeMind}
              onChange={(e) => setWhatWouldChangeMind(e.target.value)}
              placeholder="What evidence would make you exit the position?"
              rows={2}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all resize-none"
            />
          </div>

          {/* Scenarios Preview */}
          {memoScenarios.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Captured Scenarios</label>
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="grid grid-cols-3 gap-3">
                  {memoScenarios.map((s) => (
                    <div
                      key={s.name}
                      className={`p-3 rounded-lg text-center ${
                        s.name.toLowerCase() === 'bull' ? 'bg-emerald-100 text-emerald-800' :
                        s.name.toLowerCase() === 'bear' ? 'bg-red-100 text-red-800' :
                        'bg-blue-100 text-blue-800'
                      }`}
                    >
                      <div className="text-xs font-medium uppercase tracking-wider opacity-75">{s.name}</div>
                      <div className="font-mono font-bold mt-1">${s.intrinsic_value.toFixed(0)}</div>
                      <div className="text-xs mt-0.5">
                        {s.upside_percent >= 0 ? '+' : ''}{s.upside_percent.toFixed(0)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-3 rounded-xl text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white border-t border-gray-100 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-xl text-gray-600 hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Saving...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Save Memo
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
