/**
 * Provenance badges show the source/confidence of data values.
 * 
 * Institutional-grade transparency: analysts need to know whether
 * a value comes from TTM data, annual averages, or fallbacks.
 */
import type { DataProvenance, ProvenanceItem } from '../types';

interface ProvenanceBadgeProps {
  source: string;
  description: string;
  confidence: 'high' | 'medium' | 'low';
}

/**
 * Maps source strings to human-readable labels
 */
function getSourceLabel(source: string): string {
  const labelMap: Record<string, string> = {
    ttm: 'TTM',
    fy_average: 'FY AVG',
    fallback: 'FALLBACK',
    calculated: 'CALC',
    diluted: 'DILUTED',
    basic: 'BASIC',
    profile: 'PROFILE',
    synthetic: 'SYNTHETIC',
    historical: 'HISTORICAL',
  };
  return labelMap[source.toLowerCase()] || source.toUpperCase();
}

/**
 * Individual provenance badge with color-coded confidence
 */
export function ProvenanceBadge({ source, description, confidence }: ProvenanceBadgeProps) {
  const label = getSourceLabel(source);
  
  const baseClasses = 'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider cursor-help transition-opacity hover:opacity-80';
  
  const confidenceClasses = {
    high: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
    medium: 'bg-amber-100 text-amber-700 border border-amber-200',
    low: 'bg-red-100 text-red-700 border border-red-200',
  };
  
  return (
    <span
      className={`${baseClasses} ${confidenceClasses[confidence]}`}
      title={description}
    >
      {label}
    </span>
  );
}

function getMetricLabel(metric: string): string {
  const labelMap: Record<string, string> = {
    tax_rate: 'Tax Rate',
    shares_outstanding: 'Shares',
    revenue_source: 'Revenue',
    cost_of_debt: 'Cost of Debt',
  };
  return labelMap[metric] || metric;
}

/**
 * Display all provenance items in a compact row
 */
interface ProvenanceDisplayProps {
  provenance: DataProvenance | undefined;
}

export function ProvenanceDisplay({ provenance }: ProvenanceDisplayProps) {
  if (!provenance) return null;
  
  const items = Object.entries(provenance).filter(
    ([, item]) => item !== null
  ) as [string, ProvenanceItem][];
  
  if (items.length === 0) return null;
  
  return (
    <div className="flex flex-wrap gap-3 items-center">
      <span className="text-xs text-gray-400 font-medium">Data Sources:</span>
      {items.map(([key, item]) => (
        <div key={key} className="flex items-center gap-1">
          <span className="text-xs text-gray-500">{getMetricLabel(key)}</span>
          <ProvenanceBadge
            source={item.source}
            description={item.description}
            confidence={item.confidence}
          />
        </div>
      ))}
    </div>
  );
}

/**
 * Inline provenance indicator for a single metric
 */
interface InlineProvenanceProps {
  item: ProvenanceItem | null | undefined;
}

export function InlineProvenance({ item }: InlineProvenanceProps) {
  if (!item) return null;
  
  return (
    <ProvenanceBadge
      source={item.source}
      description={item.description}
      confidence={item.confidence}
    />
  );
}
