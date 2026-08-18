import React, { useState } from 'react';
import { BENCHMARK_RECIPES } from '../data/benchmarkData';
import type { RecipeEntry } from '../types/benchmark';
import { Zap, DollarSign, Brain, Info } from 'lucide-react';

interface ScatterChartProps {
  onSelectModel: (recipe: RecipeEntry) => void;
}

type ChartMetric = 'latency' | 'cost' | 'reasoning';

export const ScatterChart: React.FC<ScatterChartProps> = ({ onSelectModel }) => {
  const [metric, setMetric] = useState<ChartMetric>('latency');
  const [isLogScale, setIsLogScale] = useState(false);
  const [hoveredRecipe, setHoveredRecipe] = useState<RecipeEntry | null>(null);

  // SVG dimensions
  const width = 860;
  const height = 460;
  const padding = { top: 40, right: 60, bottom: 60, left: 70 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  // Extract X & Y values
  const points = BENCHMARK_RECIPES.map((recipe) => {
    let xVal = 0;
    if (metric === 'latency') {
      xVal = recipe.telemetry.elapsed_seconds;
    } else if (metric === 'cost') {
      xVal = recipe.telemetry.cost_usd === 'free' ? 0.001 : (recipe.telemetry.cost_usd as number);
    } else if (metric === 'reasoning') {
      xVal = Math.max(100, recipe.telemetry.reasoning_tokens);
    }
    const yVal = recipe.pilot_score;
    return { recipe, xVal, yVal };
  });

  // Calculate scales
  const yMin = 30;
  const yMax = 95;

  let xMin = Math.min(...points.map((p) => p.xVal));
  let xMax = Math.max(...points.map((p) => p.xVal));

  if (metric === 'latency') {
    xMin = isLogScale ? 80 : 0;
    xMax = isLogScale ? 3000 : 2600;
  } else if (metric === 'cost') {
    xMin = isLogScale ? 0.001 : 0;
    xMax = isLogScale ? 0.6 : 0.45;
  } else if (metric === 'reasoning') {
    xMin = isLogScale ? 100 : 0;
    xMax = isLogScale ? 120000 : 110000;
  }

  const getX = (val: number) => {
    if (isLogScale) {
      const minLog = Math.log10(Math.max(xMin, 0.0001));
      const maxLog = Math.log10(xMax);
      const valLog = Math.log10(Math.max(val, 0.0001));
      return padding.left + ((valLog - minLog) / (maxLog - minLog)) * plotWidth;
    } else {
      return padding.left + ((val - xMin) / (xMax - xMin)) * plotWidth;
    }
  };

  const getY = (val: number) => {
    return padding.top + plotHeight - ((val - yMin) / (yMax - yMin)) * plotHeight;
  };

  // Pareto Frontier Calculation for Latency (Lower X & Higher Y is better)
  const paretoPoints = [...points]
    .sort((a, b) => a.xVal - b.xVal)
    .filter((p, index, arr) => {
      // Keep only points that are not dominated by any previous (faster) point with higher score
      const maxPriorY = arr.slice(0, index).reduce((max, prev) => Math.max(max, prev.yVal), -Infinity);
      return p.yVal > maxPriorY;
    });

  // Color mapping by provider
  const getProviderColor = (provider: string) => {
    if (provider.includes('Google')) return 'var(--vendor-gemini)';
    if (provider.includes('OpenRouter') || provider.includes('OpenAI')) return 'var(--vendor-openai)';
    if (provider.includes('DeepSeek')) return 'var(--vendor-deepseek)';
    if (provider.includes('Tencent')) return 'var(--vendor-tencent)';
    if (provider.includes('Nvidia')) return 'var(--vendor-nvidia)';
    return 'var(--vendor-neutral)';
  };

  return (
    <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)', marginBottom: '32px' }}>
      {/* Header Controls */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>
              Interactive Pareto Frontier & Quality Analysis
            </h2>
            <span className="badge badge-gold">Artificial Analysis Standard</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Multi-dimensional evaluation visualizing intelligence vs. time, price, and reasoning intensity.
          </p>
        </div>

        {/* Metric Selector Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="tab-group">
            <button
              className={`tab-btn ${metric === 'latency' ? 'active' : ''}`}
              onClick={() => setMetric('latency')}
            >
              <Zap size={14} /> Quality vs. Latency
            </button>
            <button
              className={`tab-btn ${metric === 'cost' ? 'active' : ''}`}
              onClick={() => setMetric('cost')}
            >
              <DollarSign size={14} /> Quality vs. Price
            </button>
            <button
              className={`tab-btn ${metric === 'reasoning' ? 'active' : ''}`}
              onClick={() => setMetric('reasoning')}
            >
              <Brain size={14} /> Reasoning Efficiency
            </button>
          </div>

          <button
            onClick={() => setIsLogScale(!isLogScale)}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 'var(--radius-md)',
              backgroundColor: isLogScale ? 'var(--bg-card-elevated)' : 'transparent',
              border: '1px solid var(--border-medium)',
              color: isLogScale ? 'var(--brand-gold)' : 'var(--text-secondary)',
            }}
          >
            {isLogScale ? 'Log Scale: ON' : 'Linear Scale'}
          </button>
        </div>
      </div>

      {/* SVG Chart */}
      <div style={{ width: '100%', overflowX: 'auto', display: 'flex', justifyContent: 'center' }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', maxWidth: '860px', height: 'auto', overflow: 'visible', userSelect: 'none' }}
        >
          {/* Background grid lines Y */}
          {[40, 50, 60, 70, 80, 90].map((yTick) => (
            <g key={yTick}>
              <line
                x1={padding.left}
                y1={getY(yTick)}
                x2={width - padding.right}
                y2={getY(yTick)}
                stroke="var(--border-subtle)"
                strokeDasharray="4 4"
              />
              <text
                x={padding.left - 12}
                y={getY(yTick) + 4}
                textAnchor="end"
                fontSize="11"
                fill="var(--text-muted)"
                fontFamily="var(--font-mono)"
              >
                {yTick}
              </text>
            </g>
          ))}

          {/* Background grid lines X */}
          {metric === 'latency' &&
            [200, 600, 1000, 1500, 2000, 2500].map((xTick) => (
              <g key={xTick}>
                <line
                  x1={getX(xTick)}
                  y1={padding.top}
                  x2={getX(xTick)}
                  y2={height - padding.bottom}
                  stroke="var(--border-subtle)"
                  strokeDasharray="4 4"
                />
                <text
                  x={getX(xTick)}
                  y={height - padding.bottom + 20}
                  textAnchor="middle"
                  fontSize="11"
                  fill="var(--text-muted)"
                  fontFamily="var(--font-mono)"
                >
                  {xTick}s
                </text>
              </g>
            ))}

          {metric === 'cost' &&
            [0.05, 0.15, 0.25, 0.35, 0.45].map((xTick) => (
              <g key={xTick}>
                <line
                  x1={getX(xTick)}
                  y1={padding.top}
                  x2={getX(xTick)}
                  y2={height - padding.bottom}
                  stroke="var(--border-subtle)"
                  strokeDasharray="4 4"
                />
                <text
                  x={getX(xTick)}
                  y={height - padding.bottom + 20}
                  textAnchor="middle"
                  fontSize="11"
                  fill="var(--text-muted)"
                  fontFamily="var(--font-mono)"
                >
                  ${xTick}
                </text>
              </g>
            ))}

          {metric === 'reasoning' &&
            [20000, 40000, 60000, 80000, 100000].map((xTick) => (
              <g key={xTick}>
                <line
                  x1={getX(xTick)}
                  y1={padding.top}
                  x2={getX(xTick)}
                  y2={height - padding.bottom}
                  stroke="var(--border-subtle)"
                  strokeDasharray="4 4"
                />
                <text
                  x={getX(xTick)}
                  y={height - padding.bottom + 20}
                  textAnchor="middle"
                  fontSize="11"
                  fill="var(--text-muted)"
                  fontFamily="var(--font-mono)"
                >
                  {xTick / 1000}k
                </text>
              </g>
            ))}

          {/* Pareto Frontier Line (for Latency) */}
          {metric === 'latency' && paretoPoints.length > 1 && (
            <g>
              <polyline
                fill="none"
                stroke="var(--brand-gold)"
                strokeWidth="2.5"
                strokeDasharray="6 4"
                opacity="0.8"
                points={paretoPoints.map((p) => `${getX(p.xVal)},${getY(p.yVal)}`).join(' ')}
              />
              <text
                x={getX(paretoPoints[paretoPoints.length - 1].xVal) - 10}
                y={getY(paretoPoints[paretoPoints.length - 1].yVal) - 14}
                fill="var(--brand-gold)"
                fontSize="11"
                fontWeight="700"
                textAnchor="end"
              >
                Pareto Frontier (Optimal Trade-off)
              </text>
            </g>
          )}

          {/* Axis Labels */}
          <text
            x={width / 2}
            y={height - 12}
            textAnchor="middle"
            fontSize="12"
            fontWeight="600"
            fill="var(--text-secondary)"
          >
            {metric === 'latency'
              ? '3-Round Elapsed Time (seconds, lower is faster)'
              : metric === 'cost'
              ? '3-Round Inference Cost ($USD, lower is cheaper)'
              : 'Reasoning Tokens Consumed (lower is more token-efficient)'}
          </text>

          <text
            x={-height / 2}
            y={20}
            transform="rotate(-90)"
            textAnchor="middle"
            fontSize="12"
            fontWeight="600"
            fill="var(--text-secondary)"
          >
            Aventine Pilot Score (0 - 100, higher is better)
          </text>

          {/* Scatter Points */}
          {points.map((p) => {
            const cx = getX(p.xVal);
            const cy = getY(p.yVal);
            const isHovered = hoveredRecipe?.id === p.recipe.id;
            const color = getProviderColor(p.recipe.provider);

            return (
              <g
                key={p.recipe.id}
                style={{ cursor: 'pointer', transition: 'all 0.15s ease' }}
                onMouseEnter={() => setHoveredRecipe(p.recipe)}
                onMouseLeave={() => setHoveredRecipe(null)}
                onClick={() => onSelectModel(p.recipe)}
              >
                {/* Glow ring on hover */}
                {isHovered && (
                  <circle cx={cx} cy={cy} r="16" fill={color} opacity="0.25" className="animate-pulse-slow" />
                )}
                {/* Main point */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 8 : p.recipe.rank === 1 ? 7 : 5.5}
                  fill={color}
                  stroke="#ffffff"
                  strokeWidth={isHovered ? 2.5 : 1.5}
                />
                {/* Model Label Tag */}
                <text
                  x={cx + (cx > width - 180 ? -10 : 10)}
                  y={cy + 4}
                  textAnchor={cx > width - 180 ? 'end' : 'start'}
                  fontSize={isHovered ? '12' : '11'}
                  fontWeight={isHovered || p.recipe.rank <= 2 ? '700' : '500'}
                  fill={isHovered ? 'var(--text-primary)' : 'var(--text-secondary)'}
                  style={{ pointerEvents: 'none' }}
                >
                  {p.recipe.label.split('(')[0]}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Tooltip Card / Legend Footer */}
      <div
        style={{
          marginTop: '18px',
          padding: '14px 18px',
          backgroundColor: 'var(--bg-card-elevated)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          fontSize: '12px',
        }}
      >
        {hoveredRecipe ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <span className="badge badge-gold">#{hoveredRecipe.rank} {hoveredRecipe.label}</span>
            <span>
              Pilot Score: <strong className="mono">{hoveredRecipe.pilot_score.toFixed(2)}</strong>
            </span>
            <span>
              Time: <strong className="mono">{hoveredRecipe.telemetry.elapsed_seconds}s</strong>
            </span>
            <span>
              Reasoning: <strong className="mono">{hoveredRecipe.telemetry.reasoning_tokens.toLocaleString()} tok</strong>
            </span>
            <span>
              Cost: <strong className="mono">{hoveredRecipe.telemetry.cost_usd === 'free' ? 'Free' : `$${(hoveredRecipe.telemetry.cost_usd as number).toFixed(4)}`}</strong>
            </span>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
            <Info size={14} /> Hover over points to inspect metrics, or click to open full recipe manifest.
          </div>
        )}

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--vendor-gemini)' }} /> Google AI Studio
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--vendor-openai)' }} /> OpenRouter / OpenAI
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--vendor-deepseek)' }} /> DeepSeek
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--vendor-tencent)' }} /> Tencent HY3
          </span>
        </div>
      </div>
    </div>
  );
};
