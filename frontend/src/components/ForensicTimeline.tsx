import { History, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import type { ForensicHistoryItem } from '../api';

interface Props {
  history: ForensicHistoryItem[];
}

export function ForensicTimeline({ history }: Props) {
  if (history.length === 0) return null;

  // Sort history by date ascending for the timeline
  const sortedHistory = [...history].sort((a, b) => 
    new Date(a.filing_date).getTime() - new Date(b.filing_date).getTime()
  );

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50 border-green-100';
    if (score >= 60) return 'text-amber-600 bg-amber-50 border-amber-100';
    return 'text-red-600 bg-red-50 border-red-100';
  };

  const getTrendIcon = () => {
    if (history.length < 2) return null;
    const latest = sortedHistory[sortedHistory.length - 1].consistency_score;
    const previous = sortedHistory[sortedHistory.length - 2].consistency_score;
    
    if (latest > previous) return <TrendingUp className="w-4 h-4 text-green-500" />;
    if (latest < previous) return <TrendingDown className="w-4 h-4 text-red-500" />;
    return null;
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm mb-8">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-indigo-600" />
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight">Forensic Alpha Timeline</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Accounting Trend</span>
          {getTrendIcon()}
        </div>
      </div>

      <div className="p-6">
        <div className="relative">
          {/* Timeline Line */}
          <div className="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 -translate-y-1/2" />
          
          <div className="flex justify-between items-center relative z-10">
            {sortedHistory.map((item) => (
              <div key={item.accession_number} className="flex flex-col items-center gap-3">
                <div className="text-[10px] font-mono text-gray-400 font-bold">
                  {new Date(item.filing_date).getFullYear()}
                </div>
                
                <div 
                  className={`w-10 h-10 rounded-full border-2 flex items-center justify-center font-black text-xs transition-transform hover:scale-110 cursor-help shadow-sm ${getScoreColor(item.consistency_score)}`}
                  title={`${item.form_type} filed on ${item.filing_date}`}
                >
                  {item.consistency_score}
                </div>
                
                <div className="text-[9px] font-bold text-gray-500 uppercase">
                  {item.form_type}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Legend / Insight */}
        <div className="mt-8 flex items-start gap-3 p-3 bg-indigo-50/50 rounded-lg border border-indigo-100">
          <AlertTriangle className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <p className="text-[11px] text-indigo-900 leading-relaxed">
            <span className="font-bold">Institutional Insight:</span> High consistency scores ({'>'}80) over multiple years indicate stable accounting policies and lower forensic risk. A sudden drop in score is a primary alpha signal for potential shenanigans.
          </p>
        </div>
      </div>
    </div>
  );
}
