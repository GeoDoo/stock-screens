import { useState, useEffect } from 'react';
import type { StockDataResponse, ValuationRequest, ValuationResult, ScenarioAnalysisResult, ComparableResult, Provider, TechnicalAnalysisResult, ProvidersResponse } from './types';

const API_BASE = 'http://localhost:8000';

function formatCurrency(value: number | null): string {
  if (value === null) return '—';
  const abs = Math.abs(value);
  if (abs >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  // For very small values, show with commas
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number | null): string {
  if (value === null) return '—';
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null, decimals = 2): string {
  if (value === null) return '—';
  return value.toFixed(decimals);
}

function formatShareCount(value: number | null): string {
  if (value === null) return '—';
  const abs = Math.abs(value);
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toLocaleString('en-US');
}

export default function App() {
  // Provider selection - separate providers for Fundamental and Technical
  const [fundamentalProviders, setFundamentalProviders] = useState<Provider[]>([]);
  const [technicalProviders, setTechnicalProviders] = useState<Provider[]>([]);
  const [selectedFundamentalProvider, setSelectedFundamentalProvider] = useState<string>('');
  const [selectedTechnicalProvider, setSelectedTechnicalProvider] = useState<string>('');
  const [providersLoading, setProvidersLoading] = useState(true);
  
  const [ticker, setTicker] = useState('');
  const [stockData, setStockData] = useState<StockDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ValuationResult | null>(null);
  
  // Fetch available providers on mount
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/providers`);
        const data: ProvidersResponse = await res.json();
        setFundamentalProviders(data.fundamental);
        setTechnicalProviders(data.technical);
        
        // Auto-select recommended or first available providers
        const fundRecommended = data.fundamental.find((p: Provider) => p.recommended && p.available);
        const fundAvailable = data.fundamental.find((p: Provider) => p.available);
        if (fundRecommended) {
          setSelectedFundamentalProvider(fundRecommended.id);
        } else if (fundAvailable) {
          setSelectedFundamentalProvider(fundAvailable.id);
        }
        
        const techRecommended = data.technical.find((p: Provider) => p.recommended && p.available);
        const techAvailable = data.technical.find((p: Provider) => p.available);
        if (techRecommended) {
          setSelectedTechnicalProvider(techRecommended.id);
        } else if (techAvailable) {
          setSelectedTechnicalProvider(techAvailable.id);
        }
      } catch (err) {
        console.error('Failed to fetch providers:', err);
      } finally {
        setProvidersLoading(false);
      }
    };
    fetchProviders();
  }, []);
  
  // User inputs
  const [revenueGrowth, setRevenueGrowth] = useState('');
  const [operatingMargin, setOperatingMargin] = useState('');
  const [terminalGrowth, setTerminalGrowth] = useState('3');
  const [marketRiskPremium, setMarketRiskPremium] = useState('6');
  const [projectionYears, setProjectionYears] = useState('10');
  
  // Advanced: custom discount rate
  const [useCustomDiscountRate, setUseCustomDiscountRate] = useState(false);
  const [customDiscountRate, setCustomDiscountRate] = useState('');
  
  // Scenario Analysis
  const [scenarioResult, setScenarioResult] = useState<ScenarioAnalysisResult | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  
  // Comparable Analysis
  const [comparableResult, setComparableResult] = useState<ComparableResult | null>(null);
  const [comparableLoading, setComparableLoading] = useState(false);
  
  // Technical Analysis
  const [technicalResult, setTechnicalResult] = useState<TechnicalAnalysisResult | null>(null);
  const [technicalLoading, setTechnicalLoading] = useState(false);
  
  // Tab navigation
  const [activeTab, setActiveTab] = useState<'fundamental' | 'technical'>('fundamental');

  const fetchStock = async () => {
    if (!ticker.trim() || !selectedFundamentalProvider) return;
    
    setLoading(true);
    setError(null);
    setStockData(null);
    setResult(null);
    setScenarioResult(null);
    setComparableResult(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${ticker.toUpperCase()}?provider=${selectedFundamentalProvider}`);
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
      discount_rate_override: useCustomDiscountRate && customDiscountRate 
        ? parseFloat(customDiscountRate) / 100 
        : null,
    };
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${stockData.symbol}/valuation?provider=${selectedFundamentalProvider}`, {
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

  const runScenarios = async () => {
    if (!stockData) return;
    
    setScenarioLoading(true);
    setScenarioResult(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${stockData.symbol}/scenarios?provider=${selectedFundamentalProvider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projection_years: parseInt(projectionYears) || 10,
          market_risk_premium: parseFloat(marketRiskPremium) / 100 || 0.06,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Scenario analysis failed');
      }
      const data: ScenarioAnalysisResult = await res.json();
      setScenarioResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setScenarioLoading(false);
    }
  };

  const runComparables = async () => {
    if (!stockData) return;
    
    setComparableLoading(true);
    setComparableResult(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${stockData.symbol}/comparables?provider=${selectedFundamentalProvider}`);
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Comparable analysis failed');
      }
      const data: ComparableResult = await res.json();
      setComparableResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setComparableLoading(false);
    }
  };

  const runTechnicalAnalysis = async () => {
    if (!stockData || !selectedTechnicalProvider) return;
    
    setTechnicalLoading(true);
    setTechnicalResult(null);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${stockData.symbol}/technical?provider=${selectedTechnicalProvider}&days=365`);
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Technical analysis failed');
      }
      const data: TechnicalAnalysisResult = await res.json();
      setTechnicalResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setTechnicalLoading(false);
    }
  };

  const hasInputs = revenueGrowth && operatingMargin && terminalGrowth && marketRiskPremium && projectionYears;
  
  // Smart validation: WACC-related issues can be bypassed with custom discount rate
  const canBypassWithCustomRate = useCustomDiscountRate && customDiscountRate && parseFloat(customDiscountRate) > 0;
  
  // Filter errors - WACC-related errors are irrelevant when using custom discount rate
  const relevantErrors = (stockData?.validation?.errors ?? []).filter(e => {
    if (canBypassWithCustomRate && e.impacts === 'wacc') {
      return false;
    }
    return true;
  });
  
  // Filter warnings - WACC-related warnings are irrelevant when using custom discount rate
  const relevantWarnings = (stockData?.validation?.warnings ?? []).filter(w => {
    if (canBypassWithCustomRate && w.impacts === 'wacc') {
      return false;
    }
    return true;
  });
  
  const hasValidationErrors = relevantErrors.length > 0;
  const canRunValuation = hasInputs && !hasValidationErrors;

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <div className="w-full max-w-[1600px] mx-auto px-8 lg:px-16 py-16">
        {/* Header */}
        <header className="mb-12">
          <h1 className="text-3xl font-semibold tracking-tight text-gray-900">Stock Analysis</h1>
          <p className="text-sm text-gray-400 mt-2">Fundamental & Technical Analysis</p>
        </header>

        {/* Provider Selection + Ticker in one cohesive block */}
        <section className="mb-12 space-y-8">
          {/* Data Providers */}
          {providersLoading ? (
            <p className="text-sm text-gray-400">Loading providers...</p>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Fundamental Analysis Provider */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-gray-400 block mb-3">
                  Fundamental Analysis
                  <span className="font-normal text-gray-300 ml-2">(DCF, Comparables, Scenarios)</span>
                </label>
                <div className="flex gap-2 flex-wrap">
                  {fundamentalProviders.map((provider) => (
                    <button
                      key={provider.id}
                      onClick={() => {
                        setSelectedFundamentalProvider(provider.id);
                        setStockData(null);
                        setResult(null);
                        setScenarioResult(null);
                        setComparableResult(null);
                      }}
                      disabled={!provider.available}
                      className={`px-4 py-2 rounded-lg border-2 transition-all text-left ${
                        selectedFundamentalProvider === provider.id
                          ? 'border-gray-900 bg-gray-900 text-white'
                          : provider.available
                          ? 'border-gray-200 bg-white text-gray-700 hover:border-gray-400'
                          : 'border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed'
                      }`}
                    >
                      <span className="font-semibold text-sm">{provider.name}</span>
                      {provider.recommended && <span className="ml-1 text-xs">★</span>}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {fundamentalProviders.find(p => p.id === selectedFundamentalProvider)?.description}
                </p>
              </div>

              {/* Technical Analysis Provider */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-gray-400 block mb-3">
                  Technical Analysis
                  <span className="font-normal text-gray-300 ml-2">(Price Charts, Indicators)</span>
                </label>
                <div className="flex gap-2 flex-wrap">
                  {technicalProviders.map((provider) => (
                    <button
                      key={provider.id}
                      onClick={() => {
                        setSelectedTechnicalProvider(provider.id);
                        setTechnicalResult(null);
                      }}
                      disabled={!provider.available}
                      className={`px-4 py-2 rounded-lg border-2 transition-all text-left ${
                        selectedTechnicalProvider === provider.id
                          ? 'border-gray-900 bg-gray-900 text-white'
                          : provider.available
                          ? 'border-gray-200 bg-white text-gray-700 hover:border-gray-400'
                          : 'border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed'
                      }`}
                    >
                      <span className="font-semibold text-sm">{provider.name}</span>
                      {provider.recommended && <span className="ml-1 text-xs">★</span>}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {technicalProviders.find(p => p.id === selectedTechnicalProvider)?.description}
                </p>
              </div>
            </div>
          )}

          {/* Ticker Search */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-gray-400 block mb-3">Stock Ticker</label>
            <div className="flex gap-3">
              <input
                type="text"
                placeholder={selectedFundamentalProvider ? "AAPL" : "Select provider first"}
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && fetchStock()}
                disabled={!selectedFundamentalProvider}
                className="w-48 px-4 py-3 text-base font-mono font-medium bg-white border-2 border-gray-200 rounded-lg outline-none transition-colors focus:border-gray-400 placeholder:text-gray-300 placeholder:font-normal disabled:bg-gray-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={fetchStock}
                disabled={loading || !ticker.trim() || !selectedFundamentalProvider}
                className="px-8 py-3 text-sm font-semibold bg-gray-900 text-white rounded-lg transition-opacity hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>
            </div>
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          </div>
        </section>

        {/* Tab Switcher */}
        {stockData && (
          <nav className="mb-10 border-b border-gray-200">
            <div className="flex gap-8">
              <button
                onClick={() => setActiveTab('fundamental')}
                className={`pb-4 text-sm font-semibold transition-colors relative ${
                  activeTab === 'fundamental'
                    ? 'text-gray-900'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                Fundamental
                {activeTab === 'fundamental' && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-900" />
                )}
              </button>
              <button
                onClick={() => setActiveTab('technical')}
                className={`pb-4 text-sm font-semibold transition-colors relative ${
                  activeTab === 'technical'
                    ? 'text-gray-900'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                Technical
                {activeTab === 'technical' && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-900" />
                )}
              </button>
            </div>
          </nav>
        )}

        {/* FUNDAMENTAL TAB */}
        {stockData && activeTab === 'fundamental' && (
          <>
            {/* Validation Alerts */}
            {(relevantErrors.length > 0 || relevantWarnings.length > 0) && (
              <section className="mb-8 space-y-4">
                {relevantErrors.length > 0 && (
                  <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
                    <h3 className="text-sm font-semibold text-red-600 mb-3">⛔ Cannot Run Valuation</h3>
                    <ul className="space-y-1">
                      {relevantErrors.map((e, i) => (
                        <li key={i} className="text-sm text-red-800">
                          <span className="font-semibold capitalize">{e.field}:</span> {e.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {relevantWarnings.length > 0 && (
                  <div className="p-6 bg-amber-50 border border-amber-200 rounded-lg">
                    <h3 className="text-sm font-semibold text-amber-600 mb-3">⚠️ Data Quality Warnings</h3>
                    <ul className="space-y-1">
                      {relevantWarnings.map((w, i) => (
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
              <div className="flex items-center gap-3 mb-8">
                <h2 className="text-xl font-semibold">
                  {stockData.symbol} {stockData.company_name && `— ${stockData.company_name}`}
                </h2>
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-500 uppercase tracking-wide">
                  via {stockData.data_provider}
                </span>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
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
                        ['Shares Outstanding', formatShareCount(stockData.data.shares_outstanding)],
                        ['Risk-Free Rate', formatPercent(stockData.data.risk_free_rate)],
                        ['WACC (calculated)', formatPercent(stockData.data.wacc)],
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

              {/* Custom Discount Rate (non-intrusive) */}
              <div className="mb-8 pt-4 border-t border-gray-100">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={useCustomDiscountRate}
                    onChange={(e) => setUseCustomDiscountRate(e.target.checked)}
                    className="w-4 h-4 accent-emerald-600"
                  />
                  <span className="text-sm text-gray-500 group-hover:text-gray-700">
                    Use custom discount rate instead of WACC {stockData.data.wacc !== null && `(${formatPercent(stockData.data.wacc)})`}
                  </span>
                </label>
                
                {useCustomDiscountRate && (
                  <div className="mt-4 flex items-center gap-4">
                    <div className="flex flex-col gap-2 w-48">
                      <label className="text-sm font-medium text-gray-600">Your Required Return (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={customDiscountRate}
                        onChange={(e) => setCustomDiscountRate(e.target.value)}
                        placeholder={stockData.data.wacc !== null ? `WACC: ${(stockData.data.wacc * 100).toFixed(1)}` : 'e.g., 12'}
                        className="px-3 py-2.5 text-base font-mono bg-white border-2 border-emerald-200 rounded-md outline-none transition-colors focus:border-emerald-400"
                      />
      </div>
                    <p className="text-xs text-gray-400 max-w-xs">
                      Override the calculated WACC with your personal required return. 
                      Higher rate = lower intrinsic value = more conservative.
        </p>
      </div>
                )}
              </div>

            </section>
            
            {/* Run Valuation Button - separate section for visual clarity */}
            <section className="mb-16">
              <button
                onClick={runValuation}
                disabled={loading || !canRunValuation}
                className="px-10 py-4 text-sm font-semibold bg-gray-900 text-white rounded-lg transition-opacity hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : hasValidationErrors ? 'Fix Errors Above' : 'Run Valuation'}
              </button>
            </section>

            {/* Valuation Result */}
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
                    ['Calculated WACC', formatPercent(result.wacc)],
                    ['Discount Rate Used', formatPercent(result.discount_rate)],
                    ['Terminal Value', formatCurrency(result.terminal_value)],
                  ].map(([label, value]) => (
                    <tr key={label} className="border-b border-gray-100">
                      <td className="py-3 text-sm text-gray-500">
                        {label}
                        {label === 'Discount Rate Used' && result.using_custom_discount_rate && (
                          <span className="ml-2 text-xs text-emerald-600">(custom)</span>
                        )}
                      </td>
                      <td className="py-3 text-sm font-mono font-medium text-right">{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Projections */}
            {result.projections.length > 0 && (
              <div className="mb-12">
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

            {/* Sensitivity Analysis */}
            {result.sensitivity && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Sensitivity Analysis</h3>
                <p className="text-sm text-gray-400 mb-6">Intrinsic value per share at different discount rates & terminal growth rates</p>
                
                <div className="overflow-x-auto">
                  <table className="text-sm">
                    <thead>
                      <tr>
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-400">
                          <span className="block">Discount</span>
                          <span className="block">Rate ↓</span>
                        </th>
                        {result.sensitivity.terminal_growth_rates.map((tg) => (
                          <th 
                            key={tg} 
                            className={`py-2 px-3 text-center text-xs font-medium ${
                              Math.abs(tg - result.sensitivity.base_terminal_growth) < 0.001 
                                ? 'text-emerald-600 bg-emerald-50' 
                                : 'text-gray-400'
                            }`}
                          >
                            {(tg * 100).toFixed(1)}%
                          </th>
                        ))}
                      </tr>
                      <tr>
                        <th className="py-1 px-3 text-left text-xs text-gray-300">Terminal Growth →</th>
                        {result.sensitivity.terminal_growth_rates.map((tg) => (
                          <th key={tg} className="py-1"></th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.sensitivity.matrix.map((row, rowIdx) => {
                        const dr = result.sensitivity.discount_rates[rowIdx];
                        const isBaseRow = Math.abs(dr - result.sensitivity.base_discount_rate) < 0.001;
                        
                        return (
                          <tr key={rowIdx}>
                            <td className={`py-2 px-3 text-xs font-medium ${
                              isBaseRow ? 'text-emerald-600 bg-emerald-50' : 'text-gray-500'
                            }`}>
                              {(dr * 100).toFixed(1)}%
                            </td>
                            {row.map((value, colIdx) => {
                              const tg = result.sensitivity.terminal_growth_rates[colIdx];
                              const isBaseCol = Math.abs(tg - result.sensitivity.base_terminal_growth) < 0.001;
                              const isCurrentCell = isBaseRow && isBaseCol;
                              
                              // Color based on comparison to current price
                              let cellClass = 'text-gray-700';
                              if (value !== null && result.market_cap && stockData?.data.shares_outstanding) {
                                const currentPrice = result.market_cap / stockData.data.shares_outstanding;
                                const diff = ((value - currentPrice) / currentPrice) * 100;
                                if (diff > 20) cellClass = 'text-emerald-700 bg-emerald-50';
                                else if (diff > 0) cellClass = 'text-emerald-600';
                                else if (diff > -20) cellClass = 'text-red-500';
                                else cellClass = 'text-red-600 bg-red-50';
                              }
                              
                              return (
                                <td 
                                  key={colIdx} 
                                  className={`py-2 px-3 text-center font-mono text-sm ${cellClass} ${
                                    isCurrentCell ? 'ring-2 ring-emerald-500 ring-inset font-bold' : ''
                                  }`}
                                >
                                  {value !== null ? `$${value.toFixed(2)}` : '—'}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                
                <div className="mt-4 flex gap-6 text-xs text-gray-400">
                  <span><span className="inline-block w-3 h-3 bg-emerald-50 border border-emerald-200 rounded mr-1"></span> Undervalued (vs current price)</span>
                  <span><span className="inline-block w-3 h-3 bg-red-50 border border-red-200 rounded mr-1"></span> Overvalued</span>
                  <span><span className="inline-block w-3 h-3 ring-2 ring-emerald-500 rounded mr-1"></span> Current assumptions</span>
                </div>
              </div>
              )}
            </section>
            )}

            {/* Scenario Analysis Section */}
            <section className="pt-12 border-t border-gray-100">
              <div className="mb-8">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Scenario Analysis</h2>
              <p className="text-sm text-gray-400 mb-6">Bear / Base / Bull case valuations with probability weighting</p>
              <button
                onClick={runScenarios}
                disabled={scenarioLoading || hasValidationErrors}
                className="px-10 py-4 text-sm font-semibold bg-gray-900 text-white rounded-lg transition-opacity hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {scenarioLoading ? 'Analyzing...' : 'Run Scenarios'}
              </button>
            </div>

            {scenarioResult && (
              <div className="space-y-8">
                {/* Summary */}
                <div className="flex items-baseline gap-4">
                  <span className="text-4xl font-bold font-mono">${scenarioResult.probability_weighted_value?.toFixed(2)}</span>
                  <span className="text-sm text-gray-400">weighted fair value</span>
                  {(() => {
                    const current = scenarioResult.current_price || 0;
                    const fair = scenarioResult.probability_weighted_value || 0;
                    const diff = ((fair - current) / current) * 100;
                    return (
                      <span className={`text-sm font-medium ${diff >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {diff >= 0 ? '+' : ''}{diff.toFixed(0)}%
                      </span>
                    );
                  })()}
                </div>

                {/* Table */}
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Scenario</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Value</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">vs Current</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Growth</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Margin</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenarioResult.scenarios.map((scenario) => (
                      <tr key={scenario.name} className="border-b border-gray-100">
                        <td className="py-3 text-sm font-medium">{scenario.name}</td>
                        <td className="py-3 text-right font-mono text-sm">${scenario.intrinsic_value.toFixed(2)}</td>
                        <td className={`py-3 text-right font-mono text-sm ${
                          scenario.upside_percent !== null && scenario.upside_percent >= 0 
                            ? 'text-emerald-600' 
                            : 'text-red-600'
                        }`}>
                          {scenario.upside_percent !== null 
                            ? `${scenario.upside_percent >= 0 ? '+' : ''}${scenario.upside_percent.toFixed(0)}%`
                            : '—'}
                        </td>
                        <td className="py-3 text-right font-mono text-sm text-gray-500">
                          {(scenario.assumptions.revenue_growth * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 text-right font-mono text-sm text-gray-500">
                          {(scenario.assumptions.operating_margin * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 text-right font-mono text-sm text-gray-400">
                          {(scenario.probability * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

            {/* Comparable Analysis Section */}
            <section className="pt-12 border-t border-gray-100">
              <div className="mb-8">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Comparable Analysis</h2>
              <p className="text-sm text-gray-400 mb-6">Relative valuation vs sector peers using P/E, EV/EBITDA, P/S, P/B</p>
              <button
                onClick={runComparables}
                disabled={comparableLoading}
                className="px-10 py-4 text-sm font-semibold bg-gray-900 text-white rounded-lg transition-opacity hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {comparableLoading ? 'Loading...' : 'Run Comparables'}
              </button>
            </div>

            {comparableResult && (
              <div className="space-y-8">
                {/* Summary */}
                <div className="flex items-baseline gap-4">
                  <span className="text-4xl font-bold font-mono">
                    ${comparableResult.summary.average_implied_price?.toFixed(2) || '—'}
                  </span>
                  <span className="text-sm text-gray-400">implied fair value (peer median)</span>
                  {comparableResult.summary.average_upside_percent !== null && (
                    <span className={`text-sm font-medium ${
                      comparableResult.summary.average_upside_percent >= 0 ? 'text-emerald-600' : 'text-red-600'
                    }`}>
                      {comparableResult.summary.average_upside_percent >= 0 ? '+' : ''}
                      {comparableResult.summary.average_upside_percent.toFixed(0)}%
                    </span>
                  )}
                </div>

                {/* Sector Info */}
                <div className="text-sm text-gray-500">
                  <span className="font-medium">{comparableResult.sector}</span>
                  {comparableResult.industry && comparableResult.industry !== comparableResult.sector && (
                    <span> / {comparableResult.industry}</span>
                  )}
                  <span className="text-gray-400 ml-2">• {comparableResult.peers.length} peers</span>
                </div>

                {/* Implied Valuations */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Implied Value by Multiple</h3>
                  <table className="w-full max-w-2xl">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Multiple</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Company</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Peer Median</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Implied Price</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">vs Current</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparableResult.implied_valuations.map((iv) => (
                        <tr key={iv.metric} className="border-b border-gray-100">
                          <td className="py-3 text-sm font-medium">{iv.metric}</td>
                          <td className="py-3 text-right font-mono text-sm">
                            {iv.company_value !== null ? iv.company_value.toFixed(1) + 'x' : '—'}
                          </td>
                          <td className="py-3 text-right font-mono text-sm text-gray-500">
                            {iv.peer_median !== null ? iv.peer_median.toFixed(1) + 'x' : '—'}
                          </td>
                          <td className="py-3 text-right font-mono text-sm font-medium">
                            {iv.implied_price !== null ? '$' + iv.implied_price.toFixed(2) : '—'}
                          </td>
                          <td className={`py-3 text-right font-mono text-sm ${
                            iv.upside_percent !== null && iv.upside_percent >= 0 
                              ? 'text-emerald-600' 
                              : 'text-red-600'
                          }`}>
                            {iv.upside_percent !== null 
                              ? `${iv.upside_percent >= 0 ? '+' : ''}${iv.upside_percent.toFixed(0)}%`
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Peer Comparison */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Peer Companies</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Company</th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Market Cap</th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P/E</th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">EV/EBITDA</th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P/S</th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P/B</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* Target company row */}
                        <tr className="border-b border-gray-200 bg-gray-50">
                          <td className="py-3 font-medium">
                            {comparableResult.symbol}
                            <span className="text-xs text-gray-400 ml-2">(target)</span>
                          </td>
                          <td className="py-3 text-right font-mono">
                            {formatCurrency(stockData.data.market_cap)}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {comparableResult.target_metrics.pe_ratio?.toFixed(1) || '—'}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {comparableResult.target_metrics.ev_to_ebitda?.toFixed(1) || '—'}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {comparableResult.target_metrics.price_to_sales?.toFixed(1) || '—'}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {comparableResult.target_metrics.price_to_book?.toFixed(1) || '—'}
                          </td>
                        </tr>
                        {/* Peer rows */}
                        {comparableResult.peers.map((peer) => (
                          <tr key={peer.symbol} className="border-b border-gray-100">
                            <td className="py-3">
                              <span className="font-medium">{peer.symbol}</span>
                              <span className="text-xs text-gray-400 ml-2 truncate max-w-[150px] inline-block align-bottom">
                                {peer.name}
                              </span>
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {formatCurrency(peer.market_cap)}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {peer.pe_ratio?.toFixed(1) || '—'}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {peer.ev_to_ebitda?.toFixed(1) || '—'}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {peer.price_to_sales?.toFixed(1) || '—'}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {peer.price_to_book?.toFixed(1) || '—'}
                            </td>
                          </tr>
                        ))}
                        {/* Median row */}
                        <tr className="border-t-2 border-gray-200">
                          <td className="py-3 font-medium text-gray-500">Peer Median</td>
                          <td className="py-3 text-right font-mono">—</td>
                          <td className="py-3 text-right font-mono font-medium">
                            {comparableResult.peer_medians.pe_ratio?.toFixed(1) || '—'}
                          </td>
                          <td className="py-3 text-right font-mono font-medium">
                            {comparableResult.peer_medians.ev_to_ebitda?.toFixed(1) || '—'}
                          </td>
                          <td className="py-3 text-right font-mono font-medium">
                            {comparableResult.peer_medians.price_to_sales?.toFixed(1) || '—'}
                          </td>
                          <td className="py-3 text-right font-mono font-medium">
                            {comparableResult.peer_medians.price_to_book?.toFixed(1) || '—'}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
            </section>
          </>
        )}

        {/* TECHNICAL TAB */}
        {stockData && activeTab === 'technical' && (
          <div className="py-8">
            {/* Run Technical Analysis */}
            {!technicalResult && (
              <div className="mb-8">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Technical Analysis</h2>
                <p className="text-sm text-gray-400 mb-4">Price charts, moving averages, RSI, MACD indicators</p>
                <p className="text-xs text-gray-400 mb-6">
                  Provider: <span className="font-semibold text-gray-600">{technicalProviders.find(p => p.id === selectedTechnicalProvider)?.name || selectedTechnicalProvider}</span>
                </p>
                <button
                  onClick={runTechnicalAnalysis}
                  disabled={technicalLoading || !selectedTechnicalProvider}
                  className="px-10 py-4 text-sm font-semibold bg-gray-900 text-white rounded-lg transition-opacity hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {technicalLoading ? 'Loading...' : 'Run Technical Analysis'}
                </button>
              </div>
            )}

            {/* Technical Analysis Results */}
            {technicalResult && (
              <div className="space-y-8">
                {/* Price Summary */}
                <div className="mb-2">
                  <span className="text-xs text-gray-400">
                    Data from <span className="font-semibold text-gray-600">{technicalProviders.find(p => p.id === technicalResult.provider)?.name || technicalResult.provider}</span>
                  </span>
                </div>
                <div className="flex items-baseline gap-4">
                  <span className="text-4xl font-bold font-mono">${technicalResult.current_price.toFixed(2)}</span>
                  <span className={`text-lg font-semibold ${technicalResult.price_change_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {technicalResult.price_change_pct >= 0 ? '+' : ''}{technicalResult.price_change_pct.toFixed(2)}%
                  </span>
                  <span className="text-sm text-gray-400">{technicalResult.period_days} days</span>
                </div>

                {/* Signal Summary */}
                <div className="grid grid-cols-3 gap-6 max-w-xl">
                  <div className="p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Trend</div>
                    <div className={`text-lg font-semibold capitalize ${
                      technicalResult.signals.trend === 'bullish' ? 'text-emerald-600' :
                      technicalResult.signals.trend === 'bearish' ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      {technicalResult.signals.trend}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">RSI (14)</div>
                    <div className={`text-lg font-semibold capitalize ${
                      technicalResult.signals.rsi === 'overbought' ? 'text-red-600' :
                      technicalResult.signals.rsi === 'oversold' ? 'text-emerald-600' : 'text-gray-500'
                    }`}>
                      {technicalResult.signals.rsi}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">MACD</div>
                    <div className={`text-lg font-semibold capitalize ${
                      technicalResult.signals.macd === 'bullish' ? 'text-emerald-600' :
                      technicalResult.signals.macd === 'bearish' ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      {technicalResult.signals.macd}
                    </div>
                  </div>
                </div>

                {/* Price Chart */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Price Chart</h3>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-hidden">
                    <svg viewBox="0 0 800 300" className="w-full h-64">
                      {/* Chart background */}
                      <rect x="0" y="0" width="800" height="300" fill="#fafafa" />
                      
                      {/* Price line */}
                      {technicalResult.prices.length > 1 && (() => {
                        const prices = technicalResult.prices;
                        const minPrice = Math.min(...prices.map(p => p.low));
                        const maxPrice = Math.max(...prices.map(p => p.high));
                        const priceRange = maxPrice - minPrice || 1;
                        const padding = 20;
                        const chartHeight = 260;
                        const chartWidth = 760;
                        
                        const points = prices.map((p, i) => {
                          const x = padding + (i / (prices.length - 1)) * chartWidth;
                          const y = padding + ((maxPrice - p.close) / priceRange) * chartHeight;
                          return `${x},${y}`;
                        }).join(' ');
                        
                        // SMA 20 line
                        const sma20Points = technicalResult.indicators.sma_20.map((s, i) => {
                          const priceIdx = prices.findIndex(p => p.timestamp === s.timestamp);
                          if (priceIdx === -1) return null;
                          const x = padding + (priceIdx / (prices.length - 1)) * chartWidth;
                          const y = padding + ((maxPrice - s.value) / priceRange) * chartHeight;
                          return `${x},${y}`;
                        }).filter(Boolean).join(' ');
                        
                        // SMA 50 line
                        const sma50Points = technicalResult.indicators.sma_50.map((s, i) => {
                          const priceIdx = prices.findIndex(p => p.timestamp === s.timestamp);
                          if (priceIdx === -1) return null;
                          const x = padding + (priceIdx / (prices.length - 1)) * chartWidth;
                          const y = padding + ((maxPrice - s.value) / priceRange) * chartHeight;
                          return `${x},${y}`;
                        }).filter(Boolean).join(' ');
                        
                        return (
                          <>
                            {/* Grid lines */}
                            {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => (
                              <line
                                key={i}
                                x1={padding}
                                y1={padding + pct * chartHeight}
                                x2={padding + chartWidth}
                                y2={padding + pct * chartHeight}
                                stroke="#e5e7eb"
                                strokeWidth="1"
                              />
                            ))}
                            
                            {/* SMA 50 */}
                            {sma50Points && (
                              <polyline
                                points={sma50Points}
                                fill="none"
                                stroke="#f59e0b"
                                strokeWidth="1.5"
                                opacity="0.7"
                              />
                            )}
                            
                            {/* SMA 20 */}
                            {sma20Points && (
                              <polyline
                                points={sma20Points}
                                fill="none"
                                stroke="#8b5cf6"
                                strokeWidth="1.5"
                                opacity="0.7"
                              />
                            )}
                            
                            {/* Price line */}
                            <polyline
                              points={points}
                              fill="none"
                              stroke="#111827"
                              strokeWidth="2"
                            />
                            
                            {/* Price labels */}
                            <text x={padding - 5} y={padding + 5} textAnchor="end" fontSize="10" fill="#9ca3af">
                              ${maxPrice.toFixed(0)}
                            </text>
                            <text x={padding - 5} y={padding + chartHeight} textAnchor="end" fontSize="10" fill="#9ca3af">
                              ${minPrice.toFixed(0)}
                            </text>
                          </>
                        );
                      })()}
                    </svg>
                    <div className="flex gap-6 mt-2 text-xs text-gray-400">
                      <span><span className="inline-block w-3 h-0.5 bg-gray-900 mr-1"></span> Price</span>
                      <span><span className="inline-block w-3 h-0.5 bg-purple-500 mr-1"></span> SMA 20</span>
                      <span><span className="inline-block w-3 h-0.5 bg-amber-500 mr-1"></span> SMA 50</span>
                    </div>
                  </div>
                </div>

                {/* RSI Chart */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">RSI (14)</h3>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-hidden">
                    <svg viewBox="0 0 800 120" className="w-full h-24">
                      {/* Overbought/Oversold zones */}
                      <rect x="20" y="0" width="760" height="30" fill="#fef2f2" opacity="0.5" />
                      <rect x="20" y="90" width="760" height="30" fill="#ecfdf5" opacity="0.5" />
                      
                      {/* RSI line */}
                      {technicalResult.indicators.rsi_14.length > 1 && (() => {
                        const rsiData = technicalResult.indicators.rsi_14;
                        const padding = 20;
                        const chartWidth = 760;
                        const chartHeight = 120;
                        
                        const points = rsiData.map((r, i) => {
                          const x = padding + (i / (rsiData.length - 1)) * chartWidth;
                          const y = chartHeight - (r.value / 100) * chartHeight;
                          return `${x},${y}`;
                        }).join(' ');
                        
                        return (
                          <>
                            {/* 70/30 lines */}
                            <line x1={padding} y1={30} x2={padding + chartWidth} y2={30} stroke="#ef4444" strokeWidth="1" strokeDasharray="4" />
                            <line x1={padding} y1={90} x2={padding + chartWidth} y2={90} stroke="#10b981" strokeWidth="1" strokeDasharray="4" />
                            <line x1={padding} y1={60} x2={padding + chartWidth} y2={60} stroke="#e5e7eb" strokeWidth="1" />
                            
                            {/* RSI line */}
                            <polyline points={points} fill="none" stroke="#6366f1" strokeWidth="2" />
                            
                            {/* Labels */}
                            <text x={padding - 5} y={34} textAnchor="end" fontSize="9" fill="#ef4444">70</text>
                            <text x={padding - 5} y={94} textAnchor="end" fontSize="9" fill="#10b981">30</text>
                          </>
                        );
                      })()}
                    </svg>
                  </div>
                </div>

                {/* MACD Chart */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">MACD</h3>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-hidden">
                    <svg viewBox="0 0 800 120" className="w-full h-24">
                      {technicalResult.indicators.macd.length > 1 && (() => {
                        const macdData = technicalResult.indicators.macd;
                        const maxVal = Math.max(...macdData.map(m => Math.max(Math.abs(m.macd), Math.abs(m.signal), Math.abs(m.histogram))));
                        const padding = 20;
                        const chartWidth = 760;
                        const chartHeight = 120;
                        const midY = chartHeight / 2;
                        
                        const macdPoints = macdData.map((m, i) => {
                          const x = padding + (i / (macdData.length - 1)) * chartWidth;
                          const y = midY - (m.macd / maxVal) * (midY - 10);
                          return `${x},${y}`;
                        }).join(' ');
                        
                        const signalPoints = macdData.map((m, i) => {
                          const x = padding + (i / (macdData.length - 1)) * chartWidth;
                          const y = midY - (m.signal / maxVal) * (midY - 10);
                          return `${x},${y}`;
                        }).join(' ');
                        
                        return (
                          <>
                            {/* Zero line */}
                            <line x1={padding} y1={midY} x2={padding + chartWidth} y2={midY} stroke="#e5e7eb" strokeWidth="1" />
                            
                            {/* Histogram bars */}
                            {macdData.map((m, i) => {
                              const x = padding + (i / (macdData.length - 1)) * chartWidth;
                              const barHeight = (m.histogram / maxVal) * (midY - 10);
                              return (
                                <rect
                                  key={i}
                                  x={x - 1}
                                  y={barHeight > 0 ? midY - barHeight : midY}
                                  width={2}
                                  height={Math.abs(barHeight)}
                                  fill={m.histogram >= 0 ? '#10b981' : '#ef4444'}
                                  opacity="0.5"
                                />
                              );
                            })}
                            
                            {/* MACD line */}
                            <polyline points={macdPoints} fill="none" stroke="#3b82f6" strokeWidth="1.5" />
                            
                            {/* Signal line */}
                            <polyline points={signalPoints} fill="none" stroke="#f97316" strokeWidth="1.5" />
                          </>
                        );
                      })()}
                    </svg>
                    <div className="flex gap-6 mt-2 text-xs text-gray-400">
                      <span><span className="inline-block w-3 h-0.5 bg-blue-500 mr-1"></span> MACD</span>
                      <span><span className="inline-block w-3 h-0.5 bg-orange-500 mr-1"></span> Signal</span>
                      <span><span className="inline-block w-3 h-2 bg-emerald-500 opacity-50 mr-1"></span> Histogram</span>
                    </div>
                  </div>
                </div>

                {/* Run again button */}
                <button
                  onClick={runTechnicalAnalysis}
                  disabled={technicalLoading}
                  className="px-6 py-2 text-sm font-medium text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-30"
                >
                  {technicalLoading ? 'Loading...' : 'Refresh'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
