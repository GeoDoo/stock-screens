import { useState } from 'react';
import type { MonteCarloResult, MonteCarloRequest } from '../types';
import { GlossaryRef } from './GlossaryRef';

const API_BASE = 'http://localhost:8000';

interface MonteCarloInputs {
  growth: number;
  growthStd: number;
  margin: number;
  marginStd: number;
  discountRate: number;
  discountStd: number;
  terminalGrowth: number;
  projectionYears: number;
}

interface MonteCarloPanelProps {
  symbol: string;
  provider: string;
  defaultInputs: {
    growth: number;
    margin: number;
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


export function MonteCarloPanel({ 
  symbol, 
  provider, 
  defaultInputs,
  currentPrice,
}: MonteCarloPanelProps) {
  const [inputs, setInputs] = useState<MonteCarloInputs>({
    growth: defaultInputs.growth,
    growthStd: 0.03,  // ±3% default uncertainty
    margin: defaultInputs.margin,
    marginStd: 0.02,  // ±2% default uncertainty
    discountRate: defaultInputs.discountRate,
    discountStd: 0.01,  // ±1% default uncertainty
    terminalGrowth: defaultInputs.terminalGrowth,
    projectionYears: defaultInputs.projectionYears,
  });
  
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  
  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    
    try {
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
      setResult(data);
      setExpanded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };
  
  // Calculate upside/downside from current price
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
  
  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Monte Carlo Simulation<GlossaryRef id="monte-carlo" />
        </h3>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>
      
      {expanded && (
        <>
          {/* Input Controls */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Growth Rate
              </label>
              <div className="flex gap-1">
                <input
                  type="number"
                  value={(inputs.growth * 100).toFixed(1)}
                  onChange={(e) => setInputs(prev => ({ 
                    ...prev, 
                    growth: parseFloat(e.target.value) / 100 
                  }))}
                  className="w-16 px-2 py-1 text-sm border rounded"
                  step="0.5"
                />
                <span className="text-xs text-gray-400 self-center">±</span>
                <input
                  type="number"
                  value={(inputs.growthStd * 100).toFixed(1)}
                  onChange={(e) => setInputs(prev => ({ 
                    ...prev, 
                    growthStd: parseFloat(e.target.value) / 100 
                  }))}
                  className="w-12 px-2 py-1 text-sm border rounded"
                  step="0.5"
                />
                <span className="text-xs text-gray-400 self-center">%</span>
              </div>
            </div>
            
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Op. Margin
              </label>
              <div className="flex gap-1">
                <input
                  type="number"
                  value={(inputs.margin * 100).toFixed(1)}
                  onChange={(e) => setInputs(prev => ({ 
                    ...prev, 
                    margin: parseFloat(e.target.value) / 100 
                  }))}
                  className="w-16 px-2 py-1 text-sm border rounded"
                  step="0.5"
                />
                <span className="text-xs text-gray-400 self-center">±</span>
                <input
                  type="number"
                  value={(inputs.marginStd * 100).toFixed(1)}
                  onChange={(e) => setInputs(prev => ({ 
                    ...prev, 
                    marginStd: parseFloat(e.target.value) / 100 
                  }))}
                  className="w-12 px-2 py-1 text-sm border rounded"
                  step="0.5"
                />
                <span className="text-xs text-gray-400 self-center">%</span>
              </div>
            </div>
            
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Discount Rate
              </label>
              <div className="flex gap-1">
                <input
                  type="number"
                  value={(inputs.discountRate * 100).toFixed(1)}
                  onChange={(e) => setInputs(prev => ({ 
                    ...prev, 
                    discountRate: parseFloat(e.target.value) / 100 
                  }))}
                  className="w-16 px-2 py-1 text-sm border rounded"
                  step="0.5"
                />
                <span className="text-xs text-gray-400 self-center">±</span>
                <input
                  type="number"
                  value={(inputs.discountStd * 100).toFixed(1)}
                  onChange={(e) => setInputs(prev => ({ 
                    ...prev, 
                    discountStd: parseFloat(e.target.value) / 100 
                  }))}
                  className="w-12 px-2 py-1 text-sm border rounded"
                  step="0.5"
                />
                <span className="text-xs text-gray-400 self-center">%</span>
              </div>
            </div>
            
            <div className="flex items-end">
              <button
                onClick={runSimulation}
                disabled={loading}
                className="px-4 py-1 bg-gray-900 text-white text-sm rounded hover:bg-gray-700 disabled:bg-gray-400"
              >
                {loading ? 'Running...' : 'Run 5,000 Simulations'}
              </button>
            </div>
          </div>
          
          {error && (
            <div className="text-red-600 text-sm mb-4">{error}</div>
          )}
          
          {result && (
            <div className="space-y-4">
              {/* Summary Stats */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500 mb-2">
                  {result.valid_simulations.toLocaleString()} valid simulations
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs text-gray-500">Expected Value</div>
                    <div className="text-lg font-semibold">
                      {formatCurrency(result.per_share.mean)}
                    </div>
                    <div className={`text-sm ${getUpsideColor(getUpside(result.per_share.mean))}`}>
                      {getUpside(result.per_share.mean) > 0 ? '+' : ''}{getUpside(result.per_share.mean).toFixed(1)}%
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-xs text-gray-500">Median (50th)</div>
                    <div className="text-lg font-semibold">
                      {formatCurrency(result.per_share.percentiles.p50)}
                    </div>
                    <div className={`text-sm ${getUpsideColor(getUpside(result.per_share.percentiles.p50))}`}>
                      {getUpside(result.per_share.percentiles.p50) > 0 ? '+' : ''}{getUpside(result.per_share.percentiles.p50).toFixed(1)}%
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
                        left: `${((result.per_share.percentiles.p10 - result.per_share.percentiles.min) / 
                               (result.per_share.percentiles.max - result.per_share.percentiles.min)) * 100}%`,
                        width: `${((result.per_share.percentiles.p90 - result.per_share.percentiles.p10) / 
                                (result.per_share.percentiles.max - result.per_share.percentiles.min)) * 100}%`,
                      }}
                    />
                    {/* 25-75 range */}
                    <div 
                      className="absolute h-full bg-gray-500"
                      style={{
                        left: `${((result.per_share.percentiles.p25 - result.per_share.percentiles.min) / 
                               (result.per_share.percentiles.max - result.per_share.percentiles.min)) * 100}%`,
                        width: `${((result.per_share.percentiles.p75 - result.per_share.percentiles.p25) / 
                                (result.per_share.percentiles.max - result.per_share.percentiles.min)) * 100}%`,
                      }}
                    />
                    {/* Median marker */}
                    <div 
                      className="absolute w-0.5 h-full bg-gray-900"
                      style={{
                        left: `${((result.per_share.percentiles.p50 - result.per_share.percentiles.min) / 
                               (result.per_share.percentiles.max - result.per_share.percentiles.min)) * 100}%`,
                      }}
                    />
                    {/* Current price marker */}
                    {currentPrice >= result.per_share.percentiles.min && 
                     currentPrice <= result.per_share.percentiles.max && (
                      <div 
                        className="absolute w-0.5 h-full bg-blue-500"
                        style={{
                          left: `${((currentPrice - result.per_share.percentiles.min) / 
                                 (result.per_share.percentiles.max - result.per_share.percentiles.min)) * 100}%`,
                        }}
                      />
                    )}
                  </div>
                  
                  {/* Labels */}
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>{formatCurrency(result.per_share.percentiles.p10)} (10th)</span>
                    <span>{formatCurrency(result.per_share.percentiles.p50)} (median)</span>
                    <span>{formatCurrency(result.per_share.percentiles.p90)} (90th)</span>
                  </div>
                  
                  {/* Current price indicator when outside range */}
                  {currentPrice > result.per_share.percentiles.max && (
                    <div className="text-xs text-red-600 mt-1 text-right">
                      Current price ({formatCurrency(currentPrice)}) exceeds all simulated values →
                    </div>
                  )}
                  {currentPrice < result.per_share.percentiles.min && (
                    <div className="text-xs text-emerald-600 mt-1 text-left">
                      ← Current price ({formatCurrency(currentPrice)}) below all simulated values
                    </div>
                  )}
                </div>
              </div>
              
              {/* Probability Table */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(result.per_share.percentiles.p10))}`}>
                  <div className="text-xs text-gray-500">Bear Case (10th<GlossaryRef id="percentile" />)</div>
                  <div className="font-medium">{formatCurrency(result.per_share.percentiles.p10)}</div>
                  <div className={getUpsideColor(getUpside(result.per_share.percentiles.p10))}>
                    {formatUpside(getUpside(result.per_share.percentiles.p10))}
                  </div>
                </div>
                
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(result.per_share.percentiles.p25))}`}>
                  <div className="text-xs text-gray-500">Conservative (25th)</div>
                  <div className="font-medium">{formatCurrency(result.per_share.percentiles.p25)}</div>
                  <div className={getUpsideColor(getUpside(result.per_share.percentiles.p25))}>
                    {formatUpside(getUpside(result.per_share.percentiles.p25))}
                  </div>
                </div>
                
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(result.per_share.percentiles.p75))}`}>
                  <div className="text-xs text-gray-500">Base Case (75th)</div>
                  <div className="font-medium">{formatCurrency(result.per_share.percentiles.p75)}</div>
                  <div className={getUpsideColor(getUpside(result.per_share.percentiles.p75))}>
                    {formatUpside(getUpside(result.per_share.percentiles.p75))}
                  </div>
                </div>
                
                <div className={`p-2 rounded ${getBackgroundColor(getUpside(result.per_share.percentiles.p90))}`}>
                  <div className="text-xs text-gray-500">Bull Case (90th)</div>
                  <div className="font-medium">{formatCurrency(result.per_share.percentiles.p90)}</div>
                  <div className={getUpsideColor(getUpside(result.per_share.percentiles.p90))}>
                    {formatUpside(getUpside(result.per_share.percentiles.p90))}
                  </div>
                </div>
              </div>
              
              {/* Overall Assessment */}
              {(() => {
                const p90Upside = getUpside(result.per_share.percentiles.p90);
                const p10Upside = getUpside(result.per_share.percentiles.p10);
                const medianUpside = getUpside(result.per_share.percentiles.p50);
                
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
              <div className="text-xs text-gray-500 border-t pt-2">
                <p>
                  <strong>Interpretation:</strong> There's a 90% chance the stock is worth more than{' '}
                  <span className="font-medium">{formatCurrency(result.per_share.percentiles.p10)}</span>{' '}
                  and a 50% chance it's worth more than{' '}
                  <span className="font-medium">{formatCurrency(result.per_share.percentiles.p50)}</span>.
                </p>
              </div>
            </div>
          )}
          
          {!result && !loading && (
            <div className="text-sm text-gray-500 text-center py-4">
              Adjust uncertainty ranges (±) and run simulation to see value distribution
            </div>
          )}
        </>
      )}
      
      {!expanded && result && (
        <div className="text-sm text-gray-600">
          Expected: {formatCurrency(result.per_share.mean)} | 
          10th-90th: {formatCurrency(result.per_share.percentiles.p10)} - {formatCurrency(result.per_share.percentiles.p90)}
        </div>
      )}
    </div>
  );
}
