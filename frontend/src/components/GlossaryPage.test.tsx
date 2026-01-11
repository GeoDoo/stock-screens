import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { GlossaryPage } from './GlossaryPage'

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <MemoryRouter>
      {component}
    </MemoryRouter>
  )
}

describe('GlossaryPage', () => {
  it('renders the glossary title', () => {
    renderWithRouter(<GlossaryPage />)
    
    // Use role selector to get the h1 heading specifically
    expect(screen.getByRole('heading', { level: 1, name: 'Glossary' })).toBeInTheDocument()
  })

  it('displays all glossary terms', () => {
    renderWithRouter(<GlossaryPage />)
    
    // Check for some key terms
    expect(screen.getByText('DCF')).toBeInTheDocument()
    expect(screen.getByText('WACC')).toBeInTheDocument()
    expect(screen.getByText('Beta')).toBeInTheDocument()
    expect(screen.getByText('RSI')).toBeInTheDocument()
  })

  it('shows full names for terms that have them', () => {
    renderWithRouter(<GlossaryPage />)
    
    expect(screen.getByText(/Discounted Cash Flow/)).toBeInTheDocument()
    // Use getAllByText since WACC appears in multiple places (term and CEO efficiency definition)
    expect(screen.getAllByText(/Weighted Average Cost of Capital/).length).toBeGreaterThan(0)
  })

  it('displays definitions for each term', () => {
    renderWithRouter(<GlossaryPage />)
    
    // Check that definitions are rendered (partial text match)
    expect(screen.getByText(/valuation method that estimates the present value/)).toBeInTheDocument()
  })

  it('includes Investopedia links for each term', () => {
    renderWithRouter(<GlossaryPage />)
    
    const learnMoreLinks = screen.getAllByText('Learn more →')
    expect(learnMoreLinks.length).toBeGreaterThan(0)
    
    // Check that links have correct attributes
    const firstLink = learnMoreLinks[0].closest('a')
    expect(firstLink).toHaveAttribute('href')
    expect(firstLink?.getAttribute('href')).toContain('investopedia.com')
    expect(firstLink).toHaveAttribute('target', '_blank')
    expect(firstLink).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('renders terms with correct anchor IDs for navigation', () => {
    renderWithRouter(<GlossaryPage />)
    
    // Check that terms have id attributes for anchor navigation
    const dcfSection = document.getElementById('dcf')
    expect(dcfSection).toBeInTheDocument()
    
    const waccSection = document.getElementById('wacc')
    expect(waccSection).toBeInTheDocument()
  })

  it('organizes terms alphabetically', () => {
    renderWithRouter(<GlossaryPage />)
    
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

  it('renders alphabet navigation', () => {
    renderWithRouter(<GlossaryPage />)
    
    // The alphabet navigation should be present
    const letterLinks = screen.getAllByRole('link')
    // Should have Investopedia links plus alphabet links
    expect(letterLinks.length).toBeGreaterThan(26) // More than just alphabet
  })
})

