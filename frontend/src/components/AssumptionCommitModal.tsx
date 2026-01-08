/**
 * Modal prompting user to add a note when running valuation.
 * 
 * Like a git commit message - asks "Why did you make these changes?"
 * Optional but encouraged for thesis documentation.
 */
import React, { useState, useRef, useEffect } from 'react';

interface AssumptionCommitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCommit: (note: string | null) => void;
  isInitial: boolean;
  changedFields: string[];
}

const FIELD_LABELS: Record<string, string> = {
  revenue_growth: 'Revenue Growth',
  operating_margin: 'Operating Margin',
  terminal_growth: 'Terminal Growth',
  discount_rate: 'Discount Rate',
  projection_years: 'Projection Years',
  market_risk_premium: 'Market Risk Premium',
};

export function AssumptionCommitModal({
  isOpen,
  onClose,
  onCommit,
  isInitial,
  changedFields,
}: AssumptionCommitModalProps) {
  const [note, setNote] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus textarea when modal opens
  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen]);

  // Reset note when modal closes
  useEffect(() => {
    if (!isOpen) {
      setNote('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCommit(note.trim() || null);
  };

  const handleSkip = () => {
    onCommit(null);
  };

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        {/* Modal */}
        <div 
          className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h2 className="text-lg font-semibold text-gray-900">
              {isInitial ? '📝 Initial Analysis' : '📝 Document Changes'}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {isInitial 
                ? 'Starting a new investment thesis for this stock'
                : `You're updating ${changedFields.length} assumption${changedFields.length !== 1 ? 's' : ''}`
              }
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="p-6">
              {/* Changed fields summary (for updates) */}
              {!isInitial && changedFields.length > 0 && (
                <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                  <div className="text-xs font-medium text-blue-700 mb-1">Changed:</div>
                  <div className="flex flex-wrap gap-1">
                    {changedFields.map((field) => (
                      <span 
                        key={field}
                        className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded"
                      >
                        {FIELD_LABELS[field] || field}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Note input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Why? <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <textarea
                  ref={textareaRef}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder={isInitial 
                    ? "e.g., Starting position, using TTM data after Q4 earnings..."
                    : "e.g., Lowered growth estimate after guidance miss..."
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={3}
                />
                <p className="text-xs text-gray-500 mt-2">
                  💡 Notes help you remember why you made these assumptions later
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
              <button
                type="button"
                onClick={handleSkip}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Skip
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                {note.trim() ? 'Save & Run' : 'Run Valuation'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
