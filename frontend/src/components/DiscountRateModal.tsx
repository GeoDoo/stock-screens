import { useState, useEffect } from 'react'

interface DiscountRateModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (rate: number) => void
  onSkip: () => void
}

export function DiscountRateModal({ isOpen, onClose, onSubmit, onSkip }: DiscountRateModalProps) {
  const [rate, setRate] = useState('')
  const [showWarning, setShowWarning] = useState(false)

  // Clear input when modal reopens
  useEffect(() => {
    if (isOpen) {
      setRate('')
      setShowWarning(false)
    }
  }, [isOpen])

  // Validate rate
  const rateValue = parseFloat(rate)
  const isValidRate = !isNaN(rateValue) && rateValue > 0
  const isUnusuallyHigh = isValidRate && rateValue > 50

  useEffect(() => {
    setShowWarning(isUnusuallyHigh)
  }, [isUnusuallyHigh])

  const handleSubmit = () => {
    if (isValidRate) {
      onSubmit(rateValue)
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      data-testid="modal-backdrop"
      onClick={handleBackdropClick}
    >
      <div 
        className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6"
        data-testid="modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Discount Rate Required
        </h2>
        
        <p className="text-gray-600 mb-6">
          WACC cannot be calculated due to missing data (e.g., Beta, Cost of Debt). 
          Please provide your own discount rate to continue with DCF valuation, or skip DCF analysis.
        </p>

        <div className="mb-4">
          <label htmlFor="discount-rate" className="block text-sm font-medium text-gray-700 mb-2">
            Your Discount Rate (%)
          </label>
          <input
            id="discount-rate"
            type="number"
            value={rate}
            onChange={(e) => setRate(e.target.value)}
            placeholder="e.g., 10"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-500"
          />
          {showWarning && (
            <p className="mt-2 text-amber-600 text-sm">
              This rate seems unusually high. Typical rates are 8-15%.
            </p>
          )}
        </div>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onSkip}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            Skip DCF
          </button>
          <button
            onClick={handleSubmit}
            disabled={!isValidRate}
            className="px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}

