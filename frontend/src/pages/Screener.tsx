import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Filter, ChevronRight } from 'lucide-react';
import { screeningApi, Screen } from '../api/client';

const Screener: React.FC = () => {
  const { data: screens, isLoading } = useQuery({
    queryKey: ['screens'],
    queryFn: () => screeningApi.getScreens().then(r => r.data),
  });

  const screenDescriptions: Record<string, { icon: string; color: string }> = {
    graham_defensive: { icon: '🛡️', color: 'var(--accent-green)' },
    graham_enterprising: { icon: '📊', color: 'var(--accent-blue)' },
    low_debt_high_roe: { icon: '💪', color: 'var(--accent-purple)' },
    deep_value: { icon: '💎', color: 'var(--accent-yellow)' },
  };

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title">Stock Screener</h1>
        <p className="page-subtitle">Filter stocks using value investing criteria</p>
      </header>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Filter size={18} />
            Predefined Screens
          </h3>
        </div>
        
        {isLoading ? (
          <div className="loading">Loading screens...</div>
        ) : (
          <div style={{ display: 'grid', gap: 12 }}>
            {screens?.map((screen: Screen) => (
              <div
                key={screen.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: 16,
                  background: 'var(--bg-tertiary)',
                  borderRadius: 8,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  border: '1px solid var(--border-color)',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.borderColor = screenDescriptions[screen.id]?.color || 'var(--accent-cyan)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <span style={{ fontSize: 32 }}>{screenDescriptions[screen.id]?.icon || '📈'}</span>
                  <div>
                    <h4 style={{ 
                      marginBottom: 4, 
                      color: screenDescriptions[screen.id]?.color || 'var(--text-primary)' 
                    }}>
                      {screen.name}
                    </h4>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                      {screen.description}
                    </p>
                  </div>
                </div>
                <ChevronRight size={20} color="var(--text-muted)" />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Custom Filter</h3>
          <span className="badge badge-blue">Coming Soon</span>
        </div>
        <div style={{ 
          padding: 24, 
          background: 'var(--bg-tertiary)', 
          borderRadius: 8,
          textAlign: 'center',
          color: 'var(--text-muted)'
        }}>
          <p>Build custom screens with your own criteria</p>
          <p style={{ fontSize: 14, marginTop: 8 }}>
            Filter by P/E, P/B, ROE, Debt/Equity, and more
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Screen Criteria Reference</h3>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Screen</th>
              <th>Key Criteria</th>
              <th>Best For</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ color: 'var(--accent-green)', fontWeight: 500 }}>Graham Defensive</td>
              <td>P/E &lt; 15, P/B &lt; 1.5, Current Ratio &gt; 2</td>
              <td>Conservative investors</td>
            </tr>
            <tr>
              <td style={{ color: 'var(--accent-blue)', fontWeight: 500 }}>Graham Enterprising</td>
              <td>P/E &lt; 20, P/B &lt; 2.5, Current Ratio &gt; 1.5</td>
              <td>Active value investors</td>
            </tr>
            <tr>
              <td style={{ color: 'var(--accent-purple)', fontWeight: 500 }}>Low Debt, High ROE</td>
              <td>D/E &lt; 0.5, ROE &gt; 15%</td>
              <td>Quality-focused investors</td>
            </tr>
            <tr>
              <td style={{ color: 'var(--accent-yellow)', fontWeight: 500 }}>Deep Value</td>
              <td>P/E &lt; 10, P/B &lt; 1</td>
              <td>Contrarian investors</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Screener;

