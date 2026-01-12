/**
 * SEC Filings Viewer - Phase 1 of Forensic Intelligence Roadmap
 * 
 * Browse and download SEC filings as PDF.
 */
import { useState, useCallback } from 'react';
import { fetchFilings, getFilingPdfUrl, type ApiError } from '../api';
import type { SECFiling, FilingsListResponse } from '../types';

const FORM_TYPES = [
  { value: '10-K', label: '10-K (Annual Report)' },
  { value: '10-Q', label: '10-Q (Quarterly)' },
  { value: '8-K', label: '8-K (Current Report)' },
  { value: 'DEF 14A', label: 'DEF 14A (Proxy)' },
  { value: '4', label: 'Form 4 (Insider)' },
  { value: 'S-1', label: 'S-1 (IPO)' },
];

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function getFormBadgeColor(formType: string): string {
  if (formType.startsWith('10-K')) return 'bg-blue-100 text-blue-800';
  if (formType.startsWith('10-Q')) return 'bg-green-100 text-green-800';
  if (formType.startsWith('8-K')) return 'bg-amber-100 text-amber-800';
  if (formType.includes('DEF 14') || formType.includes('DEFA14')) return 'bg-purple-100 text-purple-800';
  if (formType === '4' || formType === '3' || formType === '5') return 'bg-red-100 text-red-800';
  if (formType.startsWith('S-')) return 'bg-pink-100 text-pink-800';
  return 'bg-gray-100 text-gray-800';
}


export default function FilingsPage() {
  const [ticker, setTicker] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [filings, setFilings] = useState<SECFiling[]>([]);
  const [companyName, setCompanyName] = useState<string | null>(null);
  const [cik, setCik] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    if (!ticker.trim()) return;
    
    setLoading(true);
    setError(null);
    setFilings([]);
    setCompanyName(null);
    setCik(null);
    
    try {
      // When filtering by form type, fetch more filings since filtered types
      // may be spread throughout a company's filing history (e.g., 10-Ks are annual)
      const limit = selectedTypes.length > 0 ? 1000 : 100;
      
      const result: FilingsListResponse = await fetchFilings({
        ticker: ticker.toUpperCase().trim(),
        formTypes: selectedTypes.length > 0 ? selectedTypes : undefined,
        limit,
      });
      
      setFilings(result.filings);
      setCompanyName(result.company_name);
      setCik(result.cik);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message || 'Failed to fetch filings');
    } finally {
      setLoading(false);
    }
  }, [ticker, selectedTypes]);

  const handleDownloadPdf = useCallback(async (filing: SECFiling) => {
    if (!cik) {
      setError('CIK not available');
      return;
    }
    
    setDownloadingId(filing.accession_number);
    setError(null);
    
    try {
      const pdfUrl = getFilingPdfUrl(
        ticker.toUpperCase(),
        cik,
        filing.accession_number,
        filing.form_type,
        filing.filing_date,
        filing.document_name
      );
      
      // Download the PDF
      const response = await fetch(pdfUrl);
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Download failed: ${response.status}`);
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${ticker.toUpperCase()}_${filing.form_type}_${filing.filing_date}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const error = err as Error;
      setError(`PDF generation failed: ${error.message}`);
    } finally {
      setDownloadingId(null);
    }
  }, [ticker, cik]);

  const toggleType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type)
        ? prev.filter((t) => t !== type)
        : [...prev, type]
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">SEC Filings Viewer</h1>
          <p className="mt-1 text-sm text-gray-500">
            Browse and download SEC filings as PDF
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Search Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label htmlFor="ticker" className="block text-sm font-medium text-gray-700 mb-1">
                Ticker Symbol
              </label>
              <input
                id="ticker"
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="e.g., AAPL"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading || !ticker.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>

          {/* Form Type Filters */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Form Type
            </label>
            <div className="flex flex-wrap gap-2">
              {FORM_TYPES.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => toggleType(value)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedTypes.includes(value)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {label}
                </button>
              ))}
              {selectedTypes.length > 0 && (
                <button
                  onClick={() => setSelectedTypes([])}
                  className="px-3 py-1 rounded-full text-sm font-medium text-gray-500 hover:text-gray-700"
                >
                  Clear All
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Company Info */}
        {companyName && (
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900">{companyName}</h2>
            <p className="text-sm text-gray-500">CIK: {cik}</p>
          </div>
        )}

        {/* Filings List */}
        {filings.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-semibold text-gray-900">
                {filings.length} Filing{filings.length !== 1 ? 's' : ''} Found
              </h3>
            </div>
            <ul className="divide-y divide-gray-200">
              {filings.map((filing) => (
                <li
                  key={filing.accession_number}
                  className="px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <span className={`px-2.5 py-1 rounded text-sm font-medium ${getFormBadgeColor(filing.form_type)}`}>
                          {filing.form_type}
                        </span>
                        <span className="text-sm text-gray-500">
                          {formatDate(filing.filing_date)}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-gray-700 truncate">
                        {filing.description || filing.form_type}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <a
                        href={filing.viewer_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
                      >
                        SEC Viewer
                      </a>
                      <button
                        onClick={() => handleDownloadPdf(filing)}
                        disabled={downloadingId === filing.accession_number}
                        className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:bg-blue-400 transition-colors flex items-center gap-1"
                      >
                        {downloadingId === filing.accession_number ? (
                          <>
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            Generating...
                          </>
                        ) : (
                          <>
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            PDF
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Empty State */}
        {!loading && filings.length === 0 && companyName && (
          <div className="text-center py-12 text-gray-500">
            No filings found for the selected criteria.
          </div>
        )}

        {/* Initial State */}
        {!loading && !companyName && !error && (
          <div className="text-center py-12 text-gray-400">
            Enter a ticker symbol to search for SEC filings.
          </div>
        )}
      </main>
    </div>
  );
}
