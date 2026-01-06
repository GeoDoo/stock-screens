import { describe, it, expect } from 'vitest'
import { formatCurrency, formatPercent, formatNumber, formatShareCount } from './utils'

describe('formatCurrency', () => {
  it('returns em dash for null', () => {
    expect(formatCurrency(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatCurrency(undefined as unknown as number | null)).toBe('—')
  })

  it('formats trillions correctly', () => {
    expect(formatCurrency(1500000000000)).toBe('$1.50T')
    expect(formatCurrency(3000000000000)).toBe('$3.00T')
  })

  it('formats billions correctly', () => {
    expect(formatCurrency(1500000000)).toBe('$1.50B')
    expect(formatCurrency(5000000000)).toBe('$5.00B')
  })

  it('formats millions correctly', () => {
    expect(formatCurrency(1500000)).toBe('$1.50M')
    expect(formatCurrency(500000000)).toBe('$500.00M')
  })

  it('formats thousands correctly', () => {
    expect(formatCurrency(1500)).toBe('$1.50K')
    expect(formatCurrency(5000)).toBe('$5.00K')
  })

  it('formats small values with commas', () => {
    expect(formatCurrency(999)).toBe('$999.00')
    expect(formatCurrency(50.5)).toBe('$50.50')
  })

  it('handles negative values', () => {
    expect(formatCurrency(-1500000000)).toBe('$-1.50B')
    expect(formatCurrency(-50000)).toBe('$-50.00K')
  })

  it('handles zero', () => {
    expect(formatCurrency(0)).toBe('$0.00')
  })
})

describe('formatPercent', () => {
  it('returns em dash for null', () => {
    expect(formatPercent(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatPercent(undefined as unknown as number | null)).toBe('—')
  })

  it('converts decimal to percentage', () => {
    expect(formatPercent(0.10)).toBe('10.00%')
    expect(formatPercent(0.0523)).toBe('5.23%')
  })

  it('handles values over 100%', () => {
    expect(formatPercent(1.5)).toBe('150.00%')
  })

  it('handles zero', () => {
    expect(formatPercent(0)).toBe('0.00%')
  })

  it('handles negative values', () => {
    expect(formatPercent(-0.05)).toBe('-5.00%')
  })
})

describe('formatNumber', () => {
  it('returns em dash for null', () => {
    expect(formatNumber(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatNumber(undefined as unknown as number | null)).toBe('—')
  })

  it('formats with default 2 decimals', () => {
    expect(formatNumber(1.256)).toBe('1.26')
    expect(formatNumber(100)).toBe('100.00')
  })

  it('respects custom decimal places', () => {
    expect(formatNumber(1.25678, 4)).toBe('1.2568')
    expect(formatNumber(100, 0)).toBe('100')
  })

  it('handles negative values', () => {
    expect(formatNumber(-5.5)).toBe('-5.50')
  })

  it('handles zero', () => {
    expect(formatNumber(0)).toBe('0.00')
  })
})

describe('formatShareCount', () => {
  it('returns em dash for null', () => {
    expect(formatShareCount(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatShareCount(undefined as unknown as number | null)).toBe('—')
  })

  it('formats billions correctly', () => {
    expect(formatShareCount(15744231000)).toBe('15.74B')
    expect(formatShareCount(1000000000)).toBe('1.00B')
  })

  it('formats millions correctly', () => {
    expect(formatShareCount(500000000)).toBe('500.00M')
    expect(formatShareCount(1500000)).toBe('1.50M')
  })

  it('formats thousands correctly', () => {
    expect(formatShareCount(50000)).toBe('50K')
    expect(formatShareCount(1500)).toBe('2K') // rounds to nearest
  })

  it('formats small values with commas', () => {
    expect(formatShareCount(999)).toBe('999')
    expect(formatShareCount(500)).toBe('500')
  })

  it('handles zero', () => {
    expect(formatShareCount(0)).toBe('0')
  })
})

