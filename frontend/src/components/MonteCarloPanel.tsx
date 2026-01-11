import { useState } from 'react';
import type { MonteCarloResult, MonteCarloRequest, FullMonteCarloResult, FullMonteCarloRequest } from '../types';
import { GlossaryRef } from './GlossaryRef';

import { API_BASE } from '../config';

type MCMode = 'quick' | 'decision';

interface MonteCarloInputs {
  growth: number;
  growthStd: number;
  margin: number;
  marginStd: number;
  daRatio: number;
  daRatioStd: number;
  capexRatio: number;
  capexRatioStd: number;
  wcRatio: number;
  wcRatioStd: number;
  discountRate: number;
  discountStd: number;
  terminalGrowth: number;
  terminalGrowthStd: number;
  projectionYears: number;
  // Correlations
  growthMarginCorr: number;
  growthCapexCorr: number;
  // Fat tails (Student's t-distribution)
  fatTailsDf: number | null;
}

interface MonteCarloPanelProps {
  symbol: string;
  provider: string;
  defaultInputs: {
    growth: number;
    margin: number;
    daRatio?: number;
    capexRatio?: number;
    wcRatio?: number;
    taxRate?: number;
    discountRate: number;
    terminalGrowth: number;
    projectionYears: number;
  };
  currentPrice: number;
}

const formatCurrency = (value: number): string => {
  if (Math.abs(value) >= 1e9) {
    return `$${(value / 1e9).toFixed(1)}B`;
  } else if (Math.abs(value) >= 1e6) {
    return `$${(value / 1e6).toFixed(1)}M`;
  }
  return `$${value.toFixed(2)}`;
};

const formatPercent = (value: number, decimals = 0): string => {
  return `${(value * 100).toFixed(decimals)}%`;
};


