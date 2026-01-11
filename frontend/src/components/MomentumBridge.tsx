import { GlossaryRef } from './GlossaryRef';

interface MomentumBridgeProps {
  vwmaTrend: 'uptrend' | 'downtrend' | 'flat' | undefined;
  intrinsicValue: number | null;
  currentPrice: number;
}

/**
 * Calculate the Momentum Bridge signal.
 * 
 * This bridges Value (DCF) with Momentum (trend) to avoid:
 * - "Catching falling knives" - buying cheap stocks in downtrends
 * - "Dead Money" - value traps that take years to recover
 * 
 * Signal logic:
 * - BUY: Undervalued (>15% margin) + uptrend/flat
 * - WAIT: Undervalued + downtrend (don't fight the tape)
 * - HOLD: Fair value (within ±10%)
 * - AVOID: Overvalued (<-10% margin)
 */
function getMomentumBridgeSignal(
  intrinsicValue: number | null,
  currentPrice: number,
  vwmaTrend: string | undefined,
): 'buy' | 'wait' | 'hold' | 'avoid' | null {
  if (!intrinsicValue || currentPrice <= 0 || !vwmaTrend) {
    return null;
  }
  
  const margin = (intrinsicValue - currentPrice) / currentPrice;
  
  // Overvalued: IV < 90% of price
  if (margin < -0.10) {
    return 'avoid';
  }
  
  // Undervalued: IV > 115% of price
  if (margin > 0.15) {
    if (vwmaTrend === 'uptrend' || vwmaTrend === 'flat') {
      return 'buy';
    } else {
      return 'wait';
    }
  }
  
  // Fair value
  return 'hold';
}

const signalConfig = {
  buy: {
    label: 'BUY',
    description: 'Value + Momentum aligned',
    bgColor: 'bg-emerald-100',
    textColor: 'text-emerald-700',
    borderColor: 'border-emerald-300',
  },
  wait: {
    label: 'WAIT',
    description: 'Cheap but downtrend — don\'t catch falling knife',
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-300',
  },
  hold: {
    label: 'HOLD',
    description: 'Fair value — no strong action',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-600',
    borderColor: 'border-gray-300',
  },
  avoid: {
    label: 'AVOID',
    description: 'Overvalued',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700',
    borderColor: 'border-red-300',
  },
};

const trendConfig = {
  uptrend: {
    label: 'Uptrend',
    icon: '↗',
    color: 'text-emerald-600',
  },
  downtrend: {
    label: 'Downtrend',
    icon: '↘',
    color: 'text-red-600',
  },
  flat: {
    label: 'Flat',
    icon: '→',
    color: 'text-gray-500',
  },
};

export function MomentumBridge({ 
  vwmaTrend, 
  intrinsicValue, 
  currentPrice 
}: MomentumBridgeProps) {
  const signal = getMomentumBridgeSignal(intrinsicValue, currentPrice, vwmaTrend);
  
  if (!signal || !vwmaTrend) {
    return (
      <div className="p-4 rounded-lg border border-gray-200 bg-gray-50">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
          Momentum Bridge
          <GlossaryRef id="momentum-bridge" />
        </div>
        <div className="text-sm text-gray-500">
          Requires valuation result and 200-day price history
        </div>
      </div>
    );
  }
  
  const signalInfo = signalConfig[signal];
  const trendInfo = trendConfig[vwmaTrend];
  
  // Calculate margin for display
  const margin = intrinsicValue && currentPrice > 0 
    ? ((intrinsicValue - currentPrice) / currentPrice * 100).toFixed(1)
    : null;
  
  return (
    <div className={`p-4 rounded-lg border-2 ${signalInfo.borderColor} ${signalInfo.bgColor}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Momentum Bridge
          <GlossaryRef id="momentum-bridge" />
        </div>
        <span className={`text-lg font-bold ${signalInfo.textColor}`}>
          {signalInfo.label}
        </span>
      </div>
      
      <div className="text-sm text-gray-600 mb-3">
        {signalInfo.description}
      </div>
      
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs text-gray-400 uppercase">200-Day VWMA</div>
          <div className={`font-medium ${trendInfo.color}`}>
            {trendInfo.icon} {trendInfo.label}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 uppercase">Margin of Safety</div>
          <div className={`font-medium ${margin && parseFloat(margin) > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            {margin ? `${margin}%` : '—'}
          </div>
        </div>
      </div>
    </div>
  );
}
