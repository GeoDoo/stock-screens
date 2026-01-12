import { TrendingDown, TrendingUp } from 'lucide-react';
import type { EPSAdjustment } from '../types';

interface Props {
  reportedEps: number | null | undefined;
  adjustments: EPSAdjustment[];
  totalAdjustment: number;
}

export function TruthBridge({ reportedEps, adjustments, totalAdjustment }: Props) {
  const baseEps = reportedEps || 0;
  const forensicEps = baseEps + totalAdjustment;
  const delta = forensicEps - baseEps;
  const deltaPercent = baseEps !== 0 ? (delta / baseEps) * 100 : 0;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-8 py-6 border-b border-gray-100 bg-gray-50/30 flex items-center justify-between">
        <div>
          <h3 className="text-base font-black text-gray-900 uppercase tracking-tighter">The Truth Bridge</h3>
          <p className="text-xs text-gray-500 font-medium mt-1 uppercase tracking-widest opacity-70">From Reported GAAP to Economic Reality</p>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
          delta >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
        }`}>
          {delta >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {Math.abs(deltaPercent).toFixed(1)}% Forensic Variance
        </div>
      </div>

      <div className="p-10">
        <div className="flex flex-col md:flex-row items-stretch justify-between gap-12 relative">
          {/* Base EPS */}
          <div className="flex-1 text-center md:text-left">
            <div className="text-4xl font-black text-gray-900 tracking-tighter mb-1">
              ${baseEps.toFixed(2)}
            </div>
            <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Reported GAAP EPS</div>
          </div>

          {/* Adjustments Flow */}
          <div className="flex-[3] flex items-center justify-center gap-4">
            {adjustments.length > 0 ? (
              <div className="flex flex-wrap justify-center gap-3">
                {adjustments.map((adj, idx) => (
                  <div 
                    key={idx} 
                    className={`px-4 py-2 rounded-xl border flex flex-col items-center gap-1 transition-all hover:scale-105 ${
                      adj.amount >= 0 
                        ? 'bg-emerald-50 border-emerald-100' 
                        : 'bg-red-50 border-red-100'
                    }`}
                  >
                    <span className={`text-xs font-black ${adj.amount >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                      {adj.amount >= 0 ? '+' : ''}{adj.amount.toFixed(2)}
                    </span>
                    <span className="text-[9px] font-bold text-gray-500 uppercase tracking-tighter whitespace-nowrap">
                      {adj.reason}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-3 text-gray-300">
                <div className="h-[1px] w-20 bg-gray-100" />
                <span className="text-[10px] font-black uppercase tracking-[0.3em]">No Adjustments</span>
                <div className="h-[1px] w-20 bg-gray-100" />
              </div>
            )}
          </div>

          {/* Forensic EPS */}
          <div className="flex-1 text-center md:text-right">
            <div className={`text-4xl font-black tracking-tighter mb-1 ${
              forensicEps > baseEps ? 'text-indigo-600' : 'text-red-600'
            }`}>
              ${forensicEps.toFixed(2)}
            </div>
            <div className="text-[10px] font-black text-indigo-500 uppercase tracking-widest">Forensic Reality EPS</div>
          </div>
        </div>
      </div>

      {adjustments.length > 0 && (
        <div className="px-8 py-6 bg-gray-50/50 border-t border-gray-100">
          <h4 className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-4">Adjustment Methodology</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {adjustments.map((adj, idx) => (
              <div key={idx} className="flex gap-4">
                <div className={`w-1 h-full rounded-full ${adj.amount >= 0 ? 'bg-emerald-400' : 'bg-red-400'}`} />
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-black text-gray-900">{adj.reason}</span>
                    <span className={`text-[10px] font-bold ${adj.amount >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {adj.amount >= 0 ? '+' : ''}{adj.amount.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-[12px] leading-relaxed text-gray-500 font-medium">{adj.impact}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
