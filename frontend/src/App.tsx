import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendingUp, List, Bell, Filter, Home } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Watchlist from './pages/Watchlist';
import Screener from './pages/Screener';
import Spinoffs from './pages/Spinoffs';
import './index.css';

const queryClient = new QueryClient();

type Page = 'dashboard' | 'watchlist' | 'screener' | 'spinoffs';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'watchlist':
        return <Watchlist />;
      case 'screener':
        return <Screener />;
      case 'spinoffs':
        return <Spinoffs />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-logo">
            <h1>
              <TrendingUp size={20} />
              StockScreen
            </h1>
          </div>
          <nav>
            <ul className="sidebar-nav">
              <li>
                <a 
                  href="#dashboard" 
                  className={currentPage === 'dashboard' ? 'active' : ''}
                  onClick={(e) => { e.preventDefault(); setCurrentPage('dashboard'); }}
                >
                  <Home size={18} />
                  Dashboard
                </a>
              </li>
              <li>
                <a 
                  href="#watchlist"
                  className={currentPage === 'watchlist' ? 'active' : ''}
                  onClick={(e) => { e.preventDefault(); setCurrentPage('watchlist'); }}
                >
                  <List size={18} />
                  Watchlist
                </a>
              </li>
              <li>
                <a 
                  href="#screener"
                  className={currentPage === 'screener' ? 'active' : ''}
                  onClick={(e) => { e.preventDefault(); setCurrentPage('screener'); }}
                >
                  <Filter size={18} />
                  Screener
                </a>
              </li>
              <li>
                <a 
                  href="#spinoffs"
                  className={currentPage === 'spinoffs' ? 'active' : ''}
                  onClick={(e) => { e.preventDefault(); setCurrentPage('spinoffs'); }}
                >
                  <Bell size={18} />
                  Spinoffs
                </a>
              </li>
            </ul>
          </nav>
        </aside>
        <main className="main-content">
          {renderPage()}
        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;
