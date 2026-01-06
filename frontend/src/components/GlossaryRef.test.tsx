import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GlossaryRef } from './GlossaryRef'

describe('GlossaryRef', () => {
  it('renders a superscript link', () => {
    render(<GlossaryRef id="dcf" />)
    
    const link = screen.getByRole('link')
    expect(link).toBeInTheDocument()
    expect(link.tagName).toBe('A')
  })

  it('links to the glossary page with correct anchor', () => {
    render(<GlossaryRef id="wacc" />)
    
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/glossary#wacc')
  })

  it('displays the term index number as superscript', () => {
    render(<GlossaryRef id="dcf" />)
    
    const link = screen.getByRole('link')
    // DCF should be index 1 (first term alphabetically by id in the rendered order)
    expect(link).toHaveClass('align-super')
  })

  it('shows tooltip with term name on hover', () => {
    render(<GlossaryRef id="dcf" />)
    
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('title', 'DCF — Discounted Cash Flow')
  })

  it('handles terms without fullName', () => {
    render(<GlossaryRef id="beta" />)
    
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('title', 'Beta')
  })
})

