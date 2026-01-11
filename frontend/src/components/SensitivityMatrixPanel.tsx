/**
 * 2D Sensitivity Matrix Panel
 * 
 * Displays intrinsic value sensitivity to two parameters:
 * - Margin vs Growth (execution risk)
 * - WACC vs Terminal Growth (discount assumptions)
 * 
 * Color-coded heatmap from red (low) to green (high).
 */
import { useState, useEffect } from 'react';
import { fetchSensitivityMatrix } from '../api';
import type { SensitivityMatrixResponse } from '../types';

interface SensitivityMatrixPanelProps {
  symbol: string;
  provider: string;
  baseGrowth: number;
  baseMargin: number;
  baseDiscountRate: number;
  terminalGrowth: number;
  projectionYears?: number;
  daRatio?: number;
  capexRatio?: number;
  wcRatio?: number;
}

type MatrixType = 'margin_growth' | 'wacc_terminal';

export function SensitivityMatrixPanel({
  symbol,
  provider,
  baseGrowth,
  baseMargin,
  baseDiscountRate,
  terminalGrowth,
  projectionYears = 10,
  daRatio,
  capexRatio,
  wcRatio,
}: SensitivityMatrixPanelProps) {
  const [matrixType, setMatrixType] = useState<MatrixType>('margin_growth');
  const [data, setData] = useState<SensitivityMatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMatrix() {
      setLoading(true);
      setError(null);
      
      try {
        const result = await fetchSensitivityMatrix({
          symbol,
          provider,
          matrixType,
          baseGrowth,
          baseMargin,
          baseDiscountRate,
          terminalGrowth,
          projectionYears,
          daRatio,
          capexRatio,
          wcRatio,
        });
        
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load sensitivity matrix');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadMatrix();

    return () => {
      cancelled = true;
    };
  }, [symbol, provider, matrixType, baseGrowth, baseMargin, baseDiscountRate, terminalGrowth, projectionYears, daRatio, capexRatio, wcRatio]);

  if (loading) {
    return (
      <div className="p-6 border border-gray-100 rounded-lg">
        <div className="text-sm text-gray-400">Loading sensitivity matrix...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 border border-red-100 rounded-lg bg-red-50">
        <div className="text-sm text-red-600">Error: {error}</div>
      </div>
    );
  }

  if (!data) return null;

  const rowLabels = matrixType === 'margin_growth' 
    ? (data.margins || []) 
    : (data.discount_rates || []);
  const colLabels = matrixType === 'margin_growth'
    ? (data.growth_rates || [])
    : (data.terminal_growth_rates || []);

  // Find min/max for color scaling
  const allValues = data.matrix.flat().filter((v): v is number => v !== null);
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  const range = maxValue - minValue || 1;

  // Find base case indices
  const baseRowValue = matrixType === 'margin_growth' 
    ? data.base_values.margin 
    : data.base_values.discount_rate;
  const baseColValue = matrixType === 'margin_growth'
    ? data.base_values.growth
    : data.base_values.terminal_growth;

  const baseRowIdx = rowLabels.findIndex(v => Math.abs(v - baseRowValue) < 0.001);
  const baseColIdx = colLabels.findIndex(v => Math.abs(v - baseColValue) < 0.001);

  // Color function for cells
  // If ROIC flag is set, the cell is "economically suspect" and should be grayed out
  function getCellStyle(value: number | null, rowIdx: number, colIdx: number): {
    colorClass: string;
    isSuspect: boolean;
    tooltip: string | null;
  } {
    // Check if this cell is flagged as economically suspect
    const isSuspect = data?.roic_flags?.[rowIdx]?.[colIdx] === true;
    
    if (value === null) {
      return { 
        colorClass: 'bg-gray-100 text-gray-400', 
        isSuspect: false, 
        tooltip: null 
      };
    }
    
    // If economically suspect, gray it out with a warning indicator
    if (isSuspect) {
      return {
        colorClass: 'bg-gray-200 text-gray-400 opacity-60',
        isSuspect: true,
        tooltip: 'Economically suspect: This scenario implies a terminal ROIC > 2× WACC, ' +
                 'which assumes perpetual competitive advantage that is unrealistic.',
      };
    }
    
    const normalized = (value - minValue) / range;
    
    let colorClass: string;
    if (normalized < 0.2) colorClass = 'bg-red-100 text-red-700';
    else if (normalized < 0.4) colorClass = 'bg-orange-100 text-orange-700';
    else if (normalized < 0.6) colorClass = 'bg-amber-100 text-amber-700';
    else if (normalized < 0.8) colorClass = 'bg-lime-100 text-lime-700';
    else colorClass = 'bg-emerald-100 text-emerald-700';
    
    return { colorClass, isSuspect: false, tooltip: null };
  }
  
  // Check if any cells are flagged
  const hasSuspectCells = data?.roic_flags?.some(row => row?.some(flag => flag === true)) ?? false;

  const rowLabel = matrixType === 'margin_growth' ? 'Margin' : 'WACC';
  const colLabel = matrixType === 'margin_growth' ? 'Growth' : 'Terminal Growth';

  return (
    <div className="space-y-4">
      {/* Matrix Type Selector */}
      <div className="flex gap-2">
        <button
          onClick={() => setMatrixType('margin_growth')}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
            matrixType === 'margin_growth'
              ? 'bg-gray-900 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Margin vs Growth
        </button>
        <button
          onClick={() => setMatrixType('wacc_terminal')}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
            matrixType === 'wacc_terminal'
              ? 'bg-gray-900 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          WACC vs Terminal
        </button>
      </div>

      {/* Matrix Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-xs font-semibold text-gray-500 text-right">
                {rowLabel} ↓ / {colLabel} →
              </th>
              {colLabels.map((col, i) => (
                <th 
                  key={i} 
                  className={`p-2 text-xs font-semibold text-center ${
                    i === baseColIdx ? 'text-gray-900 bg-gray-50' : 'text-gray-500'
                  }`}
                >
                  {(col * 100).toFixed(2)}%
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowLabels.map((row, rowIdx) => (
              <tr key={rowIdx}>
                <td 
                  className={`p-2 text-xs font-semibold text-right ${
                    rowIdx === baseRowIdx ? 'text-gray-900 bg-gray-50' : 'text-gray-500'
                  }`}
                >
                  {(row * 100).toFixed(2)}%
                </td>
                {data.matrix[rowIdx].map((value, colIdx) => {
                  const isBaseCase = rowIdx === baseRowIdx && colIdx === baseColIdx;
                  const cellStyle = getCellStyle(value, rowIdx, colIdx);
                  return (
                    <td
                      key={colIdx}
                      role="cell"
                      className={`p-2 text-center text-xs font-mono relative ${cellStyle.colorClass} ${
                        isBaseCase ? 'ring-2 ring-gray-900 ring-inset' : ''
                      }`}
                      title={cellStyle.tooltip || undefined}
                    >
                      {cellStyle.isSuspect && (
                        <span className="absolute top-0.5 right-0.5 text-[8px] text-amber-600" title="Economically suspect">⚠</span>
                      )}
                      {value !== null ? `$${value.toFixed(2)}` : '-'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center flex-wrap gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-red-100 border border-red-200 rounded"></span>
          Lower
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-amber-100 border border-amber-200 rounded"></span>
          Base
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-emerald-100 border border-emerald-200 rounded"></span>
          Higher
        </span>
        {hasSuspectCells && (
          <span className="flex items-center gap-1" title="These scenarios imply terminal ROIC > 2× WACC (economically unrealistic)">
            <span className="w-3 h-3 bg-gray-200 border border-gray-300 rounded opacity-60 flex items-center justify-center text-[8px] text-amber-600">⚠</span>
            Suspect
          </span>
        )}
        <span className="ml-auto text-gray-400">
          ◼ Base case highlighted
        </span>
      </div>
      
      {/* ROIC Warning Banner */}
      {hasSuspectCells && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
          <span className="font-semibold">⚠️ Economically Suspect Cells:</span>{' '}
          Grayed cells imply <strong>terminal ROIC &gt; 2× WACC</strong>, 
          meaning perpetual competitive advantage. In a competitive economy, 
          ROIC should fade toward WACC. Treat these scenarios with skepticism.
        </div>
      )}
    </div>
  );
}
