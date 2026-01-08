/**
 * Hook for tracking DCF assumption changes via the audit trail API.
 * 
 * Provides:
 * - recordAssumptions: Save current assumptions (creates initial or update entry)
 * - fetchHistory: Get full audit history for the symbol
 * - getFieldHistory: Get change history for a specific field
 */
import { useState, useCallback, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface AssumptionChange {
  field: string;
  old_value: number | null;
  new_value: number;
}

export interface AuditEntry {
  id: number;
  symbol: string;
  timestamp: string;
  changes: AssumptionChange[];
  note: string | null;
  is_initial: boolean;
  // Market context at time of recording (for thesis tracking)
  price_at_time: number | null;
  intrinsic_value_at_time: number | null;
  pe_ratio_at_time: number | null;
}

export interface Assumptions {
  revenue_growth?: number;
  operating_margin?: number;
  terminal_growth?: number;
  discount_rate?: number;
  projection_years?: number;
  market_risk_premium?: number;
}

export interface MarketContext {
  price_at_time?: number;
  intrinsic_value_at_time?: number;
  pe_ratio_at_time?: number;
}

export interface UseAssumptionTrackerResult {
  /** Full audit history, most recent first */
  history: AuditEntry[];
  /** Whether history is being loaded */
  isLoading: boolean;
  /** Whether the symbol has any audit history */
  hasHistory: boolean;
  /** Error message if any */
  error: string | null;
  
  /**
   * Record assumptions to the audit trail.
   * @param assumptions - The DCF assumptions to record
   * @param note - Optional note explaining the change
   * @param marketContext - Optional market context (price, intrinsic value, P/E)
   * @returns true if changes were recorded, false if nothing changed
   */
  recordAssumptions: (assumptions: Assumptions, note?: string, marketContext?: MarketContext) => Promise<boolean>;
  
  /** Fetch full audit history */
  fetchHistory: () => Promise<void>;
  
  /** Get change history for a specific field */
  getFieldHistory: (field: string) => Promise<AssumptionChange[]>;
}

export function useAssumptionTracker(symbol: string): UseAssumptionTrackerResult {
  const [history, setHistory] = useState<AuditEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clear history when symbol changes
  useEffect(() => {
    setHistory([]);
    setError(null);
  }, [symbol]);

  const recordAssumptions = useCallback(async (
    assumptions: Assumptions,
    note?: string,
    marketContext?: MarketContext
  ): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/api/audit/${symbol}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          assumptions,
          note: note || null,
          price_at_time: marketContext?.price_at_time || null,
          intrinsic_value_at_time: marketContext?.intrinsic_value_at_time || null,
          pe_ratio_at_time: marketContext?.pe_ratio_at_time || null,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to record assumptions: ${response.statusText}`);
      }

      const data = await response.json();
      
      // 201 = changes recorded, 200 = no changes
      if (response.status === 201) {
        // Prepend to history (most recent first)
        setHistory(prev => [data, ...prev]);
        return true;
      }
      
      return false; // No changes detected
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    }
  }, [symbol]);

  const fetchHistory = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/audit/${symbol}/history`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch history: ${response.statusText}`);
      }

      const data = await response.json();
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [symbol]);

  const getFieldHistory = useCallback(async (field: string): Promise<AssumptionChange[]> => {
    try {
      const response = await fetch(`${API_BASE}/api/audit/${symbol}/field/${field}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch field history: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    }
  }, [symbol]);

  return {
    history,
    isLoading,
    hasHistory: history.length > 0,
    error,
    recordAssumptions,
    fetchHistory,
    getFieldHistory,
  };
}
