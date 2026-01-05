import { useState } from 'react';
import type { StockDataResponse, ValuationRequest, ValuationResult } from './types';
import './App.css';

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
  const [projectionYears, setProjectionYears] = useState('5');

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

  const isValid = revenueGrowth && operatingMargin && terminalGrowth && marketRiskPremium && projectionYears;

  return (
    <div className="app">
      <header>
        <h1>Stock Valuation</h1>
        <p className="subtitle">DCF Analysis</p>
      </header>

      <section className="search-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="Enter ticker (e.g., AAPL)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && fetchStock()}
          />
          <button onClick={fetchStock} disabled={loading || !ticker.trim()}>
            {loading ? 'Loading...' : 'Analyze'}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {stockData && (
        <>
          <section className="data-section">
            <h2>{stockData.symbol} {stockData.company_name && `— ${stockData.company_name}`}</h2>
            
            <div className="data-grid">
              <div className="data-card">
                <h3>Company Data</h3>
                <p className="data-note">From financial statements (read-only)</p>
                <table>
                  <tbody>
                    <tr><td>Market Cap</td><td>{formatCurrency(stockData.data.market_cap)}</td></tr>
                    <tr><td>Beta</td><td>{formatNumber(stockData.data.beta)}</td></tr>
                    <tr><td>Total Debt</td><td>{formatCurrency(stockData.data.total_debt)}</td></tr>
                    <tr><td>Cash</td><td>{formatCurrency(stockData.data.cash)}</td></tr>
                    <tr><td>Tax Rate</td><td>{formatPercent(stockData.data.tax_rate)}</td></tr>
                    <tr><td>Cost of Debt</td><td>{formatPercent(stockData.data.cost_of_debt)}</td></tr>
                    <tr><td>Shares Outstanding</td><td>{stockData.data.shares_outstanding ? (stockData.data.shares_outstanding / 1e9).toFixed(2) + 'B' : '—'}</td></tr>
                    <tr><td>Risk-Free Rate</td><td>{formatPercent(stockData.data.risk_free_rate)}</td></tr>
                  </tbody>
                </table>
              </div>

              <div className="data-card hints">
                <h3>Historical Hints</h3>
                <p className="data-note">Based on past performance (for reference)</p>
                <table>
                  <tbody>
                    <tr><td>Revenue Growth (CAGR)</td><td>{formatPercent(stockData.hints.revenue_growth)}</td></tr>
                    <tr><td>Operating Margin</td><td>{formatPercent(stockData.hints.operating_margin)}</td></tr>
                    <tr><td>D&A / Revenue</td><td>{formatPercent(stockData.hints.da_ratio)}</td></tr>
                    <tr><td>CapEx / Revenue</td><td>{formatPercent(stockData.hints.capex_ratio)}</td></tr>
                    <tr><td>Working Capital / Revenue</td><td>{formatPercent(stockData.hints.wc_ratio)}</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section className="inputs-section">
            <h2>Your Assumptions</h2>
            <p className="data-note">Adjust these based on your analysis</p>
            
            <div className="inputs-grid">
              <div className="input-group">
                <label>Revenue Growth (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={revenueGrowth}
                  onChange={(e) => setRevenueGrowth(e.target.value)}
                  placeholder="e.g., 10"
                />
                {stockData.hints.revenue_growth !== null && (
                  <span className="hint">Historical: {(stockData.hints.revenue_growth * 100).toFixed(2)}%</span>
                )}
              </div>

              <div className="input-group">
                <label>Operating Margin (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={operatingMargin}
                  onChange={(e) => setOperatingMargin(e.target.value)}
                  placeholder="e.g., 25"
                />
                {stockData.hints.operating_margin !== null && (
                  <span className="hint">Historical: {(stockData.hints.operating_margin * 100).toFixed(2)}%</span>
                )}
              </div>

              <div className="input-group">
                <label>Terminal Growth Rate (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={terminalGrowth}
                  onChange={(e) => setTerminalGrowth(e.target.value)}
                  placeholder="e.g., 3"
                />
                <span className="hint">Typically 2-3% (GDP growth)</span>
              </div>

              <div className="input-group">
                <label>Market Risk Premium (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={marketRiskPremium}
                  onChange={(e) => setMarketRiskPremium(e.target.value)}
                  placeholder="e.g., 6"
                />
                <span className="hint">Typically 5-7%</span>
              </div>

              <div className="input-group">
                <label>Projection Years</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={projectionYears}
                  onChange={(e) => setProjectionYears(e.target.value)}
                  placeholder="e.g., 5"
                />
                <span className="hint">Usually 5-10 years</span>
              </div>
            </div>

            <button 
              className="run-btn"
              onClick={runValuation} 
              disabled={loading || !isValid}
            >
              {loading ? 'Calculating...' : 'Run Valuation'}
            </button>
          </section>
        </>
      )}

      {result && (
        <section className="result-section">
          <h2>Valuation Result</h2>
          
          <div className="result-main">
            <div className="intrinsic-value">
              <span className="label">Intrinsic Value</span>
              <span className="value">${result.intrinsic_value_per_share.toFixed(2)}</span>
              <span className="per-share">per share</span>
            </div>
            
            {result.market_cap && stockData && stockData.data.shares_outstanding && (
              <div className="comparison">
                <span className="current-price">
                  Current: ~${(result.market_cap / stockData.data.shares_outstanding).toFixed(2)}
                </span>
                {(() => {
                  const currentPrice = result.market_cap / stockData.data.shares_outstanding;
                  const upside = ((result.intrinsic_value_per_share - currentPrice) / currentPrice) * 100;
                  return (
                    <span className={`upside ${upside >= 0 ? 'positive' : 'negative'}`}>
                      {upside >= 0 ? '+' : ''}{upside.toFixed(1)}% {upside >= 0 ? 'undervalued' : 'overvalued'}
                    </span>
                  );
                })()}
              </div>
            )}
          </div>

          <div className="result-details">
            <table>
              <tbody>
                <tr><td>Enterprise Value</td><td>{formatCurrency(result.enterprise_value)}</td></tr>
                <tr><td>Equity Value</td><td>{formatCurrency(result.equity_value)}</td></tr>
                <tr><td>Net Debt</td><td>{formatCurrency(result.net_debt)}</td></tr>
                <tr><td>WACC</td><td>{formatPercent(result.wacc)}</td></tr>
                <tr><td>Terminal Value</td><td>{formatCurrency(result.terminal_value)}</td></tr>
              </tbody>
            </table>
          </div>

          {result.projections.length > 0 && (
            <div className="projections">
              <h3>FCF Projections</h3>
              <table className="projections-table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Revenue</th>
                    <th>EBIT</th>
                    <th>FCF</th>
                  </tr>
                </thead>
                <tbody>
                  {result.projections.map((p, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{formatCurrency(p.revenue)}</td>
                      <td>{formatCurrency(p.ebit)}</td>
                      <td>{formatCurrency(p.fcf)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
