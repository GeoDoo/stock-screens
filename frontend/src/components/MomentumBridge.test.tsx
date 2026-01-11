import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MomentumBridge } from './MomentumBridge';

describe('MomentumBridge', () => {
  it('shows BUY when undervalued with uptrend', () => {
    render(
      <MomentumBridge
        vwmaTrend="uptrend"
        intrinsicValue={130}
        currentPrice={100}
      />
    );
    
    expect(screen.getByText('BUY')).toBeInTheDocument();
    expect(screen.getByText('Value + Momentum aligned')).toBeInTheDocument();
    expect(screen.getByText('↗ Uptrend')).toBeInTheDocument();
  });
  
  it('shows BUY when undervalued with flat trend', () => {
    render(
      <MomentumBridge
        vwmaTrend="flat"
        intrinsicValue={125}
        currentPrice={100}
      />
    );
    
    expect(screen.getByText('BUY')).toBeInTheDocument();
  });
  
  it('shows WAIT when undervalued with downtrend', () => {
    render(
      <MomentumBridge
        vwmaTrend="downtrend"
        intrinsicValue={130}
        currentPrice={100}
      />
    );
    
    expect(screen.getByText('WAIT')).toBeInTheDocument();
    expect(screen.getByText("Cheap but downtrend — don't catch falling knife")).toBeInTheDocument();
    expect(screen.getByText('↘ Downtrend')).toBeInTheDocument();
  });
  
  it('shows AVOID when overvalued', () => {
    render(
      <MomentumBridge
        vwmaTrend="uptrend"
        intrinsicValue={85}
        currentPrice={100}
      />
    );
    
    expect(screen.getByText('AVOID')).toBeInTheDocument();
    expect(screen.getByText('Overvalued')).toBeInTheDocument();
  });
  
  it('shows HOLD when fair value', () => {
    render(
      <MomentumBridge
        vwmaTrend="flat"
        intrinsicValue={105}
        currentPrice={100}
      />
    );
    
    expect(screen.getByText('HOLD')).toBeInTheDocument();
    expect(screen.getByText('Fair value — no strong action')).toBeInTheDocument();
  });
  
  it('shows placeholder when data is missing', () => {
    render(
      <MomentumBridge
        vwmaTrend={undefined}
        intrinsicValue={null}
        currentPrice={100}
      />
    );
    
    expect(screen.getByText('Requires valuation result and 200-day price history')).toBeInTheDocument();
  });
  
  it('displays margin of safety percentage', () => {
    render(
      <MomentumBridge
        vwmaTrend="uptrend"
        intrinsicValue={150}
        currentPrice={100}
      />
    );
    
    // 50% margin of safety
    expect(screen.getByText('50.0%')).toBeInTheDocument();
  });
  
  it('displays negative margin correctly', () => {
    render(
      <MomentumBridge
        vwmaTrend="uptrend"
        intrinsicValue={80}
        currentPrice={100}
      />
    );
    
    // -20% margin (overvalued)
    expect(screen.getByText('-20.0%')).toBeInTheDocument();
  });
});
