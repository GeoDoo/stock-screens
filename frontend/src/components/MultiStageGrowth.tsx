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
const TEMPLATES = {
  highGrowthTech: [
    { name: 'Hypergrowth', years: 2, growth_rate: 0.30 },
    { name: 'High Growth', years: 3, growth_rate: 0.20 },
    { name: 'Fade', years: 3, growth_rate: 0.20, end_growth_rate: 0.08 },
    { name: 'Mature', years: 2, growth_rate: 0.05 },
  ],
  stableCompany: [
    { name: 'Current Growth', years: 3, growth_rate: 0.06 },
    { name: 'Fade', years: 4, growth_rate: 0.06, end_growth_rate: 0.03 },
    { name: 'Terminal Approach', years: 3, growth_rate: 0.03 },
  ],
  turnaround: [
    { name: 'Recovery', years: 2, growth_rate: -0.05, end_growth_rate: 0.0 },
    { name: 'Stabilization', years: 2, growth_rate: 0.02 },
    { name: 'Growth', years: 3, growth_rate: 0.02, end_growth_rate: 0.08 },
    { name: 'Mature', years: 3, growth_rate: 0.05 },
  ],
};

export function MultiStageGrowth({ stages, onChange, terminalGrowth, disabled }: MultiStageGrowthProps) {
  const [isExpanded, setIsExpanded] = useState(stages.length > 0);

  const totalYears = stages.reduce((sum, s) => sum + s.years, 0);

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
                          value={(stage.growth_rate * 100).toFixed(0)}
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
                          value={stage.end_growth_rate != null ? (stage.end_growth_rate * 100).toFixed(0) : ''}
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
                    
                    {/* Remove Button */}
                    <div className="col-span-2 text-right">
                      <button
                        onClick={() => removeStage(index)}
                        className="text-xs text-red-500 hover:text-red-700"
                        disabled={disabled}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
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
                        Y{i + 1}: {(rate * 100).toFixed(0)}%
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
                    Terminal: {(terminalGrowth * 100).toFixed(0)}%
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
