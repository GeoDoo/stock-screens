import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DiscountRateModal } from './DiscountRateModal'

describe('DiscountRateModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSubmit: vi.fn(),
    onSkip: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not render when closed', () => {
    render(<DiscountRateModal {...defaultProps} isOpen={false} />)
    expect(screen.queryByText(/Discount Rate Required/i)).not.toBeInTheDocument()
  })

  it('renders when open', () => {
    render(<DiscountRateModal {...defaultProps} />)
    expect(screen.getByText(/Discount Rate Required/i)).toBeInTheDocument()
  })

  it('displays explanation message', () => {
    render(<DiscountRateModal {...defaultProps} />)
    expect(screen.getByText(/WACC cannot be calculated/i)).toBeInTheDocument()
  })

  it('has a discount rate input field', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('type', 'number')
  })

  it('has a placeholder with hint', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    expect(input).toHaveAttribute('placeholder', 'e.g., 10')
  })

  it('calls onSubmit with rate value when Continue is clicked', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    fireEvent.change(input, { target: { value: '12' } })
    
    const continueBtn = screen.getByRole('button', { name: /Continue/i })
    fireEvent.click(continueBtn)
    
    expect(defaultProps.onSubmit).toHaveBeenCalledWith(12)
  })

  it('disables Continue button when no rate entered', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const continueBtn = screen.getByRole('button', { name: /Continue/i })
    expect(continueBtn).toBeDisabled()
  })

  it('enables Continue button when rate is entered', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    fireEvent.change(input, { target: { value: '10' } })
    
    const continueBtn = screen.getByRole('button', { name: /Continue/i })
    expect(continueBtn).not.toBeDisabled()
  })

  it('calls onSkip when Skip DCF is clicked', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const skipBtn = screen.getByRole('button', { name: /Skip DCF/i })
    fireEvent.click(skipBtn)
    
    expect(defaultProps.onSkip).toHaveBeenCalled()
  })

  it('calls onClose when backdrop is clicked', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const backdrop = screen.getByTestId('modal-backdrop')
    fireEvent.click(backdrop)
    
    expect(defaultProps.onClose).toHaveBeenCalled()
  })

  it('does not close when modal content is clicked', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const modalContent = screen.getByTestId('modal-content')
    fireEvent.click(modalContent)
    
    expect(defaultProps.onClose).not.toHaveBeenCalled()
  })

  it('validates rate is positive', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    fireEvent.change(input, { target: { value: '-5' } })
    
    const continueBtn = screen.getByRole('button', { name: /Continue/i })
    expect(continueBtn).toBeDisabled()
  })

  it('validates rate is reasonable (under 50%)', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    fireEvent.change(input, { target: { value: '60' } })
    
    // Should show warning but still allow submission
    expect(screen.getByText(/unusually high/i)).toBeInTheDocument()
  })

  it('clears input when modal reopens', () => {
    const { rerender } = render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    fireEvent.change(input, { target: { value: '12' } })
    
    // Close and reopen
    rerender(<DiscountRateModal {...defaultProps} isOpen={false} />)
    rerender(<DiscountRateModal {...defaultProps} isOpen={true} />)
    
    const newInput = screen.getByLabelText(/Your Discount Rate/i)
    expect(newInput).toHaveValue(null)
  })

  it('displays error message in red for visibility', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const errorMsg = screen.getByText(/WACC cannot be calculated/i)
    expect(errorMsg).toHaveClass('text-red-600')
  })

  it('prevents negative input with min attribute', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    expect(input).toHaveAttribute('min', '0')
  })

  it('allows decimal input with step attribute', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    expect(input).toHaveAttribute('step', '0.1')
  })

  it('disables Continue for zero rate', () => {
    render(<DiscountRateModal {...defaultProps} />)
    const input = screen.getByLabelText(/Your Discount Rate/i)
    fireEvent.change(input, { target: { value: '0' } })
    
    const continueBtn = screen.getByRole('button', { name: /Continue/i })
    expect(continueBtn).toBeDisabled()
  })
})

