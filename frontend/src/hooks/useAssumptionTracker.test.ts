/**
 * Tests for useAssumptionTracker hook.
 * TDD: Written BEFORE implementation.
 */
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useAssumptionTracker } from './useAssumptionTracker';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('useAssumptionTracker', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('recordAssumptions', () => {
    it('should POST assumptions to the audit API', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 1,
          symbol: 'AAPL',
          timestamp: '2025-01-08T12:00:00',
          changes: [
            { field: 'revenue_growth', old_value: null, new_value: 0.05 },
          ],
          is_initial: true,
          note: 'Initial analysis',
        }),
      });

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      await act(async () => {
        await result.current.recordAssumptions(
          {
            revenue_growth: 0.05,
            operating_margin: 0.25,
          },
          'Initial analysis'
        );
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/audit/AAPL'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            assumptions: {
              revenue_growth: 0.05,
              operating_margin: 0.25,
            },
            note: 'Initial analysis',
          }),
        })
      );
    });

    it('should return true when changes were recorded', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 1,
          symbol: 'AAPL',
          changes: [{ field: 'revenue_growth', old_value: 0.05, new_value: 0.08 }],
          is_initial: false,
        }),
      });

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      let hasChanges;
      await act(async () => {
        hasChanges = await result.current.recordAssumptions({ revenue_growth: 0.08 });
      });

      expect(hasChanges).toBe(true);
    });

    it('should return false when no changes detected', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          message: 'No changes detected',
          changes: [],
        }),
      });

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      let hasChanges;
      await act(async () => {
        hasChanges = await result.current.recordAssumptions({ revenue_growth: 0.05 });
      });

      expect(hasChanges).toBe(false);
    });
  });

  describe('fetchHistory', () => {
    it('should fetch audit history for a symbol', async () => {
      const mockHistory = [
        {
          id: 2,
          symbol: 'AAPL',
          timestamp: '2025-01-08T14:00:00',
          changes: [{ field: 'revenue_growth', old_value: 0.05, new_value: 0.08 }],
          note: 'Updated after earnings',
          is_initial: false,
        },
        {
          id: 1,
          symbol: 'AAPL',
          timestamp: '2025-01-08T12:00:00',
          changes: [{ field: 'revenue_growth', old_value: null, new_value: 0.05 }],
          note: 'Initial',
          is_initial: true,
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHistory,
      });

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      await act(async () => {
        await result.current.fetchHistory();
      });

      expect(result.current.history).toEqual(mockHistory);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/audit/AAPL/history')
      );
    });

    it('should set loading state while fetching', async () => {
      let resolvePromise: () => void;
      const promise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      mockFetch.mockImplementationOnce(() => 
        promise.then(() => ({
          ok: true,
          json: async () => [],
        }))
      );

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      // Start fetch but don't await
      act(() => {
        result.current.fetchHistory();
      });

      // Should be loading
      expect(result.current.isLoading).toBe(true);

      // Resolve and wait
      await act(async () => {
        resolvePromise!();
        await promise;
      });

      // Should no longer be loading
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  describe('hasHistory', () => {
    it('should return true when history exists', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: 1 }],
      });

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      await act(async () => {
        await result.current.fetchHistory();
      });

      expect(result.current.hasHistory).toBe(true);
    });

    it('should return false when no history', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      await act(async () => {
        await result.current.fetchHistory();
      });

      expect(result.current.hasHistory).toBe(false);
    });
  });

  describe('getFieldHistory', () => {
    it('should fetch history for a specific field', async () => {
      const fieldHistory = [
        { field: 'revenue_growth', old_value: 0.05, new_value: 0.08 },
        { field: 'revenue_growth', old_value: null, new_value: 0.05 },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => fieldHistory,
      });

      const { result } = renderHook(() => useAssumptionTracker('AAPL'));

      let history;
      await act(async () => {
        history = await result.current.getFieldHistory('revenue_growth');
      });

      expect(history).toEqual(fieldHistory);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/audit/AAPL/field/revenue_growth')
      );
    });
  });

  describe('symbol changes', () => {
    it('should clear history when symbol changes', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => [{ id: 1, symbol: 'AAPL' }],
      });

      const { result, rerender } = renderHook(
        ({ symbol }) => useAssumptionTracker(symbol),
        { initialProps: { symbol: 'AAPL' } }
      );

      // Fetch history for AAPL
      await act(async () => {
        await result.current.fetchHistory();
      });

      expect(result.current.history.length).toBe(1);

      // Change symbol
      rerender({ symbol: 'MSFT' });

      // History should be cleared
      expect(result.current.history).toEqual([]);
    });
  });
});
