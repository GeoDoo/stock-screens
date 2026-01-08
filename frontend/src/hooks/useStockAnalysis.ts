/**
 * Custom hook for managing stock analysis state and fetching.
 * 
 * Handles:
 * - Fetching stock data via batch endpoint
 * - Normalization of response data
 * - Provider fallback on errors
 * - Comparables fetching
 * - Technical analysis fetching
 */
import { useState, useCallback, useRef } from 'react';
import type {
  StockDataResponse,
  ComparableResult,
  TechnicalAnalysisResult,
  FinancialRatiosResult,
  DividendHistoryResult,
  HistoricalValuationResult,
  Provider,
} from '../types';
import {
  normalizeStockData,
  normalizeComparableResult,
  normalizeTechnicalResult,
  normalizeHistoricalValuation,
} from '../normalizers';
import { shouldFallback, getAlternativeProvider, getProviderDisplayName } from '../providerFallback';
import { API_BASE } from '../config';

export interface UseStockAnalysisResult {
  // Stock data
  stockData: StockDataResponse | null;
  loading: boolean;
  error: string | null;
  
  // Related data (fetched via batch endpoint)
  ratiosResult: FinancialRatiosResult | null;
  dividendResult: DividendHistoryResult | null;
  historicalValuation: HistoricalValuationResult | null;
  
  // Comparables
  comparableResult: ComparableResult | null;
  comparableLoading: boolean;
  
  // Technical
  technicalResult: TechnicalAnalysisResult | null;
  technicalLoading: boolean;
  
  // Flags
  hasAttemptedAnalysis: boolean;
  fallbackNotice: string | null;
  
  // Actions
  analyzeStock: (
    ticker: string,
    provider: string,
    providers: Provider[],
    onSuccess?: (data: StockDataResponse, actualProvider: string) => void | Promise<void>,
  ) => Promise<void>;
  fetchComparables: (symbol: string, provider: string) => Promise<void>;
  fetchTechnical: (
    symbol: string,
    provider: string,
    providers: Provider[],
  ) => Promise<void>;
  clearData: () => void;
  clearError: () => void;
  setFallbackNotice: (notice: string | null) => void;
  refreshRateLimits: () => Promise<void>;
}

