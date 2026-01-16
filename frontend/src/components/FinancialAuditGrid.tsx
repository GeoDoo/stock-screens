import { Shield, AlertTriangle, CheckCircle2, Info, Calculator, Activity, BarChart3 } from 'lucide-react';
import type { QuantitativeAudit } from '../types';
import { formatCurrency } from '../utils';

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

  const formatRatio = (val: number | null | undefined, type: 'percent' | 'decimal' | 'days' | 'multiple' = 'decimal') => {
    if (val === null || val === undefined) return 'N/A';
    if (type === 'percent') return (val * 100).toFixed(1) + '%';
    if (type === 'days') return val.toFixed(0);
    if (type === 'multiple') return val.toFixed(2) + 'x';
    return val.toFixed(2);
  };

  const sloan = getSloanStatus(audit.sloan_ratio);
  const altman = getAltmanStatus(audit.altman_z_score);
  const beneish = getBeneishStatus(audit.beneish_m_score);

  return (
    <div className="space-y-8">
      {/* Top Models Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Sloan Ratio Card */}
        <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:border-indigo-100 transition-colors">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Sloan Ratio</span>
            <sloan.icon className={`w-4 h-4 ${sloan.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-gray-900">
              {formatRatio(audit.sloan_ratio, 'percent')}
            </span>
            <span className={`text-[10px] font-bold uppercase ${sloan.color}`}>{sloan.label}</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-3 leading-relaxed font-medium">
            Measures accrual quality. Ratio &gt; 10% indicates earnings aren't backed by cash, suggesting aggressive accounting.
          </p>
        </div>

        {/* Altman Z-Score Card */}
        <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:border-indigo-100 transition-colors">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Altman Z-Score</span>
            <altman.icon className={`w-4 h-4 ${altman.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-gray-900">
              {formatRatio(audit.altman_z_score, 'decimal')}
            </span>
            <span className={`text-[10px] font-bold uppercase ${altman.color}`}>{altman.label}</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-3 leading-relaxed font-medium">
            Predicts bankruptcy risk. Score &lt; 1.81 indicates high distress probability for public manufacturing firms.
          </p>
        </div>

        {/* Beneish M-Score Card */}
        <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:border-indigo-100 transition-colors">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Beneish M-Score</span>
            <beneish.icon className={`w-4 h-4 ${beneish.color}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-gray-900">
              {formatRatio(audit.beneish_m_score, 'decimal')}
            </span>
            <span className={`text-[10px] font-bold uppercase ${beneish.color}`}>{beneish.label}</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-3 leading-relaxed font-medium">
            Probabilistic model for earnings manipulation. Score &gt; -1.78 suggests a high risk of "cooking the books".
          </p>
        </div>
      </div>

      {/* Ratios Table Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Profitability */}
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm">
          <div className="bg-slate-50 px-5 py-3 border-b border-gray-100 flex items-center gap-2">
            <BarChart3 className="w-3 h-3 text-indigo-600" />
            <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Profitability</h4>
          </div>
          <div className="p-0">
            <table className="w-full text-left border-collapse">
              <tbody className="divide-y divide-gray-50">
                <RatioRow label="Gross Margin" value={audit.profitability_ratios?.gross_margin} type="percent" />
                <RatioRow label="Operating Margin" value={audit.profitability_ratios?.operating_margin} type="percent" />
                <RatioRow label="Net Margin" value={audit.profitability_ratios?.net_margin} type="percent" />
                <RatioRow label="ROE" value={audit.profitability_ratios?.roe} type="percent" />
                <RatioRow label="ROA" value={audit.profitability_ratios?.roa} type="percent" />
                <RatioRow label="ROIC" value={audit.profitability_ratios?.roic} type="percent" />
                <RatioRow label="ROTIC" value={audit.profitability_ratios?.rotic} type="percent" />
                <RatioRow label="FCF Conversion" value={audit.profitability_ratios?.fcf_conversion} type="percent" />
              </tbody>
            </table>
          </div>
        </div>

        {/* Valuation - Requires Market Data */}
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm">
          <div className="bg-amber-50 px-5 py-3 border-b border-amber-100 flex items-center gap-2">
            <Calculator className="w-3 h-3 text-amber-600" />
            <h4 className="text-[10px] font-black text-amber-600 uppercase tracking-widest">Valuation</h4>
            <span className="ml-auto text-[9px] font-medium text-amber-500 bg-amber-100 px-2 py-0.5 rounded">
              Requires Live Market Data
            </span>
          </div>
          <div className="p-4 bg-amber-50/30 border-b border-amber-100">
            <p className="text-[10px] text-amber-700 leading-relaxed">
              <strong>Single Source of Truth:</strong> Valuation ratios (P/E, P/S, EV multiples) require real-time market price & market cap, 
              which are not available in SEC filings. Use the <strong>Analysis</strong> page for live valuation metrics.
            </p>
          </div>
          <div className="p-0 opacity-50">
            <table className="w-full text-left border-collapse">
              <tbody className="divide-y divide-gray-50">
                <RatioRow label="P/E Ratio" value={audit.valuation_ratios?.pe_ratio} type="decimal" hint="Needs price" />
                <RatioRow label="P/S Ratio" value={audit.valuation_ratios?.ps_ratio} type="decimal" hint="Needs market cap" />
                <RatioRow label="P/B Ratio" value={audit.valuation_ratios?.pb_ratio} type="decimal" hint="Needs market cap" />
                <RatioRow label="EV / Revenue" value={audit.valuation_ratios?.ev_to_revenue} type="decimal" hint="Needs market cap" />
                <RatioRow label="EV / EBITDA" value={audit.valuation_ratios?.ev_to_ebitda} type="decimal" hint="Needs market cap" />
                <RatioRow label="FCF Yield" value={audit.valuation_ratios?.fcf_yield} type="percent" hint="Needs market cap" />
                <RatioRow label="Dividend Yield" value={audit.valuation_ratios?.dividend_yield} type="percent" hint="Needs price" />
              </tbody>
            </table>
          </div>
        </div>

        {/* Efficiency */}
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm">
          <div className="bg-slate-50 px-5 py-3 border-b border-gray-100 flex items-center gap-2">
            <Activity className="w-3 h-3 text-indigo-600" />
            <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Efficiency</h4>
          </div>
          <div className="p-0">
            <table className="w-full text-left border-collapse">
              <tbody className="divide-y divide-gray-50">
                <RatioRow label="Asset Turnover" value={audit.efficiency_ratios?.asset_turnover} type="decimal" />
                <RatioRow label="Inventory Turnover" value={audit.efficiency_ratios?.inventory_turnover} type="decimal" hint="No inventory" />
                <RatioRow label="DSO (Days Sales Out.)" value={audit.efficiency_ratios?.days_sales_outstanding} type="days" />
                <RatioRow label="DIO (Days Inv. Out.)" value={audit.efficiency_ratios?.days_inventory_outstanding} type="days" hint="No inventory" />
                <RatioRow label="DPO (Days Pay. Out.)" value={audit.efficiency_ratios?.days_payable_outstanding} type="days" hint="No payables" />
                <RatioRow label="Cash Conversion Cycle" value={audit.efficiency_ratios?.cash_conversion_cycle} type="days" hint="Needs inventory" />
              </tbody>
            </table>
          </div>
        </div>

        {/* Liquidity & Solvency */}
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm">
          <div className="bg-slate-50 px-5 py-3 border-b border-gray-100 flex items-center gap-2">
            <Shield className="w-3 h-3 text-indigo-600" />
            <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Liquidity & Solvency</h4>
          </div>
          <div className="p-0">
            <table className="w-full text-left border-collapse">
              <tbody className="divide-y divide-gray-50">
                <RatioRow label="Current Ratio" value={audit.liquidity_ratios?.current_ratio} type="decimal" />
                <RatioRow label="Quick Ratio" value={audit.liquidity_ratios?.quick_ratio} type="decimal" />
                <RatioRow label="Cash Ratio" value={audit.liquidity_ratios?.cash_ratio} type="decimal" hint="Needs current liab." />
                <RatioRow label="Debt to Equity" value={audit.solvency_ratios?.debt_to_equity} type="decimal" />
                <RatioRow label="Debt to Assets" value={audit.solvency_ratios?.debt_to_assets} type="decimal" />
                <RatioRow label="Interest Coverage" value={audit.solvency_ratios?.interest_coverage} type="multiple" />
                <RatioRow label="Equity Multiplier" value={audit.solvency_ratios?.equity_multiplier} type="decimal" />
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Accounting Corrections */}
      {audit.accounting_corrections && audit.accounting_corrections.length > 0 && (
        <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-6">
          <h4 className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-6 flex items-center gap-2">
            <Calculator className="w-3 h-3 text-indigo-600" />
            Accounting Adjustments (Economic Reality)
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {audit.accounting_corrections.map((correction, idx) => (
              <div key={idx} className="bg-white border border-indigo-100 rounded-lg p-5 shadow-sm">
                <h5 className="text-sm font-bold text-indigo-900 mb-2">{correction.name}</h5>
                <p className="text-xs text-gray-600 mb-4 leading-relaxed">{correction.description}</p>
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-indigo-50">
                  <div>
                    <span className="block text-[10px] font-bold text-gray-400 uppercase">EBIT Impact</span>
                    <span className={`text-xs font-bold ${correction.impact_on_ebit >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {correction.impact_on_ebit >= 0 ? '+' : ''}{formatCurrency(correction.impact_on_ebit)}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold text-gray-400 uppercase">Asset Impact</span>
                    <span className={`text-xs font-bold ${correction.impact_on_assets >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {correction.impact_on_assets >= 0 ? '+' : ''}{formatCurrency(correction.impact_on_assets)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quantitative Findings (Red Flags) */}
      {audit.findings.length > 0 && (
        <div className="bg-red-50/50 rounded-xl p-6 border border-red-100">
          <h4 className="text-[10px] font-black text-red-400 uppercase tracking-widest mb-4 flex items-center gap-2">
            <Shield className="w-3 h-3 text-red-600" />
            Numerical Red Flags & Violations
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
            {audit.findings.map((finding, idx) => (
              <div key={idx} className="flex gap-3 items-start">
                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
                <p className="text-xs font-bold text-red-900 leading-normal">{finding}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RatioRow({ label, value, type, hint }: { 
  label: string, 
  value: number | null | undefined, 
  type: 'percent' | 'decimal' | 'days' | 'multiple',
  hint?: string 
}) {
  const formatValue = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'N/A';
    if (type === 'percent') return (val * 100).toFixed(1) + '%';
    if (type === 'days') return val.toFixed(0) + 'd';
    if (type === 'multiple') return val.toFixed(2) + 'x';
    return val.toFixed(2);
  };

  const isNA = value === null || value === undefined;
  const displayValue = formatValue(value);

  return (
    <tr className="group hover:bg-slate-50 transition-colors">
      <td className="py-3 px-5 text-xs font-medium text-gray-500 group-hover:text-gray-900">{label}</td>
      <td className="py-3 px-5 text-xs text-right font-mono">
        {isNA && hint ? (
          <span className="text-amber-500 font-medium text-[10px]" title={hint}>
            {hint}
          </span>
        ) : (
          <span className={isNA ? 'text-gray-400' : 'font-black text-gray-900'}>{displayValue}</span>
        )}
      </td>
    </tr>
  );
}
