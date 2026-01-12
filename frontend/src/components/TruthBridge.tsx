import React from 'react';
import { TrendingDown, TrendingUp, ShieldCheck, Scale } from 'lucide-react';
import type { EPSAdjustment } from '../types';

interface Props {
  reportedEps: number | null | undefined;
  adjustments: EPSAdjustment[];
  totalAdjustment: number;
}

export function TruthBridge({ reportedEps, adjustments, totalAdjustment }: Props) {
  const baseEps = reportedEps || 0;
  const forensicEps = baseEps + totalAdjustment;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-slate-600" />
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-tight">The "Truth" Bridge</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Forensic Reality</span>
          <div className={`px-2 py-0.5 rounded text-xs font-black ${forensicEps >= baseEps ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            ${forensicEps.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {/* Reported EPS */}
        <div className="flex justify-between items-center pb-2 border-b border-gray-100">
          <div>
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Reported EPS</div>
            <div className="text-lg font-bold text-gray-900">${baseEps.toFixed(2)}</div>
          </div>
          <div className="text-xs text-gray-500 font-medium italic">As per filing</div>
        </div>

        {/* Adjustments */}
        <div className="space-y-3">
          {adjustments.length > 0 ? (
            adjustments.map((adj, i) => (
              <div key={i} className="flex justify-between items-start gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {adj.amount < 0 ? (
                      <TrendingDown className="w-3.5 h-3.5 text-red-500 shrink-0" />
                    ) : (
                      <TrendingUp className="w-3.5 h-3.5 text-green-500 shrink-0" />
                    )}
                    <span className="text-xs font-bold text-gray-700 leading-tight">{adj.reason}</span>
                  </div>
                  <p className="text-[10px] text-gray-500 mt-0.5 ml-5 leading-relaxed">{adj.impact}</p>
                </div>
                <div className={`text-xs font-mono font-bold whitespace-nowrap ${adj.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {adj.amount < 0 ? '-' : '+'}${Math.abs(adj.amount).toFixed(2)}
                </div>
              </div>
            ))
          ) : (
            <div className="py-4 text-center">
              <ShieldCheck className="w-8 h-8 text-green-200 mx-auto mb-2" />
              <p className="text-xs text-gray-400 font-medium">No material accounting adjustments identified</p>
            </div>
          )}
        </div>

        {/* Total Bridge */}
        <div className={`mt-6 p-4 rounded-xl border-2 flex justify-between items-center ${forensicEps >= baseEps ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
          <div>
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Forensic "Truth" EPS</div>
            <div className={`text-2xl font-black ${forensicEps >= baseEps ? 'text-green-700' : 'text-red-700'}`}>
              ${forensicEps.toFixed(2)}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] font-bold text-gray-400 uppercase">Delta</div>
            <div className={`text-sm font-bold ${totalAdjustment < 0 ? 'text-red-600' : totalAdjustment > 0 ? 'text-green-600' : 'text-gray-500'}`}>
              {totalAdjustment < 0 ? '-' : totalAdjustment > 0 ? '+' : ''}{Math.abs((totalAdjustment / (baseEps || 1)) * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
