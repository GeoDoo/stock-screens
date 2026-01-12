import type { RedFlagCategory } from '../types';

interface Props {
  redFlags: RedFlagCategory[];
  consistencyScore: number;
}

const getScoreColor = (score: number) => {
  if (score <= 3) return 'bg-green-100 text-green-800 border-green-200';
  if (score <= 6) return 'bg-amber-100 text-amber-800 border-amber-200';
  return 'bg-red-100 text-red-800 border-red-200';
};

const getConsistencyColor = (score: number) => {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-amber-600';
  return 'text-red-600';
};

export function RedFlagHeatmap({ redFlags, consistencyScore }: Props) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-8 py-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/30">
        <div>
          <h3 className="text-base font-black text-gray-900 uppercase tracking-tighter">Forensic Intelligence Heatmap</h3>
          <p className="text-xs text-gray-500 font-medium mt-1 uppercase tracking-widest opacity-70">Accounting Quality & Management Integrity Analysis</p>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className={`text-4xl font-black leading-none ${getConsistencyColor(consistencyScore)}`}>
              {consistencyScore}
              <span className="text-xs text-gray-400 ml-1 font-bold">/100</span>
            </div>
            <div className="text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mt-1">Consistency Score</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-b border-gray-100">
        {redFlags.map((data) => (
          <div 
            key={data.category} 
            className="p-8 border-r border-b lg:border-b-0 border-gray-100 last:border-r-0 transition-all hover:bg-gray-50/50 group"
          >
            <div className="flex justify-between items-center mb-6">
              <span className="font-black text-[11px] uppercase tracking-widest text-gray-500 group-hover:text-indigo-600 transition-colors">{data.category}</span>
              <span className={`text-xs font-black px-2.5 py-1 rounded-full border ${getScoreColor(data.score)} shadow-sm`}>
                {data.score}/10
              </span>
            </div>
            
            <div className="space-y-4">
              {data.findings.slice(0, 3).map((finding: string, i: number) => (
                <div key={i} className="flex gap-3">
                  <span className="text-indigo-300 font-bold text-xs mt-0.5">•</span>
                  <p className="text-[13px] leading-relaxed font-medium text-gray-700">
                    {finding}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {redFlags.some(d => d.evidence_quotes.length > 0) && (
        <div className="bg-gray-50/50 p-8">
          <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-6">Verified Evidence & Direct Quotes</h4>
          <div className="columns-1 md:columns-2 lg:columns-3 gap-8">
            {redFlags.map((data) => (
              data.evidence_quotes.map((quote: string, i: number) => (
                <div key={`${data.category}-${i}`} className="break-inside-avoid mb-6 bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-[9px] font-black text-indigo-500 uppercase tracking-widest">{data.category}</span>
                  </div>
                  <blockquote className="text-[12px] leading-relaxed text-gray-600 italic font-medium border-l-2 border-indigo-100 pl-4">
                    "{quote}"
                  </blockquote>
                </div>
              ))
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
