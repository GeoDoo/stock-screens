import { useState } from 'react';
import type { GrowthStage } from '../types';
import { GlossaryRef } from './GlossaryRef';

interface MultiStageGrowthProps {
  stages: GrowthStage[];
  onChange: (stages: GrowthStage[]) => void;
  terminalGrowth: number;
  disabled?: boolean;
}

// Pre-built templates for common scenarios
// Now includes economics (margin/capex/wc fading) for institutional-grade modeling
const TEMPLATES: Record<string, GrowthStage[]> = {
  highGrowthTech: [
    { name: 'Hypergrowth', years: 2, growth_rate: 0.30, operating_margin: 0.10, capex_ratio: 0.15, wc_ratio: 0.20 },
    { name: 'High Growth', years: 3, growth_rate: 0.20, operating_margin: 0.10, end_operating_margin: 0.18, capex_ratio: 0.12, wc_ratio: 0.18 },
    { name: 'Fade', years: 3, growth_rate: 0.20, end_growth_rate: 0.08, operating_margin: 0.18, end_operating_margin: 0.22, capex_ratio: 0.10, end_capex_ratio: 0.06, wc_ratio: 0.15 },
    { name: 'Mature', years: 2, growth_rate: 0.05, operating_margin: 0.22, capex_ratio: 0.06, wc_ratio: 0.12 },
  ],
  stableCompany: [
    { name: 'Current Growth', years: 3, growth_rate: 0.06, operating_margin: 0.15, capex_ratio: 0.05, wc_ratio: 0.10 },
    { name: 'Fade', years: 4, growth_rate: 0.06, end_growth_rate: 0.03, operating_margin: 0.15, capex_ratio: 0.05, wc_ratio: 0.10 },
    { name: 'Terminal Approach', years: 3, growth_rate: 0.03, operating_margin: 0.14, capex_ratio: 0.04, wc_ratio: 0.08 },
  ],
  turnaround: [
    { name: 'Recovery', years: 2, growth_rate: -0.05, end_growth_rate: 0.0, operating_margin: -0.05, end_operating_margin: 0.02, capex_ratio: 0.03, wc_ratio: 0.25 },
    { name: 'Stabilization', years: 2, growth_rate: 0.02, operating_margin: 0.02, end_operating_margin: 0.08, capex_ratio: 0.05, wc_ratio: 0.20, end_wc_ratio: 0.15 },
    { name: 'Growth', years: 3, growth_rate: 0.02, end_growth_rate: 0.08, operating_margin: 0.08, end_operating_margin: 0.12, capex_ratio: 0.06, wc_ratio: 0.15 },
    { name: 'Mature', years: 3, growth_rate: 0.05, operating_margin: 0.12, capex_ratio: 0.05, wc_ratio: 0.12 },
  ],
  // Operating Leverage: For capital-intensive businesses (airlines, manufacturing, semis)
  // Margins stay low during capacity fill, then jump when utilization hits threshold
  capitalIntensive: [
    { 
      name: 'Capacity Fill', 
      years: 4, 
      growth_rate: 0.12, 
      operating_margin: 0.06, 
      end_operating_margin: 0.22,
      margin_fade_mode: 'step',  // Step function instead of linear
      margin_step_at_year: 3,    // Margin jumps at year 3 when capacity fills
      capex_ratio: 0.15, 
      wc_ratio: 0.15 
    },
    { name: 'Mature Ops', years: 3, growth_rate: 0.08, end_growth_rate: 0.05, operating_margin: 0.22, capex_ratio: 0.08, wc_ratio: 0.12 },
    { name: 'Terminal', years: 3, growth_rate: 0.05, end_growth_rate: 0.03, operating_margin: 0.20, capex_ratio: 0.06, wc_ratio: 0.10 },
  ],
};

