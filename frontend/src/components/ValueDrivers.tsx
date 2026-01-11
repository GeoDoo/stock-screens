import type { ValueDriver } from '../types';

interface ValueDriversProps {
  drivers: ValueDriver[];
}

/**
 * ValueDrivers displays a ranked list of inputs by their impact on valuation.
 * Uses true perturb-and-revalue sensitivity (not proxies).
 * Higher bars = more sensitive assumptions = higher model risk.
 */
export function ValueDrivers({ drivers }: ValueDriversProps) {
  if (!drivers || drivers.length === 0) {
    return null;
  }

  // Sort by impact (highest first)
  const sorted = [...drivers].sort((a, b) => b.impact_percent - a.impact_percent);
  const maxImpact = sorted[0]?.impact_percent || 1;

  // Human-readable labels
  const inputLabels: Record<string, string> = {
    discount_rate: 'Discount Rate',
    terminal_growth: 'Terminal Growth',
    revenue_growth: 'Revenue Growth',
    operating_margin: 'Operating Margin',
  };

  // Color based on impact level
  const getBarColor = (impact: number): string => {
    if (impact >= 20) return 'bg-red-500';
    if (impact >= 10) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
        Value Sensitivity
      </div>
      {sorted.map((driver) => (
        <div key={driver.input} className="space-y-1">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-700 font-medium">
              {inputLabels[driver.input] || driver.input}
            </span>
            <span 
              className={`font-mono text-xs ${
                driver.impact_percent >= 20 ? 'text-red-600' : 
                driver.impact_percent >= 10 ? 'text-amber-600' : 
                'text-gray-500'
              }`}
            >
              {driver.impact_percent.toFixed(2)}%
            </span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${getBarColor(driver.impact_percent)}`}
              style={{ width: `${(driver.impact_percent / maxImpact) * 100}%` }}
              title={driver.description}
            />
          </div>
          <div className="text-[10px] text-gray-400 italic">
            {driver.description}
          </div>
        </div>
      ))}
      <div className="text-[10px] text-gray-400 border-t pt-2 mt-3">
        Higher sensitivity = bigger impact from assumption changes
      </div>
    </div>
  );
}
