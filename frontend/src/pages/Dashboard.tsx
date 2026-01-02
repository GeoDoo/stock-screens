import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, AlertCircle, Eye } from 'lucide-react';
import { watchlistApi, spinoffApi } from '../api/client';

const Dashboard: React.FC = () => {
  const { data: watchlist, isLoading: loadingWatchlist } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => watchlistApi.getAll().then(r => r.data),
  });

  const { data: alerts, isLoading: loadingAlerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => spinoffApi.getAlerts().then(r => r.data),
  });

  const unreadAlerts = alerts?.filter(a => !a.is_read) || [];

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Overview of your value investing research</p>
      </header>

      <div className="grid grid-4" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-label">Watchlist</div>
          <div className="stat-value">{watchlist?.length || 0}</div>
          <div className="stat-change" style={{ color: 'var(--text-muted)' }}>
            stocks tracked
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Alerts</div>
          <div className="stat-value" style={{ color: unreadAlerts.length > 0 ? 'var(--accent-yellow)' : 'inherit' }}>
            {unreadAlerts.length}
          </div>
          <div className="stat-change" style={{ color: 'var(--text-muted)' }}>
            new spinoffs
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Undervalued</div>
          <div className="stat-value" style={{ color: 'var(--accent-green)' }}>-</div>
          <div className="stat-change" style={{ color: 'var(--text-muted)' }}>
            margin of safety
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Screens</div>
          <div className="stat-value">4</div>
          <div className="stat-change" style={{ color: 'var(--text-muted)' }}>
            predefined
          </div>
        </div>
      </div>

      {unreadAlerts.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertCircle size={18} color="var(--accent-yellow)" />
              New Spinoff Alerts
            </h3>
          </div>
          <div>
            {unreadAlerts.map(alert => (
              <div 
                key={alert.id} 
                className="alert alert-warning"
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <div>
                  <strong>{alert.title}</strong>
                  <p style={{ margin: '4px 0 0', fontSize: 13 }}>{alert.message}</p>
                </div>
                <span className="badge badge-yellow">New</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Eye size={18} />
            Watchlist Preview
          </h3>
        </div>
        {loadingWatchlist ? (
          <div className="loading">Loading...</div>
        ) : watchlist && watchlist.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Target Price</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {watchlist.slice(0, 5).map(item => (
                <tr key={item.id}>
                  <td className="symbol">{item.symbol}</td>
                  <td>{item.target_price ? `$${item.target_price.toFixed(2)}` : '-'}</td>
                  <td>{new Date(item.added_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-state">
            <p>No stocks in watchlist yet</p>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Quick Start</h3>
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 6 }}>
            <h4 style={{ marginBottom: 8, color: 'var(--accent-cyan)' }}>1. Add stocks to your watchlist</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Track stocks you're interested in. The system will fetch fundamentals and technicals automatically.
            </p>
          </div>
          <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 6 }}>
            <h4 style={{ marginBottom: 8, color: 'var(--accent-cyan)' }}>2. Use predefined screens</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Filter stocks using Graham's Defensive, Deep Value, or custom criteria.
            </p>
          </div>
          <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 6 }}>
            <h4 style={{ marginBottom: 8, color: 'var(--accent-cyan)' }}>3. Monitor spinoffs</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Get alerts when new spinoffs are filed with the SEC. These are often undervalued opportunities.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

