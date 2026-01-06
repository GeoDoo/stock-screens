import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GlossaryPage } from './GlossaryPage'

describe('GlossaryPage', () => {
  it('renders the glossary title', () => {
    render(<GlossaryPage />)
    
    expect(screen.getByText('Glossary')).toBeInTheDocument()
  })

  it('displays all glossary terms', () => {
    render(<GlossaryPage />)
    
    // Check for some key terms
    expect(screen.getByText('DCF')).toBeInTheDocument()
    expect(screen.getByText('WACC')).toBeInTheDocument()
    expect(screen.getByText('Beta')).toBeInTheDocument()
    expect(screen.getByText('RSI')).toBeInTheDocument()
  })

  it('shows full names for terms that have them', () => {
    render(<GlossaryPage />)
    
    expect(screen.getByText(/Discounted Cash Flow/)).toBeInTheDocument()
    expect(screen.getByText(/Weighted Average Cost of Capital/)).toBeInTheDocument()
  })

  it('displays definitions for each term', () => {
    render(<GlossaryPage />)
    
    // Check that definitions are rendered (partial text match)
    expect(screen.getByText(/valuation method that estimates the present value/)).toBeInTheDocument()
  })

  it('includes Investopedia links for each term', () => {
    render(<GlossaryPage />)
    
    const investopediaLinks = screen.getAllByText('Learn more on Investopedia →')
    expect(investopediaLinks.length).toBeGreaterThan(0)
    
    // Check that links have correct attributes
    const firstLink = investopediaLinks[0].closest('a')
    expect(firstLink).toHaveAttribute('href')
    expect(firstLink?.getAttribute('href')).toContain('investopedia.com')
    expect(firstLink).toHaveAttribute('target', '_blank')
    expect(firstLink).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('renders terms with correct anchor IDs for navigation', () => {
    render(<GlossaryPage />)
    
    // Check that terms have id attributes for anchor navigation
    const dcfSection = document.getElementById('dcf')
    expect(dcfSection).toBeInTheDocument()
    
    const waccSection = document.getElementById('wacc')
    expect(waccSection).toBeInTheDocument()
  })

  it('organizes terms alphabetically', () => {
    render(<GlossaryPage />)
    
    const terms = screen.getAllByRole('heading', { level: 3 })
    // Extract just the term name (before the dash)
    const termTexts = terms.map(t => {
      const text = t.textContent || ''
      return text.split('—')[0].trim()
    })
    
    // Beta should come before DCF alphabetically
    const betaIndex = termTexts.findIndex(t => t === 'Beta')
    const dcfIndex = termTexts.findIndex(t => t === 'DCF')
    
    expect(betaIndex).toBeGreaterThan(-1) // Beta exists
    expect(dcfIndex).toBeGreaterThan(-1)  // DCF exists
    expect(betaIndex).toBeLessThan(dcfIndex)
  })

  it('includes a back to app link', () => {
    render(<GlossaryPage />)
    
    // There are two "Back to App" links (header and footer)
    const backLinks = screen.getAllByText(/Back to App/i)
    expect(backLinks.length).toBeGreaterThanOrEqual(1)
    
    // Check the first one has correct href
    const firstBackLink = backLinks[0].closest('a')
    expect(firstBackLink).toHaveAttribute('href', '/')
  })
})

