import React, { useState } from 'react';
import { BENCHMARK_RECIPES } from '../data/benchmarkData';
import type { RecipeEntry } from '../types/benchmark';
import { VendorLogo } from './VendorLogo';

interface RadarComparisonProps {
  onSelectModel: (recipe: RecipeEntry) => void;
}

export const RadarComparison: React.FC<RadarComparisonProps> = ({ onSelectModel: _onSelectModel }) => {
  // Default select top 3 models: Gemini 3.6, HY3, Luna
  const [selectedIds, setSelectedIds] = useState<string[]>([
    'remis.google-ai-studio.gemini-3-6-flash.high',
    'remis.openrouter.tencent-hy3.high',
    'remis.openrouter.gpt-5-6-luna.high',
  ]);

  const toggleModel = (id: string) => {
    if (selectedIds.includes(id)) {
      if (selectedIds.length > 1) {
        setSelectedIds(selectedIds.filter((item) => item !== id));
      }
    } else {
      if (selectedIds.length < 4) {
        setSelectedIds([...selectedIds, id]);
      }
    }
  };

  const dimensions: Array<{ key: keyof RecipeEntry['components']; label: string; max: number }> = [
    { key: 'semantic_fidelity', label: 'Semantic Fidelity (30%)', max: 100 },
    { key: 'constraint_integrity', label: 'Constraint Integrity (20%)', max: 100 },
    { key: 'cross_context_consistency', label: 'Cross-Context (15%)', max: 100 },
    { key: 'repair_precision', label: 'Repair Restraint (15%)', max: 100 },
    { key: 'style_voice', label: 'Style & Voice (10%)', max: 100 },
    { key: 'repeatability', label: 'Repeatability (10%)', max: 100 },
  ];

  const colors = ['#E5A93C', '#3B82F6', '#10B981', '#8B5CF6'];

  // Radar geometry
  const size = 420;
  const center = size / 2;
  const radius = size * 0.38;
  const numSides = dimensions.length;

  const getCoordinates = (index: number, value: number) => {
    const angle = (Math.PI * 2 * index) / numSides - Math.PI / 2;
    const r = (value / 100) * radius;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  const selectedRecipes = selectedIds
    .map((id) => BENCHMARK_RECIPES.find((r) => r.id === id))
    .filter(Boolean) as RecipeEntry[];

  return (
    <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)', marginBottom: '32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>
              6-Dimension Capability Radar Comparison
            </h2>
            <span className="badge badge-gold">Issue #6 Metric Formulation</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Compare models across semantic fidelity, hard constraint integrity, repair restraint, and repeatability.
          </p>
        </div>
      </div>

      {/* Main Container: Selector + SVG */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', alignItems: 'center' }}>
        {/* Model Selector Checkboxes */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '12px' }}>
            Select up to 4 models to compare side-by-side:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {BENCHMARK_RECIPES.map((recipe) => {
              const isSelected = selectedIds.includes(recipe.id);
              const colorIndex = selectedIds.indexOf(recipe.id);
              const color = isSelected ? colors[colorIndex % colors.length] : 'var(--text-muted)';

              return (
                <div
                  key={recipe.id}
                  onClick={() => toggleModel(recipe.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: isSelected ? 'var(--bg-card-elevated)' : 'transparent',
                    border: isSelected ? `1.5px solid ${color}` : '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span
                      style={{
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        backgroundColor: isSelected ? color : 'var(--border-medium)',
                      }}
                    />
                    <VendorLogo
                      signals={[recipe.provider_icon, recipe.model_id, recipe.label, recipe.provider]}
                      size={18}
                    />
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: isSelected ? 700 : 500, color: 'var(--text-primary)' }}>
                        {recipe.label}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{recipe.provider}</div>
                    </div>
                  </div>

                  <span className="mono" style={{ fontSize: '13px', fontWeight: 700, color: isSelected ? color : 'var(--text-secondary)' }}>
                    {recipe.pilot_score.toFixed(1)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* SVG Radar Chart */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%' }}>
          <svg viewBox={`0 0 ${size} ${size}`} style={{ width: '100%', maxWidth: '380px', height: 'auto', overflow: 'visible' }}>
            {/* Background Web Polygons */}
            {[20, 40, 60, 80, 100].map((level) => {
              const polyPoints = dimensions
                .map((_, i) => {
                  const { x, y } = getCoordinates(i, level);
                  return `${x},${y}`;
                })
                .join(' ');

              return (
                <polygon
                  key={level}
                  points={polyPoints}
                  fill={level === 100 ? 'var(--bg-card-elevated)' : 'none'}
                  stroke="var(--border-subtle)"
                  strokeWidth="1"
                />
              );
            })}

            {/* Axis Lines & Labels */}
            {dimensions.map((dim, i) => {
              const { x: endX, y: endY } = getCoordinates(i, 100);
              const labelCoord = getCoordinates(i, 118);

              return (
                <g key={dim.key}>
                  <line x1={center} y1={center} x2={endX} y2={endY} stroke="var(--border-subtle)" strokeWidth="1" />
                  <text
                    x={labelCoord.x}
                    y={labelCoord.y + 4}
                    fontSize="10"
                    fontWeight="600"
                    fill="var(--text-secondary)"
                    textAnchor={labelCoord.x > center + 10 ? 'start' : labelCoord.x < center - 10 ? 'end' : 'middle'}
                  >
                    {dim.label.split('(')[0]}
                  </text>
                </g>
              );
            })}

            {/* Model Radar Polygons */}
            {selectedRecipes.map((recipe, index) => {
              const color = colors[index % colors.length];
              const polyPoints = dimensions
                .map((dim, i) => {
                  const val = recipe.components[dim.key];
                  const { x, y } = getCoordinates(i, val);
                  return `${x},${y}`;
                })
                .join(' ');

              return (
                <g key={recipe.id}>
                  <polygon
                    points={polyPoints}
                    fill={color}
                    fillOpacity="0.18"
                    stroke={color}
                    strokeWidth="2.5"
                  />
                  {dimensions.map((dim, i) => {
                    const val = recipe.components[dim.key];
                    const { x, y } = getCoordinates(i, val);
                    return <circle key={dim.key} cx={x} cy={y} r="3.5" fill={color} stroke="#ffffff" strokeWidth="1.5" />;
                  })}
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
};
