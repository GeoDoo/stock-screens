import type { CapitalEfficiency } from '../types';
import { GlossaryRef } from './GlossaryRef';

interface CapitalEfficiencyPanelProps {
  data: CapitalEfficiency;
  wacc: number;
}

/**
 * CapitalEfficiencyPanel displays ROIC, Value Spread, and Economic Profit.
 * 
 * NOTES4: These metrics help users understand whether a company is
 * creating or destroying shareholder value through its capital investments.
 */
export function CapitalEfficiencyPanel({ data, wacc }: CapitalEfficiencyPanelProps) {
  if (data.data_issue) {
    return (
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
          Capital Efficiency
        </div>
        <div className="text-sm text-gray-500 italic">
          {data.data_issue}
        </div>
      </div>
    );
  }

  // Format ROIC with color coding
  const formatROIC = (roic: number | null) => {
    if (roic === null) return { text: 'N/A', color: 'text-gray-400' };
    const pct = (roic * 100).toFixed(1);
    if (roic > 0.20) return { text: `${pct}%`, color: 'text-emerald-600 font-semibold' };
    if (roic > 0.15) return { text: `${pct}%`, color: 'text-emerald-500' };
    if (roic > 0.10) return { text: `${pct}%`, color: 'text-gray-700' };
    if (roic > wacc) return { text: `${pct}%`, color: 'text-amber-500' };
    return { text: `${pct}%`, color: 'text-red-500' };
  };

  // Format Value Spread with color coding
  const formatSpread = (spread: number | null) => {
    if (spread === null) return { text: 'N/A', color: 'text-gray-400' };
    const pct = (spread * 100).toFixed(1);
    if (spread > 0.10) return { text: `+${pct}%`, color: 'text-emerald-600 font-semibold' };
    if (spread > 0.02) return { text: `+${pct}%`, color: 'text-emerald-500' };
    if (spread > -0.02) return { text: `${pct}%`, color: 'text-gray-500' };
    return { text: `${pct}%`, color: 'text-red-500' };
  };

  // Format Economic Profit
  const formatEVA = (eva: number | null) => {
    if (eva === null) return { text: 'N/A', color: 'text-gray-400' };
    const absValue = Math.abs(eva);
    let formatted: string;
    if (absValue >= 1e9) {
      formatted = `$${(eva / 1e9).toFixed(2)}B`;
    } else if (absValue >= 1e6) {
      formatted = `$${(eva / 1e6).toFixed(2)}M`;
    } else {
      formatted = `$${eva.toFixed(0)}`;
    }
    if (eva > 0) return { text: formatted, color: 'text-emerald-600' };
    if (eva < 0) return { text: formatted, color: 'text-red-500' };
    return { text: formatted, color: 'text-gray-500' };
  };

  const roic = formatROIC(data.roic);
  const spread = formatSpread(data.value_spread);
  const eva = formatEVA(data.economic_profit);

  // Status badge
  const status = data.is_value_creating === true
    ? { text: 'Value Creator', color: 'bg-emerald-100 text-emerald-700' }
    : data.is_value_creating === false
    ? { text: 'Value Destroyer', color: 'bg-red-100 text-red-700' }
    : { text: 'Unknown', color: 'bg-gray-100 text-gray-500' };

  return (
    <div className="bg-gradient-to-br from-slate-50 to-gray-100 rounded-lg p-4 border border-gray-200">
      <div className="flex justify-between items-center mb-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Capital Efficiency <GlossaryRef id="roic" />
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${status.color}`}>
          {status.text}
        </span>
      </div>

      {/* Main metrics grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">
            ROIC <GlossaryRef id="roic" />
          </div>
          <div className={`text-xl font-mono ${roic.color}`}>
            {roic.text}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">
            Spread <GlossaryRef id="value-spread" />
          </div>
          <div className={`text-xl font-mono ${spread.color}`}>
            {spread.text}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">
            EVA <GlossaryRef id="economic-profit" />
          </div>
          <div className={`text-xl font-mono ${eva.color}`}>
            {eva.text}
          </div>
        </div>
      </div>

      {/* Assessment */}
      {data.assessment && (
        <div className="text-xs text-gray-600 bg-white/50 rounded p-2 mb-2">
          {data.assessment}
        </div>
      )}

      {/* Reinvestment rate if available */}
      {data.reinvestment_rate !== undefined && data.reinvestment_rate !== null && (
        <div className="text-[10px] text-gray-500 border-t border-gray-200 pt-2 mt-2">
          Reinvestment Rate <GlossaryRef id="reinvestment-rate" />:{' '}
          <span className="font-mono">{(data.reinvestment_rate * 100).toFixed(1)}%</span>
          {data.reinvestment_rate > 1 && (
            <span className="text-amber-600 ml-1">
              (⚠ &gt;100% — unsustainable without external capital)
            </span>
          )}
        </div>
      )}

      {/* Interpretation help */}
      <div className="text-[10px] text-gray-400 border-t border-gray-200 pt-2 mt-2">
        ROIC &gt; WACC ({(wacc * 100).toFixed(1)}%) = Growth creates value
      </div>
    </div>
  );
}
