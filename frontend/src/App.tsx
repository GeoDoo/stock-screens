import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import type { StockDataResponse, ValuationRequest, ValuationResult, ScenarioAnalysisResult, CreateMemoRequest, GrowthStage } from './types';
import { GlossaryRef } from './components/GlossaryRef';
import { FinancialRatiosTable } from './components/FinancialRatiosTable';
import { DiscountRateModal } from './components/DiscountRateModal';
import { AssumptionHistoryDrawer } from './components/AssumptionHistoryDrawer';
import { AssumptionCommitModal } from './components/AssumptionCommitModal';
import { formatCurrency, formatPercent, formatNumber, formatShareCount } from './utils';
import {
  normalizeValuationResult,
  normalizeScenarioResult,
  formatMetric,
} from './normalizers';
import { useAssumptionTracker } from './hooks/useAssumptionTracker';
import { useProviders } from './hooks/useProviders';
import { useStockAnalysis } from './hooks/useStockAnalysis';
import { MemoCreateModal } from './components/MemoCreateModal';
import { Layout } from './components/Layout';
import { MonteCarloPanel } from './components/MonteCarloPanel';
import { MultiStageGrowth } from './components/MultiStageGrowth';
import { ProvenanceDisplay } from './components/ProvenanceBadge';
import { SensitivityMatrixPanel } from './components/SensitivityMatrixPanel';
import { ValueDrivers } from './components/ValueDrivers';
import { VolumeSignals } from './components/VolumeSignals';

import { API_BASE } from './config';
import { createMemo } from './api';

