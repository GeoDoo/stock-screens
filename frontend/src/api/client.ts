import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface WatchlistItem {
  id: number;
  symbol: string;
  added_at: string;
  target_price: number | null;
  notes: Note[];
}

export interface Note {
  id: number;
  symbol: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Screen {
  id: string;
  name: string;
  description: string;
}

export interface Spinoff {
  id: number;
  spinoff_symbol: string | null;
  spinoff_name: string;
  parent_symbol: string;
  parent_name: string;
  sec_filing_url: string | null;
  sec_filing_date: string | null;
  status: string;
}

export interface SpinoffAlert {
  id: number;
  spinoff_id: number;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

// API functions
export const watchlistApi = {
  getAll: () => api.get<WatchlistItem[]>('/api/watchlist'),
  add: (symbol: string, targetPrice?: number) => 
    api.post<WatchlistItem>('/api/watchlist', { symbol, target_price: targetPrice }),
  remove: (symbol: string) => api.delete(`/api/watchlist/${symbol}`),
  getNotes: (symbol: string) => api.get<Note[]>(`/api/watchlist/${symbol}/notes`),
  addNote: (symbol: string, content: string) => 
    api.post<Note>(`/api/watchlist/${symbol}/notes`, { content }),
};

export const screeningApi = {
  getScreens: () => api.get<Screen[]>('/api/screening/screens'),
  getScreenDetails: (screenId: string) => api.get(`/api/screening/screens/${screenId}`),
};

export const spinoffApi = {
  getAll: () => api.get<Spinoff[]>('/api/spinoffs'),
  getAlerts: () => api.get<SpinoffAlert[]>('/api/spinoffs/alerts'),
  markAlertRead: (alertId: number) => api.post(`/api/spinoffs/alerts/${alertId}/read`),
};

export const healthApi = {
  check: () => api.get('/health'),
};

