import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, ExternalLink, Check, RefreshCw } from 'lucide-react';
import { spinoffApi, Spinoff, SpinoffAlert } from '../api/client';

const Spinoffs: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: spinoffs, isLoading: loadingSpinoffs } = useQuery({
    queryKey: ['spinoffs'],
    queryFn: () => spinoffApi.getAll().then(r => r.data),
  });

  const { data: alerts, isLoading: loadingAlerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => spinoffApi.getAlerts().then(r => r.data),
  });

  const markReadMutation = useMutation({
    mutationFn: (alertId: number) => spinoffApi.markAlertRead(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const unreadAlerts = alerts?.filter(a => !a.is_read) || [];

  const statusColors: Record<string, string> = {
    announced: 'var(--accent-yellow)',
    pending: 'var(--accent-blue)',
    completed: 'var(--accent-green)',
    cancelled: 'var(--accent-red)',
  };

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title">Spinoff Monitor</h1>
        <p className="page-subtitle">Track corporate spinoffs - often undervalued opportunities</p>
      </header>

      {unreadAlerts.length > 0 && (
        <div className="card" style={{ borderColor: 'var(--accent-yellow)', borderWidth: 2 }}>
          <div className="card-header">
            <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Bell size={18} color="var(--accent-yellow)" />
              New Alerts ({unreadAlerts.length})
            </h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {unreadAlerts.map((alert: SpinoffAlert) => (
              <div 
                key={alert.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: 16,
                  background: 'var(--bg-tertiary)',
                  borderRadius: 8,
                  borderLeft: '3px solid var(--accent-yellow)',
                }}
              >
                <div>
                  <h4 style={{ color: 'var(--accent-yellow)', marginBottom: 4 }}>{alert.title}</h4>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{alert.message}</p>
                  <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>
                    {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={() => markReadMutation.mutate(alert.id)}
                  disabled={markReadMutation.isPending}
                >
                  <Check size={14} />
                  Mark Read
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Tracked Spinoffs</h3>
          <span className="badge badge-blue">{spinoffs?.length || 0} total</span>
        </div>
        
        {loadingSpinoffs ? (
          <div className="loading">
            <RefreshCw size={20} className="spin" />
            Loading spinoffs...
          </div>
        ) : spinoffs && spinoffs.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Spinoff</th>
                <th>Parent</th>
                <th>Filing Type</th>
                <th>Date</th>
                <th>Status</th>
                <th>SEC Filing</th>
              </tr>
            </thead>
            <tbody>
              {spinoffs.map((spinoff: Spinoff) => (
                <tr key={spinoff.id}>
                  <td>
                    <div>
                      <span className="symbol">{spinoff.spinoff_symbol || '—'}</span>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                        {spinoff.spinoff_name}
                      </p>
                    </div>
                  </td>
                  <td>
                    <div>
                      <span className="symbol">{spinoff.parent_symbol}</span>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                        {spinoff.parent_name}
                      </p>
                    </div>
                  </td>
                  <td>
                    <span className="badge badge-blue">{spinoff.sec_filing_type}</span>
                  </td>
                  <td>
                    {spinoff.sec_filing_date 
                      ? new Date(spinoff.sec_filing_date).toLocaleDateString() 
                      : '—'}
                  </td>
                  <td>
                    <span 
                      className="badge" 
                      style={{ 
                        background: `${statusColors[spinoff.status]}20`,
                        color: statusColors[spinoff.status],
                      }}
                    >
                      {spinoff.status}
                    </span>
                  </td>
                  <td>
                    {spinoff.sec_filing_url ? (
                      <a 
                        href={spinoff.sec_filing_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ 
                          color: 'var(--accent-cyan)', 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: 4 
                        }}
                      >
                        View <ExternalLink size={14} />
                      </a>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-state">
            <p>No spinoffs tracked yet</p>
            <p style={{ fontSize: 14, marginTop: 8 }}>
              The system automatically monitors SEC filings for new spinoffs
            </p>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Why Monitor Spinoffs?</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 8 }}>
            <h4 style={{ color: 'var(--accent-green)', marginBottom: 8 }}>🏦 Forced Selling</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Index funds and institutions often must sell spinoffs due to mandate restrictions, creating buying opportunities.
            </p>
          </div>
          <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 8 }}>
            <h4 style={{ color: 'var(--accent-blue)', marginBottom: 8 }}>📉 Under-Followed</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Spinoffs typically have little analyst coverage initially, leading to market inefficiencies.
            </p>
          </div>
          <div style={{ padding: 16, background: 'var(--bg-tertiary)', borderRadius: 8 }}>
            <h4 style={{ color: 'var(--accent-purple)', marginBottom: 8 }}>💡 Hidden Value</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Spinoffs often unlock value that was hidden within a larger conglomerate structure.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Spinoffs;

