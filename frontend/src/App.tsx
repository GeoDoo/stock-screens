import { useState } from 'react';
import type { StockDataResponse, ValuationRequest, ValuationResult } from './types';

const API_BASE = 'http://localhost:8000';

function formatCurrency(value: number | null): string {
  if (value === null) return '—';
  if (Math.abs(value) >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  return `$${value.toFixed(2)}`;
}

function formatPercent(value: number | null): string {
  if (value === null) return '—';
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null, decimals = 2): string {
  if (value === null) return '—';
  return value.toFixed(decimals);
}

export default function App() {
  const [ticker, setTicker] = useState('');
  const [stockData, setStockData] = useState<StockDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ValuationResult | null>(null);
  
  // User inputs
  const [revenueGrowth, setRevenueGrowth] = useState('');
  const [operatingMargin, setOperatingMargin] = useState('');
  const [terminalGrowth, setTerminalGrowth] = useState('3');
  const [marketRiskPremium, setMarketRiskPremium] = useState('6');
  const [projectionYears, setProjectionYears] = useState('10');

  const fetchStock = async () => {
    if (!ticker.trim()) return;
    
    setLoading(true);
    setError(null);
    setStockData(null);
    setResult(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${ticker.toUpperCase()}`);
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to fetch stock data');
      }
      const data: StockDataResponse = await res.json();
      setStockData(data);
      
      // Pre-fill inputs with hints
      if (data.hints.revenue_growth !== null) {
        setRevenueGrowth((data.hints.revenue_growth * 100).toFixed(2));
      }
      if (data.hints.operating_margin !== null) {
        setOperatingMargin((data.hints.operating_margin * 100).toFixed(2));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const runValuation = async () => {
    if (!stockData) return;
    
    setLoading(true);
    setError(null);
    
    const request: ValuationRequest = {
      revenue_growth: parseFloat(revenueGrowth) / 100,
      operating_margin: parseFloat(operatingMargin) / 100,
      terminal_growth_rate: parseFloat(terminalGrowth) / 100,
      market_risk_premium: parseFloat(marketRiskPremium) / 100,
      projection_years: parseInt(projectionYears),
    };
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${stockData.symbol}/valuation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Valuation failed');
      }
      const data: ValuationResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const hasInputs = revenueGrowth && operatingMargin && terminalGrowth && marketRiskPremium && projectionYears;
  const hasValidationErrors = stockData?.validation?.has_errors ?? false;
  const canRunValuation = hasInputs && !hasValidationErrors;

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <div className="max-w-6xl mx-auto px-6 py-16">
        {/* Header */}
        <header className="mb-16">
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900">Stock Valuation</h1>
          <p className="text-sm text-gray-400 mt-1">DCF Analysis</p>
        </header>

        {/* Search */}
        <section className="mb-16">
          <div className="flex gap-4 max-w-xl">
            <input
              type="text"
              placeholder="Enter ticker (e.g., AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && fetchStock()}
              className="flex-1 px-4 py-3 text-base font-mono font-medium bg-white border-2 border-gray-200 rounded-lg outline-none transition-colors focus:border-gray-400 placeholder:text-gray-400 placeholder:font-normal"
            />
            <button
              onClick={fetchStock}
              disabled={loading || !ticker.trim()}
              className="px-8 py-3 text-sm font-semibold bg-gray-900 text-white rounded-lg transition-opacity hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Analyze'}
            </button>
          </div>
          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        </section>

        {stockData && (
          <>
            {/* Validation Alerts */}
            {(stockData.validation.has_errors || stockData.validation.has_warnings) && (
              <section className="mb-8 space-y-4">
                {stockData.validation.errors.length > 0 && (
                  <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
                    <h3 className="text-sm font-semibold text-red-600 mb-3">⛔ Cannot Run Valuation</h3>
                    <ul className="space-y-1">
                      {stockData.validation.errors.map((e, i) => (
                        <li key={i} className="text-sm text-red-800">
                          <span className="font-semibold capitalize">{e.field}:</span> {e.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {stockData.validation.warnings.length > 0 && (
                  <div className="p-6 bg-amber-50 border border-amber-200 rounded-lg">
                    <h3 className="text-sm font-semibold text-amber-600 mb-3">⚠️ Data Quality Warnings</h3>
                    <ul className="space-y-1">
                      {stockData.validation.warnings.map((w, i) => (
                        <li key={i} className="text-sm text-amber-800">
                          <span className="font-semibold capitalize">{w.field}:</span> {w.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            )}

            {/* Company Data */}
            <section className="mb-16">
              <h2 className="text-xl font-semibold mb-8">
                {stockData.symbol} {stockData.company_name && `— ${stockData.company_name}`}
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                {/* Company Data Card */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Company Data</h3>
                  <p className="text-sm text-gray-400 mb-6">From financial statements (read-only)</p>
                  <table className="w-full">
                    <tbody>
                      {[
                        ['Market Cap', formatCurrency(stockData.data.market_cap)],
                        ['Beta', formatNumber(stockData.data.beta)],
                        ['Total Debt', formatCurrency(stockData.data.total_debt)],
                        ['Cash', formatCurrency(stockData.data.cash)],
                        ['Tax Rate', formatPercent(stockData.data.tax_rate)],
                        ['Cost of Debt', formatPercent(stockData.data.cost_of_debt)],
                        ['Shares Outstanding', stockData.data.shares_outstanding ? (stockData.data.shares_outstanding / 1e9).toFixed(2) + 'B' : '—'],
                        ['Risk-Free Rate', formatPercent(stockData.data.risk_free_rate)],
                      ].map(([label, value]) => (
                        <tr key={label} className="border-b border-gray-100">
                          <td className="py-3 text-sm text-gray-500">{label}</td>
                          <td className="py-3 text-sm font-mono font-medium text-right">{value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Historical Hints Card */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 mb-2">Historical Hints</h3>
                  <p className="text-sm text-gray-400 mb-6">Based on past performance (for reference)</p>
                  <table className="w-full">
                    <tbody>
                      {[
                        ['Revenue Growth (CAGR)', formatPercent(stockData.hints.revenue_growth)],
                        ['Operating Margin', formatPercent(stockData.hints.operating_margin)],
                        ['D&A / Revenue', formatPercent(stockData.hints.da_ratio)],
                        ['CapEx / Revenue', formatPercent(stockData.hints.capex_ratio)],
                        ['Working Capital / Revenue', formatPercent(stockData.hints.wc_ratio)],
                      ].map(([label, value]) => (
                        <tr key={label} className="border-b border-gray-100">
                          <td className="py-3 text-sm text-gray-500">{label}</td>
                          <td className="py-3 text-sm font-mono font-medium text-right">{value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            {/* Assumptions */}
            <section className="mb-16 pt-8 border-t border-gray-100">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Your Assumptions</h2>
              <p className="text-sm text-gray-400 mb-8">Adjust these based on your analysis</p>
              
              <div className="grid grid-cols-2 md:grid-cols-5 gap-6 mb-8">
                {[
                  { label: 'Revenue Growth (%)', value: revenueGrowth, setter: setRevenueGrowth, hint: stockData.hints.revenue_growth !== null ? `Historical: ${(stockData.hints.revenue_growth * 100).toFixed(2)}%` : null },
                  { label: 'Operating Margin (%)', value: operatingMargin, setter: setOperatingMargin, hint: stockData.hints.operating_margin !== null ? `Historical: ${(stockData.hints.operating_margin * 100).toFixed(2)}%` : null },
                  { label: 'Terminal Growth Rate (%)', value: terminalGrowth, setter: setTerminalGrowth, hint: 'Typically 2-3% (GDP growth)' },
                  { label: 'Market Risk Premium (%)', value: marketRiskPremium, setter: setMarketRiskPremium, hint: 'Typically 5-7%' },
                  { label: 'Projection Years', value: projectionYears, setter: setProjectionYears, hint: 'Usually 5-10 years' },
                ].map(({ label, value, setter, hint }) => (
                  <div key={label} className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-gray-600">{label}</label>
                    <input
                      type="number"
                      step="0.1"
                      value={value}
                      onChange={(e) => setter(e.target.value)}
                      className="px-3 py-2.5 text-base font-mono bg-white border-2 border-gray-200 rounded-md outline-none transition-colors focus:border-gray-400"
                    />
                    {hint && <span className="text-xs text-gray-400">{hint}</span>}
                  </div>
                ))}
              </div>

              <button
                onClick={runValuation}
                disabled={loading || !canRunValuation}
                className="px-10 py-3 text-sm font-semibold bg-emerald-600 text-white rounded-lg transition-colors hover:bg-emerald-700 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : hasValidationErrors ? 'Fix Errors Above' : 'Run Valuation'}
              </button>
            </section>
          </>
        )}

        {result && (
          <section className="pt-8 border-t border-gray-100">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 mb-8">Valuation Result</h2>
            
            {/* Main Result */}
            <div className="mb-12">
              <div className="flex items-baseline gap-4 mb-3">
                <span className="text-sm text-gray-500">Intrinsic Value</span>
                <span className="text-5xl font-bold font-mono tracking-tight">${result.intrinsic_value_per_share.toFixed(2)}</span>
                <span className="text-sm text-gray-400">per share</span>
              </div>
              
              {result.market_cap && stockData && stockData.data.shares_outstanding && (
                <div className="flex items-center gap-6 mt-4">
                  <span className="text-sm text-gray-500">
                    Current: ~${(result.market_cap / stockData.data.shares_outstanding).toFixed(2)}
                  </span>
                  {(() => {
                    const currentPrice = result.market_cap / stockData.data.shares_outstanding;
                    const upside = ((result.intrinsic_value_per_share - currentPrice) / currentPrice) * 100;
                    return (
                      <span className={`text-sm font-semibold px-3 py-1 rounded-md ${
                        upside >= 0 
                          ? 'text-emerald-600 bg-emerald-50' 
                          : 'text-red-600 bg-red-50'
                      }`}>
                        {upside >= 0 ? '+' : ''}{upside.toFixed(1)}% {upside >= 0 ? 'undervalued' : 'overvalued'}
                      </span>
                    );
                  })()}
                </div>
              )}
            </div>

            {/* Details */}
            <div className="mb-12">
              <table className="w-full max-w-md">
                <tbody>
                  {[
                    ['Enterprise Value', formatCurrency(result.enterprise_value)],
                    ['Equity Value', formatCurrency(result.equity_value)],
                    ['Net Debt', formatCurrency(result.net_debt)],
                    ['WACC', formatPercent(result.wacc)],
                    ['Terminal Value', formatCurrency(result.terminal_value)],
                  ].map(([label, value]) => (
                    <tr key={label} className="border-b border-gray-100">
                      <td className="py-3 text-sm text-gray-500">{label}</td>
                      <td className="py-3 text-sm font-mono font-medium text-right">{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Projections */}
            {result.projections.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">FCF Projections</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="py-3 text-left font-medium text-gray-400 uppercase text-xs tracking-wide">Year</th>
                      <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide">Revenue</th>
                      <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide">EBIT</th>
                      <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide">FCF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.projections.map((p, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        <td className="py-3 font-mono">{i + 1}</td>
                        <td className="py-3 text-right font-mono">{formatCurrency(p.revenue)}</td>
                        <td className="py-3 text-right font-mono">{formatCurrency(p.ebit)}</td>
                        <td className="py-3 text-right font-mono">{formatCurrency(p.fcf)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
