import { useState, useEffect } from 'react';
import { 
  FileText, 
  ArrowLeft, 
  Download, 
  ExternalLink, 
  Brain, 
  History,
  AlertCircle,
  Loader2,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { 
  fetchFilings, 
  analyzeFiling, 
  getFilingPdfUrl, 
  fetchCompanyInfo,
  fetchFilingSections,
  analyzeFilingSection,
  compareFilingSections,
  runForensicAudit,
  fetchForensicHistory,
  type ForensicHistoryItem
} from '../api';
import type { 
  SECFiling, 
  FilingAnalysisResponse, 
  CompanyInfoResponse,
  FilingForensicResponse 
} from '../types';
import { ForensicRedFlags } from '../components/ForensicRedFlags';
import { RedFlagHeatmap } from '../components/RedFlagHeatmap';
import { TruthBridge } from '../components/TruthBridge';
import { ForensicTimeline } from '../components/ForensicTimeline';
import { Layout } from '../components/Layout';

export function FilingsAnalysisPage({ symbol: propSymbol }: { symbol?: string }) {
  // Use symbol from props (passed by custom router) or fallback to nothing
  const symbol = propSymbol;
  const [filings, setFilings] = useState<SECFiling[]>([]);
  const [companyInfo, setCompanyInfo] = useState<CompanyInfoResponse | null>(null);
  const [selectedFiling, setSelectedFiling] = useState<SECFiling | null>(null);
  const [sections, setSections] = useState<string[]>([]);
  const [selectedSection, setSelectedSection] = useState<string>('');
  const [compareWithPrevious] = useState(false);
  const [analysis, setAnalysis] = useState<FilingAnalysisResponse | null>(null);
  const [forensicReport, setForensicReport] = useState<FilingForensicResponse | null>(null);
  const [forensicHistory, setForensicHistory] = useState<ForensicHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [formFilter, setFormFilter] = useState<'10-K' | '10-Q' | 'ALL'>('10-K');
  const [loadingSections, setLoadingSections] = useState(false);
  const [analyzing, setAnalyzing] = useState<'none' | 'scan' | 'deep'>('none');
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'document' | 'intelligence'>('document');
  const [isFocusMode, setIsFocusMode] = useState(false);

  useEffect(() => {
    if (forensicReport || analysis) {
      setActiveTab('intelligence');
    }
  }, [forensicReport, analysis]);

  useEffect(() => {
    if (symbol) {
      loadData();
    }
  }, [symbol, formFilter]);

  useEffect(() => {
    if (selectedFiling) {
      loadSections();
    }
  }, [selectedFiling]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'f' && activeTab === 'document' && !analyzing) {
        setIsFocusMode(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, analyzing]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const types = formFilter === 'ALL' ? ['10-K', '10-Q'] : [formFilter];
      const [filingsRes, infoRes, historyRes] = await Promise.all([
        fetchFilings({ ticker: symbol!, formTypes: types, limit: 20 }),
        fetchCompanyInfo(symbol!),
        fetchForensicHistory(symbol!)
      ]);
      setFilings(filingsRes.filings);
      setCompanyInfo(infoRes);
      setForensicHistory(historyRes.history);
      if (filingsRes.filings.length > 0) {
        setSelectedFiling(filingsRes.filings[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load filings');
    } finally {
      setLoading(false);
    }
  };

  const loadSections = async () => {
    if (!selectedFiling) return;
    setLoadingSections(true);
    try {
      const res = await fetchFilingSections(selectedFiling.document_url);
      setSections(res.sections);
      // Default to Full Archive (empty string) instead of auto-selecting Item 7
      setSelectedSection('');
    } catch (err) {
      console.error('Failed to load sections', err);
    } finally {
      setLoadingSections(false);
    }
  };

  const runAnalysis = async () => {
    if (!selectedFiling || !symbol) return;
    
    setAnalyzing('scan');
    setAnalysis(null);
    setForensicReport(null); // Clear deep audit report
    try {
      let res;
      if (compareWithPrevious && selectedSection) {
        // Find previous filing of same type
        const previousFiling = filings.find(f => 
          f.form_type === selectedFiling.form_type && 
          f.filing_date < selectedFiling.filing_date
        );
        
        if (!previousFiling) {
          throw new Error(`No previous ${selectedFiling.form_type} found for comparison.`);
        }
        
        res = await compareFilingSections({
          ticker: symbol,
          currentUrl: selectedFiling.document_url,
          previousUrl: previousFiling.document_url,
          sectionName: selectedSection
        });
      } else if (selectedSection) {
        res = await analyzeFilingSection({
          ticker: symbol,
          documentUrl: selectedFiling.document_url,
          sectionName: selectedSection
        });
      } else {
        res = await analyzeFiling({
          ticker: symbol,
          documentUrl: selectedFiling.document_url
        });
      }
      setAnalysis(res);
    } catch (err) {
      console.error('Analysis failed', err);
      const apiError = err as any;
      setError(apiError.message || 'Analysis failed');
    } finally {
      setAnalyzing('none');
    }
  };

  const runDeepAudit = async () => {
    if (!selectedFiling || !symbol) return;
    
    setAnalyzing('deep');
    setForensicReport(null);
    setAnalysis(null); // Clear quick scan/comparison
    setError(null);
    
    try {
      const res = await runForensicAudit({
        ticker: symbol,
        documentUrl: selectedFiling.document_url,
        accessionNumber: selectedFiling.accession_number
      });
      setForensicReport(res);
    } catch (err) {
      console.error('Forensic audit failed', err);
      let message = 'Forensic audit failed';
      if (err instanceof Error) {
        message = err.message;
        // P0: Detect JSON truncation error and provide a better message
        if (message.includes('Invalid JSON') || message.includes('EOF while parsing')) {
          message = 'The forensic report was too complex for the current AI window. Try scanning a specific section instead.';
        }
      }
      setError(message);
    } finally {
      setAnalyzing('none');
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
        {/* Header - Compact */}
        {!isFocusMode && (
          <header className="bg-white border-b border-gray-100 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
            <div className="flex items-center gap-4">
              <a 
                href="/filings"
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors text-gray-400"
                title="Back to SEC Filings"
              >
                <ArrowLeft className="w-4 h-4" />
              </a>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-lg font-black text-gray-900 tracking-tighter uppercase leading-none">{symbol}</h1>
                <div className="h-3 w-[1px] bg-gray-200" />
                <span className="text-[9px] font-black text-indigo-600 uppercase tracking-[0.2em] bg-indigo-50/50 px-2 py-0.5 rounded-full border border-indigo-100/50">
                  Forensic Intelligence
                </span>
              </div>
              {companyInfo && (
                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-[0.1em] mt-1 opacity-80">
                  {companyInfo.name}
                </p>
              )}
            </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="h-8 w-[1px] bg-gray-100" />
              <div className="flex items-center gap-4">
                 {/* Global Status/Actions can go here if needed */}
              </div>
            </div>
          </header>
        )}

        <div className="flex-1 flex overflow-hidden">
          {/* Left Sidebar: Filings List */}
          {!isFocusMode && (
          <aside className="w-40 bg-white border-r border-gray-100 overflow-y-auto flex flex-col">
            <div className="p-3 border-b border-gray-100 bg-gray-50/30">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.25em]">
                  Archives
                </h2>
              </div>
              <div className="flex gap-1 p-0.5 bg-gray-100 rounded-lg">
                {(['10-K', '10-Q', 'ALL'] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setFormFilter(type)}
                    className={`flex-1 py-1 text-[8px] font-black rounded-md transition-all ${
                      formFilter === type 
                        ? 'bg-white text-indigo-600 shadow-sm' 
                        : 'text-gray-400 hover:text-gray-600'
                    }`}
                  >
                    {type === 'ALL' ? 'ALL' : type.split('-')[1]}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex-1">
                {filings.map((filing) => (
                  <button
                    key={filing.accession_number}
                    onClick={() => {
                      setSelectedFiling(filing);
                      setAnalysis(null);
                    }}
                    className={`w-full text-left px-3 py-3 border-b border-gray-50 transition-all ${
                      selectedFiling?.accession_number === filing.accession_number
                        ? 'bg-indigo-50/50 border-r-4 border-r-indigo-600'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`px-1 py-0.5 rounded-[3px] text-[8px] font-black uppercase tracking-wider ${
                        filing.form_type === '10-K' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {filing.form_type}
                      </span>
                      <span className="text-[8px] font-black text-gray-400">
                        {new Date(filing.filing_date).getFullYear()}
                      </span>
                    </div>
                    <p className={`text-[9px] leading-tight line-clamp-1 ${
                      selectedFiling?.accession_number === filing.accession_number ? 'font-bold text-gray-900' : 'font-medium text-gray-400'
                    }`}>
                      {new Date(filing.filing_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </p>
                  </button>
                ))}
              </div>
            </aside>
          )}

          {/* Main Content */}
          <main className="flex-1 flex flex-col bg-[#FBFBFC] overflow-hidden">
            {/* Action Bar / Tabs Combined */}
            {!isFocusMode && (
              <div className="bg-white border-b border-gray-200 px-6 flex items-center justify-between shadow-[0_1px_2px_rgba(0,0,0,0.02)] z-10">
                <div className="flex items-center gap-8 self-stretch">
                  <button
                    onClick={() => setActiveTab('document')}
                    className={`h-12 text-[10px] font-black uppercase tracking-[0.25em] transition-all border-b-2 -mb-[1px] ${
                      activeTab === 'document' 
                        ? 'border-indigo-600 text-indigo-600' 
                        : 'border-transparent text-gray-400 hover:text-gray-600'
                    }`}
                  >
                    Document
                  </button>
                  <button
                    onClick={() => setActiveTab('intelligence')}
                    className={`h-12 text-[10px] font-black uppercase tracking-[0.25em] transition-all border-b-2 -mb-[1px] flex items-center gap-2 ${
                      activeTab === 'intelligence' 
                        ? 'border-indigo-600 text-indigo-600' 
                        : 'border-transparent text-gray-400 hover:text-gray-600'
                    }`}
                  >
                    Intelligence
                    {(forensicReport || analysis) && (
                      <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-pulse" />
                    )}
                  </button>
                </div>

                {/* Contextual Controls Moved Here */}
                <div className="flex items-center gap-4 h-12">
                  {selectedFiling && (
                    <>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Target:</span>
                        <select
                          value={selectedSection}
                          onChange={(e) => setSelectedSection(e.target.value)}
                          disabled={loadingSections || analyzing !== 'none'}
                          className="bg-gray-50 border border-gray-200 text-gray-900 text-[10px] font-bold rounded-lg focus:ring-1 focus:ring-indigo-500 block px-2 py-1.5 transition-all outline-none"
                        >
                          {loadingSections ? (
                            <option>Extracting...</option>
                          ) : sections.length > 0 ? (
                            <>
                              <option value="">Full Archive</option>
                              {sections.map((s) => (
                                <option key={s} value={s}>{s}</option>
                              ))}
                            </>
                          ) : (
                            <option value="">No Sections</option>
                          )}
                        </select>
                      </div>

                      <div className="h-4 w-[1px] bg-gray-200" />

                      <div className="flex items-center gap-3">
                        <button
                          onClick={runAnalysis}
                          disabled={analyzing !== 'none'}
                          className="flex items-center gap-2 bg-white border border-gray-200 hover:border-indigo-200 hover:bg-indigo-50 text-indigo-600 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all shadow-sm"
                        >
                          {analyzing === 'scan' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Brain className="w-3 h-3" />}
                          {compareWithPrevious ? 'Compare' : 'Scan'}
                        </button>

                        <button
                          onClick={runDeepAudit}
                          disabled={analyzing !== 'none'}
                          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all shadow-md shadow-slate-200"
                        >
                          {analyzing === 'deep' ? <Loader2 className="w-3 h-3 animate-spin" /> : <div className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />}
                          Deep Audit
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            <div className={`flex-1 overflow-y-auto ${isFocusMode ? 'p-0' : 'p-8'}`}>
              <div className={isFocusMode ? 'w-full h-full' : 'max-w-6xl mx-auto'}>
                {activeTab === 'document' ? (
                  selectedFiling ? (
                    <div className={`bg-white shadow-sm flex flex-col overflow-hidden ${
                      isFocusMode ? 'h-full w-full rounded-none' : 'rounded-2xl border border-gray-200 h-[calc(100vh-180px)]'
                    }`}>
                      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/30">
                        <div className="flex items-center gap-3">
                          <FileText className="w-5 h-5 text-gray-400" />
                          <span className="text-sm font-bold text-gray-900">{selectedFiling.document_name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setIsFocusMode(!isFocusMode)}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
                            title={isFocusMode ? "Exit Focus Mode" : "Focus Mode"}
                          >
                            {isFocusMode ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                          </button>
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
                      <div className={`flex-1 relative ${isFocusMode ? 'bg-black' : 'bg-gray-800'}`}>
                        <iframe
                          src={getFilingPdfUrl(
                            symbol!,
                            companyInfo!.cik,
                            selectedFiling.accession_number,
                            selectedFiling.form_type,
                            selectedFiling.filing_date,
                            selectedFiling.document_name
                          )}
                          className="w-full h-full border-none"
                          title="Filing PDF"
                        />
                      </div>
                    </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-[60vh] text-center bg-white rounded-2xl border-2 border-dashed border-gray-200">
                    <FileText className="w-12 h-12 text-gray-200 mb-4" />
                    <h3 className="text-sm font-bold text-gray-900 mb-1">No Filing Selected</h3>
                    <p className="text-xs text-gray-400">Select a document from the history to begin.</p>
                  </div>
                )
              ) : (
                <div className="space-y-8">
                  {error && (
                    <div className="bg-red-50 border border-red-100 rounded-xl p-4 flex gap-3 text-red-800">
                      <AlertCircle className="w-5 h-5 shrink-0" />
                      <div>
                        <div className="font-bold text-sm">Action Required</div>
                        <div className="text-xs opacity-90 mt-1">{error}</div>
                      </div>
                    </div>
                  )}

                  {analyzing !== 'none' ? (
                    <div className="flex flex-col items-center justify-center py-24 gap-6 bg-white rounded-2xl border border-gray-200 shadow-sm">
                      <div className="relative">
                        <Loader2 className="w-12 h-12 text-indigo-600 animate-spin" />
                        <Brain className="w-6 h-6 text-indigo-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-black text-gray-900 tracking-tight">
                          {analyzing === 'deep' ? 'Executing Deep Forensic Audit' : 'Digitizing Corporate Intelligence'}
                        </p>
                        <p className="text-sm text-gray-500 mt-2">
                          {analyzing === 'deep' 
                            ? 'Applying comprehensive forensic prompt suite to all archive notes...'
                            : 'Applying forensic accounting prompt suite to targeted section...'}
                        </p>
                      </div>
                    </div>
                  ) : forensicReport ? (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                      <div className="grid grid-cols-1 gap-8">
                        <TruthBridge 
                          reportedEps={forensicReport.report.reported_eps}
                          adjustments={forensicReport.report.adjustments}
                          totalAdjustment={forensicReport.report.forensic_eps_adjustment}
                        />
                        
                        <RedFlagHeatmap 
                          redFlags={forensicReport.report.red_flags} 
                          consistencyScore={forensicReport.report.accounting_consistency_score} 
                        />

                        {forensicHistory.length > 0 && (
                          <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm">
                            <h3 className="text-sm font-bold text-gray-900 uppercase tracking-widest mb-6 flex items-center gap-2">
                              <History className="w-4 h-4 text-indigo-600" />
                              Historical Consistency Timeline
                            </h3>
                            <ForensicTimeline history={forensicHistory} ticker={symbol!} />
                          </div>
                        )}
                      </div>
                    </div>
                  ) : analysis ? (
                    <div className="bg-white p-10 rounded-2xl border border-gray-200 shadow-sm">
                       <ForensicRedFlags analysis={analysis.analysis} />
                    </div>
                  ) : (
                    <div className="bg-white border border-gray-200 rounded-2xl p-12 text-center shadow-sm">
                      <div className="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Brain className="w-10 h-10 text-indigo-600" />
                      </div>
                      <h3 className="text-xl font-black text-gray-900 mb-3 tracking-tight">Intelligence Engine Standby</h3>
                      <p className="text-gray-500 max-w-md mx-auto text-sm leading-relaxed">
                        Select a target section above and trigger a scan to uncover hidden accounting risks, tone shifts, and management red flags.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  </Layout>
);
}
