import type { TechnicalAnalysisResult } from '../types';
import { GlossaryRef } from './GlossaryRef';

interface InstitutionalTechnicalsProps {
  technicalResult: TechnicalAnalysisResult;
}

export function InstitutionalTechnicals({ technicalResult }: InstitutionalTechnicalsProps) {
  const { indicators } = technicalResult;
  
  // Latest VW-MACD
  const latestVwMacd = indicators.vw_macd?.length ? indicators.vw_macd[indicators.vw_macd.length - 1] : null;
  const latestMacd = indicators.macd?.length ? indicators.macd[indicators.macd.length - 1] : null;
  
  // Latest V-RSI
  const latestVRsi = indicators.v_rsi_14?.length ? indicators.v_rsi_14[indicators.v_rsi_14.length - 1] : null;
  const latestRsi = indicators.rsi_14?.length ? indicators.rsi_14[indicators.rsi_14.length - 1] : null;

  return (
    <div className="space-y-4">
      <div className="text-sm font-semibold text-gray-700 flex items-center">
        Institutional Confirmation
        <GlossaryRef id="institutional-technicals" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* VW-MACD vs MACD */}
        <div className="p-3 bg-gray-50 rounded border border-gray-100">
          <div className="text-xs text-gray-400 uppercase mb-1 flex items-center">
            VW-MACD vs MACD
            <GlossaryRef id="vw-macd" />
          </div>
          {latestVwMacd && latestMacd ? (
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">VW-MACD Hist:</span>
                <span className={latestVwMacd.histogram > 0 ? 'text-emerald-600' : 'text-red-600 font-medium'}>
                  {latestVwMacd.histogram.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <span>Std MACD Hist:</span>
                <span>{latestMacd.histogram.toFixed(4)}</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-2 leading-tight">
                {latestVwMacd.histogram > latestMacd.histogram 
                  ? "Volume confirms bullish momentum" 
                  : "Volume reveals weakening momentum"}
              </div>
            </div>
          ) : (
            <div className="text-xs text-gray-400">Insufficient history</div>
          )}
        </div>

        {/* V-RSI vs RSI */}
        <div className="p-3 bg-gray-50 rounded border border-gray-100">
          <div className="text-xs text-gray-400 uppercase mb-1 flex items-center">
            V-RSI vs RSI
            <GlossaryRef id="v-rsi" />
          </div>
          {latestVRsi && latestRsi ? (
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">V-RSI (Vol):</span>
                <span className="font-medium">{latestVRsi.value.toFixed(1)}</span>
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <span>Std RSI:</span>
                <span>{latestRsi.value.toFixed(1)}</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-2 leading-tight">
                {Math.abs(latestVRsi.value - latestRsi.value) > 5
                  ? `Significant divergence (${(latestVRsi.value - latestRsi.value).toFixed(1)})`
                  : "Price and volume RSI are aligned"}
              </div>
            </div>
          ) : (
            <div className="text-xs text-gray-400">Insufficient history</div>
          )}
        </div>
      </div>
    </div>
  );
}
