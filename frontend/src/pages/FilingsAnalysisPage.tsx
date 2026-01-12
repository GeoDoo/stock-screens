import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  ArrowLeft, 
  Download, 
  ExternalLink, 
  Brain, 
  History,
  AlertCircle,
  Loader2,
  Calendar,
  Building2
} from 'lucide-react';
import { 
  fetchFilings, 
  analyzeFiling, 
  getFilingPdfUrl, 
  fetchCompanyInfo 
} from '../api';
import type { SECFiling, FilingsListResponse, FilingAnalysisResponse, CompanyInfoResponse } from '../types';
import { ForensicRedFlags } from '../components/ForensicRedFlags';
import { Layout } from '../components/Layout';

export function FilingsAnalysisPage({ symbol: propSymbol }: { symbol?: string }) {
  // Use symbol from props (passed by custom router) or fallback to nothing
  const symbol = propSymbol;
  const [filings, setFilings] = useState<SECFiling[]>([]);
  const [companyInfo, setCompanyInfo] = useState<CompanyInfoResponse | null>(null);
  const [selectedFiling, setSelectedFiling] = useState<SECFiling | null>(null);
  const [analysis, setAnalysis] = useState<FilingAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (symbol) {
      loadData();
    }
  }, [symbol]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [filingsRes, infoRes] = await Promise.all([
        fetchFilings({ ticker: symbol!, formTypes: ['10-K', '10-Q'], limit: 20 }),
        fetchCompanyInfo(symbol!)
      ]);
      setFilings(filingsRes.filings);
      setCompanyInfo(infoRes);
      if (filingsRes.filings.length > 0) {
        setSelectedFiling(filingsRes.filings[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load filings');
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async () => {
    if (!selectedFiling || !symbol) return;
    
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const res = await analyzeFiling({
        ticker: symbol,
        documentUrl: selectedFiling.document_url
      });
      setAnalysis(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-sm text-gray-500 font-medium">Retrieving SEC Archive...</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout fullWidth={true}>
      <div className="h-screen flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <a 
            href={`/?symbol=${symbol}`}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
          >
            <ArrowLeft className="w-5 h-5" />
          </a>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900">{symbol} Forensic Intelligence</h1>
              <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 text-[10px] font-bold rounded uppercase tracking-wider">
                10-K Alpha
              </span>
            </div>
            {companyInfo && (
              <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {companyInfo.name} • CIK {companyInfo.cik}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {selectedFiling && (
            <button
              onClick={runAnalysis}
              disabled={analyzing}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-sm transition-all"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing Shenanigans...
                </>
              ) : (
                <>
                  <Brain className="w-4 h-4" />
                  Run Forensic Audit
                </>
              )}
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Filings List */}
        <aside className="w-80 bg-white border-r border-gray-200 overflow-y-auto flex flex-col">
          <div className="p-4 border-b border-gray-100 bg-gray-50/50">
            <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <History className="w-3.5 h-3.5" />
              Filing History
            </h2>
          </div>
          <div className="flex-1">
            {filings.map((filing) => (
              <button
                key={filing.accession_number}
                onClick={() => {
                  setSelectedFiling(filing);
                  setAnalysis(null);
                }}
                className={`w-full text-left p-4 border-b border-gray-50 transition-colors ${
                  selectedFiling?.accession_number === filing.accession_number
                    ? 'bg-indigo-50 border-r-4 border-r-indigo-600'
                    : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    filing.form_type === '10-K' ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {filing.form_type}
                  </span>
                  <span className="text-[10px] text-gray-400 font-mono">
                    {filing.filing_date}
                  </span>
                </div>
                <p className="text-xs font-semibold text-gray-900 line-clamp-2 leading-snug">
                  {filing.description}
                </p>
              </button>
            ))}
          </div>
        </aside>

        {/* Main Content: PDF Viewer & Analysis */}
        <main className="flex-1 flex bg-gray-100 overflow-hidden">
          {/* PDF Viewer */}
          <div className="flex-1 flex flex-col p-6 overflow-hidden">
            {selectedFiling ? (
              <div className="bg-white rounded-xl shadow-lg border border-gray-200 flex-1 flex flex-col overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <span className="text-sm font-bold text-gray-900">{selectedFiling.document_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={getFilingPdfUrl(
                        symbol!,
                        companyInfo!.cik,
                        selectedFiling.accession_number,
                        selectedFiling.form_type,
                        selectedFiling.filing_date,
                        selectedFiling.document_name
                      )}
                      className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
                      title="Download PDF"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <a
                      href={selectedFiling.document_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
                      title="View on SEC.gov"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
                <div className="flex-1 bg-gray-500 relative">
                  <iframe
                    src={getFilingPdfUrl(
                      symbol!,
                      companyInfo!.cik,
                      selectedFiling.accession_number,
                      selectedFiling.form_type,
                      selectedFiling.filing_date,
                      selectedFiling.document_name
                    )}
                    className="w-full h-full"
                    title="Filing PDF"
                  />
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">Select a filing to begin analysis</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel: Intelligence Sidepanel */}
          <aside className="w-96 bg-white border-l border-gray-200 overflow-y-auto flex flex-col shadow-[-10px_0_15px_-3px_rgba(0,0,0,0.02)]">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Brain className="w-5 h-5 text-indigo-600" />
                Intelligence Panel
              </h2>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                LLM-powered forensic audit of footnotes and management commentary.
              </p>
            </div>

            <div className="p-6">
              {error && (
                <div className="bg-red-50 border border-red-100 rounded-xl p-4 flex gap-3 text-red-800 mb-6">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <div>
                    <div className="font-semibold text-sm">Action Required</div>
                    <div className="text-xs opacity-90 mt-1">{error}</div>
                  </div>
                </div>
              )}

              {analyzing ? (
                <div className="flex flex-col items-center justify-center py-12 gap-4">
                  <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
                  <div className="text-center">
                    <p className="text-sm font-bold text-gray-900">Digitizing Footnotes</p>
                    <p className="text-xs text-gray-500 mt-1">Applying Forensic Prompt Suite...</p>
                  </div>
                </div>
              ) : analysis ? (
                <ForensicRedFlags analysis={analysis.analysis} />
              ) : (
                <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-6 text-center">
                  <Brain className="w-10 h-10 text-indigo-200 mx-auto mb-4" />
                  <h3 className="text-sm font-bold text-indigo-900 mb-2">Ready for Audit</h3>
                  <p className="text-xs text-indigo-700/70 mb-4 leading-relaxed">
                    Select a filing and click 'Run Forensic Audit' to scan for financial shenanigans.
                  </p>
                  <button
                    onClick={runAnalysis}
                    className="w-full py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold shadow-md hover:bg-indigo-700 transition-colors"
                  >
                    Start Analysis
                  </button>
                </div>
              )}
            </div>

            {analysis && (
              <div className="mt-auto p-6 border-t border-gray-100 bg-gray-50">
                <div className="flex items-center gap-2 mb-2">
                  <Calendar className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Audit Details</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-gray-500">Engine</span>
                    <span className="text-gray-900 font-bold">{analysis.model}</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-gray-500">Timestamp</span>
                    <span className="text-gray-900 font-bold">{new Date(analysis.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            )}
          </aside>
        </main>
      </div>
    </div>
  </Layout>
);
}
