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
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="border-b border-gray-100 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium text-gray-900">Create Investment Memo</h2>
            <p className="text-sm text-gray-400 mt-0.5">{symbol}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Market Context */}
          <div className="border border-gray-100 rounded p-4">
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wider">Price</div>
                <div className="font-mono text-gray-900">${currentPrice.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wider">Intrinsic Value</div>
                <div className="font-mono text-gray-900">${intrinsicValue.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wider">Upside</div>
                <div className={`font-mono ${upside >= 0 ? 'text-gray-900' : 'text-gray-500'}`}>
                  {upside >= 0 ? '+' : ''}{upside.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wider">P/E</div>
                <div className="font-mono text-gray-900">
                  {peRatio ? peRatio.toFixed(1) : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm text-gray-600 mb-1.5">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., AI iPhone Cycle"
              className="w-full px-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none transition-colors text-sm"
            />
          </div>

          {/* Thesis */}
          <div>
            <label className="block text-sm text-gray-600 mb-1.5">Investment Thesis</label>
            <textarea
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              placeholder="Why is this stock mispriced?"
              rows={3}
              className="w-full px-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none transition-colors resize-none text-sm"
            />
          </div>

          {/* Conviction & Time Horizon */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1.5">Conviction</label>
              <div className="flex gap-1">
                {(['low', 'medium', 'high'] as MemoConviction[]).map((level) => (
                  <button
                    key={level}
                    onClick={() => setConviction(level)}
                    className={`flex-1 py-1.5 px-2 text-sm rounded transition-colors ${
                      conviction === level
                        ? 'bg-gray-900 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1.5">Time Horizon</label>
              <select
                value={timeHorizon}
                onChange={(e) => setTimeHorizon(parseInt(e.target.value))}
                className="w-full px-3 py-1.5 border border-gray-200 rounded focus:border-gray-400 outline-none text-sm"
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
            <label className="block text-sm text-gray-600 mb-1.5">Target Price</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
              <input
                type="number"
                step="0.01"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                className="w-full pl-7 pr-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none transition-colors text-sm"
              />
            </div>
          </div>

          {/* Catalysts */}
          <div>
            <label className="block text-sm text-gray-600 mb-1.5">Catalysts</label>
            <textarea
              value={catalysts}
              onChange={(e) => setCatalysts(e.target.value)}
              placeholder="What could drive the stock to target?"
              rows={2}
              className="w-full px-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none transition-colors resize-none text-sm"
            />
          </div>

          {/* Risks */}
          <div>
            <label className="block text-sm text-gray-600 mb-1.5">Key Risks</label>
            <textarea
              value={risks}
              onChange={(e) => setRisks(e.target.value)}
              placeholder="What could go wrong?"
              rows={2}
              className="w-full px-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none transition-colors resize-none text-sm"
            />
          </div>

          {/* Exit Criteria */}
          <div>
            <label className="block text-sm text-gray-600 mb-1.5">Exit Criteria</label>
            <textarea
              value={whatWouldChangeMind}
              onChange={(e) => setWhatWouldChangeMind(e.target.value)}
              placeholder="What would make you exit?"
              rows={2}
              className="w-full px-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none transition-colors resize-none text-sm"
            />
          </div>

          {/* Scenarios */}
          {memoScenarios.length > 0 && (
            <div>
              <label className="block text-sm text-gray-600 mb-1.5">Scenarios</label>
              <div className="grid grid-cols-3 gap-2">
                {memoScenarios.map((s) => (
                  <div key={s.name} className="border border-gray-100 rounded p-3 text-center">
                    <div className="text-xs text-gray-400 uppercase tracking-wider">{s.name}</div>
                    <div className="font-mono text-sm mt-1">${s.intrinsic_value.toFixed(0)}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {s.upside_percent >= 0 ? '+' : ''}{s.upside_percent.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-100 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm bg-gray-900 text-white rounded hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Memo'}
          </button>
        </div>
      </div>
    </div>
  );
}
