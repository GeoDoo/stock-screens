import { AlertTriangle } from 'lucide-react';

interface ExecutionRiskMatrixProps {
  margins: number[];
  growthRates: number[];
  matrix: (number | null)[][];
  roicFlags: boolean[][];
  baseMargin: number;
  baseGrowth: number;
}

export function ExecutionRiskMatrix({
  margins,
  growthRates,
  matrix,
  roicFlags,
  baseMargin,
  baseGrowth,
}: ExecutionRiskMatrixProps) {
  const formatValue = (val: number | null) => {
    if (val === null) return 'N/A';
    return '$' + val.toFixed(2);
  };

  const isBaseCase = (m: number, g: number) => {
    return Math.abs(m - baseMargin) < 0.001 && Math.abs(g - baseGrowth) < 0.001;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-widest flex items-center gap-2">
            Execution Risk Matrix
          </h3>
          <p className="text-[10px] text-gray-500 mt-1 font-medium">
            Intrinsic value sensitivity to Operating Margin and Revenue Growth assumptions.
          </p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-indigo-600" />
            <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Base Case</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-amber-50" />
            <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Gated (High ROIC)</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-separate border-spacing-1">
          <thead>
            <tr>
              <th className="p-2 text-[9px] font-black text-gray-400 uppercase tracking-widest bg-gray-50/50 rounded-lg">
                Margin ↓ / Growth →
              </th>
              {growthRates.map((g, i) => (
                <th key={i} className="p-2 text-[10px] font-black text-gray-600 text-center bg-gray-50/50 rounded-lg">
                  {(g * 100).toFixed(1)}%
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {margins.map((m, rowIdx) => (
              <tr key={rowIdx}>
                <td className="p-2 text-[10px] font-black text-gray-600 bg-gray-50/50 rounded-lg">
                  {(m * 100).toFixed(1)}%
                </td>
                {growthRates.map((g, colIdx) => {
                  const val = matrix[rowIdx][colIdx];
                  const isSuspect = roicFlags[rowIdx][colIdx];
                  const isBase = isBaseCase(m, g);

                  return (
                    <td
                      key={colIdx}
                      className={`p-3 text-center rounded-lg transition-all ${
                        isBase 
                          ? 'bg-indigo-600 text-white shadow-md ring-2 ring-indigo-200' 
                          : isSuspect 
                            ? 'bg-amber-50 text-amber-700' 
                            : 'bg-white border border-gray-100 text-gray-900 hover:border-indigo-200'
                      }`}
                    >
                      <div className="text-[11px] font-black">{formatValue(val)}</div>
                      {isSuspect && !isBase && (
                        <div className="text-[7px] font-black uppercase tracking-tighter mt-0.5 opacity-60">
                          Suspect ROIC
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex gap-4 items-start">
        <div className="p-2 bg-white rounded-lg border border-slate-200">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
        </div>
        <div>
          <h4 className="text-[10px] font-black text-slate-900 uppercase tracking-widest mb-1">
            Economic Sanity Check (ROIC Gating)
          </h4>
          <p className="text-[10px] text-slate-500 leading-relaxed font-medium">
            Shaded cells indicate scenarios where the implied terminal ROIC exceeds 2× WACC. These represent "economically heroic" assumptions that assume an infinite competitive advantage. High margins combined with high growth often produce unrealistic valuations.
          </p>
        </div>
      </div>
    </div>
  );
}
