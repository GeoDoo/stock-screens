import React from 'react';
import type { RedFlagCategory } from '../api';

interface Props {
  redFlags: Record<string, RedFlagCategory>;
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
  const categories = Object.entries(redFlags);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Forensic Intelligence Heatmap</h3>
          <p className="text-sm text-gray-500">Structured analysis of accounting quality and management behavior.</p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-black ${getConsistencyColor(consistencyScore)}`}>
            {consistencyScore}/100
          </div>
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Consistency Score</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {categories.map(([name, data]) => (
          <div 
            key={name} 
            className={`p-4 rounded-xl border transition-all hover:shadow-md ${getScoreColor(data.score)}`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="font-bold text-sm uppercase tracking-tight">{name}</span>
              <span className="text-xs font-black px-2 py-0.5 rounded-full bg-white/50">
                {data.score}/10
              </span>
            </div>
            
            <div className="space-y-2">
              {data.findings.slice(0, 2).map((finding, i) => (
                <p key={i} className="text-[11px] leading-tight font-medium opacity-90">
                  • {finding}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-gray-50 rounded-xl border border-gray-200">
        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Key Evidence & Quotes</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.filter(([_, d]) => d.score > 5).map(([name, data]) => (
            <div key={name} className="space-y-2">
              <span className="text-[10px] font-bold text-gray-500">{name} Evidence:</span>
              {data.evidence_quotes.map((quote, i) => (
                <blockquote key={i} className="pl-3 border-l-2 border-amber-300 italic text-[11px] text-gray-600">
                  "{quote}"
                </blockquote>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
