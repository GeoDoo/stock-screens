import React from 'react';
import { AlertTriangle, ShieldCheck, Info, FileSearch } from 'lucide-react';

interface RedFlag {
  category: string;
  severity: 'high' | 'medium' | 'info';
  title: string;
  description: string;
  evidence?: string;
}

interface ForensicRedFlagsProps {
  analysis: string;
  loading?: boolean;
}

export function ForensicRedFlags({ analysis, loading }: ForensicRedFlagsProps) {
  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-gray-100 rounded-xl" />
        ))}
      </div>
    );
  }

  // Parse the analysis text into structured flags
  // The backend uses SECTION [NAME] headers
  const parseFlags = (text: string): RedFlag[] => {
    const flags: RedFlag[] = [];
    
    // This is a simple parser for the LLM's Markdown output
    // Looking for specific headers or keywords
    const lines = text.split('\n');
    let currentCategory = 'General';
    
    lines.forEach(line => {
      const lower = line.toLowerCase();
      const trimmed = line.trim();
      
      if (trimmed.includes('SECTION')) {
        currentCategory = trimmed.split('SECTION')[1].trim().replace(':', '');
      } else if (trimmed.startsWith('###') || trimmed.startsWith('**')) {
        // Potential finding
        const title = trimmed.replace(/[#*]/g, '').trim();
        if (title.length > 2 && title.length < 100) {
            flags.push({
                category: currentCategory,
                severity: lower.includes('high') || lower.includes('severe') || lower.includes('red flag') ? 'high' : 
                          lower.includes('warning') || lower.includes('risk') ? 'medium' : 'info',
                title,
                description: '',
            });
        }
      } else if (flags.length > 0 && trimmed.length > 5) {
          // Append description to the last flag
          flags[flags.length - 1].description += trimmed + ' ';
      }
    });

    return flags.filter(f => f.description.length > 10);
  };

  const flags = parseFlags(analysis);

  if (flags.length === 0 && analysis) {
      return (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 flex gap-3 text-emerald-800">
              <ShieldCheck className="w-5 h-5 shrink-0" />
              <div>
                  <div className="font-semibold text-sm">No critical red flags detected</div>
                  <div className="text-xs opacity-90 mt-1">The AI analysis did not find obvious signs of financial shenanigans in this filing.</div>
              </div>
          </div>
      );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <FileSearch className="w-4 h-4 text-indigo-600" />
          Forensic Findings
        </h3>
        <span className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full uppercase tracking-wider font-bold">
          {flags.length} Findings
        </span>
      </div>

      <div className="grid gap-3">
        {flags.map((flag, idx) => (
          <div 
            key={idx} 
            className={`p-4 rounded-xl border-l-4 transition-all hover:shadow-md ${
              flag.severity === 'high' ? 'bg-red-50 border-red-500' :
              flag.severity === 'medium' ? 'bg-amber-50 border-amber-500' :
              'bg-blue-50 border-blue-500'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <div className={`text-[10px] font-bold uppercase tracking-widest ${
                flag.severity === 'high' ? 'text-red-600' :
                flag.severity === 'medium' ? 'text-amber-600' :
                'text-blue-600'
              }`}>
                {flag.category}
              </div>
              {flag.severity === 'high' ? <AlertTriangle className="w-4 h-4 text-red-600" /> : 
               flag.severity === 'medium' ? <AlertTriangle className="w-4 h-4 text-amber-600" /> :
               <Info className="w-4 h-4 text-blue-600" />}
            </div>
            <h4 className="text-sm font-bold text-gray-900 mb-1">{flag.title}</h4>
            <p className="text-xs text-gray-700 leading-relaxed line-clamp-3">
              {flag.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
