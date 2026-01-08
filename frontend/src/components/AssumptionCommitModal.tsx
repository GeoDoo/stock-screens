/**
 * Modal prompting user to add a note when running valuation.
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

  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen]);

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
    <div 
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-lg shadow-xl max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-medium text-gray-900">
            {isInitial ? 'Initial Analysis' : 'Document Changes'}
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            {isInitial 
              ? 'Starting a new investment thesis'
              : `Updating ${changedFields.length} assumption${changedFields.length !== 1 ? 's' : ''}`
            }
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="p-6">
            {/* Changed fields */}
            {!isInitial && changedFields.length > 0 && (
              <div className="mb-4 text-sm text-gray-500">
                <span className="text-gray-400">Changed: </span>
                {changedFields.map((field) => FIELD_LABELS[field] || field).join(', ')}
              </div>
            )}

            {/* Note input */}
            <div>
              <label className="block text-sm text-gray-600 mb-1.5">
                Why? <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                ref={textareaRef}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={isInitial 
                  ? "e.g., Starting position, using TTM data..."
                  : "e.g., Lowered growth after guidance miss..."
                }
                className="w-full px-3 py-2 border border-gray-200 rounded focus:border-gray-400 outline-none transition-colors resize-none text-sm"
                rows={3}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
            <button
              type="button"
              onClick={handleSkip}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              Skip
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm bg-gray-900 text-white rounded hover:bg-gray-800 transition-colors"
            >
              {note.trim() ? 'Save & Run' : 'Run Valuation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
