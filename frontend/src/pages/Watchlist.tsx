import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, StickyNote } from 'lucide-react';
import { watchlistApi, WatchlistItem } from '../api/client';

const Watchlist: React.FC = () => {
  const queryClient = useQueryClient();
  const [newSymbol, setNewSymbol] = useState('');
  const [newTargetPrice, setNewTargetPrice] = useState('');
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [newNote, setNewNote] = useState('');

  const { data: watchlist, isLoading, error } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => watchlistApi.getAll().then(r => r.data),
  });

  const { data: notes } = useQuery({
    queryKey: ['notes', selectedStock],
    queryFn: () => selectedStock ? watchlistApi.getNotes(selectedStock).then(r => r.data) : [],
    enabled: !!selectedStock,
  });

  const addMutation = useMutation({
    mutationFn: (data: { symbol: string; targetPrice?: number }) => 
      watchlistApi.add(data.symbol, data.targetPrice),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
      setNewSymbol('');
      setNewTargetPrice('');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => watchlistApi.remove(symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
  });

  const addNoteMutation = useMutation({
    mutationFn: (data: { symbol: string; content: string }) => 
      watchlistApi.addNote(data.symbol, data.content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', selectedStock] });
      setNewNote('');
    },
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSymbol.trim()) return;
    addMutation.mutate({
      symbol: newSymbol.toUpperCase(),
      targetPrice: newTargetPrice ? parseFloat(newTargetPrice) : undefined,
    });
  };

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStock || !newNote.trim()) return;
    addNoteMutation.mutate({ symbol: selectedStock, content: newNote });
  };

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title">Watchlist</h1>
        <p className="page-subtitle">Track stocks for fundamental analysis</p>
      </header>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Add Stock</h3>
        </div>
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 12 }}>
          <input
            type="text"
            className="input"
            placeholder="Symbol (e.g., AAPL)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            style={{ width: 150 }}
          />
          <input
            type="number"
            className="input"
            placeholder="Target price (optional)"
            value={newTargetPrice}
            onChange={(e) => setNewTargetPrice(e.target.value)}
            style={{ width: 180 }}
            step="0.01"
          />
          <button type="submit" className="btn btn-primary" disabled={addMutation.isPending}>
            <Plus size={16} />
            {addMutation.isPending ? 'Adding...' : 'Add to Watchlist'}
          </button>
        </form>
        {addMutation.isError && (
          <p style={{ color: 'var(--accent-red)', marginTop: 12, fontSize: 14 }}>
            {(addMutation.error as any)?.response?.data?.detail || 'Failed to add stock'}
          </p>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedStock ? '1fr 400px' : '1fr', gap: 16 }}>
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Your Watchlist</h3>
            <span className="badge badge-blue">{watchlist?.length || 0} stocks</span>
          </div>
          {isLoading ? (
            <div className="loading">Loading...</div>
          ) : error ? (
            <div className="alert alert-warning">Failed to load watchlist</div>
          ) : watchlist && watchlist.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Target Price</th>
                  <th>Added</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.map((item: WatchlistItem) => (
                  <tr 
                    key={item.id} 
                    style={{ 
                      cursor: 'pointer',
                      background: selectedStock === item.symbol ? 'var(--bg-tertiary)' : undefined 
                    }}
                    onClick={() => setSelectedStock(item.symbol)}
                  >
                    <td className="symbol">{item.symbol}</td>
                    <td>{item.target_price ? `$${item.target_price.toFixed(2)}` : '-'}</td>
                    <td>{new Date(item.added_at).toLocaleDateString()}</td>
                    <td>
                      <button 
                        className="btn btn-danger" 
                        style={{ padding: '6px 10px' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          removeMutation.mutate(item.symbol);
                        }}
                        disabled={removeMutation.isPending}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <p>No stocks in watchlist</p>
              <p style={{ fontSize: 14, marginTop: 8 }}>Add a stock above to get started</p>
            </div>
          )}
        </div>

        {selectedStock && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <StickyNote size={16} />
                Notes for {selectedStock}
              </h3>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '6px 10px' }}
                onClick={() => setSelectedStock(null)}
              >
                Close
              </button>
            </div>
            
            <form onSubmit={handleAddNote} style={{ marginBottom: 16 }}>
              <textarea
                className="input"
                placeholder="Add your investment thesis..."
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                style={{ width: '100%', minHeight: 80, resize: 'vertical', marginBottom: 8 }}
              />
              <button type="submit" className="btn btn-primary" disabled={addNoteMutation.isPending}>
                <Plus size={14} />
                Add Note
              </button>
            </form>

            {notes && notes.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {notes.map(note => (
                  <div 
                    key={note.id} 
                    style={{ 
                      padding: 12, 
                      background: 'var(--bg-tertiary)', 
                      borderRadius: 6,
                      borderLeft: '2px solid var(--accent-purple)' 
                    }}
                  >
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                      {note.content}
                    </p>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                      {new Date(note.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>No notes yet</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Watchlist;