export function MonteCarloPanel({ 
  symbol, 
  provider, 
  defaultInputs,
  currentPrice,
}: MonteCarloPanelProps) {
  const [mode, setMode] = useState<MCMode>('decision');
  const [inputs, setInputs] = useState<MonteCarloInputs>({
    growth: defaultInputs.growth,
    growthStd: 0.03,
    margin: defaultInputs.margin,
    marginStd: 0.02,
    daRatio: defaultInputs.daRatio || 0.05,
    daRatioStd: 0.01,
    capexRatio: defaultInputs.capexRatio || 0.06,
    capexRatioStd: 0.02,
    wcRatio: defaultInputs.wcRatio || 0.10,
    wcRatioStd: 0.02,
    discountRate: defaultInputs.discountRate,
    discountStd: 0.01,
    terminalGrowth: defaultInputs.terminalGrowth,
    terminalGrowthStd: 0.005,
    projectionYears: defaultInputs.projectionYears,
    growthMarginCorr: -0.2,
    growthCapexCorr: 0.3,
    fatTailsDf: null,  // null = Normal distribution
  });
  
  const [quickResult, setQuickResult] = useState<MonteCarloResult | null>(null);
  const [fullResult, setFullResult] = useState<FullMonteCarloResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  
  const result = mode === 'decision' ? fullResult : quickResult;
  
  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (mode === 'quick') {
        const request: MonteCarloRequest = {
          base_growth: inputs.growth,
          growth_std: inputs.growthStd,
          base_margin: inputs.margin,
          margin_std: inputs.marginStd,
          base_discount_rate: inputs.discountRate,
          discount_std: inputs.discountStd,
          terminal_growth: inputs.terminalGrowth,
          projection_years: inputs.projectionYears,
          iterations: 5000,
        };
        
        const response = await fetch(
          `${API_BASE}/api/stock/${symbol}/monte-carlo?provider=${provider}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
          }
        );
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Simulation failed');
        }
        
        const data = await response.json();
        setQuickResult(data);
      } else {
        // Full-model Monte Carlo
        const request: FullMonteCarloRequest = {
          base_growth: inputs.growth,
          base_margin: inputs.margin,
          base_da_ratio: inputs.daRatio,
          base_capex_ratio: inputs.capexRatio,
          base_wc_ratio: inputs.wcRatio,
          base_tax_rate: defaultInputs.taxRate || 0.25,
          base_discount_rate: inputs.discountRate,
          base_terminal_growth: inputs.terminalGrowth,
          growth_std: inputs.growthStd,
          margin_std: inputs.marginStd,
          da_ratio_std: inputs.daRatioStd,
          capex_ratio_std: inputs.capexRatioStd,
          wc_ratio_std: inputs.wcRatioStd,
          discount_std: inputs.discountStd,
          terminal_growth_std: inputs.terminalGrowthStd,
          projection_years: inputs.projectionYears,
          iterations: 5000,
          growth_margin_correlation: inputs.growthMarginCorr,
          growth_capex_correlation: inputs.growthCapexCorr,
          fat_tails_df: inputs.fatTailsDf,
        };
        
        const response = await fetch(
          `${API_BASE}/api/stock/${symbol}/monte-carlo-full?provider=${provider}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
          }
        );
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Simulation failed');
        }
        
        const data = await response.json();
        setFullResult(data);
      }
      
      setExpanded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };
  
  const getUpside = (value: number): number => {
    return ((value - currentPrice) / currentPrice) * 100;
  };
  
  const getUpsideColor = (upside: number): string => {
    if (upside > 20) return 'text-emerald-600';
    if (upside > 0) return 'text-emerald-500';
    if (upside > -20) return 'text-amber-600';
    return 'text-red-600';
  };
  
  const getBackgroundColor = (upside: number): string => {
    if (upside > 20) return 'bg-emerald-100';
    if (upside > 0) return 'bg-emerald-50';
    if (upside > -20) return 'bg-amber-50';
    return 'bg-red-50';
  };
  
  const formatUpside = (upside: number): string => {
    const sign = upside > 0 ? '+' : '';
    return `${sign}${upside.toFixed(0)}%`;
  };
  
  // Get per-share data regardless of mode
  // Both quick and full mode have per_share, but full mode adds median and std_dev
  const perShare = result && 'per_share' in result 
    ? result.per_share as { 
        mean: number; 
        median?: number; 
        std_dev?: number; 
        percentiles: import('../types').MonteCarloPercentiles; 
      } 
    : null;
  
  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Monte Carlo Simulation<GlossaryRef id="monte-carlo" />
        </h3>
        <div className="flex items-center gap-3">
          {/* Mode Toggle */}
          <div className="flex text-xs border rounded overflow-hidden">
            <button
              onClick={() => setMode('quick')}
              className={`px-2 py-1 ${mode === 'quick' ? 'bg-gray-200 font-medium' : 'bg-white hover:bg-gray-50'}`}
            >
              Quick
            </button>
            <button
              onClick={() => setMode('decision')}
              className={`px-2 py-1 ${mode === 'decision' ? 'bg-gray-900 text-white font-medium' : 'bg-white hover:bg-gray-50'}`}
            >
              Decision
            </button>
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            {expanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>
      
      {expanded && (
        <>
          {/* Mode Description */}
          <div className={`text-xs mb-4 p-2 rounded border-l-2 ${
            mode === 'quick' 
              ? 'text-gray-500 bg-gray-50 border-gray-300' 
              : 'text-emerald-700 bg-emerald-50 border-emerald-400'
          }`}>
            {mode === 'quick' ? (
              <>
                <strong>Quick Mode:</strong> Simplified FCF model (Revenue × Margin × 0.75). 
                Best for visualizing uncertainty, not precise valuations.
              </>
            ) : (
              <>
                <strong>Decision Mode:</strong> Full DCF engine with NOPAT, D&A, CapEx, WC, 
                bounded distributions, and input correlations. Use for investment decisions.
              </>
            )}
          </div>
          
          {/* Input Controls */}
          <div className="space-y-4 mb-4">
            {/* Row 1: Core inputs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Growth Rate</label>
                <div className="flex gap-1 items-center">
                  <input
                    type="number"
                    value={(inputs.growth * 100).toFixed(1)}
                    onChange={(e) => setInputs(prev => ({ ...prev, growth: parseFloat(e.target.value) / 100 }))}
                    className="w-16 px-2 py-1 text-sm border rounded"
                    step="0.5"
                  />
                  <span className="text-xs text-gray-400">±</span>
                  <input
                    type="number"
                    value={(inputs.growthStd * 100).toFixed(1)}
                    onChange={(e) => setInputs(prev => ({ ...prev, growthStd: parseFloat(e.target.value) / 100 }))}
                    className="w-14 px-2 py-1 text-sm border rounded"
                    step="0.5"
                  />
                  <span className="text-xs text-gray-400">%</span>
                </div>
              </div>
              
              <div>
                <label className="block text-xs text-gray-500 mb-1">Op. Margin</label>
                <div className="flex gap-1 items-center">
                  <input
                    type="number"
                    value={(inputs.margin * 100).toFixed(1)}
                    onChange={(e) => setInputs(prev => ({ ...prev, margin: parseFloat(e.target.value) / 100 }))}
                    className="w-16 px-2 py-1 text-sm border rounded"
                    step="0.5"
                  />
                  <span className="text-xs text-gray-400">±</span>
                  <input
                    type="number"
                    value={(inputs.marginStd * 100).toFixed(1)}
                    onChange={(e) => setInputs(prev => ({ ...prev, marginStd: parseFloat(e.target.value) / 100 }))}
                    className="w-14 px-2 py-1 text-sm border rounded"
                    step="0.5"
                  />
                  <span className="text-xs text-gray-400">%</span>
                </div>
              </div>
              
              <div>
                <label className="block text-xs text-gray-500 mb-1">Discount Rate</label>
                <div className="flex gap-1 items-center">
                  <input
                    type="number"
                    value={(inputs.discountRate * 100).toFixed(1)}
                    onChange={(e) => setInputs(prev => ({ ...prev, discountRate: parseFloat(e.target.value) / 100 }))}
                    className="w-16 px-2 py-1 text-sm border rounded"
                    step="0.5"
                  />
                  <span className="text-xs text-gray-400">±</span>
                  <input
                    type="number"
                    value={(inputs.discountStd * 100).toFixed(1)}
                    onChange={(e) => setInputs(prev => ({ ...prev, discountStd: parseFloat(e.target.value) / 100 }))}
                    className="w-14 px-2 py-1 text-sm border rounded"
                    step="0.5"
                  />
                  <span className="text-xs text-gray-400">%</span>
                </div>
              </div>
              
              <div>
                <label className="block text-xs text-gray-500 mb-1">Terminal Growth</label>
                <div className="flex gap-1 items-center">
                  <input
                    type="number"
                    value={(inputs.terminalGrowth * 100).toFixed(1)}
                    onChange={(e) => setInputs(prev => ({ ...prev, terminalGrowth: parseFloat(e.target.value) / 100 }))}
                    className="w-16 px-2 py-1 text-sm border rounded"
                    step="0.5"
                  />
                  {mode === 'decision' && (
                    <>
                      <span className="text-xs text-gray-400">±</span>
                      <input
                        type="number"
                        value={(inputs.terminalGrowthStd * 100).toFixed(2)}
                        onChange={(e) => setInputs(prev => ({ ...prev, terminalGrowthStd: parseFloat(e.target.value) / 100 }))}
                        className="w-14 px-2 py-1 text-sm border rounded"
                        step="0.1"
                      />
                    </>
                  )}
                  <span className="text-xs text-gray-400">%</span>
                </div>
              </div>
            </div>
            
            {/* Row 2: Decision-mode only inputs */}
            {mode === 'decision' && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">D&A Ratio</label>
                    <div className="flex gap-1 items-center">
                      <input
                        type="number"
                        value={(inputs.daRatio * 100).toFixed(1)}
                        onChange={(e) => setInputs(prev => ({ ...prev, daRatio: parseFloat(e.target.value) / 100 }))}
                        className="w-16 px-2 py-1 text-sm border rounded"
                        step="0.5"
                      />
                      <span className="text-xs text-gray-400">±</span>
                      <input
                        type="number"
                        value={(inputs.daRatioStd * 100).toFixed(1)}
                        onChange={(e) => setInputs(prev => ({ ...prev, daRatioStd: parseFloat(e.target.value) / 100 }))}
                        className="w-14 px-2 py-1 text-sm border rounded"
                        step="0.1"
                      />
                      <span className="text-xs text-gray-400">%</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">CapEx Ratio</label>
                    <div className="flex gap-1 items-center">
                      <input
                        type="number"
                        value={(inputs.capexRatio * 100).toFixed(1)}
                        onChange={(e) => setInputs(prev => ({ ...prev, capexRatio: parseFloat(e.target.value) / 100 }))}
                        className="w-16 px-2 py-1 text-sm border rounded"
                        step="0.5"
                      />
                      <span className="text-xs text-gray-400">±</span>
                      <input
                        type="number"
                        value={(inputs.capexRatioStd * 100).toFixed(1)}
                        onChange={(e) => setInputs(prev => ({ ...prev, capexRatioStd: parseFloat(e.target.value) / 100 }))}
                        className="w-14 px-2 py-1 text-sm border rounded"
                        step="0.5"
                      />
                      <span className="text-xs text-gray-400">%</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">WC Ratio</label>
                    <div className="flex gap-1 items-center">
                      <input
                        type="number"
                        value={(inputs.wcRatio * 100).toFixed(1)}
                        onChange={(e) => setInputs(prev => ({ ...prev, wcRatio: parseFloat(e.target.value) / 100 }))}
                        className="w-16 px-2 py-1 text-sm border rounded"
                        step="0.5"
                      />
                      <span className="text-xs text-gray-400">±</span>
                      <input
                        type="number"
                        value={(inputs.wcRatioStd * 100).toFixed(1)}
                        onChange={(e) => setInputs(prev => ({ ...prev, wcRatioStd: parseFloat(e.target.value) / 100 }))}
                        className="w-14 px-2 py-1 text-sm border rounded"
                        step="0.5"
                      />
                      <span className="text-xs text-gray-400">%</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Years</label>
                    <input
                      type="number"
                      value={inputs.projectionYears}
                      onChange={(e) => setInputs(prev => ({ ...prev, projectionYears: parseInt(e.target.value) || 5 }))}
                      className="w-16 px-2 py-1 text-sm border rounded"
                      min="3"
                      max="15"
                    />
                  </div>
                </div>
                
                {/* Correlations */}
                <div className="flex gap-6 items-center">
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-gray-500">Growth↔Margin</label>
                    <input
                      type="number"
                      value={inputs.growthMarginCorr.toFixed(1)}
                      onChange={(e) => setInputs(prev => ({ ...prev, growthMarginCorr: parseFloat(e.target.value) }))}
                      className="w-16 px-2 py-1 text-sm border rounded"
                      step="0.1"
                      min="-1"
                      max="1"
                    />
                    <span className="text-xs text-gray-400">(-1 to 1)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-gray-500">Growth↔CapEx</label>
                    <input
                      type="number"
                      value={inputs.growthCapexCorr.toFixed(1)}
                      onChange={(e) => setInputs(prev => ({ ...prev, growthCapexCorr: parseFloat(e.target.value) }))}
                      className="w-16 px-2 py-1 text-sm border rounded"
                      step="0.1"
                      min="-1"
                      max="1"
                    />
                  </div>
                </div>
                
                {/* Fat Tails (Risk Model) */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="fatTails"
                      checked={inputs.fatTailsDf !== null}
                      onChange={(e) => setInputs(prev => ({ 
                        ...prev, 
                        fatTailsDf: e.target.checked ? 4 : null 
                      }))}
                      className="rounded"
                    />
                    <label htmlFor="fatTails" className="text-xs text-gray-500 cursor-pointer">
                      Fat Tails (Student's t)
                    </label>
                  </div>
                  {inputs.fatTailsDf !== null && (
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-gray-500">df:</label>
                      <input
                        type="number"
                        value={inputs.fatTailsDf}
                        onChange={(e) => setInputs(prev => ({ 
                          ...prev, 
                          fatTailsDf: Math.max(3, parseFloat(e.target.value) || 4)
                        }))}
                        className="w-16 px-2 py-1 text-sm border rounded"
                        step="1"
                        min="3"
                        max="100"
                      />
                      <span 
                        className="text-xs text-gray-400 cursor-help" 
                        title="Degrees of freedom. Lower = fatter tails (more extreme events). Recommended: 3-4 for realistic market crashes. Must be ≥3 for valid math."
                      >
                        (3-100)
                      </span>
                    </div>
                  )}
                </div>
              </>
            )}
            
            {/* Run Button */}
            <div>
              <button
                onClick={runSimulation}
                disabled={loading}
                className="px-4 py-2 bg-gray-900 text-white text-sm rounded hover:bg-gray-700 disabled:bg-gray-400"
              >
                {loading ? 'Running...' : `Run 5,000 ${mode === 'decision' ? 'Full-Model' : ''} Simulations`}
              </button>
            </div>
          </div>
          
          {error && (
            <div className="text-red-600 text-sm mb-4">{error}</div>
          )}
          
          {perShare && (
            <div className="space-y-4">
              {/* Decision Metrics (Full-Model Only) */}
              {mode === 'decision' && fullResult?.decision_metrics && (
                <div className="bg-gray-900 text-white rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-3">Decision Metrics</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-xs text-gray-400">P(Undervalued)</div>
                      <div className={`text-lg font-semibold ${
                        fullResult.decision_metrics.probability_positive_upside > 0.7 
                          ? 'text-emerald-400' 
                          : fullResult.decision_metrics.probability_positive_upside > 0.5 
                            ? 'text-yellow-400' 
                            : 'text-red-400'
                      }`}>
                        {formatPercent(fullResult.decision_metrics.probability_positive_upside)}
                      </div>
                      <div className="text-xs text-gray-500">IV {'>'} Price</div>
                    </div>
                    
                    <div>
                      <div className="text-xs text-gray-400">P(20%+ Upside)</div>
                      <div className={`text-lg font-semibold ${
                        fullResult.decision_metrics.probability_20pct_upside > 0.5 
                          ? 'text-emerald-400' 
                          : fullResult.decision_metrics.probability_20pct_upside > 0.3 
                            ? 'text-yellow-400' 
                            : 'text-gray-400'
                      }`}>
                        {formatPercent(fullResult.decision_metrics.probability_20pct_upside)}
                      </div>
                      <div className="text-xs text-gray-500">IV {'>'} Price × 1.2</div>
                    </div>
                    
                    <div>
                      <div className="text-xs text-gray-400">P(20%+ Loss)</div>
                      <div className={`text-lg font-semibold ${
                        fullResult.decision_metrics.probability_20pct_downside > 0.3 
                          ? 'text-red-400' 
                          : fullResult.decision_metrics.probability_20pct_downside > 0.15 
                            ? 'text-yellow-400' 
                            : 'text-emerald-400'
                      }`}>
                        {formatPercent(fullResult.decision_metrics.probability_20pct_downside)}
                      </div>
                      <div className="text-xs text-gray-500">IV {'<'} Price × 0.8</div>
                    </div>
                    
                    <div>
                      <div className="text-xs text-gray-400">CVaR 10%<GlossaryRef id="cvar" /></div>
                      <div className="text-lg font-semibold">
                        {formatCurrency(fullResult.decision_metrics.cvar_10)}
                      </div>
                      <div className="text-xs text-gray-500">Worst 10% avg</div>
                    </div>
                  </div>
                  
                  {/* Margin of Safety */}
                  <div className="mt-4 pt-3 border-t border-gray-700">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400">Margin of Safety<GlossaryRef id="margin-of-safety" /></span>
                      <div className="text-right">
                        <span className={`font-medium ${
                          fullResult.decision_metrics.margin_of_safety_median > 0.2 
                            ? 'text-emerald-400' 
                            : fullResult.decision_metrics.margin_of_safety_median > 0 
                              ? 'text-yellow-400' 
                              : 'text-red-400'
                        }`}>
                          {formatPercent(fullResult.decision_metrics.margin_of_safety_median, 1)} median
                        </span>
                        <span className="text-gray-500 ml-2">
                          ({formatPercent(fullResult.decision_metrics.margin_of_safety_mean, 1)} mean)
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* P2: Simulation Quality Warnings */}
                  {fullResult.warnings && fullResult.warnings.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-gray-700 space-y-2">
                      {fullResult.warnings.map((warning, idx) => (
                        <div 
                          key={idx} 
                          className={`text-xs rounded px-2 py-1 ${
                            warning.includes('CRITICAL') 
                              ? 'bg-red-900 text-red-200' 
                              : warning.includes('WARNING') 
                                ? 'bg-amber-900 text-amber-200' 
                                : 'bg-gray-700 text-gray-300'
                          }`}
                        >
                          {warning}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              
              {/* Summary Stats */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500 mb-2">
                  {result?.valid_simulations?.toLocaleString() || 0} valid simulations
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs text-gray-500">Expected Value</div>
                    <div className="text-lg font-semibold">
                      {formatCurrency(perShare.mean)}
                    </div>
                    <div className={`text-sm ${getUpsideColor(getUpside(perShare.mean))}`}>
                      {formatUpside(getUpside(perShare.mean))}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-xs text-gray-500">Median (50th)</div>
                    <div className="text-lg font-semibold">
                      {formatCurrency(perShare.median || perShare.percentiles.p50)}
                    </div>
                    <div className={`text-sm ${getUpsideColor(getUpside(perShare.median || perShare.percentiles.p50))}`}>
                      {formatUpside(getUpside(perShare.median || perShare.percentiles.p50))}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-xs text-gray-500">Current Price</div>
                    <div className="text-lg font-semibold">
                      {formatCurrency(currentPrice)}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Percentile Distribution */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Value Distribution (Per Share)
                </h4>
                <div className="relative">
                  {/* Visual Bar */}
                  <div className="h-8 bg-gray-100 rounded relative overflow-hidden">
                    {/* 10-90 range */}
                    <div 
                      className="absolute h-full bg-gray-300"
                      style={{
                        left: `${((perShare.percentiles.p10 - perShare.percentiles.min) / 
                               (perShare.percentiles.max - perShare.percentiles.min)) * 100}%`,
                        width: `${((perShare.percentiles.p90 - perShare.percentiles.p10) / 
                                (perShare.percentiles.max - perShare.percentiles.min)) * 100}%`,
                      }}
                    />
                    {/* 25-75 range */}
                    <div 
                      className="absolute h-full bg-gray-500"
                      style={{
                        left: `${((perShare.percentiles.p25 - perShare.percentiles.min) / 
                               (perShare.percentiles.max - perShare.percentiles.min)) * 100}%`,
                        width: `${((perShare.percentiles.p75 - perShare.percentiles.p25) / 
                                (perShare.percentiles.max - perShare.percentiles.min)) * 100}%`,
                      }}
                    />
                    {/* Median marker */}
                    <div 
                      className="absolute w-0.5 h-full bg-gray-900"
                      style={{
                        left: `${((perShare.percentiles.p50 - perShare.percentiles.min) / 
                               (perShare.percentiles.max - perShare.percentiles.min)) * 100}%`,
                      }}
                    />
                    {/* Current price marker */}
                    {currentPrice >= perShare.percentiles.min && 
                     currentPrice <= perShare.percentiles.max && (
                      <div 
                        className="absolute w-0.5 h-full bg-blue-500"
                        style={{
                          left: `${((currentPrice - perShare.percentiles.min) / 
                                 (perShare.percentiles.max - perShare.percentiles.min)) * 100}%`,
                        }}
                      />
                    )}
                  </div>
                  
                  {/* Labels */}
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>{formatCurrency(perShare.percentiles.p10)} (10th)</span>
                    <span>{formatCurrency(perShare.percentiles.p50)} (median)</span>
                    <span>{formatCurrency(perShare.percentiles.p90)} (90th)</span>
                  </div>
                  
                  {/* Current price indicator when outside range */}
                  {currentPrice > perShare.percentiles.max && (
                    <div className="text-xs text-red-600 mt-1 text-right">
                      Current price ({formatCurrency(currentPrice)}) exceeds all simulated values
                    </div>
                  )}
                  {currentPrice < perShare.percentiles.min && (
                    <div className="text-xs text-emerald-600 mt-1 text-left">
                      Current price ({formatCurrency(currentPrice)}) below all simulated values
                    </div>
                  )}
                </div>
              </div>
              
              {/* Probability Table */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(perShare.percentiles.p10))}`}>
                  <div className="text-xs text-gray-500">Bear Case (10th<GlossaryRef id="percentile" />)</div>
                  <div className="font-medium">{formatCurrency(perShare.percentiles.p10)}</div>
                  <div className={getUpsideColor(getUpside(perShare.percentiles.p10))}>
                    {formatUpside(getUpside(perShare.percentiles.p10))}
                  </div>
                </div>
                
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(perShare.percentiles.p25))}`}>
                  <div className="text-xs text-gray-500">Conservative (25th)</div>
                  <div className="font-medium">{formatCurrency(perShare.percentiles.p25)}</div>
                  <div className={getUpsideColor(getUpside(perShare.percentiles.p25))}>
                    {formatUpside(getUpside(perShare.percentiles.p25))}
                  </div>
                </div>
                
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(perShare.percentiles.p75))}`}>
                  <div className="text-xs text-gray-500">Base Case (75th)</div>
                  <div className="font-medium">{formatCurrency(perShare.percentiles.p75)}</div>
                  <div className={getUpsideColor(getUpside(perShare.percentiles.p75))}>
                    {formatUpside(getUpside(perShare.percentiles.p75))}
                  </div>
                </div>
                
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(perShare.percentiles.p90))}`}>
                  <div className="text-xs text-gray-500">Bull Case (90th)</div>
                  <div className="font-medium">{formatCurrency(perShare.percentiles.p90)}</div>
                  <div className={getUpsideColor(getUpside(perShare.percentiles.p90))}>
                    {formatUpside(getUpside(perShare.percentiles.p90))}
                  </div>
                </div>
              </div>
              
              {/* Overall Assessment */}
              {(() => {
                const p90Upside = getUpside(perShare.percentiles.p90);
                const p10Upside = getUpside(perShare.percentiles.p10);
                const medianUpside = getUpside(perShare.percentiles.p50);
                
                let assessment = '';
                let assessmentColor = '';
                
                if (p90Upside < -30) {
                  assessment = 'Significantly Overvalued — Even the most optimistic scenario suggests substantial downside';
                  assessmentColor = 'text-red-700 bg-red-50';
                } else if (p90Upside < 0) {
                  assessment = 'Overvalued — All scenarios suggest the stock is priced above fair value';
                  assessmentColor = 'text-red-600 bg-red-50';
                } else if (p10Upside > 30) {
                  assessment = 'Significantly Undervalued — Even conservative scenarios show substantial upside';
                  assessmentColor = 'text-emerald-700 bg-emerald-50';
                } else if (p10Upside > 0) {
                  assessment = 'Undervalued — All scenarios suggest upside potential';
                  assessmentColor = 'text-emerald-600 bg-emerald-50';
                } else if (medianUpside > 10) {
                  assessment = 'Fairly Valued to Slightly Undervalued — Median suggests moderate upside';
                  assessmentColor = 'text-emerald-600 bg-emerald-50';
                } else if (medianUpside < -10) {
                  assessment = 'Fairly Valued to Slightly Overvalued — Median suggests moderate downside';
                  assessmentColor = 'text-amber-600 bg-amber-50';
                } else {
                  assessment = 'Fairly Valued — Price is within the expected range';
                  assessmentColor = 'text-gray-600 bg-gray-50';
                }
                
                return (
                  <div className={`text-sm font-medium px-3 py-2 rounded ${assessmentColor}`}>
                    {assessment}
                  </div>
                );
              })()}
              
              {/* Interpretation */}
              <div className="text-xs text-gray-500 border-t pt-2 space-y-1">
                <p>
                  <strong>Interpretation:</strong> There's a 90% chance the stock is worth more than{' '}
                  <span className="font-medium">{formatCurrency(perShare.percentiles.p10)}</span>{' '}
                  and a 50% chance it's worth more than{' '}
                  <span className="font-medium">{formatCurrency(perShare.percentiles.p50)}</span>.
                </p>
                {mode === 'quick' && (
                  <p className="text-gray-400 italic">
                    Note: Quick mode uses a simplified model. Switch to Decision mode for precise valuations.
                  </p>
                )}
              </div>
            </div>
          )}
          
          {!result && !loading && (
            <div className="text-sm text-gray-500 text-center py-4">
              Adjust inputs and run simulation to see value distribution
            </div>
          )}
        </>
      )}
      
      {!expanded && result && perShare && (
        <div className="text-sm text-gray-600">
          Expected: {formatCurrency(perShare.mean)} | 
          10th-90th: {formatCurrency(perShare.percentiles.p10)} - {formatCurrency(perShare.percentiles.p90)}
          {mode === 'decision' && fullResult?.decision_metrics && (
            <span className="ml-2 text-xs">
              | P(undervalued): {formatPercent(fullResult.decision_metrics.probability_positive_upside)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
