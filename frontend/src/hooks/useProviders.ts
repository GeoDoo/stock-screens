/**
 * Custom hook for managing data providers and rate limits.
 * 
 * Handles:
 * - Fetching available providers (fundamental + technical)
 * - Rate limit tracking with localStorage caching
 * - Auto-switching to available provider when current one hits rate limit
 * - Provider persistence in localStorage
 */
import { useState, useEffect, useCallback } from 'react';
import type { Provider, RateLimitStats, ProvidersResponse } from '../types';
import { API_BASE } from '../config';

export interface UseProvidersResult {
  // Fundamental providers
  fundamentalProviders: Provider[];
  selectedFundamentalProvider: string;
  setSelectedFundamentalProvider: (id: string) => void;
  
  // Technical providers
  technicalProviders: Provider[];
  selectedTechnicalProvider: string;
  setSelectedTechnicalProvider: (id: string) => void;
  
  // Rate limits
  rateLimits: Record<string, RateLimitStats>;
  rateLimitsLoading: boolean;
  
  // Loading state
  providersLoading: boolean;
  
  // Helpers
  isProviderAtLimit: (providerId: string) => boolean;
  refreshRateLimits: () => Promise<void>;
  getProviderName: (providerId: string, type: 'fundamental' | 'technical') => string;
}

export function useProviders(): UseProvidersResult {
  const [fundamentalProviders, setFundamentalProviders] = useState<Provider[]>([]);
  const [technicalProviders, setTechnicalProviders] = useState<Provider[]>([]);
  const [selectedFundamentalProvider, setSelectedFundamentalProvider] = useState<string>('');
  const [selectedTechnicalProvider, setSelectedTechnicalProvider] = useState<string>('');
  const [providersLoading, setProvidersLoading] = useState(true);
  
  // Rate limits with localStorage cache for instant display
  const [rateLimits, setRateLimits] = useState<Record<string, RateLimitStats>>(() => {
    try {
      const cached = localStorage.getItem('rateLimits');
      return cached ? JSON.parse(cached) : {};
    } catch {
      return {};
    }
  });
  const [rateLimitsLoading, setRateLimitsLoading] = useState(true);

  // Check if a provider is at its rate limit
  const isProviderAtLimit = useCallback((providerId: string): boolean => {
    const stats = rateLimits[providerId.toLowerCase()];
    return stats ? (stats.api_limited || stats.remaining === 0) : false;
  }, [rateLimits]);

  // Fetch rate limits from backend
  const refreshRateLimits = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/rate-limits`);
      if (res.ok) {
        const data = await res.json();
        setRateLimits(data);
        // Cache to localStorage for instant display on next page load
        try {
          localStorage.setItem('rateLimits', JSON.stringify(data));
        } catch {
          // localStorage might be full or disabled
        }
      }
    } catch (err) {
      console.error('Failed to fetch rate limits:', err);
    } finally {
      setRateLimitsLoading(false);
    }
  }, []);

  // Get provider display name
  const getProviderName = useCallback((providerId: string, type: 'fundamental' | 'technical'): string => {
    const providers = type === 'fundamental' ? fundamentalProviders : technicalProviders;
    return providers.find(p => p.id === providerId)?.name || providerId;
  }, [fundamentalProviders, technicalProviders]);

  // Auto-switch fundamental provider when current one hits rate limit
  useEffect(() => {
    if (selectedFundamentalProvider && isProviderAtLimit(selectedFundamentalProvider) && fundamentalProviders.length > 0) {
      const available = fundamentalProviders.find(p => p.available && !isProviderAtLimit(p.id));
      if (available) {
        setSelectedFundamentalProvider(available.id);
      }
    }
  }, [rateLimits, selectedFundamentalProvider, fundamentalProviders, isProviderAtLimit]);

  // Auto-switch technical provider when current one hits rate limit
  useEffect(() => {
    if (selectedTechnicalProvider && isProviderAtLimit(selectedTechnicalProvider) && technicalProviders.length > 0) {
      const available = technicalProviders.find(p => p.available && !isProviderAtLimit(p.id));
      if (available) {
        setSelectedTechnicalProvider(available.id);
      }
    }
  }, [rateLimits, selectedTechnicalProvider, technicalProviders, isProviderAtLimit]);

  // Fetch providers on mount
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/providers`);
        const data: ProvidersResponse = await res.json();
        setFundamentalProviders(data.fundamental);
        setTechnicalProviders(data.technical);
        
        // Also fetch accurate rate limits
        await refreshRateLimits();
        
        // Check localStorage for rate limit data (to avoid rate-limited providers)
        const cachedLimits = localStorage.getItem('rateLimits');
        const limits = cachedLimits ? JSON.parse(cachedLimits) : {};
        const isLimited = (providerId: string) => limits[providerId]?.api_limited === true;
        
        // Try to restore saved provider, but only if not rate-limited
        const savedFundamental = localStorage.getItem('selectedFundamentalProvider');
        const savedTechnical = localStorage.getItem('selectedTechnicalProvider');
        
        // Find best fundamental provider: saved (if not limited) > recommended (if not limited) > any available
        const fundSaved = savedFundamental && data.fundamental.find((p: Provider) => p.id === savedFundamental && p.available && !isLimited(p.id));
        const fundRecommended = data.fundamental.find((p: Provider) => p.recommended && p.available && !isLimited(p.id));
        const fundAvailable = data.fundamental.find((p: Provider) => p.available && !isLimited(p.id));
        const fundFallback = data.fundamental.find((p: Provider) => p.available);
        
        const selectedFund = fundSaved || fundRecommended || fundAvailable || fundFallback;
        if (selectedFund) {
          setSelectedFundamentalProvider(selectedFund.id);
          localStorage.setItem('selectedFundamentalProvider', selectedFund.id);
        }
        
        // Same logic for technical provider
        const techSaved = savedTechnical && data.technical.find((p: Provider) => p.id === savedTechnical && p.available && !isLimited(p.id));
        const techRecommended = data.technical.find((p: Provider) => p.recommended && p.available && !isLimited(p.id));
        const techAvailable = data.technical.find((p: Provider) => p.available && !isLimited(p.id));
        const techFallback = data.technical.find((p: Provider) => p.available);
        
        const selectedTech = techSaved || techRecommended || techAvailable || techFallback;
        if (selectedTech) {
          setSelectedTechnicalProvider(selectedTech.id);
          localStorage.setItem('selectedTechnicalProvider', selectedTech.id);
        }
      } catch (err) {
        console.error('Failed to fetch providers:', err);
      } finally {
        setProvidersLoading(false);
      }
    };
    fetchProviders();
  }, [refreshRateLimits]);

  // Periodic refresh of rate limits (every 30 seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      refreshRateLimits();
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshRateLimits]);

  return {
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
    getProviderName,
  };
}
