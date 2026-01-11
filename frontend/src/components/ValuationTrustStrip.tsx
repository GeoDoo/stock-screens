/**
 * ValuationTrustStrip - Transparency strip for investment-grade trust
 * 
 * P1.6 from NOTES.md: Improve provenance exposure in the UI.
 * 
 * Displays critical context near the intrinsic value so analysts know:
 * - Period used (TTM vs Annual)
 * - Discount rate source (Custom override vs Computed WACC)
 * - Shares basis (Diluted vs Basic, plus dilution rate if applied)
 * - Terminal value dominance (% of EV from terminal value)
 * - Provenance flags (any fallback/synthetic data sources)
 * - Data freshness (NOTES2.md: flag stale data >120 days)
 */

import type { ValuationResult, DataProvenance } from '../types';

interface ValuationTrustStripProps {
  result: ValuationResult;
  period: 'ttm' | 'annual';
  provenance?: DataProvenance;
  dataFreshnessDays?: number;
  dataIsStale?: boolean;
  latestStatementDate?: string;
}

interface TrustItem {
  label: string;
  value: string;
  type: 'info' | 'warning' | 'custom';
  tooltip?: string;
}

export function ValuationTrustStrip({ 
  result, 
  period, 
  provenance,
  dataFreshnessDays,
  dataIsStale,
  latestStatementDate,
}: ValuationTrustStripProps) {
  const items: TrustItem[] = [];
  
  // 1. Period used
  items.push({
    label: 'Period',
    value: period === 'ttm' ? 'TTM' : 'Annual',
    type: period === 'ttm' ? 'info' : 'info',
    tooltip: period === 'ttm' 
      ? 'Using Trailing Twelve Months data (more current)' 
      : 'Using last fiscal year data',
  });
  
  // 2. Discount rate source
  items.push({
    label: 'Discount',
    value: result.using_custom_discount_rate 
      ? `${(result.discount_rate * 100).toFixed(1)}% (Custom)` 
      : `${(result.discount_rate * 100).toFixed(1)}% (WACC)`,
    type: result.using_custom_discount_rate ? 'custom' : 'info',
    tooltip: result.using_custom_discount_rate 
      ? 'Using your custom discount rate override' 
      : 'Using computed Weighted Average Cost of Capital',
  });
  
  // 3. Shares basis
  const sharesType = result.inputs.shares_type || 'unknown';
  const dilutionRate = typeof result.inputs.annual_dilution_rate === 'number' ? result.inputs.annual_dilution_rate : 0;
  const dilutionApplied = dilutionRate > 0;
  let sharesValue = sharesType === 'diluted' ? 'Diluted' : sharesType === 'basic' ? 'Basic' : 'Unknown';
  if (dilutionApplied) {
    sharesValue += ` +${(dilutionRate * 100).toFixed(1)}%/yr`;
  }
  // Determine tooltip based on shares type (handle unknown case explicitly)
  let sharesTooltip: string;
  if (sharesType === 'basic') {
    sharesTooltip = 'Using basic shares (diluted not available) - may overstate per-share value';
  } else if (sharesType === 'diluted') {
    sharesTooltip = dilutionApplied 
      ? `Using diluted shares with ${(dilutionRate * 100).toFixed(1)}% annual SBC dilution`
      : 'Using fully diluted shares outstanding';
  } else {
    sharesTooltip = 'Shares type unknown - verify data source';
  }
  
  items.push({
    label: 'Shares',
    value: sharesValue,
    type: sharesType === 'basic' || sharesType === 'unknown' ? 'warning' : 'info',
    tooltip: sharesTooltip,
  });
  
  // 4. Terminal value dominance
  const terminalPct = result.terminal_value_check?.terminal_value_pct ?? 0;
  const terminalDominant = terminalPct > 75;
  items.push({
    label: 'Terminal',
    value: `${terminalPct.toFixed(0)}% of EV`,
    type: terminalDominant ? 'warning' : 'info',
    tooltip: terminalDominant 
      ? 'Terminal value dominates (>75%) - valuation highly sensitive to terminal assumptions'
      : 'Terminal value contribution to Enterprise Value',
  });
  
  // 5. Provenance flags (check for fallbacks)
  const hasFallbacks = provenance && Object.values(provenance).some(
    item => item && (item.source === 'fallback' || item.confidence === 'low')
  );
  if (hasFallbacks) {
    items.push({
      label: 'Data',
      value: 'Has Fallbacks',
      type: 'warning',
      tooltip: 'Some metrics use fallback values - check provenance details below',
    });
  }
  
  // 6. Data freshness (NOTES2.md enhancement)
  if (dataFreshnessDays !== undefined) {
    const freshValue = dataIsStale 
      ? `${dataFreshnessDays}d old ⚠️` 
      : `${dataFreshnessDays}d ago`;
    items.push({
      label: 'Data Age',
      value: freshValue,
      type: dataIsStale ? 'warning' : 'info',
      tooltip: dataIsStale 
        ? `Data is ${dataFreshnessDays} days old (last: ${latestStatementDate}). Post-earnings update may be required for accurate valuation.`
        : `Latest financial statement from ${latestStatementDate} (${dataFreshnessDays} days ago)`,
    });
  }
  
  return (
    <div className="flex flex-wrap gap-2 items-center py-2 px-3 bg-gray-50 rounded-lg border border-gray-200">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mr-1">
        Valuation Context:
      </span>
      {items.map((item, idx) => (
        <span
          key={idx}
          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium cursor-help ${
            item.type === 'warning' 
              ? 'bg-amber-100 text-amber-700 border border-amber-200' 
              : item.type === 'custom'
                ? 'bg-blue-100 text-blue-700 border border-blue-200'
                : 'bg-gray-100 text-gray-600 border border-gray-200'
          }`}
          title={item.tooltip}
        >
          <span className="text-gray-400 mr-1">{item.label}:</span>
          {item.value}
        </span>
      ))}
    </div>
  );
}
