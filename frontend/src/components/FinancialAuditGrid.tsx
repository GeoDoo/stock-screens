import { Shield, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import type { QuantitativeAudit } from '../types';

interface FinancialAuditGridProps {
  audit: QuantitativeAudit;
}

export function FinancialAuditGrid({ audit }: FinancialAuditGridProps) {
  const getSloanStatus = (ratio: number | null) => {
    if (ratio === null) return { label: 'Insufficient Data', color: 'text-gray-400', icon: Info };
    if (ratio > 0.10) return { label: 'High Accruals', color: 'text-red-600', icon: AlertTriangle };
    if (ratio > 0.05) return { label: 'Elevated Accruals', color: 'text-amber-600', icon: AlertTriangle };
    return { label: 'High Quality', color: 'text-emerald-600', icon: CheckCircle2 };
  };

  const getAltmanStatus = (score: number | null) => {
    if (score === null) return { label: 'Insufficient Data', color: 'text-gray-400', icon: Info };
    if (score < 1.81) return { label: 'Distress Zone', color: 'text-red-600', icon: AlertTriangle };
    if (score < 2.99) return { label: 'Gray Zone', color: 'text-amber-600', icon: AlertTriangle };
    return { label: 'Safe Zone', color: 'text-emerald-600', icon: CheckCircle2 };
  };

  const getBeneishStatus = (score: number | null) => {
    if (score === null) return { label: 'Insufficient Data', color: 'text-gray-400', icon: Info };
    if (score > -1.78) return { label: 'Potential Manipulator', color: 'text-red-600', icon: AlertTriangle };
    return { label: 'Low Manipulation Risk', color: 'text-emerald-600', icon: CheckCircle2 };
  };

  const sloan = getSloanStatus(audit.sloan_ratio);
  const altman = getAltmanStatus(audit.altman_z_score);
  const beneish = getBeneishStatus(audit.beneish_m_score);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Sloan Ratio Card */}
        <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Sloan Ratio</span>
            <sloan.icon className={`w-4 h-4 ${sloan.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-gray-900">
              {audit.sloan_ratio !== null ? (audit.sloan_ratio * 100).toFixed(1) + '%' : 'N/A'}
            </span>
            <span className={`text-[10px] font-bold uppercase ${sloan.color}`}>{sloan.label}</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-3 leading-relaxed">
            Measures accrual quality. Ratio &gt; 10% indicates earnings aren't backed by cash.
          </p>
        </div>

        {/* Altman Z-Score Card */}
        <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Altman Z-Score</span>
            <altman.icon className={`w-4 h-4 ${altman.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-gray-900">
              {audit.altman_z_score !== null ? audit.altman_z_score.toFixed(2) : 'N/A'}
            </span>
            <span className={`text-[10px] font-bold uppercase ${altman.color}`}>{altman.label}</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-3 leading-relaxed">
            Predicts bankruptcy risk. Score &lt; 1.81 indicates high distress probability.
          </p>
        </div>

        {/* Beneish M-Score Card */}
        <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Beneish M-Score</span>
            <beneish.icon className={`w-4 h-4 ${beneish.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-gray-900">
              {audit.beneish_m_score !== null ? audit.beneish_m_score.toFixed(2) : 'N/A'}
            </span>
            <span className={`text-[10px] font-bold uppercase ${beneish.color}`}>{beneish.label}</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-3 leading-relaxed">
            Detects earnings manipulation. Score &gt; -1.78 suggests manipulation risk.
          </p>
        </div>
      </div>

      {audit.findings.length > 0 && (
        <div className="bg-slate-50 rounded-xl p-6 border border-slate-100">
          <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
            <Shield className="w-3 h-3 text-indigo-600" />
            Quantitative Red Flags
          </h4>
          <div className="space-y-3">
            {audit.findings.map((finding, idx) => (
              <div key={idx} className="flex gap-3 items-start">
                <div className="mt-1 w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
                <p className="text-xs font-bold text-slate-700 leading-normal">{finding}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
