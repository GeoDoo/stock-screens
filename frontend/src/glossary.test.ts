import { describe, it, expect } from 'vitest'
import { glossaryTerms, glossaryMap, getGlossaryTerm } from './glossary'
import type { GlossaryTerm } from './glossary'

describe('glossaryTerms', () => {
  it('contains multiple terms', () => {
    expect(glossaryTerms.length).toBeGreaterThan(30)
  })

  it('each term has required fields', () => {
    glossaryTerms.forEach(term => {
      expect(term.id).toBeDefined()
      expect(term.term).toBeDefined()
      expect(term.definition).toBeDefined()
      expect(term.investopediaUrl).toBeDefined()
    })
  })

  it('all IDs are unique', () => {
    const ids = glossaryTerms.map(t => t.id)
    const uniqueIds = new Set(ids)
    expect(uniqueIds.size).toBe(ids.length)
  })

  it('all Investopedia URLs are valid', () => {
    glossaryTerms.forEach(term => {
      expect(term.investopediaUrl).toMatch(/^https:\/\/www\.investopedia\.com\//)
    })
  })

  it('contains key financial terms', () => {
    const termNames = glossaryTerms.map(t => t.term)
    expect(termNames).toContain('DCF')
    expect(termNames).toContain('WACC')
    expect(termNames).toContain('Beta')
    expect(termNames).toContain('RSI')
    expect(termNames).toContain('MACD')
  })
})

describe('glossaryMap', () => {
  it('is a Map with same size as terms array', () => {
    expect(glossaryMap.size).toBe(glossaryTerms.length)
  })

  it('maps id to term correctly', () => {
    const dcf = glossaryMap.get('dcf')
    expect(dcf).toBeDefined()
    expect(dcf?.term).toBe('DCF')
    expect(dcf?.fullName).toBe('Discounted Cash Flow')
  })

  it('returns undefined for unknown id', () => {
    expect(glossaryMap.get('unknown-term')).toBeUndefined()
  })
})

describe('getGlossaryTerm', () => {
  it('returns term by id', () => {
    const wacc = getGlossaryTerm('wacc')
    expect(wacc).toBeDefined()
    expect(wacc?.term).toBe('WACC')
    expect(wacc?.fullName).toBe('Weighted Average Cost of Capital')
  })

  it('returns undefined for unknown id', () => {
    expect(getGlossaryTerm('nonexistent')).toBeUndefined()
  })

  it('returns term with all properties', () => {
    const beta = getGlossaryTerm('beta')
    expect(beta).toBeDefined()
    expect(beta?.id).toBe('beta')
    expect(beta?.term).toBe('Beta')
    expect(beta?.definition).toBeTruthy()
    expect(beta?.investopediaUrl).toContain('investopedia.com')
  })

  it('handles terms with fullName', () => {
    const fcf = getGlossaryTerm('fcf')
    expect(fcf?.fullName).toBe('Free Cash Flow')
  })

  it('handles terms without fullName', () => {
    const beta = getGlossaryTerm('beta')
    expect(beta?.fullName).toBeUndefined()
  })
})

describe('term content quality', () => {
  it('definitions are meaningful (not empty or too short)', () => {
    glossaryTerms.forEach(term => {
      expect(term.definition.length).toBeGreaterThan(50)
    })
  })

  it('IDs use kebab-case', () => {
    glossaryTerms.forEach(term => {
      expect(term.id).toMatch(/^[a-z0-9-]+$/)
    })
  })

  it('terms are capitalized properly', () => {
    glossaryTerms.forEach(term => {
      // First character should be uppercase or a letter
      expect(term.term[0]).toMatch(/[A-Z]/)
    })
  })
})