// Format seconds into human-readable time (e.g., "5m 30s" or "2h 15m")
function formatResetTime(seconds: number | null): string {
  if (seconds === null || seconds <= 0) return 'soon';
  
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hours > 0) {
    return `${hours}h ${mins}m`;
  } else if (mins > 0) {
    return `${mins}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

export default function App() {
  // Provider management (extracted to hook)
  const {
    fundamentalProviders,
    selectedFundamentalProvider,
    setSelectedFundamentalProvider,
    technicalProviders,
    selectedTechnicalProvider,
    setSelectedTechnicalProvider,
    rateLimits,
    rateLimitsLoading,
    providersLoading,
    isProviderAtLimit,
    refreshRateLimits,
  } = useProviders();

  // Stock analysis (extracted to hook)
  const {
    stockData,
    loading,
    error,
    ratiosResult,
    dividendResult,
    historicalValuation,
    comparableResult,
    comparableLoading,
    technicalResult,
    technicalLoading,
    hasAttemptedAnalysis,
    fallbackNotice,
    analyzeStock: analyzeStockHook,
    fetchComparables,
    fetchTechnical,
    setFallbackNotice,
  } = useStockAnalysis(refreshRateLimits);
  
  // P2 Fix: Read ticker from URL for shareable links
  const [ticker, setTicker] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('symbol')?.toUpperCase() || '';
  });
  
  // P2 Fix: Update URL when ticker changes (matches pattern for fundamentalPeriod)
  useEffect(() => {
    const url = new URL(window.location.href);
    if (ticker) {
      url.searchParams.set('symbol', ticker);
    } else {
      url.searchParams.delete('symbol'); // Don't clutter URL with empty symbol
    }
    window.history.replaceState({}, '', url.toString());
  }, [ticker]);
  
  const [result, setResult] = useState<ValuationResult | null>(null);
  
  // User inputs
  const [revenueGrowth, setRevenueGrowth] = useState('');
  const [operatingMargin, setOperatingMargin] = useState('');
  const [terminalGrowth, setTerminalGrowth] = useState('3');
  const [marketRiskPremium, setMarketRiskPremium] = useState('6');
  const [projectionYears, setProjectionYears] = useState('10');
  
  // Advanced: custom discount rate
  const [useCustomDiscountRate, setUseCustomDiscountRate] = useState(false);
  const [customDiscountRate, setCustomDiscountRate] = useState('');
  
  // Advanced DCF options
  const [useMidYearDiscounting, setUseMidYearDiscounting] = useState(false);
  const [wcMode, setWcMode] = useState<'level' | 'incremental'>('level');
  const [growthStages, setGrowthStages] = useState<GrowthStage[]>([]);
  const [annualDilutionRate, setAnnualDilutionRate] = useState('0');  // SBC dilution %
  const [sectorEvEbitdaMultiple, setSectorEvEbitdaMultiple] = useState('');  // Exit multiple cross-check
  
  // Valuation state (loading/error tracked but not displayed separately)
  const [_valuationLoading, setValuationLoading] = useState(false);
  const [_valuationError, setValuationError] = useState<string | null>(null);
  void _valuationLoading; void _valuationError; // Suppress unused warnings
  
  // Scenario Analysis
  const [scenarioResult, setScenarioResult] = useState<ScenarioAnalysisResult | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [_scenarioError, setScenarioError] = useState<string | null>(null);
  void _scenarioError; // Suppress unused warning
  
  // Discount Rate Modal (for when WACC is missing)
  const [showDiscountModal, setShowDiscountModal] = useState(false);
  const [pendingAnalysis, setPendingAnalysis] = useState<StockDataResponse | null>(null);
  
  // Assumption Audit Trail
  const [showCommitModal, setShowCommitModal] = useState(false);
  
  // Investment Memo state
  const [showMemoCreate, setShowMemoCreate] = useState(false);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
  
  // Tab navigation
  const [activeTab, setActiveTab] = useState<'fundamental' | 'technical'>('fundamental');
  
  // P2 Fix: Read period from URL query params for shareable links
  const [fundamentalPeriod, setFundamentalPeriod] = useState<'annual' | 'ttm'>(() => {
    const params = new URLSearchParams(window.location.search);
    const periodFromUrl = params.get('period');
    return periodFromUrl === 'annual' ? 'annual' : 'ttm'; // Default to TTM
  });
  
  // P2 Fix: Update URL when period changes (without page reload)
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('period', fundamentalPeriod);
    window.history.replaceState({}, '', url.toString());
  }, [fundamentalPeriod]);
  
  // Assumption Audit Trail hook
  const assumptionTracker = useAssumptionTracker(stockData?.symbol || '');
  
  // Fetch audit history when stock changes
  useEffect(() => {
    if (stockData?.symbol) {
      assumptionTracker.fetchHistory();
    }
  }, [stockData?.symbol]);
  
  
  // Computed: Get hints for the selected period
  const currentHints = stockData ? 
    (fundamentalPeriod === 'ttm' && stockData.hints_ttm) ? stockData.hints_ttm : stockData.hints_annual 
    : null;
  
  // Detect significant discrepancies between Annual and TTM data (indicates company transformation)
  const dataDiscrepancyWarning = useMemo(() => {
    if (!stockData?.hints_annual || !stockData?.hints_ttm) return null;
    
    const annual = stockData.hints_annual;
    const ttm = stockData.hints_ttm;
    const warnings: string[] = [];
    
    // Check operating margin discrepancy (most important for DCF)
    if (annual.operating_margin !== null && ttm.operating_margin !== null) {
      const diff = Math.abs(annual.operating_margin - ttm.operating_margin);
      // If difference is more than 50 percentage points OR sign changed
      if (diff > 0.5 || (annual.operating_margin < 0 !== ttm.operating_margin < 0)) {
        const annualPct = (annual.operating_margin * 100).toFixed(1);
        const ttmPct = (ttm.operating_margin * 100).toFixed(1);
        warnings.push(`Operating margin changed dramatically: Annual avg ${annualPct}% → TTM ${ttmPct}%`);
      }
    }
    
    // Check D&A ratio discrepancy (indicates business model change)
    if (annual.da_ratio !== null && ttm.da_ratio !== null) {
      const ratio = annual.da_ratio !== 0 ? Math.abs(ttm.da_ratio / annual.da_ratio) : 0;
      if (ratio < 0.3 || ratio > 3) { // More than 3x change
        warnings.push(`D&A/Revenue ratio changed significantly (may indicate restructuring)`);
      }
    }
    
    return warnings.length > 0 ? warnings : null;
  }, [stockData?.hints_annual, stockData?.hints_ttm]);
  

  // Unified analyze function - uses hook for fetching, adds App-specific logic
  const analyzeStock = async () => {
    if (!ticker.trim() || !selectedFundamentalProvider) return;
    
    setResult(null);
    setScenarioResult(null);
    setShowDiscountModal(false);
    setPendingAnalysis(null);
    
    const symbol = ticker.toUpperCase();
    
    // Use hook for fetching with fallback support
    // onSuccess receives the actual provider that served the data (may differ after fallback)
    await analyzeStockHook(
      symbol,
      selectedFundamentalProvider,
      fundamentalProviders,
      async (stockResponse: StockDataResponse, actualProvider: string) => {
        // Update selected provider if fallback occurred
        if (actualProvider !== selectedFundamentalProvider) {
          setSelectedFundamentalProvider(actualProvider);
        }
        
        // Pre-fill inputs with hints (prefer TTM if available, else annual)
        const hintsToUse = stockResponse.hints_ttm || stockResponse.hints_annual;
        if (hintsToUse?.revenue_growth !== null && hintsToUse?.revenue_growth !== undefined) {
          setRevenueGrowth((hintsToUse.revenue_growth * 100).toFixed(2));
        }
        if (hintsToUse?.operating_margin !== null && hintsToUse?.operating_margin !== undefined) {
          setOperatingMargin((hintsToUse.operating_margin * 100).toFixed(2));
        }
        
        // Fetch comparables separately (requires peer data fetching)
        // Use actualProvider which is correct even after fallback
        fetchComparables(symbol, actualProvider);
        
        // Check if WACC is available for DCF
        const hasWACC = stockResponse.data.wacc !== null;
        
        // Check if inputs are reasonable for auto-running DCF
        // Don't auto-run with extreme values (e.g., -1349% operating margin)
        const opMargin = hintsToUse?.operating_margin;
        const hasExtremeInputs = opMargin !== null && (opMargin < -1.0 || opMargin > 1.0);
        
        if (hasWACC && !hasExtremeInputs) {
          await runValuationWithData(stockResponse, undefined, actualProvider);
          await runScenariosWithData(stockResponse, undefined, actualProvider);
        } else if (!hasWACC) {
          setPendingAnalysis(stockResponse);
          setShowDiscountModal(true);
        } else if (hasExtremeInputs) {
          setFallbackNotice(`Historical operating margin (${(opMargin! * 100).toFixed(0)}%) is extreme. Please adjust assumptions before running DCF valuation.`);
        }
      },
    );
  };

  // Handle modal submit - run DCF with custom rate
  const handleDiscountRateSubmit = async (rate: number) => {
    setShowDiscountModal(false);
    if (!pendingAnalysis) return;
    
    // Set the custom discount rate in state for the valuation
    setUseCustomDiscountRate(true);
    setCustomDiscountRate(rate.toString());
    
    // Run valuation and scenarios with custom rate
    await runValuationWithData(pendingAnalysis, rate / 100);
    await runScenariosWithData(pendingAnalysis, rate / 100);
    
    setPendingAnalysis(null);
  };

  // Handle modal skip - skip DCF analysis
  const handleDiscountRateSkip = () => {
    setShowDiscountModal(false);
    setPendingAnalysis(null);
    // All other analyses (ratios, dividends, comparables) are already running/complete
  };

  // NOTE: fetchComparables, fetchRatios, fetchDividends, fetchHistoricalValuation
  // are now handled by useStockAnalysis hook

  // Run valuation with provided stock data and optional custom discount rate
  const runValuationWithData = async (data: StockDataResponse, discountRateOverride?: number, providerOverride?: string) => {
    const provider = providerOverride || selectedFundamentalProvider;
    setValuationLoading(true);
    setValuationError(null);
    
    // Use hints from SELECTED PERIOD (TTM or Annual) - clean separation
    const periodHints = fundamentalPeriod === 'ttm' && data.hints_ttm 
      ? data.hints_ttm 
      : data.hints_annual;
    
    const revGrowth = revenueGrowth ? parseFloat(revenueGrowth) / 100 : (periodHints?.revenue_growth ?? 0.05);
    const opMargin = operatingMargin ? parseFloat(operatingMargin) / 100 : (periodHints?.operating_margin ?? 0.15);
    
    const request: ValuationRequest = {
      revenue_growth: revGrowth,
      operating_margin: opMargin,
      terminal_growth_rate: parseFloat(terminalGrowth) / 100,
      market_risk_premium: parseFloat(marketRiskPremium) / 100,
      projection_years: parseInt(projectionYears),
      discount_rate_override: discountRateOverride ?? (useCustomDiscountRate && customDiscountRate 
        ? parseFloat(customDiscountRate) / 100 
        : null),
      // Pass FCF ratios from selected period - ensures clean TTM/Annual separation
      da_ratio: periodHints?.da_ratio ?? null,
      capex_ratio: periodHints?.capex_ratio ?? null,
      wc_ratio: periodHints?.wc_ratio ?? null,
      // Advanced DCF options
      use_mid_year_discounting: useMidYearDiscounting,
      wc_mode: wcMode,
      // Multi-stage growth (overrides revenue_growth if provided)
      growth_stages: growthStages.length > 0 ? growthStages : null,
      // SBC dilution - affects per-share value
      annual_dilution_rate: annualDilutionRate ? parseFloat(annualDilutionRate) / 100 : 0,
      // Exit Multiple cross-check (optional)
      sector_ev_ebitda_multiple: sectorEvEbitdaMultiple ? parseFloat(sectorEvEbitdaMultiple) : null,
    };
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${data.symbol}/valuation?provider=${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Valuation failed');
      }
      const resultData: ValuationResult = await res.json();
      setResult(normalizeValuationResult(resultData));
    } catch (err) {
      setValuationError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setValuationLoading(false);
    }
  };


  // Run scenarios with provided stock data and optional custom discount rate
  const runScenariosWithData = async (data: StockDataResponse, discountRateOverride?: number, providerOverride?: string) => {
    const provider = providerOverride || selectedFundamentalProvider;
    setScenarioLoading(true);
    setScenarioResult(null);
    
    // Use hints from SELECTED PERIOD (TTM or Annual) - clean separation
    const periodHints = fundamentalPeriod === 'ttm' && data.hints_ttm 
      ? data.hints_ttm 
      : data.hints_annual;
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${data.symbol}/scenarios?provider=${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projection_years: parseInt(projectionYears) || 10,
          market_risk_premium: parseFloat(marketRiskPremium) / 100 || 0.06,
          discount_rate_override: discountRateOverride ?? null,
          // Pass hints from selected period - ensures clean TTM/Annual separation
          revenue_growth_hint: periodHints?.revenue_growth ?? null,
          operating_margin_hint: periodHints?.operating_margin ?? null,
          da_ratio: periodHints?.da_ratio ?? null,
          capex_ratio: periodHints?.capex_ratio ?? null,
          wc_ratio: periodHints?.wc_ratio ?? null,
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Scenario analysis failed');
      }
      const resultData: ScenarioAnalysisResult = await res.json();
      setScenarioResult(normalizeScenarioResult(resultData));
    } catch (err) {
      setScenarioError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setScenarioLoading(false);
    }
  };

  // === Assumption Audit Trail Functions ===
  
  // Get current assumptions as an object for audit trail
  // Uses currentHints which respects TTM/Annual period selection
  const getCurrentAssumptions = useCallback(() => {
    return {
      revenue_growth: revenueGrowth ? parseFloat(revenueGrowth) / 100 : (currentHints?.revenue_growth ?? 0.05),
      operating_margin: operatingMargin ? parseFloat(operatingMargin) / 100 : (currentHints?.operating_margin ?? 0.15),
      terminal_growth: parseFloat(terminalGrowth) / 100,
      discount_rate: useCustomDiscountRate && customDiscountRate 
        ? parseFloat(customDiscountRate) / 100 
        : (stockData?.data.wacc ?? 0.10),
      projection_years: parseInt(projectionYears),
      market_risk_premium: parseFloat(marketRiskPremium) / 100,
    };
  }, [revenueGrowth, operatingMargin, terminalGrowth, customDiscountRate, useCustomDiscountRate, projectionYears, marketRiskPremium, stockData, currentHints]);

  // Detect which fields changed from the last recorded snapshot
  const getChangedFields = useCallback((): string[] => {
    if (!assumptionTracker.hasHistory) return [];
    
    // Compare current values to what's in history
    const current = getCurrentAssumptions();
    const history = assumptionTracker.history;
    
    if (history.length === 0) return Object.keys(current);
    
    // Build latest snapshot from history
    const latestValues: Record<string, number | null> = {};
    for (const entry of [...history].reverse()) {
      for (const change of entry.changes) {
        latestValues[change.field] = change.new_value;
      }
    }
    
    // Find differences
    const changed: string[] = [];
    for (const [field, value] of Object.entries(current)) {
      const prev = latestValues[field];
      if (prev === undefined || Math.abs((prev || 0) - (value || 0)) > 0.0001) {
        changed.push(field);
      }
    }
    
    return changed;
  }, [getCurrentAssumptions, assumptionTracker.history, assumptionTracker.hasHistory]);

  // Handle "Re-run Valuation" button - shows commit modal
  const handleRerunValuation = () => {
    setShowCommitModal(true);
  };

  // Handle commit confirmation - record assumptions then run valuation
  const handleCommitAndRun = async (note: string | null) => {
    setShowCommitModal(false);
    
    if (!stockData) return;
    
    // Record assumptions to audit trail with market context
    const assumptions = getCurrentAssumptions();
    const marketContext = {
      price_at_time: stockData.data.market_cap && stockData.data.shares_outstanding
        ? stockData.data.market_cap / stockData.data.shares_outstanding
        : undefined,
      intrinsic_value_at_time: result?.intrinsic_value_per_share,
      pe_ratio_at_time: ratiosResult?.annual?.valuation?.pe_ratio ?? ratiosResult?.ttm?.valuation?.pe_ratio ?? undefined,
    };
    
    try {
      await assumptionTracker.recordAssumptions(assumptions, note || undefined, marketContext);
    } catch (err) {
      console.error('Failed to record assumptions:', err);
      // Continue with valuation even if audit fails
    }
    
    // Run valuation and scenarios
    const discountOverride = useCustomDiscountRate && customDiscountRate 
      ? parseFloat(customDiscountRate) / 100 
      : undefined;
    
    await runValuationWithData(stockData, discountOverride);
    await runScenariosWithData(stockData, discountOverride);
  };

  // Memo handlers
  // P2 Fix: Use centralized API instead of raw fetch
  const handleSaveMemo = async (memo: CreateMemoRequest): Promise<void> => {
    await createMemo(memo);
  };

  // Auto-run technical analysis when switching to Technical tab or changing provider
  useEffect(() => {
    // Only fetch if on technical tab, have stock data, and either:
    // 1. No result yet, or
    // 2. Provider changed
    const shouldFetchTechnical = activeTab === 'technical' && 
      stockData && 
      !technicalLoading &&
      (!technicalResult || technicalResult.provider !== selectedTechnicalProvider);
    
    if (shouldFetchTechnical) {
      fetchTechnical(stockData.symbol, selectedTechnicalProvider, technicalProviders);
    }
  }, [activeTab, stockData?.symbol, selectedTechnicalProvider, technicalResult, technicalLoading, fetchTechnical, technicalProviders, stockData]);

  // Track previous fundamental provider to detect changes
  const prevFundamentalProviderRef = useRef<string>('');
  
  // Auto-refresh fundamental data when provider changes (only if already have data)
  useEffect(() => {
    if (!stockData || !selectedFundamentalProvider) return;
    
    const prevProvider = prevFundamentalProviderRef.current;
    prevFundamentalProviderRef.current = selectedFundamentalProvider;
    
    // Only re-fetch if provider actually changed (not on initial set)
    if (prevProvider && prevProvider !== selectedFundamentalProvider) {
      // Re-run analysis with new provider, with rate limit detection
      const refreshWithNewProvider = async () => {
        try {
          const res = await fetch(`${API_BASE}/api/stock/${stockData.symbol}/analyze?provider=${selectedFundamentalProvider}`);
          if (!res.ok) {
            const errData = await res.json();
            const isRateLimit = res.status === 429 || 
              (errData.detail && errData.detail.toLowerCase().includes('rate limit'));
            
            if (isRateLimit) {
              // Revert to previous provider
              setSelectedFundamentalProvider(prevProvider);
              prevFundamentalProviderRef.current = prevProvider;
              const newName = fundamentalProviders.find(p => p.id === selectedFundamentalProvider)?.name || selectedFundamentalProvider;
              const prevName = fundamentalProviders.find(p => p.id === prevProvider)?.name || prevProvider;
              setFallbackNotice(`${newName} is rate limited. Staying with ${prevName}.`);
              await refreshRateLimits();
              return;
            }
            throw new Error(errData.detail || 'Failed to fetch stock data');
          }
          
          // Success - proceed with data
          await analyzeStockHook(
            stockData.symbol,
            selectedFundamentalProvider,
            fundamentalProviders,
            async (stockResponse: StockDataResponse, actualProvider: string) => {
              // Update selected provider if fallback occurred
              if (actualProvider !== selectedFundamentalProvider) {
                setSelectedFundamentalProvider(actualProvider);
              }
              
              const hasWACC = stockResponse.data.wacc !== null;
              if (hasWACC) {
                // Use actualProvider which is correct even after fallback
                await runValuationWithData(stockResponse, undefined, actualProvider);
                await runScenariosWithData(stockResponse, undefined, actualProvider);
              }
              fetchComparables(stockData.symbol, actualProvider);
            },
          );
        } catch (err) {
          // On error, revert to previous provider
          setSelectedFundamentalProvider(prevProvider);
          prevFundamentalProviderRef.current = prevProvider;
        }
      };
      
      refreshWithNewProvider();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFundamentalProvider, stockData?.symbol]);

  // Smart validation: WACC-related issues can be bypassed with custom discount rate
  const canBypassWithCustomRate = useCustomDiscountRate && customDiscountRate && parseFloat(customDiscountRate) > 0;
  
  // Fields that are WACC-related (can be bypassed with custom discount rate)
  const waccFields = ['beta', 'market_cap', 'total_debt', 'cost_of_debt'];
  
  const isWaccRelated = (issue: { field: string; impacts?: string }) => {
    // Check impacts field if available, otherwise fall back to field name
    if (issue.impacts) return issue.impacts === 'wacc';
    return waccFields.includes(issue.field.toLowerCase());
  };
  
  // Filter errors - WACC-related errors are irrelevant when using custom discount rate
  const relevantErrors = (stockData?.validation.errors ?? []).filter(e => {
    if (canBypassWithCustomRate && isWaccRelated(e)) {
      return false;
    }
    return true;
  });
  
  // Filter warnings - WACC-related warnings are irrelevant when using custom discount rate
  const relevantWarnings = (stockData?.validation.warnings ?? []).filter(w => {
    if (canBypassWithCustomRate && isWaccRelated(w)) {
      return false;
    }
    return true;
  });

  return (
    <Layout>

        {/* Provider Selection + Ticker in one cohesive block */}
        <section className="mb-12 space-y-8">
          {/* Data Providers */}
          {providersLoading ? (
            <p className="text-sm text-gray-400">Loading providers...</p>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Fundamental Analysis Provider */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-gray-400 block mb-3">
                  Fundamental Analysis
                  <span className="font-normal text-gray-300 ml-2">(DCF, Comparables, Scenarios)</span>
                </label>
                <div className="flex gap-2 flex-wrap">
                  {fundamentalProviders.map((provider) => {
                    const atLimit = isProviderAtLimit(provider.id);
                    const isDisabled = !provider.available || atLimit;
                    return (
                      <button
                        key={provider.id}
                        onClick={() => {
                          // Just update provider - useEffect will handle refresh if data exists
                          setSelectedFundamentalProvider(provider.id);
                        }}
                        disabled={isDisabled}
                        title={atLimit ? 'Rate limit exceeded' : undefined}
                        className={`px-4 py-2 rounded-lg border-2 transition-all text-left ${
                          selectedFundamentalProvider === provider.id
                            ? 'border-gray-900 bg-gray-900 text-white'
                            : isDisabled
                            ? 'border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400'
                        }`}
                      >
                        <span className="font-semibold text-sm">{provider.name}</span>
                        {provider.recommended && !atLimit && <span className="ml-1 text-xs">★</span>}
                        {atLimit && <span className="ml-1 text-xs text-gray-400">⊘</span>}
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {fundamentalProviders.find(p => p.id === selectedFundamentalProvider)?.description}
                  {selectedFundamentalProvider && (
                    rateLimits[selectedFundamentalProvider] ? (
                      <span className={`ml-2 ${
                        rateLimits[selectedFundamentalProvider].api_limited || rateLimits[selectedFundamentalProvider].remaining === 0
                          ? 'text-gray-500'
                          : rateLimits[selectedFundamentalProvider].percentage >= 80
                          ? 'text-gray-500'
                          : 'text-gray-400'
                      }`}>
                        {rateLimits[selectedFundamentalProvider].api_limited 
                          ? `⊘ Limited — resets in ${formatResetTime(rateLimits[selectedFundamentalProvider].reset_in_seconds)}`
                          : `(${rateLimits[selectedFundamentalProvider].remaining}/${rateLimits[selectedFundamentalProvider].limit} calls left${rateLimits[selectedFundamentalProvider].reset_schedule === 'daily' ? '/day' : '/min'})`
                        }
                      </span>
                    ) : rateLimitsLoading ? (
                      <span className="ml-2 text-gray-300">(...)</span>
                    ) : null
                  )}
                </p>
              </div>

              {/* Technical Analysis Provider */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-gray-400 block mb-3">
                  Technical Analysis
                  <span className="font-normal text-gray-300 ml-2">(Price Charts, Indicators)</span>
                </label>
                <div className="flex gap-2 flex-wrap">
                  {technicalProviders.map((provider) => {
                    const atLimit = isProviderAtLimit(provider.id);
                    const isDisabled = !provider.available || atLimit;
                    return (
                      <button
                        key={provider.id}
                        onClick={() => setSelectedTechnicalProvider(provider.id)}
                        disabled={isDisabled}
                        title={atLimit ? 'Rate limit exceeded' : undefined}
                        className={`px-4 py-2 rounded-lg border-2 transition-all text-left ${
                          selectedTechnicalProvider === provider.id
                            ? 'border-gray-900 bg-gray-900 text-white'
                            : isDisabled
                            ? 'border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400'
                        }`}
                      >
                        <span className="font-semibold text-sm">{provider.name}</span>
                        {provider.recommended && !atLimit && <span className="ml-1 text-xs">★</span>}
                        {atLimit && <span className="ml-1 text-xs text-gray-400">⊘</span>}
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {technicalProviders.find(p => p.id === selectedTechnicalProvider)?.description}
                  {selectedTechnicalProvider && (
                    rateLimits[selectedTechnicalProvider] ? (
                      <span className={`ml-2 ${
                        rateLimits[selectedTechnicalProvider].api_limited || rateLimits[selectedTechnicalProvider].remaining === 0
                          ? 'text-gray-500'
                          : rateLimits[selectedTechnicalProvider].percentage >= 80
                          ? 'text-gray-500'
                          : 'text-gray-400'
                      }`}>
                        {rateLimits[selectedTechnicalProvider].api_limited 
                          ? `⊘ Limited — resets in ${formatResetTime(rateLimits[selectedTechnicalProvider].reset_in_seconds)}`
                          : `(${rateLimits[selectedTechnicalProvider].remaining}/${rateLimits[selectedTechnicalProvider].limit} calls left${rateLimits[selectedTechnicalProvider].reset_schedule === 'daily' ? '/day' : '/min'})`
                        }
                      </span>
                    ) : rateLimitsLoading ? (
                      <span className="ml-2 text-gray-300">(...)</span>
                    ) : null
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Ticker Search */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-gray-400 block mb-3">Stock Ticker</label>
            <div className="flex gap-3">
              <input
                type="text"
                placeholder={selectedFundamentalProvider ? "AAPL" : "Select provider first"}
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && analyzeStock()}
                disabled={!selectedFundamentalProvider}
                className="w-48 px-4 py-3 text-base font-mono font-medium bg-white border-2 border-gray-200 rounded-lg outline-none transition-colors focus:border-gray-400 placeholder:text-gray-300 placeholder:font-normal disabled:bg-gray-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={analyzeStock}
                disabled={loading || !ticker.trim() || !selectedFundamentalProvider}
                className="px-8 py-3 text-sm font-semibold bg-gray-900 text-white rounded-lg transition-opacity hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
            {fallbackNotice && (
              <p className="mt-3 text-sm text-amber-600">
                {fallbackNotice}
              </p>
            )}
          </div>
        </section>

        {/* Tab Switcher */}
        {stockData && (
          <nav className="mb-10 border-b border-gray-200">
            <div className="flex gap-8">
              <button
                onClick={() => setActiveTab('fundamental')}
                className={`pb-4 text-sm font-semibold transition-colors relative ${
                  activeTab === 'fundamental'
                    ? 'text-gray-900'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                Fundamental
                {activeTab === 'fundamental' && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-900" />
                )}
              </button>
              <button
                onClick={() => setActiveTab('technical')}
                className={`pb-4 text-sm font-semibold transition-colors relative ${
                  activeTab === 'technical'
                    ? 'text-gray-900'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                Technical
                {activeTab === 'technical' && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-900" />
                )}
              </button>
            </div>
          </nav>
        )}

        {/* FUNDAMENTAL TAB - No Data Message */}
        {!stockData && activeTab === 'fundamental' && !loading && (
          <div className="text-center py-16">
            {hasAttemptedAnalysis && error ? (
              <>
                <p className="text-gray-400 mb-2">Analysis failed</p>
                <p className="text-sm text-gray-300">Try a different ticker or provider</p>
              </>
            ) : (
              <>
                <p className="text-gray-400 mb-2">No stock data available</p>
                <p className="text-sm text-gray-300">Enter a ticker and click Analyze to get started</p>
              </>
            )}
          </div>
        )}

        {/* FUNDAMENTAL TAB */}
        {stockData && activeTab === 'fundamental' && (
          <>
            {/* Data Period Selector - TTM vs Annual */}
            <div className="mb-8 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                {fundamentalPeriod === 'ttm' 
                  ? 'Showing Trailing Twelve Months data (sum of last 4 quarters)' 
                  : 'Showing most recent Annual Report data'}
              </p>
              <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
                <button
                  onClick={() => setFundamentalPeriod('ttm')}
                  disabled={!stockData.hints_ttm}
                  title={!stockData.hints_ttm 
                    ? "TTM data unavailable — provider doesn't support quarterly data for this stock" 
                    : "Trailing Twelve Months (sum of last 4 quarters)"}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                    fundamentalPeriod === 'ttm'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : stockData.hints_ttm
                        ? 'text-gray-600 hover:text-gray-900'
                        : 'text-gray-300 cursor-not-allowed'
                  }`}
                >
                  TTM
                  {!stockData.hints_ttm && (
                    <span className="ml-1 text-amber-400" title="TTM unavailable">⚠</span>
                  )}
                </button>
                <button
                  onClick={() => setFundamentalPeriod('annual')}
                  title="Most recent Annual Report data"
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                    fundamentalPeriod === 'annual'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Annual
                </button>
              </div>
            </div>

            {/* Historical Data Discrepancy Warning */}
            {dataDiscrepancyWarning && (
              <div className="mb-6 p-4 border border-gray-200 rounded">
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Company Has Transformed Significantly
                </h3>
                <p className="text-sm text-gray-600 mb-2">
                  Historical annual data differs dramatically from recent TTM data. This often indicates major restructuring, pivots, or turnarounds. 
                  <strong> TTM data is recommended</strong> for this stock.
                </p>
                <ul className="text-sm text-gray-600 list-disc list-inside">
                  {dataDiscrepancyWarning.map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Validation Alerts */}
            {(relevantErrors.length > 0 || relevantWarnings.length > 0) && (
              <section className="mb-8 space-y-4">
                {relevantErrors.length > 0 && (
                  <div className="p-6 border border-gray-200 rounded">
                    <h3 className="text-sm font-medium text-gray-700 mb-3">Cannot Run Valuation</h3>
                    <ul className="space-y-1">
                      {relevantErrors.map((e, i) => (
                        <li key={i} className="text-sm text-gray-700">
                          <span className="font-semibold capitalize">{e.field}:</span> {e.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {relevantWarnings.length > 0 && (
                  <div className="p-6 border border-gray-200 rounded">
                    <h3 className="text-sm font-medium text-gray-600 mb-3">Data Quality Warnings</h3>
                    <ul className="space-y-1">
                      {relevantWarnings.map((w, i) => (
                        <li key={i} className="text-sm text-gray-600">
                          <span className="font-semibold capitalize">{w.field}:</span> {w.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            )}

            {/* Company Data */}
            <section className="mb-16">
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                  <h2 className="text-xl font-semibold">
                    {stockData.symbol} {stockData.company_name && `— ${stockData.company_name}`}
                  </h2>
                  <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-500 uppercase tracking-wide">
                    via {selectedFundamentalProvider}
                  </span>
                  {stockData.is_using_ltm && (
                    <span className="px-2 py-0.5 text-xs font-medium rounded bg-emerald-50 text-emerald-600 uppercase tracking-wide" title="Using Last Twelve Months (TTM) data - more current than annual">
                      LTM
                    </span>
                  )}
                </div>
                {stockData.industry && (
                  <p className="text-sm text-gray-500">{stockData.industry}{stockData.sector && ` · ${stockData.sector}`}</p>
                )}
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
                {/* Company Data Card */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Company Data</h3>
                  <p className="text-sm text-gray-400 mb-6">From most recent annual report (not TTM)</p>
                  <table className="w-full">
                    <tbody>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Market Cap<GlossaryRef id="market-cap" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatCurrency(stockData.data.market_cap)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Beta<GlossaryRef id="beta" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatNumber(stockData.data.beta)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Total Debt</td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatCurrency(stockData.data.total_debt)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Cash</td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatCurrency(stockData.data.cash)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Tax Rate<GlossaryRef id="tax-rate" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(stockData.data.tax_rate)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Cost of Debt<GlossaryRef id="cost-of-debt" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(stockData.data.cost_of_debt)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Shares Outstanding<GlossaryRef id="shares-outstanding" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatShareCount(stockData.data.shares_outstanding)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Risk-Free Rate<GlossaryRef id="risk-free-rate" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(stockData.data.risk_free_rate)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">WACC (calculated)<GlossaryRef id="wacc" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(stockData.data.wacc)}</td>
                      </tr>
                    </tbody>
                  </table>
                  
                  {/* Data Provenance - shows source/confidence for key metrics */}
                  {stockData.provenance && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <ProvenanceDisplay provenance={stockData.provenance} />
                    </div>
                  )}
                </div>

                {/* Historical Hints Card */}
      <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Historical Hints</h3>
                  <p className="text-sm text-gray-400 mb-6">Averaged from multiple annual reports (may differ from TTM)</p>
                  <table className="w-full">
                    <tbody>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Revenue Growth (CAGR)<GlossaryRef id="cagr" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(currentHints?.revenue_growth)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Operating Margin<GlossaryRef id="operating-margin" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(currentHints?.operating_margin)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">D&A / Revenue<GlossaryRef id="da" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(currentHints?.da_ratio)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">CapEx / Revenue<GlossaryRef id="capex" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(currentHints?.capex_ratio)}</td>
                      </tr>
                      <tr className="border-b border-gray-100">
                        <td className="py-3 text-sm text-gray-500">Working Capital / Revenue<GlossaryRef id="working-capital" /></td>
                        <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(currentHints?.wc_ratio)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            {/* Financial Ratios */}
            {ratiosResult && (ratiosResult.annual || ratiosResult.ttm) && (
              <section className="mb-16 pt-8 border-t border-gray-100">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-6">Financial Ratios</h2>
                
                {/* Render ratios table based on selected period */}
                {fundamentalPeriod === 'ttm' && ratiosResult.ttm ? (
                  <FinancialRatiosTable ratios={ratiosResult.ttm} />
                ) : fundamentalPeriod === 'annual' && ratiosResult.annual ? (
                  <FinancialRatiosTable ratios={ratiosResult.annual} />
                ) : ratiosResult.annual ? (
                  <FinancialRatiosTable ratios={ratiosResult.annual} />
                ) : ratiosResult.ttm ? (
                  <FinancialRatiosTable ratios={ratiosResult.ttm} />
                ) : (
                  <p className="text-gray-500">No ratios data available</p>
                )}
              </section>
            )}

            {/* Dividend History */}
            {dividendResult && dividendResult.has_dividends && (
              <section className="mb-16 pt-8 border-t border-gray-100">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Dividend History<GlossaryRef id="dividend-yield" /></h2>
                <p className="text-sm text-gray-400 mb-8">Track record of dividend payments</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                  {/* Key Metrics */}
                  <div className="border border-gray-100 rounded p-4">
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Annual Dividend</p>
                    <p className="text-2xl font-medium text-gray-900">
                      {dividendResult.current_annual_dividend ? `$${dividendResult.current_annual_dividend.toFixed(2)}` : '—'}
                    </p>
                  </div>
                  
                  <div className="border border-gray-100 rounded p-4">
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Yield<GlossaryRef id="dividend-yield" /></p>
                    <p className="text-2xl font-medium text-gray-900">
                      {formatPercent(dividendResult.current_yield)}
                    </p>
                  </div>
                  
                  <div className="border border-gray-100 rounded p-4">
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Payout Ratio<GlossaryRef id="payout-ratio" /></p>
                    <p className="text-2xl font-medium text-gray-900">
                      {formatPercent(dividendResult.payout_ratio)}
                    </p>
                    {/* FCF-based payout ratio (more accurate) */}
                    {dividendResult.fcf_payout_ratio != null && (
                      <p className={`text-xs mt-1 ${
                        dividendResult.fcf_payout_ratio > 1 ? 'text-red-500' :
                        dividendResult.fcf_payout_ratio > 0.8 ? 'text-amber-500' :
                        'text-gray-400'
                      }`}>
                        FCF: {formatPercent(dividendResult.fcf_payout_ratio)}
                      </p>
                    )}
                  </div>
                  
                  <div className="border border-gray-100 rounded p-4">
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Growth (CAGR)<GlossaryRef id="cagr" /></p>
                    <p className="text-2xl font-medium text-gray-900">
                      {formatPercent(dividendResult.dividend_cagr)}
                    </p>
                  </div>
                  
                  <div className="border border-gray-100 rounded p-4">
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Consecutive Years</p>
                    <p className="text-2xl font-medium text-gray-900">
                      {dividendResult.consecutive_years} yrs
                    </p>
                  </div>
                </div>
                
                {/* Annual Dividend History Chart */}
                {Object.keys(dividendResult.annual_dividends).length > 0 && (
                  <div className="mt-8">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Annual Dividends</h3>
                    {(() => {
                      const sortedData = Object.entries(dividendResult.annual_dividends)
                        .sort(([a], [b]) => Number(a) - Number(b))  // Oldest first for chart
                        .slice(-10);  // Last 10 years
                      const maxAmount = Math.max(...sortedData.map(([, amt]) => amt));
                      const chartHeight = 120;
                      const topPadding = 25;  // Space for amount labels
                      const barWidth = 40;
                      const gap = 8;
                      const chartWidth = sortedData.length * (barWidth + gap);
                      
                      return (
                        <div className="overflow-x-auto">
                          <svg width={chartWidth} height={chartHeight + topPadding + 30} className="min-w-full">
                            {/* Bars */}
                            {sortedData.map(([year, amount], i) => {
                              const barHeight = maxAmount > 0 ? (amount / maxAmount) * chartHeight : 0;
                              const x = i * (barWidth + gap);
                              const y = topPadding + chartHeight - barHeight;
                              
                              return (
                                <g key={year}>
                                  {/* Bar */}
                                  <rect
                                    x={x}
                                    y={y}
                                    width={barWidth}
                                    height={barHeight}
                                    fill="#22c55e"
                                    className="opacity-80 hover:opacity-100 transition-opacity"
                                    rx={4}
                                  />
                                  {/* Amount label */}
                                  <text
                                    x={x + barWidth / 2}
                                    y={y - 5}
                                    textAnchor="middle"
                                    className="text-xs fill-gray-600 font-mono"
                                  >
                                    ${amount.toFixed(2)}
                                  </text>
                                  {/* Year label */}
                                  <text
                                    x={x + barWidth / 2}
                                    y={topPadding + chartHeight + 16}
                                    textAnchor="middle"
                                    className="text-xs fill-gray-400"
                                  >
                                    {year}
                                  </text>
                                </g>
                              );
                            })}
                          </svg>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </section>
            )}
            
            {dividendResult && !dividendResult.has_dividends && (
              <section className="mb-16 pt-8 border-t border-gray-100">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Dividend History</h2>
                <p className="text-sm text-gray-500">This company does not pay dividends.</p>
              </section>
            )}

            {/* Historical Valuation Context */}
            {historicalValuation && historicalValuation.current && historicalValuation.average_5yr && historicalValuation.premium_discount && historicalValuation.assessment && historicalValuation.average_5yr.pe && (
              <section className="mb-16 pt-8 border-t border-gray-100">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Historical Valuation Context</h2>
                <p className="text-sm text-gray-400 mb-8">Current multiples vs. 5-year averages</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {[
                    { label: 'P/E Ratio', glossaryId: 'pe-ratio', current: historicalValuation.current.pe, avg: historicalValuation.average_5yr.pe, premium: historicalValuation.premium_discount.pe, assessment: historicalValuation.assessment.pe },
                    { label: 'P/S Ratio', glossaryId: 'ps-ratio', current: historicalValuation.current.ps, avg: historicalValuation.average_5yr.ps, premium: historicalValuation.premium_discount.ps, assessment: historicalValuation.assessment.ps },
                    { label: 'P/B Ratio', glossaryId: 'pb-ratio', current: historicalValuation.current.pb, avg: historicalValuation.average_5yr.pb, premium: historicalValuation.premium_discount.pb, assessment: historicalValuation.assessment.pb },
                    { label: 'EV/EBITDA', glossaryId: 'ev-ebitda', current: historicalValuation.current.ev_ebitda, avg: historicalValuation.average_5yr.ev_ebitda, premium: historicalValuation.premium_discount.ev_ebitda, assessment: historicalValuation.assessment.ev_ebitda },
                  ].map(({ label, glossaryId, current, avg, premium, assessment }) => (
                    <div key={label} className="border border-gray-200 rounded-lg p-4">
                      <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">{label}<GlossaryRef id={glossaryId} /></p>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-500">Current</span>
                          <span className="text-sm font-mono font-medium">{formatNumber(current)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-500">5yr Avg</span>
                          <span className="text-sm font-mono font-medium">{formatNumber(avg)}</span>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-gray-100">
                          <span className="text-sm text-gray-500">vs. Avg</span>
                          <span className={`text-sm font-medium px-2 py-0.5 rounded ${
                            assessment === 'cheap' ? 'bg-emerald-100 text-emerald-700' :
                            assessment === 'expensive' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {premium !== null ? `${premium > 0 ? '+' : ''}${(premium * 100).toFixed(0)}%` : '—'} ({assessment})
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Assumptions */}
            <section className="mb-16 pt-8 border-t border-gray-100">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Your Assumptions</h2>
                {assumptionTracker.hasHistory && (
                  <button
                    onClick={() => setShowHistoryDrawer(true)}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    <span>View History ({assumptionTracker.history.length})</span>
                  </button>
                )}
              </div>
              <p className="text-sm text-gray-400 mb-8">Adjust these based on your analysis</p>
              
              <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-8">
                {[
                  { label: <>Revenue Growth (%)<GlossaryRef id="revenue-growth" /></>, value: revenueGrowth, setter: setRevenueGrowth, hint: currentHints?.revenue_growth !== null ? `${fundamentalPeriod === 'ttm' ? 'TTM' : 'Historical'}: ${((currentHints?.revenue_growth ?? 0) * 100).toFixed(2)}%` : null, key: 'revenue' },
                  { label: <>Operating Margin (%)<GlossaryRef id="operating-margin" /></>, value: operatingMargin, setter: setOperatingMargin, hint: currentHints?.operating_margin !== null ? `${fundamentalPeriod === 'ttm' ? 'TTM' : 'Historical'}: ${((currentHints?.operating_margin ?? 0) * 100).toFixed(2)}%` : null, key: 'margin' },
                  { label: <>Terminal Growth Rate (%)<GlossaryRef id="terminal-growth" /></>, value: terminalGrowth, setter: setTerminalGrowth, hint: 'Typically 2-3% (GDP growth)', key: 'terminal' },
                  { label: <>Market Risk Premium (%)<GlossaryRef id="market-risk-premium" /></>, value: marketRiskPremium, setter: setMarketRiskPremium, hint: 'Typically 5-7%', key: 'mrp' },
                  { label: 'Projection Years', value: projectionYears, setter: setProjectionYears, hint: 'Usually 5-10 years', key: 'years' },
                ].map(({ label, value, setter, hint, key }) => (
                  <div key={key} className="flex flex-col">
                    <label className="text-sm font-medium text-gray-500 mb-2">{label}</label>
                    <input
                      type="number"
                      step="0.1"
                      value={value}
                      onChange={(e) => setter(e.target.value)}
                      className="w-full px-4 py-3 text-lg font-mono border border-gray-200 rounded-lg outline-none transition-all focus:border-gray-400 focus:ring-2 focus:ring-gray-100"
                      style={{ backgroundColor: '#fff' }}
                    />
                    {hint && <span className="text-xs text-gray-400 mt-2">{hint}</span>}
                  </div>
                ))}
              </div>

              {/* Custom Discount Rate (non-intrusive) */}
              <div className="mb-8 pt-4 border-t border-gray-100">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={useCustomDiscountRate}
                    onChange={(e) => setUseCustomDiscountRate(e.target.checked)}
                    className="w-4 h-4 accent-emerald-600"
                  />
                  <span className="text-sm text-gray-500 group-hover:text-gray-700">
                    Use custom discount rate instead of WACC {stockData.data.wacc !== null && `(${formatPercent(stockData.data.wacc)})`}
                  </span>
                </label>
                
                {useCustomDiscountRate && (
                  <div className="mt-4 flex items-center gap-4">
                    <div className="flex flex-col gap-2 w-48">
                      <label className="text-sm font-medium text-gray-600">Your Required Return (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={customDiscountRate}
                        onChange={(e) => setCustomDiscountRate(e.target.value)}
                        placeholder={stockData.data.wacc !== null ? `WACC: ${(stockData.data.wacc * 100).toFixed(1)}` : 'e.g., 12'}
                        className="px-3 py-2.5 text-base font-mono bg-white border-2 border-emerald-200 rounded-md outline-none transition-colors focus:border-emerald-400"
                      />
      </div>
                    <p className="text-xs text-gray-400 max-w-xs">
                      Override the calculated WACC with your personal required return. 
                      Higher rate = lower intrinsic value = more conservative.
        </p>
      </div>
                )}
              </div>

              {/* Advanced DCF Options */}
              <div className="mb-8 pt-4 border-t border-gray-100">
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Advanced Options</p>
                <div className="flex flex-wrap gap-6">
                  <div className="flex flex-col">
                    <label className="flex items-center gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={useMidYearDiscounting}
                        onChange={(e) => setUseMidYearDiscounting(e.target.checked)}
                        className="w-4 h-4 accent-gray-600"
                      />
                      <span className="text-sm text-gray-500 group-hover:text-gray-700">
                        Mid-year discounting
                      </span>
                      <span className="text-xs text-gray-400">(assumes cash flows occur mid-year)</span>
                    </label>
                    {useMidYearDiscounting && (
                      <div className="ml-7 mt-1 text-xs text-emerald-600">
                        +2-5% value increase (cash flows arrive 6 months earlier)
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500">Working Capital:</span>
                    <select
                      value={wcMode}
                      onChange={(e) => setWcMode(e.target.value as 'level' | 'incremental')}
                      className="px-2 py-1 text-sm border border-gray-200 rounded bg-white text-gray-700"
                    >
                      <option value="level">Level (WC = Revenue × Ratio)</option>
                      <option value="incremental">Incremental (ΔWC = ΔRevenue × Intensity)</option>
                    </select>
                  </div>
                  
                  {/* SBC Dilution Rate */}
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500">SBC Dilution:</span>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      step="0.1"
                      value={annualDilutionRate}
                      onChange={(e) => setAnnualDilutionRate(e.target.value)}
                      className="w-16 px-2 py-1 text-sm font-mono border border-gray-200 rounded bg-white text-gray-700"
                    />
                    <span className="text-xs text-gray-400">%/year</span>
                    <span className="text-xs text-gray-400" title="Annual share issuance from stock-based compensation. Reduces per-share value.">
                      (share dilution)
                    </span>
                  </div>
                  
                  {/* Sector EV/EBITDA Multiple for Exit Multiple Cross-Check */}
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500">Sector EV/EBITDA:</span>
                    <input
                      type="number"
                      min="0"
                      max="50"
                      step="0.5"
                      value={sectorEvEbitdaMultiple}
                      onChange={(e) => setSectorEvEbitdaMultiple(e.target.value)}
                      placeholder="—"
                      className="w-16 px-2 py-1 text-sm font-mono border border-gray-200 rounded bg-white text-gray-700"
                    />
                    <span className="text-xs text-gray-400">×</span>
                    <span className="text-xs text-gray-400" title="Sector/peer median EV/EBITDA. Used to cross-check Gordon Growth terminal value. Leave empty to skip cross-check.">
                      (exit multiple cross-check)
                    </span>
                  </div>
                </div>
                
                {/* WC Mode Impact Calculator */}
                {stockData.data.working_capital !== null && stockData.data.revenue !== null && currentHints?.wc_ratio !== null && (
                  <div className="mt-4 p-4 rounded-lg border bg-gray-50 border-gray-200">
                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Working Capital Mode Impact</p>
                    
                    {(() => {
                      const actualWC = stockData.data.working_capital || 0;
                      const revenue = stockData.data.revenue || 1;
                      const inputRatio = (currentHints?.wc_ratio ?? 0);
                      const actualRatio = actualWC / revenue;
                      const targetWC = revenue * inputRatio;
                      const mismatch = actualWC - targetWC;
                      const mismatchPct = Math.abs(mismatch / targetWC) * 100;
                      const growth = parseFloat(revenueGrowth) / 100 || 0.05;
                      
                      // Year 1 calculations
                      const newRevenue = revenue * (1 + growth);
                      const levelDelta = (newRevenue * inputRatio) - actualWC;
                      const incrDelta = (newRevenue - revenue) * inputRatio;
                      const fcfDiff = incrDelta - levelDelta; // Positive = Level releases more cash
                      
                      const isSignificant = mismatchPct > 10;
                      
                      return (
                        <div className="space-y-3">
                          {/* Actual vs Target comparison */}
                          <div className="grid grid-cols-2 gap-4 text-xs">
                            <div>
                              <span className="text-gray-500">Actual WC/Revenue:</span>
                              <span className="ml-2 font-mono font-medium">{(actualRatio * 100).toFixed(1)}%</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Input Ratio:</span>
                              <span className="ml-2 font-mono font-medium">{(inputRatio * 100).toFixed(1)}%</span>
                            </div>
                          </div>
                          
                          {/* Mismatch indicator */}
                          <div className={`p-3 rounded ${isSignificant ? 'bg-amber-100 border border-amber-200' : 'bg-emerald-50 border border-emerald-100'}`}>
                            {isSignificant ? (
                              <div className="text-xs">
                                <p className="font-medium text-amber-800 mb-1">
                                  WC is {mismatch > 0 ? 'ABOVE' : 'BELOW'} target by {formatCurrency(Math.abs(mismatch))}
                                </p>
                                <p className="text-amber-700">
                                  <strong>Year 1 FCF difference:</strong> {formatCurrency(Math.abs(fcfDiff))}
                                  {fcfDiff > 0 
                                    ? ' — Level mode releases cash (WC normalizes down)'
                                    : ' — Level mode invests cash (WC builds up)'}
                                </p>
                                <p className="text-amber-600 mt-1">
                                  Modes will produce noticeably different results!
                                </p>
                              </div>
                            ) : (
                              <div className="text-xs text-emerald-700">
                                <p className="font-medium mb-1">WC is close to target ratio</p>
                                <p>Year 1 FCF difference: ~{formatCurrency(Math.abs(fcfDiff))} (minimal impact)</p>
                                <p className="text-emerald-600 mt-1">Both modes will produce similar results for this company.</p>
                              </div>
                            )}
                          </div>
                          
                          {/* Mode descriptions */}
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div className={`p-2 rounded ${wcMode === 'level' ? 'bg-blue-100 border border-blue-200' : 'bg-gray-100'}`}>
                              <p className="font-medium text-gray-700">Level</p>
                              <p className="text-gray-500">Resets WC to target each year</p>
                            </div>
                            <div className={`p-2 rounded ${wcMode === 'incremental' ? 'bg-amber-100 border border-amber-200' : 'bg-gray-100'}`}>
                              <p className="font-medium text-gray-700">Incremental</p>
                              <p className="text-gray-500">Grows WC with revenue only</p>
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>

              {/* Multi-Stage Growth */}
              <div className="mt-8 pt-4 border-t border-gray-100">
                <MultiStageGrowth
                  stages={growthStages}
                  onChange={setGrowthStages}
                  terminalGrowth={parseFloat(terminalGrowth) / 100 || 0.03}
                />
              </div>

              {/* Re-run Valuation Button */}
              {result && (
                <div className="mt-8 pt-6 border-t border-gray-100 flex items-center gap-4">
                  <button
                    onClick={handleRerunValuation}
                    disabled={loading}
                    className="px-6 py-3 bg-gray-900 text-white font-medium rounded hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                        Running...
                      </>
                    ) : (
                      <>
                        Re-run Valuation
                      </>
                    )}
                  </button>
                  <span className="text-sm text-gray-400">
                    Updates will be tracked in your assumption history
                  </span>
                </div>
              )}

            </section>

            {/* Valuation Result */}
            {result && (
              <section className="pt-8 border-t border-gray-100">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-8">Valuation Result</h2>
            
            {/* Main Result */}
            <div className="mb-12">
              <div className="flex items-baseline gap-4 mb-3">
                <span className="text-sm text-gray-500">Intrinsic Value<GlossaryRef id="intrinsic-value" /></span>
                <span className="text-5xl font-bold font-mono tracking-tight">${result.intrinsic_value_per_share.toFixed(2)}</span>
                <span className="text-sm text-gray-400">per share</span>
              </div>
              
              {result.market_cap && stockData && stockData.data.shares_outstanding && result.intrinsic_value_per_share && (
                <div className="flex items-center gap-6 mt-4">
                  <span className="text-sm text-gray-500">
                    Current: ~${(result.market_cap / stockData.data.shares_outstanding).toFixed(2)}
                  </span>
                  {(() => {
                    const currentPrice = result.market_cap / stockData.data.shares_outstanding;
                    if (currentPrice === 0) return null;
                    const upside = ((result.intrinsic_value_per_share - currentPrice) / currentPrice) * 100;
                    return (
                      <span className={`text-sm font-semibold px-3 py-1 rounded-md ${
                        upside >= 0 
                          ? 'text-emerald-600 bg-emerald-50' 
                          : 'text-red-600 bg-red-50'
                      }`}>
                        {upside >= 0 ? `+${upside.toFixed(1)}% undervalued` : `${Math.abs(upside).toFixed(1)}% overvalued`}
                      </span>
                    );
                  })()}
                  
                  {/* Create Memo Button */}
                  <button
                    onClick={() => setShowMemoCreate(true)}
                    className="ml-4 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 px-3 py-1 rounded hover:border-gray-300 transition-colors"
                  >
                    Create Memo
                  </button>
                </div>
              )}
            </div>

            {/* Details */}
            <div className="mb-12">
              <table className="w-full max-w-md">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="py-3 text-sm text-gray-500">Enterprise Value<GlossaryRef id="enterprise-value" /></td>
                    <td className="py-3 text-sm font-mono font-medium text-right">{formatCurrency(result.enterprise_value)}</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="py-3 text-sm text-gray-500">Equity Value<GlossaryRef id="equity-value" /></td>
                    <td className="py-3 text-sm font-mono font-medium text-right">{formatCurrency(result.equity_value)}</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="py-3 text-sm text-gray-500">Net Debt<GlossaryRef id="net-debt" /></td>
                    <td className="py-3 text-sm font-mono font-medium text-right">{formatCurrency(result.net_debt)}</td>
                  </tr>
                  {/* Equity Bridge - Institutional Grade */}
                  {result.equity_bridge && (result.equity_bridge.minority_interest !== 0 || 
                    result.equity_bridge.preferred_stock !== 0 || 
                    result.equity_bridge.deferred_tax_assets !== 0 || 
                    result.equity_bridge.pension_deficit !== 0) && (
                    <>
                      {result.equity_bridge.minority_interest !== 0 && (
                        <tr className="border-b border-gray-50">
                          <td className="py-2 text-xs text-gray-400 pl-4">− Minority Interest</td>
                          <td className="py-2 text-xs font-mono text-gray-500 text-right">{formatCurrency(result.equity_bridge.minority_interest)}</td>
                        </tr>
                      )}
                      {result.equity_bridge.preferred_stock !== 0 && (
                        <tr className="border-b border-gray-50">
                          <td className="py-2 text-xs text-gray-400 pl-4">− Preferred Stock</td>
                          <td className="py-2 text-xs font-mono text-gray-500 text-right">{formatCurrency(result.equity_bridge.preferred_stock)}</td>
                        </tr>
                      )}
                      {result.equity_bridge.deferred_tax_assets !== 0 && (
                        <tr className="border-b border-gray-50">
                          <td className="py-2 text-xs text-green-600 pl-4">+ NOLs/Tax Assets</td>
                          <td className="py-2 text-xs font-mono text-green-600 text-right">{formatCurrency(result.equity_bridge.deferred_tax_assets)}</td>
                        </tr>
                      )}
                      {result.equity_bridge.pension_deficit !== 0 && (
                        <tr className="border-b border-gray-50">
                          <td className="py-2 text-xs text-gray-400 pl-4">− Pension Deficit</td>
                          <td className="py-2 text-xs font-mono text-gray-500 text-right">{formatCurrency(result.equity_bridge.pension_deficit)}</td>
                        </tr>
                      )}
                    </>
                  )}
                  <tr className="border-b border-gray-100">
                    <td className="py-3 text-sm text-gray-500">
                      {result.using_custom_discount_rate ? 'Discount Rate (custom)' : 'Discount Rate (WACC)'}<GlossaryRef id="discount-rate" />
                    </td>
                    <td className="py-3 text-sm font-mono font-medium text-right">{formatPercent(result.discount_rate)}</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="py-3 text-sm text-gray-500">Terminal Value<GlossaryRef id="terminal-value" /></td>
                    <td className="py-3 text-sm font-mono font-medium text-right">{formatCurrency(result.terminal_value)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Projections - Full FCF Breakdown */}
            {result.projections.length > 0 && (
              <div className="mb-12">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">FCF<GlossaryRef id="fcf" /> Projections - Full Breakdown</h3>
                <p className="text-xs text-gray-400 mb-4">
                  FCF = NOPAT + D&A − CapEx − ΔWC | Discount Rate: {(result.discount_rate * 100).toFixed(2)}%
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="py-3 text-left font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">Year</th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">Revenue</th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">EBIT<GlossaryRef id="ebit" /></th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">Taxes</th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">NOPAT<GlossaryRef id="nopat" /></th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">+ D&A<GlossaryRef id="da" /></th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">− CapEx<GlossaryRef id="capex" /></th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">− ΔWC<GlossaryRef id="working-capital" /></th>
                        <th className="py-3 text-right font-medium text-gray-600 uppercase text-xs tracking-wide whitespace-nowrap border-l border-gray-200 pl-3">FCF</th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">Discount</th>
                        <th className="py-3 text-right font-medium text-gray-400 uppercase text-xs tracking-wide whitespace-nowrap">PV of FCF</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.projections.map((p, i) => {
                        const year = i + 1;
                        const taxes = p.ebit - p.nopat;
                        const discountFactor = Math.pow(1 + result.discount_rate, year);
                        const pvFcf = p.fcf / discountFactor;
                        return (
                          <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-3 font-mono font-medium">{year}</td>
                            <td className="py-3 text-right font-mono text-gray-600">{formatCurrency(p.revenue)}</td>
                            <td className="py-3 text-right font-mono text-gray-600">{formatCurrency(p.ebit)}</td>
                            <td className="py-3 text-right font-mono text-gray-400">({formatCurrency(Math.abs(taxes))})</td>
                            <td className="py-3 text-right font-mono text-gray-600">{formatCurrency(p.nopat)}</td>
                            <td className="py-3 text-right font-mono text-emerald-600">+{formatCurrency(p.da)}</td>
                            <td className="py-3 text-right font-mono text-red-600">−{formatCurrency(Math.abs(p.capex))}</td>
                            <td className={`py-3 text-right font-mono ${p.delta_wc >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                              {p.delta_wc >= 0 ? '−' : '+'}{formatCurrency(Math.abs(p.delta_wc))}
                            </td>
                            <td className={`py-3 text-right font-mono font-medium border-l border-gray-200 pl-3 ${p.fcf >= 0 ? 'text-gray-900' : 'text-red-600'}`}>
                              {formatCurrency(p.fcf)}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-400 text-xs">
                              ÷{discountFactor.toFixed(3)}
                            </td>
                            <td className={`py-3 text-right font-mono font-medium ${pvFcf >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {formatCurrency(pvFcf)}
                            </td>
                          </tr>
                        );
                      })}
                      {/* Totals row */}
                      <tr className="border-t-2 border-gray-300 bg-gray-50 font-semibold">
                        <td className="py-3 font-mono">Total</td>
                        <td className="py-3 text-right font-mono text-gray-600">
                          {formatCurrency(result.projections.reduce((sum, p) => sum + p.revenue, 0))}
                        </td>
                        <td colSpan={6}></td>
                        <td className="py-3 text-right font-mono border-l border-gray-200 pl-3">
                          {formatCurrency(result.projections.reduce((sum, p) => sum + p.fcf, 0))}
                        </td>
                        <td></td>
                        <td className="py-3 text-right font-mono text-emerald-600">
                          {formatCurrency(result.projections.reduce((sum, p, i) => {
                            const discountFactor = Math.pow(1 + result.discount_rate, i + 1);
                            return sum + p.fcf / discountFactor;
                          }, 0))}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                
                {/* Terminal Value breakdown */}
                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">Terminal Value Calculation</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Final Year FCF</span>
                      <p className="font-mono font-medium">{formatCurrency(result.projections[result.projections.length - 1]?.fcf || 0)}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Terminal Growth</span>
                      <p className="font-mono font-medium">{((result.inputs as Record<string, number>)?.terminal_growth_rate * 100 || 2.5).toFixed(1)}%</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Terminal Value<GlossaryRef id="terminal-value" /></span>
                      <p className="font-mono font-medium">{formatCurrency(result.terminal_value)}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">PV of Terminal Value</span>
                      <p className="font-mono font-medium text-emerald-600">
                        {formatCurrency(result.terminal_value / Math.pow(1 + result.discount_rate, result.projections.length))}
                      </p>
                    </div>
                  </div>
                  
                  {/* Terminal Value Cross-Check & Warnings */}
                  {result.terminal_value_check && (
                    <div className="mt-4 space-y-3">
                      {/* Exit Multiple Cross-Check (if sector multiple provided) */}
                      {result.terminal_value_check.exit_multiple_tv && (
                        <div className="text-xs p-3 bg-white rounded border border-gray-200">
                          <div className="flex justify-between items-center mb-2">
                            <span className="font-semibold text-gray-600">Exit Multiple Cross-Check</span>
                            <span className="text-gray-400">{result.terminal_value_check.sector_ev_ebitda_multiple?.toFixed(1)}× EV/EBITDA</span>
                          </div>
                          <div className="grid grid-cols-2 gap-4 text-gray-500">
                            <div>
                              <span className="block text-gray-400">Gordon Growth TV:</span>
                              <span className="font-mono">{formatCurrency(result.terminal_value_check.gordon_growth_tv || 0)}</span>
                            </div>
                            <div>
                              <span className="block text-gray-400">Exit Multiple TV:</span>
                              <span className="font-mono">{formatCurrency(result.terminal_value_check.exit_multiple_tv)}</span>
                            </div>
                          </div>
                          {result.terminal_value_check.method_divergence_pct != null && (
                            <div className="mt-2">
                              <span className="text-gray-400">Divergence: </span>
                              <span className={`font-mono font-semibold ${
                                Math.abs(result.terminal_value_check.method_divergence_pct) > 0.20 
                                  ? 'text-amber-600' 
                                  : 'text-emerald-600'
                              }`}>
                                {(result.terminal_value_check.method_divergence_pct * 100).toFixed(1)}%
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* Implied Exit Multiple */}
                      {result.terminal_value_check.implied_exit_multiple && (
                        <div className="text-xs text-gray-500">
                          <span>Implied Exit Multiple: </span>
                          <span className="font-mono font-medium">{result.terminal_value_check.implied_exit_multiple.toFixed(1)}× EV/EBITDA</span>
                          <span className="text-gray-400 ml-2">(Terminal EBITDA: {formatCurrency(result.terminal_value_check.terminal_ebitda)})</span>
                        </div>
                      )}
                      
                      {/* TV Dominance % */}
                      {result.terminal_value_check.terminal_value_pct > 0 && (
                        <div className="text-xs text-gray-500">
                          <span>Terminal Value % of EV: </span>
                          <span className={`font-mono font-medium ${
                            result.terminal_value_check.terminal_value_pct > 0.70 
                              ? 'text-amber-600' 
                              : 'text-gray-600'
                          }`}>
                            {(result.terminal_value_check.terminal_value_pct * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                      
                      {/* Warning Alerts */}
                      {result.terminal_value_check.method_divergence_warning && (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                          <span className="font-semibold">⚠️ Terminal Value Divergence:</span>
                          <span className="block mt-1">{result.terminal_value_check.method_divergence_warning}</span>
                        </div>
                      )}
                      
                      {result.terminal_value_check.dominance_warning && (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                          <span className="font-semibold">⚠️ Terminal Value Dominance:</span>
                          <span className="block mt-1">{result.terminal_value_check.dominance_warning}</span>
                        </div>
                      )}
                      
                      {result.terminal_value_check.warning && (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                          <span className="font-semibold">⚠️ High Implied Multiple:</span>
                          <span className="block mt-1">{result.terminal_value_check.warning}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Value Drivers - Key Sensitivity Summary */}
            {result.value_drivers && result.value_drivers.length > 0 && (
              <div className="bg-gray-50 rounded-xl p-6 border border-gray-100">
                <ValueDrivers drivers={result.value_drivers} />
              </div>
            )}

            {/* Sensitivity Analysis */}
            {result.sensitivity && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Sensitivity Analysis</h3>
                <p className="text-sm text-gray-400 mb-6">Intrinsic value per share at different discount rates & terminal growth rates</p>
                
                <div className="overflow-x-auto">
                  <table className="text-sm">
                    <thead>
                      <tr>
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-400">
                          <span className="block">Discount</span>
                          <span className="block">Rate ↓</span>
                        </th>
                        {result.sensitivity.terminal_growth_rates.map((tg) => (
                          <th 
                            key={tg} 
                            className={`py-2 px-3 text-center text-xs font-medium ${
                              Math.abs(tg - result.sensitivity.base_terminal_growth) < 0.001 
                                ? 'text-emerald-600 bg-emerald-50' 
                                : 'text-gray-400'
                            }`}
                          >
                            {(tg * 100).toFixed(1)}%
                          </th>
                        ))}
                      </tr>
                      <tr>
                        <th className="py-1 px-3 text-left text-xs text-gray-300">Terminal Growth →</th>
                        {result.sensitivity.terminal_growth_rates.map((tg) => (
                          <th key={tg} className="py-1"></th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.sensitivity.matrix.map((row, rowIdx) => {
                        const dr = result.sensitivity.discount_rates[rowIdx];
                        const isBaseRow = Math.abs(dr - result.sensitivity.base_discount_rate) < 0.001;
                        
                        return (
                          <tr key={rowIdx}>
                            <td className={`py-2 px-3 text-xs font-medium ${
                              isBaseRow ? 'text-emerald-600 bg-emerald-50' : 'text-gray-500'
                            }`}>
                              {(dr * 100).toFixed(1)}%
                            </td>
                            {row.map((value, colIdx) => {
                              const tg = result.sensitivity.terminal_growth_rates[colIdx];
                              const isBaseCol = Math.abs(tg - result.sensitivity.base_terminal_growth) < 0.001;
                              const isCurrentCell = isBaseRow && isBaseCol;
                              
                              // Color based on comparison to current price
                              let cellClass = 'text-gray-700';
                              if (value !== null && result.market_cap && stockData?.data.shares_outstanding) {
                                const currentPrice = result.market_cap / stockData.data.shares_outstanding;
                                const diff = ((value - currentPrice) / currentPrice) * 100;
                                if (diff > 20) cellClass = 'text-emerald-700 bg-emerald-50';
                                else if (diff > 0) cellClass = 'text-emerald-600';
                                else if (diff > -20) cellClass = 'text-red-500';
                                else cellClass = 'text-red-600 bg-red-50';
                              }
                              
                              return (
                                <td 
                                  key={colIdx} 
                                  className={`py-2 px-3 text-center font-mono text-sm ${cellClass} ${
                                    isCurrentCell ? 'ring-2 ring-emerald-500 ring-inset font-bold' : ''
                                  }`}
                                >
                                  {value !== null ? `$${value.toFixed(2)}` : '—'}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                
                <div className="mt-4 flex gap-6 text-xs text-gray-400">
                  <span><span className="inline-block w-3 h-3 bg-emerald-50 border border-emerald-200 rounded mr-1"></span> Undervalued</span>
                  <span><span className="inline-block w-3 h-3 bg-red-50 border border-red-200 rounded mr-1"></span> Overvalued</span>
                  <span><span className="inline-block w-3 h-3 ring-2 ring-emerald-500 rounded mr-1"></span> Current</span>
                </div>
              </div>
              )}

              {/* 2D Sensitivity Matrix - Margin vs Growth / WACC vs Terminal */}
              <div className="mt-8">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Advanced Sensitivity Matrix</h3>
                <p className="text-sm text-gray-400 mb-6">Explore how intrinsic value changes with margin/growth assumptions or WACC/terminal growth</p>
                <SensitivityMatrixPanel
                  symbol={stockData.symbol}
                  provider={selectedFundamentalProvider}
                  baseGrowth={parseFloat(revenueGrowth) / 100 || 0.10}
                  baseMargin={parseFloat(operatingMargin) / 100 || 0.15}
                  baseDiscountRate={result?.discount_rate || 0.10}
                  terminalGrowth={parseFloat(terminalGrowth) / 100 || 0.03}
                  projectionYears={parseInt(projectionYears) || 10}
                  daRatio={currentHints?.da_ratio ?? undefined}
                  capexRatio={currentHints?.capex_ratio ?? undefined}
                  wcRatio={currentHints?.wc_ratio ?? undefined}
                />
              </div>
            </section>
            )}

            {/* Scenario Analysis Section */}
            {(scenarioResult || scenarioLoading) && (
            <section className="pt-12 border-t border-gray-100">
              <div className="mb-8">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Scenario Analysis</h2>
              <p className="text-sm text-gray-400">Bear / Base / Bull case valuations with probability weighting</p>
              {scenarioLoading && <p className="text-sm text-gray-400 mt-2">Analyzing scenarios...</p>}
            </div>

            {scenarioResult && scenarioResult.probability_weighted_value !== null && (
              <div className="space-y-8">
                {/* Probabilities Normalized Warning */}
                {scenarioResult.probabilities_normalized && (
                  <div className="px-3 py-2 rounded bg-amber-50 border border-amber-200 text-sm text-amber-700">
                    ⚠️ Scenario probabilities were auto-adjusted to sum to 100%
                  </div>
                )}
                {/* Summary */}
                <div className="flex items-baseline gap-4">
                  <span className="text-4xl font-bold font-mono">${scenarioResult.probability_weighted_value.toFixed(2)}</span>
                  <span className="text-sm text-gray-400">weighted fair value</span>
                  {(() => {
                    const current = scenarioResult.current_price || 0;
                    const fair = scenarioResult.probability_weighted_value || 0;
                    if (current === 0) return null;
                    const diff = ((fair - current) / current) * 100;
                    return (
                      <span className={`text-sm font-medium ${diff >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {diff >= 0 ? '+' : ''}{diff.toFixed(0)}%
                      </span>
                    );
                  })()}
                </div>

                {/* Table */}
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Scenario</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Value</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">vs Current</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Growth</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Margin</th>
                      <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenarioResult.scenarios.map((scenario) => (
                      <tr key={scenario.name} className="border-b border-gray-100">
                        <td className="py-3 text-sm font-medium">{scenario.name}</td>
                        <td className="py-3 text-right font-mono text-sm">${scenario.intrinsic_value.toFixed(2)}</td>
                        <td className={`py-3 text-right font-mono text-sm ${
                          scenario.upside_percent !== null && scenario.upside_percent >= 0 
                            ? 'text-emerald-600' 
                            : 'text-red-600'
                        }`}>
                          {scenario.upside_percent !== null 
                            ? `${scenario.upside_percent >= 0 ? '+' : ''}${scenario.upside_percent.toFixed(0)}%`
                            : '—'}
                        </td>
                        <td className="py-3 text-right font-mono text-sm text-gray-500">
                          {(scenario.assumptions.revenue_growth * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 text-right font-mono text-sm text-gray-500">
                          {(scenario.assumptions.operating_margin * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 text-right font-mono text-sm text-gray-400">
                          {(scenario.probability * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
            )}

            {/* Capital Efficiency Section */}
            {result && stockData && stockData.data.total_equity !== null && (
            <section className="pt-12 border-t border-gray-100">
              <div className="mb-8">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                  Capital Efficiency<GlossaryRef id="roic" />
                </h2>
                <p className="text-sm text-gray-400">Is growth creating or destroying shareholder value?</p>
              </div>
              
              {(() => {
                // Calculate capital efficiency metrics
                const nopat = result.projections[0]?.nopat || 0;
                const totalEquity = stockData.data.total_equity || 0;
                const totalDebt = stockData.data.total_debt || 0;
                const cash = stockData.data.cash || 0;
                const investedCapital = totalEquity + totalDebt - cash;
                const wacc = result.discount_rate;
                const revenueGrowthRate = (result.inputs.revenue_growth as number) || 0;
                
                // Calculate metrics
                const roic = investedCapital > 0 ? nopat / investedCapital : null;
                const reinvestmentRate = roic && roic > 0 && revenueGrowthRate > 0 
                  ? revenueGrowthRate / roic 
                  : null;
                const valueSpread = roic !== null ? roic - wacc : null;
                const economicProfit = valueSpread !== null ? valueSpread * investedCapital : null;
                const isValueCreating = roic !== null && roic > wacc;
                
                // Assessment
                let assessment = '';
                let assessmentColor = 'text-gray-600';
                if (roic === null) {
                  assessment = 'Unable to calculate (invalid invested capital)';
                } else if (valueSpread !== null) {
                  if (valueSpread > 0.10) {
                    assessment = 'Strong value creator';
                    assessmentColor = 'text-emerald-600';
                  } else if (valueSpread > 0.02) {
                    assessment = 'Modest value creator';
                    assessmentColor = 'text-emerald-500';
                  } else if (valueSpread > -0.02) {
                    assessment = 'Value neutral';
                    assessmentColor = 'text-amber-500';
                  } else {
                    assessment = 'Value destroyer - growth reduces shareholder value';
                    assessmentColor = 'text-red-600';
                  }
                }
                
                return (
                  <div className="space-y-6">
                    {/* Key Insight Banner */}
                    <div className={`p-4 rounded-lg border ${isValueCreating ? 'bg-emerald-50 border-emerald-200' : valueSpread !== null && valueSpread > -0.02 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
                      <p className={`text-sm font-medium ${assessmentColor}`}>{assessment}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {roic !== null && (
                          <>ROIC ({(roic * 100).toFixed(1)}%) {roic > wacc ? '>' : '<'} WACC ({(wacc * 100).toFixed(1)}%)</>
                        )}
                      </p>
                    </div>
                    
                    {/* Metrics Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                          ROIC<GlossaryRef id="roic" />
                        </p>
                        <p className="text-xl font-mono font-medium">
                          {roic !== null ? `${(roic * 100).toFixed(1)}%` : '—'}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">Return on Invested Capital</p>
                      </div>
                      
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                          Value Spread<GlossaryRef id="value-spread" />
                        </p>
                        <p className={`text-xl font-mono font-medium ${valueSpread !== null ? (valueSpread > 0 ? 'text-emerald-600' : valueSpread < -0.02 ? 'text-red-600' : 'text-amber-600') : ''}`}>
                          {valueSpread !== null ? `${valueSpread > 0 ? '+' : ''}${(valueSpread * 100).toFixed(1)}%` : '—'}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">ROIC minus WACC</p>
                      </div>
                      
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                          Economic Profit<GlossaryRef id="economic-profit" />
                        </p>
                        <p className={`text-xl font-mono font-medium ${economicProfit !== null ? (economicProfit > 0 ? 'text-emerald-600' : 'text-red-600') : ''}`}>
                          {economicProfit !== null ? formatCurrency(economicProfit) : '—'}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">Value created/destroyed annually</p>
                      </div>
                      
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                          Reinvestment Rate<GlossaryRef id="reinvestment-rate" />
                        </p>
                        <p className="text-xl font-mono font-medium">
                          {reinvestmentRate !== null ? `${(reinvestmentRate * 100).toFixed(0)}%` : '—'}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">Earnings needed for growth</p>
                      </div>
                    </div>
                    
                    {/* Invested Capital Breakdown */}
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">
                        Invested Capital<GlossaryRef id="invested-capital" /> Breakdown
                      </p>
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Total Equity</p>
                          <p className="font-mono">{formatCurrency(totalEquity)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">+ Total Debt</p>
                          <p className="font-mono">{formatCurrency(totalDebt)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">- Cash</p>
                          <p className="font-mono">{formatCurrency(cash)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 font-medium">= Invested Capital</p>
                          <p className="font-mono font-medium">{formatCurrency(investedCapital)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </section>
            )}

            {/* Monte Carlo Simulation Section */}
            {result && stockData && (
            <section className="pt-12 border-t border-gray-100">
              <div className="mb-8">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Monte Carlo Simulation</h2>
                <p className="text-sm text-gray-400">Run 5,000 simulations with varying assumptions to see probability distribution</p>
              </div>
              <MonteCarloPanel
                symbol={ticker}
                provider={selectedFundamentalProvider}
                defaultInputs={{
                  growth: result.inputs.revenue_growth as number,
                  margin: result.inputs.operating_margin as number,
                  daRatio: result.inputs.da_ratio as number,
                  capexRatio: result.inputs.capex_ratio as number,
                  wcRatio: result.inputs.wc_ratio as number,
                  taxRate: result.inputs.tax_rate as number,
                  discountRate: result.discount_rate,
                  terminalGrowth: result.inputs.terminal_growth_rate as number,
                  projectionYears: result.inputs.projection_years as number,
                }}
                currentPrice={
                  stockData.data.market_cap && stockData.data.shares_outstanding
                    ? stockData.data.market_cap / stockData.data.shares_outstanding
                    : scenarioResult?.current_price || 0
                }
              />
            </section>
            )}

            {/* Comparable Analysis Section */}
            {(comparableResult || comparableLoading) && (
            <section className="pt-12 border-t border-gray-100">
              <div className="mb-8">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Comparable Analysis</h2>
              <p className="text-sm text-gray-400">
                Relative valuation vs sector peers using P/E<GlossaryRef id="pe-ratio" />, EV/EBITDA<GlossaryRef id="ev-ebitda" />, P/S<GlossaryRef id="ps-ratio" />, P/B<GlossaryRef id="pb-ratio" />
              </p>
              {comparableLoading && <p className="text-sm text-gray-400 mt-2">Loading peer data...</p>}
            </div>

            {comparableResult && (
              <div className="space-y-8">
                {/* Summary */}
                <div className="flex items-baseline gap-4">
                  <span className="text-4xl font-bold font-mono">
                    ${formatMetric(comparableResult.summary.average_implied_price, 2)}
                  </span>
                  <span className="text-sm text-gray-400">implied fair value (peer median)</span>
                  {comparableResult.summary.average_upside_percent !== null && (
                    <span className={`text-sm font-medium ${
                      comparableResult.summary.average_upside_percent >= 0 ? 'text-emerald-600' : 'text-red-600'
                    }`}>
                      {comparableResult.summary.average_upside_percent >= 0 ? '+' : ''}
                      {comparableResult.summary.average_upside_percent.toFixed(0)}%
                    </span>
                  )}
                </div>

                {/* Sector Info */}
                <div className="text-sm text-gray-500">
                  <span className="font-medium">{comparableResult.sector}</span>
                  {comparableResult.industry && comparableResult.industry !== comparableResult.sector && (
                    <span> / {comparableResult.industry}</span>
                  )}
                  <span className="text-gray-400 ml-2">• {comparableResult.peers.length} peers</span>
                  {comparableResult.currency_conversions && comparableResult.currency_conversions.length > 0 && (
                    <span 
                      className="text-gray-400 ml-2 cursor-help" 
                      title={`${comparableResult.currency_conversions.length} peer(s) converted to ${comparableResult.base_currency || 'USD'}: ${comparableResult.currency_conversions.map(c => `${c.symbol} (${c.original_currency})`).join(', ')}`}
                    >
                      • 🌐 {comparableResult.currency_conversions.length} FX-adjusted
                    </span>
                  )}
                </div>

                {/* Implied Valuations */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Implied Value by Multiple</h3>
                  <table className="w-full max-w-2xl">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Multiple</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Company</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Peer Median</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Implied Price</th>
                        <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">vs Current</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparableResult.implied_valuations.map((iv) => (
                        <tr key={iv.metric} className="border-b border-gray-100">
                          <td className="py-3 text-sm font-medium">{iv.metric}</td>
                          <td className="py-3 text-right font-mono text-sm">
                            {iv.company_value !== null ? iv.company_value.toFixed(1) + 'x' : '—'}
                          </td>
                          <td className="py-3 text-right font-mono text-sm text-gray-500">
                            {iv.peer_median !== null ? iv.peer_median.toFixed(1) + 'x' : '—'}
                          </td>
                          <td className="py-3 text-right font-mono text-sm font-medium">
                            {iv.implied_price !== null ? '$' + iv.implied_price.toFixed(2) : '—'}
                          </td>
                          <td className={`py-3 text-right font-mono text-sm ${
                            iv.upside_percent !== null && iv.upside_percent >= 0 
                              ? 'text-emerald-600' 
                              : 'text-red-600'
                          }`}>
                            {iv.upside_percent !== null 
                              ? `${iv.upside_percent >= 0 ? '+' : ''}${iv.upside_percent.toFixed(0)}%`
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Peer Comparison */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Peer Companies</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Company</th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Market Cap</th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P/E<GlossaryRef id="pe-ratio" /></th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">EV/EBITDA<GlossaryRef id="ev-ebitda" /></th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P/S<GlossaryRef id="ps-ratio" /></th>
                          <th className="py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P/B<GlossaryRef id="pb-ratio" /></th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* Target company row */}
                        <tr className="border-b border-gray-200 bg-gray-50">
                          <td className="py-3 font-medium">
                            {comparableResult.symbol}
                            <span className="text-xs text-gray-400 ml-2">(target)</span>
                          </td>
                          <td className="py-3 text-right font-mono">
                            {formatCurrency(stockData.data.market_cap)}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {formatMetric(comparableResult.target_metrics.pe_ratio)}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {formatMetric(comparableResult.target_metrics.ev_to_ebitda)}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {formatMetric(comparableResult.target_metrics.price_to_sales)}
                          </td>
                          <td className="py-3 text-right font-mono">
                            {formatMetric(comparableResult.target_metrics.price_to_book)}
                          </td>
                        </tr>
                        {/* Peer rows */}
                        {comparableResult.peers.map((peer) => {
                          const conversion = comparableResult.currency_conversions?.find(c => c.symbol === peer.symbol);
                          return (
                          <tr key={peer.symbol} className="border-b border-gray-100">
                            <td className="py-3">
                              <span className="font-medium">{peer.symbol}</span>
                              {conversion && (
                                <span 
                                  className="text-[10px] text-amber-500 ml-1 cursor-help" 
                                  title={`Converted from ${conversion.original_currency} to ${conversion.converted_to} (×${conversion.rate < 0.01 ? conversion.rate.toExponential(2) : conversion.rate.toFixed(4)})`}
                                >
                                  ({conversion.original_currency})
                                </span>
                              )}
                              <span className="text-xs text-gray-400 ml-2 truncate max-w-[150px] inline-block align-bottom">
                                {peer.name}
                              </span>
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {formatCurrency(peer.market_cap)}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {formatMetric(peer.pe_ratio)}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {formatMetric(peer.ev_to_ebitda)}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {formatMetric(peer.price_to_sales)}
                            </td>
                            <td className="py-3 text-right font-mono text-gray-500">
                              {formatMetric(peer.price_to_book)}
                            </td>
                          </tr>
                        );
                        })}
                        {/* Median row */}
                        <tr className="border-t-2 border-gray-200">
                          <td className="py-3 font-medium text-gray-500">Peer Median</td>
                          <td className="py-3 text-right font-mono">—</td>
                          <td className="py-3 text-right font-mono font-medium">
                            {formatMetric(comparableResult.peer_medians.pe_ratio)}
                          </td>
                          <td className="py-3 text-right font-mono font-medium">
                            {formatMetric(comparableResult.peer_medians.ev_to_ebitda)}
                          </td>
                          <td className="py-3 text-right font-mono font-medium">
                            {formatMetric(comparableResult.peer_medians.price_to_sales)}
                          </td>
                          <td className="py-3 text-right font-mono font-medium">
                            {formatMetric(comparableResult.peer_medians.price_to_book)}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
            </section>
            )}
          </>
        )}

        {/* TECHNICAL TAB - No Data Message */}
        {!stockData && activeTab === 'technical' && (
          <div className="text-center py-16">
            {hasAttemptedAnalysis && error ? (
              <>
                <p className="text-gray-400 mb-2">Analysis failed</p>
                <p className="text-sm text-gray-300">Try a different ticker or provider</p>
              </>
            ) : (
              <>
                <p className="text-gray-400 mb-2">No stock data available</p>
                <p className="text-sm text-gray-300">Enter a ticker and click Analyze to get started</p>
              </>
            )}
          </div>
        )}

        {/* TECHNICAL TAB */}
        {stockData && activeTab === 'technical' && (
          <div className="space-y-8">
            {/* Company Header - always visible, same as Fundamental */}
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-xl font-semibold">
                  {stockData.symbol} {stockData.company_name && `— ${stockData.company_name}`}
                </h2>
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-500 uppercase tracking-wide">
                  via {technicalResult 
                    ? (technicalProviders.find(p => p.id === technicalResult.provider)?.name || technicalResult.provider)
                    : (technicalProviders.find(p => p.id === selectedTechnicalProvider)?.name || selectedTechnicalProvider)}
                </span>
              </div>
              {stockData.industry && (
                <p className="text-sm text-gray-500">{stockData.industry}{stockData.sector && ` · ${stockData.sector}`}</p>
              )}
            </div>

            {/* Loading Technical Analysis */}
            {!technicalResult && technicalLoading && (
              <div className="text-sm text-gray-400">
                Loading technical analysis...
              </div>
            )}

            {/* Technical Analysis Results */}
            {technicalResult && (
              <div className="space-y-8">
                {/* Price Summary */}
                <div className="space-y-1">
                  <div className="flex items-baseline gap-3">
                    <span className="text-sm text-gray-500">Current Price</span>
                    <span className="text-3xl font-bold font-mono">${technicalResult.current_price.toFixed(2)}</span>
                  </div>
                  <div className="flex items-baseline gap-3">
                    <span className="text-sm text-gray-500">Change (past {technicalResult.period_days} days)</span>
                    <span className={`text-lg font-medium ${technicalResult.price_change_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {technicalResult.price_change_pct >= 0 ? '+' : ''}{technicalResult.price_change_pct.toFixed(2)}%
                    </span>
                  </div>
                </div>

                {/* Limited data warning */}
                {technicalResult.prices.length < 50 && (
                  <div className="p-4 border border-gray-200 rounded">
                    <p className="text-sm text-gray-600">
                      <span className="font-semibold">Limited data:</span> Only {technicalResult.prices.length} trading days available. 
                      Some indicators need more data to calculate.
                    </p>
                  </div>
                )}

                {/* Signal Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
                  <div className="p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Trend</div>
                    <div className={`text-lg font-medium capitalize ${
                      technicalResult.signals.trend === 'bullish' ? 'text-emerald-600' :
                      technicalResult.signals.trend === 'bearish' ? 'text-red-600' : 'text-gray-400'
                    }`}>
                      {technicalResult.signals.trend}
                    </div>
                    {/* Volume Confirmation Badge */}
                    {technicalResult.signals.volume_confirmation && technicalResult.signals.volume_confirmation !== 'neutral' && (
                      <div className={`mt-1 text-xs font-medium ${
                        technicalResult.signals.volume_confirmation === 'confirmed' ? 'text-emerald-500' : 'text-amber-500'
                      }`}>
                        {technicalResult.signals.volume_confirmation === 'confirmed' ? '✓ Vol Confirmed' : '⚠ Low Volume'}
                      </div>
                    )}
                  </div>
                  <div className="p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Momentum</div>
                    <div className={`text-lg font-medium capitalize ${
                      technicalResult.signals.rsi === 'overbought' ? 'text-red-600' :
                      technicalResult.signals.rsi === 'oversold' ? 'text-emerald-600' : 'text-gray-400'
                    }`}>
                      {technicalResult.signals.rsi}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">MACD</div>
                    <div className={`text-lg font-medium capitalize ${
                      technicalResult.signals.macd === 'bullish' ? 'text-emerald-600' :
                      technicalResult.signals.macd === 'bearish' ? 'text-red-600' : 'text-gray-400'
                    }`}>
                      {technicalResult.signals.macd}
                    </div>
                  </div>
                  {/* Volume Metrics */}
                  <div className="p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Volume<GlossaryRef id="relative-volume" /></div>
                    {technicalResult.volume?.relative_volume != null ? (
                      <div className={`text-lg font-medium ${
                        technicalResult.volume.relative_volume >= 1.2 ? 'text-emerald-600' :
                        technicalResult.volume.relative_volume <= 0.8 ? 'text-amber-500' : 'text-gray-600'
                      }`}>
                        {technicalResult.volume.relative_volume.toFixed(1)}x
                      </div>
                    ) : (
                      <div className="text-lg font-medium text-gray-400">—</div>
                    )}
                    {technicalResult.volume?.average_volume != null && (
                      <div className="text-xs text-gray-400 mt-1">
                        Avg: {(technicalResult.volume.average_volume / 1e6).toFixed(1)}M
                      </div>
                    )}
                  </div>
                </div>

                {/* Volume-Weighted Signals (MFI & OBV) */}
                {(technicalResult.signals.mfi_signal || technicalResult.signals.obv_trend) && (
                  <div className="mt-6">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Volume-Weighted Signals</h3>
                    <VolumeSignals technicalResult={technicalResult} />
                  </div>
                )}

                {/* Price Chart */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Price Chart</h3>
                  <div className="bg-gray-50 rounded-lg p-6 overflow-hidden">
                    <svg viewBox="0 0 800 400" className="w-full h-96">
                      {/* Chart background */}
                      <rect x="0" y="0" width="800" height="400" fill="#fafafa" />
                      
                      {/* Price line */}
                      {technicalResult.prices.length > 1 && (() => {
                        const prices = technicalResult.prices;
                        const minPrice = Math.min(...prices.map(p => p.low));
                        const maxPrice = Math.max(...prices.map(p => p.high));
                        const priceRange = maxPrice - minPrice || 1;
                        const padding = 20;
                        const chartHeight = 360;
                        const chartWidth = 760;
                        
                        const points = prices.map((p, i) => {
                          const x = padding + (i / (prices.length - 1)) * chartWidth;
                          const y = padding + ((maxPrice - p.close) / priceRange) * chartHeight;
                          return `${x},${y}`;
                        }).join(' ');
                        
                        // SMA 20 line
                        const sma20Points = technicalResult.indicators.sma_20.map((s) => {
                          const priceIdx = prices.findIndex(p => p.timestamp === s.timestamp);
                          if (priceIdx === -1) return null;
                          const x = padding + (priceIdx / (prices.length - 1)) * chartWidth;
                          const y = padding + ((maxPrice - s.value) / priceRange) * chartHeight;
                          return `${x},${y}`;
                        }).filter(Boolean).join(' ');
                        
                        // SMA 50 line
                        const sma50Points = technicalResult.indicators.sma_50.map((s) => {
                          const priceIdx = prices.findIndex(p => p.timestamp === s.timestamp);
                          if (priceIdx === -1) return null;
                          const x = padding + (priceIdx / (prices.length - 1)) * chartWidth;
                          const y = padding + ((maxPrice - s.value) / priceRange) * chartHeight;
                          return `${x},${y}`;
                        }).filter(Boolean).join(' ');
                        
                        return (
                          <>
                            {/* Grid lines */}
                            {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => (
                              <line
                                key={i}
                                x1={padding}
                                y1={padding + pct * chartHeight}
                                x2={padding + chartWidth}
                                y2={padding + pct * chartHeight}
                                stroke="#e5e7eb"
                                strokeWidth="1"
                              />
                            ))}
                            
                            {/* SMA 50 */}
                            {sma50Points && (
                              <polyline
                                points={sma50Points}
                                fill="none"
                                stroke="#f59e0b"
                                strokeWidth="1.5"
                                opacity="0.7"
                              />
                            )}
                            
                            {/* SMA 20 */}
                            {sma20Points && (
                              <polyline
                                points={sma20Points}
                                fill="none"
                                stroke="#8b5cf6"
                                strokeWidth="1.5"
                                opacity="0.7"
                              />
                            )}
                            
                            {/* Price line */}
                            <polyline
                              points={points}
                              fill="none"
                              stroke="#111827"
                              strokeWidth="2"
                            />
                            
                            {/* Price labels */}
                            <text x={padding - 5} y={padding + 5} textAnchor="end" fontSize="10" fill="#9ca3af">
                              ${maxPrice.toFixed(0)}
                            </text>
                            <text x={padding - 5} y={padding + chartHeight} textAnchor="end" fontSize="10" fill="#9ca3af">
                              ${minPrice.toFixed(0)}
                            </text>
                          </>
                        );
                      })()}
                    </svg>
                    <div className="flex gap-6 mt-2 text-xs text-gray-400">
                      <span><span className="inline-block w-3 h-0.5 bg-gray-900 mr-1"></span> Price</span>
                      <span><span className="inline-block w-3 h-0.5 bg-gray-500 mr-1"></span> SMA 20<GlossaryRef id="sma" /></span>
                      <span><span className="inline-block w-3 h-0.5 bg-gray-400 mr-1"></span> SMA 50</span>
                    </div>
                  </div>
                </div>

                {/* RSI Chart */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Momentum (RSI)<GlossaryRef id="rsi" /></h3>
                  {technicalResult.indicators.rsi_14.length > 1 ? (
                    <div className="bg-gray-50 rounded-lg p-6 overflow-hidden">
                      <svg viewBox="0 0 800 200" className="w-full h-48">
                        {/* Overbought/Oversold zones */}
                        <rect x="20" y="0" width="760" height="60" fill="#fef2f2" opacity="0.5" />
                        <rect x="20" y="140" width="760" height="60" fill="#ecfdf5" opacity="0.5" />
                        
                        {(() => {
                          const rsiData = technicalResult.indicators.rsi_14;
                          const padding = 20;
                          const chartWidth = 760;
                          const chartHeight = 200;
                          
                          const points = rsiData.map((r, i) => {
                            const x = padding + (i / (rsiData.length - 1)) * chartWidth;
                            const y = chartHeight - (r.value / 100) * chartHeight;
                            return `${x},${y}`;
                          }).join(' ');
                          
                          return (
                            <>
                              {/* 70/30/50 lines */}
                              <line x1={padding} y1={60} x2={padding + chartWidth} y2={60} stroke="#ef4444" strokeWidth="1" strokeDasharray="4" />
                              <line x1={padding} y1={140} x2={padding + chartWidth} y2={140} stroke="#10b981" strokeWidth="1" strokeDasharray="4" />
                              <line x1={padding} y1={100} x2={padding + chartWidth} y2={100} stroke="#e5e7eb" strokeWidth="1" />
                              
                              {/* RSI line */}
                              <polyline points={points} fill="none" stroke="#6366f1" strokeWidth="2" />
                              
                              {/* Labels */}
                              <text x={padding - 5} y={64} textAnchor="end" fontSize="10" fill="#ef4444">70</text>
                              <text x={padding - 5} y={144} textAnchor="end" fontSize="10" fill="#10b981">30</text>
                            </>
                          );
                        })()}
                      </svg>
                    </div>
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-6 text-center">
                      <p className="text-sm text-gray-500">Not enough trading data available.</p>
                    </div>
                  )}
                </div>

                {/* MACD Chart */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Momentum Trend (MACD)<GlossaryRef id="macd" /></h3>
                  {technicalResult.indicators.macd.length > 1 ? (
                    <div className="bg-gray-50 rounded-lg p-6 overflow-hidden">
                      <svg viewBox="0 0 800 200" className="w-full h-48">
                        {(() => {
                          const macdData = technicalResult.indicators.macd;
                          const maxVal = Math.max(...macdData.map(m => Math.max(Math.abs(m.macd), Math.abs(m.signal), Math.abs(m.histogram))));
                          const padding = 20;
                          const chartWidth = 760;
                          const chartHeight = 200;
                          const midY = chartHeight / 2;
                          
                          const macdPoints = macdData.map((m, i) => {
                            const x = padding + (i / (macdData.length - 1)) * chartWidth;
                            const y = midY - (m.macd / maxVal) * (midY - 10);
                            return `${x},${y}`;
                          }).join(' ');
                          
                          const signalPoints = macdData.map((m, i) => {
                            const x = padding + (i / (macdData.length - 1)) * chartWidth;
                            const y = midY - (m.signal / maxVal) * (midY - 10);
                            return `${x},${y}`;
                          }).join(' ');
                          
                          return (
                            <>
                              {/* Zero line */}
                              <line x1={padding} y1={midY} x2={padding + chartWidth} y2={midY} stroke="#e5e7eb" strokeWidth="1" />
                              
                              {/* Histogram bars */}
                              {macdData.map((m, i) => {
                                const x = padding + (i / (macdData.length - 1)) * chartWidth;
                                const barHeight = (m.histogram / maxVal) * (midY - 10);
                                return (
                                  <rect
                                    key={i}
                                    x={x - 1}
                                    y={barHeight > 0 ? midY - barHeight : midY}
                                    width={2}
                                    height={Math.abs(barHeight)}
                                    fill={m.histogram >= 0 ? '#10b981' : '#ef4444'}
                                    opacity="0.5"
                                  />
                                );
                              })}
                              
                              {/* MACD line */}
                              <polyline points={macdPoints} fill="none" stroke="#3b82f6" strokeWidth="1.5" />
                              
                              {/* Signal line */}
                              <polyline points={signalPoints} fill="none" stroke="#f97316" strokeWidth="1.5" />
                            </>
                          );
                        })()}
                      </svg>
                      <div className="flex gap-6 mt-2 text-xs text-gray-400">
                        <span><span className="inline-block w-3 h-0.5 bg-gray-700 mr-1"></span> MACD</span>
                        <span><span className="inline-block w-3 h-0.5 bg-gray-400 mr-1"></span> Signal</span>
                        <span><span className="inline-block w-3 h-2 bg-gray-300 mr-1"></span> Histogram</span>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-6 text-center">
                      <p className="text-sm text-gray-500">Not enough trading data available.</p>
                    </div>
                  )}
                </div>

                {/* Run again button */}
                <button
                  onClick={() => stockData && fetchTechnical(stockData.symbol, selectedTechnicalProvider, technicalProviders)}
                  disabled={technicalLoading || !stockData}
                  className="px-6 py-2 text-sm font-medium text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-30"
                >
                  {technicalLoading ? 'Loading...' : 'Refresh'}
                </button>
              </div>
            )}
          </div>
        )}

      {/* Discount Rate Modal - shown when WACC is missing */}
      <DiscountRateModal
        isOpen={showDiscountModal}
        onClose={() => {
          setShowDiscountModal(false);
          setPendingAnalysis(null);
        }}
        onSubmit={handleDiscountRateSubmit}
        onSkip={handleDiscountRateSkip}
      />

      {/* Assumption Commit Modal - shown when re-running valuation */}
      <AssumptionCommitModal
        isOpen={showCommitModal}
        onClose={() => setShowCommitModal(false)}
        onCommit={handleCommitAndRun}
        isInitial={!assumptionTracker.hasHistory}
        changedFields={getChangedFields()}
      />

      {/* Assumption History Drawer */}
      <AssumptionHistoryDrawer
        isOpen={showHistoryDrawer}
        onClose={() => setShowHistoryDrawer(false)}
        symbol={stockData?.symbol || ''}
        history={assumptionTracker.history}
        isLoading={assumptionTracker.isLoading}
      />

      {/* Investment Memo Modals */}
      {showMemoCreate && stockData && result && (
        <MemoCreateModal
          isOpen={showMemoCreate}
          onClose={() => setShowMemoCreate(false)}
          onSave={handleSaveMemo}
          symbol={stockData.symbol}
          currentPrice={stockData.data.market_cap && stockData.data.shares_outstanding 
            ? stockData.data.market_cap / stockData.data.shares_outstanding 
            : 0}
          intrinsicValue={result.intrinsic_value_per_share}
          peRatio={ratiosResult?.annual?.valuation?.pe_ratio ?? ratiosResult?.ttm?.valuation?.pe_ratio ?? null}
          assumptions={{
            revenue_growth: parseFloat(revenueGrowth) / 100,
            operating_margin: parseFloat(operatingMargin) / 100,
            terminal_growth_rate: parseFloat(terminalGrowth) / 100,
            discount_rate: result.discount_rate,
            projection_years: parseInt(projectionYears),
            da_ratio: currentHints?.da_ratio,
            capex_ratio: currentHints?.capex_ratio,
            wc_ratio: currentHints?.wc_ratio,
          }}
          scenarios={scenarioResult}
        />
      )}

    </Layout>
  );
}