export function MultiStageGrowth({ stages, onChange, terminalGrowth, disabled }: MultiStageGrowthProps) {
  const [isExpanded, setIsExpanded] = useState(stages.length > 0);
  const [economicsExpanded, setEconomicsExpanded] = useState<Record<number, boolean>>({});

  const totalYears = stages.reduce((sum, s) => sum + s.years, 0);
  
  const toggleEconomics = (index: number) => {
    setEconomicsExpanded(prev => ({ ...prev, [index]: !prev[index] }));
  };
  
  // Check if any stage has economics defined
  const hasEconomics = (stage: GrowthStage): boolean => {
    return stage.operating_margin != null || stage.capex_ratio != null || stage.wc_ratio != null;
  };

  const addStage = () => {
    onChange([
      ...stages,
      { name: `Stage ${stages.length + 1}`, years: 3, growth_rate: 0.10 },
    ]);
  };

  const removeStage = (index: number) => {
    onChange(stages.filter((_, i) => i !== index));
  };

  const updateStage = (index: number, updates: Partial<GrowthStage>) => {
    onChange(stages.map((s, i) => (i === index ? { ...s, ...updates } : s)));
  };

  const applyTemplate = (templateName: keyof typeof TEMPLATES) => {
    onChange(TEMPLATES[templateName]);
    setIsExpanded(true);
  };

  const clearStages = () => {
    onChange([]);
  };

  // Calculate year-by-year growth rates for visualization
  const calculateSchedule = (): number[] => {
    const schedule: number[] = [];
    for (const stage of stages) {
      if (stage.end_growth_rate != null) {
        // Fade stage
        const step = (stage.end_growth_rate - stage.growth_rate) / Math.max(stage.years - 1, 1);
        for (let i = 0; i < stage.years; i++) {
          schedule.push(stage.growth_rate + step * i);
        }
      } else {
        // Constant rate stage
        for (let i = 0; i < stage.years; i++) {
          schedule.push(stage.growth_rate);
        }
      }
    }
    return schedule;
  };

  const schedule = calculateSchedule();

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium text-gray-700">
            Multi-Stage Growth <GlossaryRef id="multi-stage-growth" />
          </h4>
          {stages.length > 0 && (
            <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">
              Active ({totalYears} years)
            </span>
          )}
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-gray-500 hover:text-gray-700"
          disabled={disabled}
        >
          {isExpanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {isExpanded && (
        <>
          {/* Templates */}
          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-2">Quick templates:</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => applyTemplate('highGrowthTech')}
                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-white"
                disabled={disabled}
              >
                High Growth Tech
              </button>
              <button
                onClick={() => applyTemplate('stableCompany')}
                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-white"
                disabled={disabled}
              >
                Stable Company
              </button>
              <button
                onClick={() => applyTemplate('turnaround')}
                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-white"
                disabled={disabled}
              >
                Turnaround
              </button>
              <button
                onClick={() => applyTemplate('capitalIntensive')}
                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-white"
                disabled={disabled}
                title="Operating leverage: margins stay low until capacity fills, then jump"
              >
                Capital Intensive
              </button>
              {stages.length > 0 && (
                <button
                  onClick={clearStages}
                  className="text-xs px-2 py-1 text-red-600 border border-red-200 rounded hover:bg-red-50"
                  disabled={disabled}
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Stages List */}
          {stages.length > 0 && (
            <div className="space-y-3 mb-4">
              {stages.map((stage, index) => (
                <div key={index} className="bg-white border border-gray-200 rounded p-3">
                  {/* Main row: Name, Years, Growth, Fade, Actions */}
                  <div className="grid grid-cols-12 gap-2 items-center">
                    {/* Stage Name */}
                    <div className="col-span-3">
                      <input
                        type="text"
                        value={stage.name}
                        onChange={(e) => updateStage(index, { name: e.target.value })}
                        className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white"
                        placeholder="Stage name"
                        disabled={disabled}
                      />
                    </div>
                    
                    {/* Years */}
                    <div className="col-span-2">
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          min="1"
                          max="20"
                          value={stage.years}
                          onChange={(e) => updateStage(index, { years: parseInt(e.target.value) || 1 })}
                          className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                          disabled={disabled}
                        />
                        <span className="text-xs text-gray-500">yrs</span>
                      </div>
                    </div>
                    
                    {/* Growth Rate */}
                    <div className="col-span-2">
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          step="1"
                          value={(stage.growth_rate * 100).toFixed(2)}
                          onChange={(e) => updateStage(index, { growth_rate: parseFloat(e.target.value) / 100 || 0 })}
                          className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                          disabled={disabled}
                        />
                        <span className="text-xs text-gray-500">%</span>
                      </div>
                    </div>
                    
                    {/* Fade To (optional) */}
                    <div className="col-span-3">
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-gray-400">fade to</span>
                        <input
                          type="number"
                          step="1"
                          value={stage.end_growth_rate != null ? (stage.end_growth_rate * 100).toFixed(2) : ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            updateStage(index, { 
                              end_growth_rate: val ? parseFloat(val) / 100 : null 
                            });
                          }}
                          className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                          placeholder="—"
                          disabled={disabled}
                        />
                        <span className="text-xs text-gray-500">%</span>
                      </div>
                    </div>
                    
                    {/* Actions: Economics toggle + Remove */}
                    <div className="col-span-2 flex items-center justify-end gap-2">
                      <button
                        onClick={() => toggleEconomics(index)}
                        className={`text-xs px-1.5 py-0.5 rounded border ${
                          hasEconomics(stage) || economicsExpanded[index]
                            ? 'bg-blue-50 text-blue-600 border-blue-200'
                            : 'text-gray-400 border-gray-200 hover:text-gray-600'
                        }`}
                        disabled={disabled}
                        title="Toggle unit economics (margin, capex, working capital)"
                      >
                        {economicsExpanded[index] ? '▼' : '▶'} Econ
                      </button>
                      <button
                        onClick={() => removeStage(index)}
                        className="text-xs text-red-500 hover:text-red-700"
                        disabled={disabled}
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                  
                  {/* Economics panel (collapsible) */}
                  {economicsExpanded[index] && (
                    <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                      <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-2">Unit Economics (override global inputs for this stage)</p>
                      
                      {/* Operating Margin */}
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500 w-24">Op. Margin</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            step="1"
                            value={stage.operating_margin != null ? (stage.operating_margin * 100).toFixed(2) : ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              updateStage(index, { operating_margin: val ? parseFloat(val) / 100 : null });
                            }}
                            className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                            placeholder="—"
                            disabled={disabled}
                          />
                          <span className="text-xs text-gray-400">%</span>
                        </div>
                        <span className="text-xs text-gray-400">→</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            step="1"
                            value={stage.end_operating_margin != null ? (stage.end_operating_margin * 100).toFixed(2) : ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              updateStage(index, { end_operating_margin: val ? parseFloat(val) / 100 : null });
                            }}
                            className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                            placeholder="—"
                            disabled={disabled}
                          />
                          <span className="text-xs text-gray-400">%</span>
                        </div>
                      </div>
                      
                      {/* Margin Fade Mode (Operating Leverage) */}
                      {stage.operating_margin != null && stage.end_operating_margin != null && (
                        <div className="flex items-center gap-3 ml-24 pl-1">
                          <span className="text-xs text-gray-400">Mode:</span>
                          <select
                            value={stage.margin_fade_mode || 'linear'}
                            onChange={(e) => {
                              const mode = e.target.value as 'linear' | 'step';
                              updateStage(index, { 
                                margin_fade_mode: mode,
                                // Default step at year 2 when switching to step mode
                                margin_step_at_year: mode === 'step' ? (stage.margin_step_at_year || Math.ceil(stage.years / 2)) : null,
                              });
                            }}
                            className="text-xs border border-gray-200 rounded px-1 py-0.5 bg-white"
                            disabled={disabled}
                            title="Linear: smooth fade. Step: jump at specific year (operating leverage)"
                          >
                            <option value="linear">Linear Fade</option>
                            <option value="step">Step (Op. Leverage)</option>
                          </select>
                          {stage.margin_fade_mode === 'step' && (
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-gray-400">Jump at year:</span>
                              <input
                                type="number"
                                min="1"
                                max={stage.years}
                                value={stage.margin_step_at_year || Math.ceil(stage.years / 2)}
                                onChange={(e) => {
                                  const val = parseInt(e.target.value);
                                  if (val >= 1 && val <= stage.years) {
                                    updateStage(index, { margin_step_at_year: val });
                                  }
                                }}
                                className="w-12 text-xs border border-gray-200 rounded px-1 py-0.5 bg-white text-center"
                                disabled={disabled}
                              />
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* CapEx Ratio */}
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500 w-24">CapEx Ratio</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            step="1"
                            value={stage.capex_ratio != null ? (stage.capex_ratio * 100).toFixed(2) : ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              updateStage(index, { capex_ratio: val ? parseFloat(val) / 100 : null });
                            }}
                            className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                            placeholder="—"
                            disabled={disabled}
                          />
                          <span className="text-xs text-gray-400">%</span>
                        </div>
                        <span className="text-xs text-gray-400">→</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            step="1"
                            value={stage.end_capex_ratio != null ? (stage.end_capex_ratio * 100).toFixed(2) : ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              updateStage(index, { end_capex_ratio: val ? parseFloat(val) / 100 : null });
                            }}
                            className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                            placeholder="—"
                            disabled={disabled}
                          />
                          <span className="text-xs text-gray-400">%</span>
                        </div>
                      </div>
                      
                      {/* Working Capital Ratio */}
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500 w-24">WC Ratio</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            step="1"
                            value={stage.wc_ratio != null ? (stage.wc_ratio * 100).toFixed(2) : ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              updateStage(index, { wc_ratio: val ? parseFloat(val) / 100 : null });
                            }}
                            className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                            placeholder="—"
                            disabled={disabled}
                          />
                          <span className="text-xs text-gray-400">%</span>
                        </div>
                        <span className="text-xs text-gray-400">→</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            step="1"
                            value={stage.end_wc_ratio != null ? (stage.end_wc_ratio * 100).toFixed(2) : ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              updateStage(index, { end_wc_ratio: val ? parseFloat(val) / 100 : null });
                            }}
                            className="w-14 text-sm border border-gray-200 rounded px-2 py-1 bg-white text-center"
                            placeholder="—"
                            disabled={disabled}
                          />
                          <span className="text-xs text-gray-400">%</span>
                        </div>
                      </div>
                      
                      <p className="text-[10px] text-gray-400 mt-1">
                        Leave blank to use global inputs. Set start→end for fading.
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Add Stage Button */}
          <button
            onClick={addStage}
            className="text-sm text-gray-600 hover:text-gray-800 border border-dashed border-gray-300 rounded w-full py-2 hover:bg-white"
            disabled={disabled}
          >
            + Add Stage
          </button>

          {/* Growth Schedule Preview */}
          {schedule.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-500 mb-2">Growth schedule preview:</p>
              <div className="flex items-end gap-1 h-16">
                {schedule.map((rate, i) => {
                  const height = Math.max(10, Math.min(100, (rate + 0.1) * 200));
                  const isNegative = rate < 0;
                  return (
                    <div
                      key={i}
                      className="flex-1 relative group"
                      style={{ height: '100%' }}
                    >
                      <div
                        className={`absolute bottom-0 w-full rounded-t ${isNegative ? 'bg-red-300' : 'bg-emerald-300'}`}
                        style={{ height: `${height}%` }}
                      />
                      <div className="absolute -top-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 text-xs bg-gray-800 text-white px-1 rounded whitespace-nowrap">
                        Y{i + 1}: {(rate * 100).toFixed(2)}%
                      </div>
                    </div>
                  );
                })}
                {/* Terminal */}
                <div className="flex-1 relative group" style={{ height: '100%' }}>
                  <div
                    className="absolute bottom-0 w-full rounded-t bg-gray-300"
                    style={{ height: `${Math.max(10, Math.min(100, (terminalGrowth + 0.1) * 200))}%` }}
                  />
                  <div className="absolute -top-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 text-xs bg-gray-800 text-white px-1 rounded whitespace-nowrap">
                    Terminal: {(terminalGrowth * 100).toFixed(2)}%
                  </div>
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Year 1</span>
                <span>Year {totalYears} + Terminal</span>
              </div>
            </div>
          )}

          {/* Info text when no stages */}
          {stages.length === 0 && (
            <p className="text-xs text-gray-500 mt-2">
              Add stages to use variable growth rates instead of constant growth.
              If no stages defined, uses single growth rate from above.
            </p>
          )}
        </>
      )}

      {!isExpanded && stages.length === 0 && (
        <p className="text-xs text-gray-500">
          Click expand to define growth phases (optional)
        </p>
      )}
    </div>
  );
}