export function useStockAnalysis(
  onRateLimitRefresh?: () => Promise<void>,
): UseStockAnalysisResult {
  // Stock data state
  const [stockData, setStockData] = useState<StockDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Related data from batch endpoint
  const [ratiosResult, setRatiosResult] = useState<FinancialRatiosResult | null>(null);
  const [dividendResult, setDividendResult] = useState<DividendHistoryResult | null>(null);
  const [historicalValuation, setHistoricalValuation] = useState<HistoricalValuationResult | null>(null);
  
  // Comparables
  const [comparableResult, setComparableResult] = useState<ComparableResult | null>(null);
  const [comparableLoading, setComparableLoading] = useState(false);
  
  // Technical
  const [technicalResult, setTechnicalResult] = useState<TechnicalAnalysisResult | null>(null);
  const [technicalLoading, setTechnicalLoading] = useState(false);
  
  // Flags
  const [hasAttemptedAnalysis, setHasAttemptedAnalysis] = useState(false);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  
  // Ref to prevent duplicate technical calls
  const technicalFetchRef = useRef<{ inProgress: boolean; provider: string | null }>({
    inProgress: false,
    provider: null,
  });

  // Helper to refresh rate limits
  const refreshRateLimits = useCallback(async () => {
    if (onRateLimitRefresh) {
      await onRateLimitRefresh();
    }
  }, [onRateLimitRefresh]);

  // Clear all data
  const clearData = useCallback(() => {
    setStockData(null);
    setRatiosResult(null);
    setDividendResult(null);
    setHistoricalValuation(null);
    setComparableResult(null);
    setTechnicalResult(null);
    setError(null);
    setFallbackNotice(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Analyze stock - uses batch endpoint
  const analyzeStock = useCallback(async (
    ticker: string,
    provider: string,
    providers: Provider[],
    onSuccess?: (data: StockDataResponse, actualProvider: string) => void | Promise<void>,
  ) => {
    if (!ticker.trim() || !provider) return;
    
    setLoading(true);
    setError(null);
    clearData();
    setHasAttemptedAnalysis(true);
    
    // Track which provider actually served the data (may change due to fallback)
    let actualProvider = provider;
    
    const symbol = ticker.toUpperCase();
    
    // Try provider with fallback
    const tryProvider = async (prov: string, isFallback = false): Promise<boolean> => {
      try {
        const res = await fetch(`${API_BASE}/api/stock/${symbol}/analyze?provider=${prov}`);
        if (!res.ok) {
          const errData = await res.json();
          const errorMsg = errData.detail || 'Failed to fetch stock data';
          await refreshRateLimits();
          
          // Try fallback if error is fallback-worthy
          if (!isFallback && shouldFallback(errorMsg)) {
            const altProvider = getAlternativeProvider(prov, providers);
            if (altProvider) {
              // Update actualProvider BEFORE recursive call so onSuccess receives correct provider
              actualProvider = altProvider;
              
              const success = await tryProvider(altProvider, true);
              if (success) {
                const primaryName = getProviderDisplayName(prov, providers);
                const altName = getProviderDisplayName(altProvider, providers);
                setFallbackNotice(`${primaryName} unavailable for ${symbol}. Using ${altName} instead.`);
                return true;
              }
            }
          }
          throw new Error(errorMsg);
        }
        
        const batchData = await res.json();
        await refreshRateLimits();
        
        // Extract and normalize data
        const stockResponse = normalizeStockData(batchData.stock as StockDataResponse);
        if (!stockResponse) {
          throw new Error('Failed to parse stock data');
        }
        
        setStockData(stockResponse);
        setRatiosResult(batchData.ratios);
        setDividendResult(batchData.dividends);
        setHistoricalValuation(normalizeHistoricalValuation(batchData.historical_valuation));
        
        if (onSuccess) {
          // Await to ensure async callbacks complete before returning
          // Pass actualProvider which is correct even after fallback
          await onSuccess(stockResponse, actualProvider);
        }
        
        return true;
      } catch (err) {
        if (isFallback) throw err;
        throw err;
      }
    };

    try {
      await tryProvider(provider);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [clearData, refreshRateLimits]);

  // Fetch comparables
  const fetchComparables = useCallback(async (symbol: string, provider: string) => {
    if (!provider || !symbol) return;
    
    setComparableLoading(true);
    setComparableResult(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/stock/${symbol}/comparables?provider=${provider}`);
      if (res.ok) {
        const data: ComparableResult = await res.json();
        setComparableResult(normalizeComparableResult(data));
      }
    } catch (err) {
      console.error('Failed to fetch comparables:', err);
    } finally {
      setComparableLoading(false);
    }
  }, []);

  // Fetch technical analysis
  const fetchTechnical = useCallback(async (
    symbol: string,
    provider: string,
    providers: Provider[],
  ) => {
    if (!symbol || !provider) return;
    
    // Skip if already fetching with same provider
    if (technicalFetchRef.current.inProgress && technicalFetchRef.current.provider === provider) {
      return;
    }
    
    technicalFetchRef.current = { inProgress: true, provider };
    setTechnicalLoading(true);
    setError(null);
    
    const tryProvider = async (prov: string, isFallback = false): Promise<boolean> => {
      try {
        const res = await fetch(`${API_BASE}/api/stock/${symbol}/technical?provider=${prov}&days=365`);
        if (!res.ok) {
          const errData = await res.json();
          const errorMsg = errData.detail || 'Technical analysis failed';
          
          if (!isFallback && shouldFallback(errorMsg)) {
            const altProvider = getAlternativeProvider(prov, providers);
            if (altProvider) {
              const success = await tryProvider(altProvider, true);
              if (success) {
                const primaryName = getProviderDisplayName(prov, providers);
                const altName = getProviderDisplayName(altProvider, providers);
                setFallbackNotice(`${primaryName} unavailable for technical data. Using ${altName} instead.`);
                return true;
              }
            }
          }
          throw new Error(errorMsg);
        }
        
        const data: TechnicalAnalysisResult = await res.json();
        setTechnicalResult(normalizeTechnicalResult(data));
        return true;
      } catch (err) {
        if (isFallback) throw err;
        throw err;
      }
    };

    try {
      await tryProvider(provider);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setTechnicalLoading(false);
      technicalFetchRef.current.inProgress = false;
    }
  }, []);

  return {
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
    analyzeStock,
    fetchComparables,
    fetchTechnical,
    clearData,
    clearError,
    setFallbackNotice,
    refreshRateLimits,
  };
}
