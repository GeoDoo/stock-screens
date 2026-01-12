import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ShieldCheck, FileSearch } from 'lucide-react';

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

  if (!analysis) {
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
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-gray-100">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <FileSearch className="w-4 h-4 text-indigo-600" />
          Institutional Forensic Analysis
        </h3>
      </div>

      <div className="forensic-analysis-content prose prose-sm max-w-none">
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({node, ...props}) => <h1 className="text-xl font-black text-gray-900 mt-8 mb-4 border-b-2 border-gray-100 pb-2 uppercase tracking-tighter" {...props} />,
            h2: ({node, ...props}) => <h2 className="text-base font-black text-indigo-900 mt-6 mb-3 uppercase tracking-tight" {...props} />,
            h3: ({node, ...props}) => <h3 className="text-sm font-bold text-gray-900 mt-4 mb-2" {...props} />,
            p: ({node, ...props}) => <p className="text-[14px] text-gray-700 leading-relaxed mb-4 font-medium" {...props} />,
            ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-4 space-y-2" {...props} />,
            li: ({node, ...props}) => <li className="text-[14px] text-gray-700 font-medium" {...props} />,
            table: ({node, ...props}) => (
              <div className="overflow-x-auto my-6 rounded-xl border border-gray-200 shadow-sm">
                <table className="min-w-full divide-y divide-gray-200 text-[12px]" {...props} />
              </div>
            ),
            thead: ({node, ...props}) => <thead className="bg-gray-50" {...props} />,
            th: ({node, ...props}) => <th className="px-3 py-2 text-left font-bold text-gray-500 uppercase tracking-wider" {...props} />,
            td: ({node, ...props}) => <td className="px-3 py-2 whitespace-normal border-t border-gray-100 text-gray-600" {...props} />,
            blockquote: ({node, ...props}) => (
              <blockquote className="border-l-4 border-amber-300 bg-amber-50/50 p-3 my-3 italic text-xs text-gray-700 rounded-r-lg" {...props} />
            ),
            strong: ({node, ...props}) => <strong className="font-bold text-gray-900" {...props} />,
          }}
        >
          {analysis}
        </ReactMarkdown>
      </div>
    </div>
  );
}
