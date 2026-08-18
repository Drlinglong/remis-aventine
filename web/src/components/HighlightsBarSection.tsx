import React, { useState } from 'react';
import { BENCHMARK_RECIPES } from '../data/benchmarkData';
import type { RecipeEntry } from '../types/benchmark';
import { ArrowUpRight } from 'lucide-react';

interface HighlightsBarSectionProps {
  onSelectModel: (recipe: RecipeEntry) => void;
  onSelectTab: (tab: string) => void;
}

export const HighlightsBarSection: React.FC<HighlightsBarSectionProps> = ({
  onSelectModel,
  onSelectTab,
}) => {
  const [hoveredRecipeId, setHoveredRecipeId] = useState<string | null>(null);

  // 1. Intelligence / Pilot Score (Ranked highest to lowest)
  const scoreRanked = [...BENCHMARK_RECIPES].sort((a, b) => b.pilot_score - a.pilot_score);
  const maxScore = Math.max(...scoreRanked.map((r) => r.pilot_score));

  // 2. Speed / Throughput (Ranked highest tokens/sec)
  const speedRanked = [...BENCHMARK_RECIPES].sort(
    (a, b) => b.telemetry.tokens_per_second - a.telemetry.tokens_per_second
  );
  const maxSpeed = Math.max(...speedRanked.map((r) => r.telemetry.tokens_per_second));

  // 3. Cost per Task (USD) (Ranked lowest to highest)
  const costRanked = [...BENCHMARK_RECIPES].sort((a, b) => {
    const aCost = a.telemetry.cost_usd === 'free' ? 0.001 : (a.telemetry.cost_usd as number);
    const bCost = b.telemetry.cost_usd === 'free' ? 0.001 : (b.telemetry.cost_usd as number);
    return bCost - aCost; // tallest bar for highest cost or vice versa
  });
  const maxCost = Math.max(
    ...costRanked.map((r) => (r.telemetry.cost_usd === 'free' ? 0.01 : (r.telemetry.cost_usd as number)))
  );

  // Helper for brand bar colors
  const getBarColor = (recipe: RecipeEntry, isHighlighted: boolean) => {
    if (hoveredRecipeId && hoveredRecipeId !== recipe.id && !isHighlighted) {
      return 'var(--bg-muted)';
    }
    if (recipe.provider.includes('Google')) return 'var(--vendor-gemini)';
    if (recipe.provider.includes('OpenAI') || recipe.provider.includes('Luna')) return 'var(--vendor-openai)';
    if (recipe.provider.includes('DeepSeek')) return 'var(--vendor-deepseek)';
    if (recipe.provider.includes('Tencent')) return 'var(--vendor-tencent)';
    if (recipe.provider.includes('Nvidia')) return 'var(--vendor-nvidia)';
    if (recipe.provider.includes('Qwen') || recipe.provider.includes('alibaba')) return 'var(--vendor-qwen)';
    return 'var(--vendor-neutral)';
  };

  // Helper for provider icon / letter
  const getProviderInitial = (provider: string) => {
    if (provider.includes('Google')) return 'G';
    if (provider.includes('OpenAI')) return 'O';
    if (provider.includes('DeepSeek')) return 'D';
    if (provider.includes('Tencent')) return 'T';
    if (provider.includes('Nvidia')) return 'N';
    if (provider.includes('Local')) return 'L';
    return 'R';
  };

  const chartHeight = 160;

  return (
    <div style={{ marginBottom: '40px' }}>
      <div className="section-title">
        <span>Highlights</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {/* CARD 1: Intelligence / Pilot Score */}
        <div
          className="av-card"
          style={{
            padding: '20px',
            backgroundColor: 'var(--bg-card)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '10px', height: '10px', backgroundColor: 'var(--brand-purple)', borderRadius: '2px' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>Pilot Score</h3>
              </div>
              <button
                onClick={() => onSelectTab('leaderboard')}
                style={{ color: 'var(--text-muted)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '2px' }}
              >
                View all <ArrowUpRight size={12} />
              </button>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '24px' }}>
              Aventine Pilot Index · Higher is better
            </p>
          </div>

          {/* Bar Chart Container */}
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', height: `${chartHeight}px`, gap: '6px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            {scoreRanked.slice(0, 9).map((recipe) => {
              const barH = (recipe.pilot_score / maxScore) * (chartHeight - 32);
              const isHovered = hoveredRecipeId === recipe.id;
              const color = getBarColor(recipe, isHovered);

              return (
                <div
                  key={recipe.id}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    height: '100%',
                    cursor: 'pointer',
                    position: 'relative',
                  }}
                  onMouseEnter={() => setHoveredRecipeId(recipe.id)}
                  onMouseLeave={() => setHoveredRecipeId(null)}
                  onClick={() => onSelectModel(recipe)}
                >
                  {/* Score Label on Top */}
                  <span
                    className="mono"
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      color: isHovered ? 'var(--brand-gold)' : 'var(--text-secondary)',
                      marginBottom: '4px',
                    }}
                  >
                    {recipe.pilot_score.toFixed(0)}
                  </span>

                  {/* Bar */}
                  <div
                    style={{
                      width: '100%',
                      maxWidth: '28px',
                      height: `${Math.max(barH, 12)}px`,
                      backgroundColor: color,
                      borderRadius: '4px 4px 1px 1px',
                      transition: 'all 0.2s ease',
                      opacity: isHovered ? 1 : 0.85,
                      transform: isHovered ? 'scaleY(1.03)' : 'scaleY(1)',
                      transformOrigin: 'bottom',
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* Labels & Provider Logos Row below chart */}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '6px', paddingTop: '8px', height: '65px', overflow: 'hidden' }}>
            {scoreRanked.slice(0, 9).map((recipe) => (
              <div
                key={recipe.id}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  cursor: 'pointer',
                }}
                onClick={() => onSelectModel(recipe)}
              >
                <div
                  style={{
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--bg-card-elevated)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '9px',
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    marginBottom: '4px',
                  }}
                >
                  {getProviderInitial(recipe.provider)}
                </div>
                <span
                  style={{
                    fontSize: '9px',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    transform: 'rotate(-45deg) translate(-8px, 4px)',
                    transformOrigin: 'top left',
                    display: 'inline-block',
                    width: '42px',
                    textAlign: 'left',
                  }}
                >
                  {recipe.label.split(' ')[0]}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CARD 2: Speed & Throughput */}
        <div
          className="av-card"
          style={{
            padding: '20px',
            backgroundColor: 'var(--bg-card)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '10px', height: '10px', backgroundColor: 'var(--brand-emerald)', borderRadius: '2px' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>Throughput Speed</h3>
              </div>
              <button
                onClick={() => onSelectTab('charts')}
                style={{ color: 'var(--text-muted)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '2px' }}
              >
                View all <ArrowUpRight size={12} />
              </button>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '24px' }}>
              Output tokens per second · Higher is better
            </p>
          </div>

          {/* Bar Chart Container */}
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', height: `${chartHeight}px`, gap: '6px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            {speedRanked.slice(0, 9).map((recipe) => {
              const barH = (recipe.telemetry.tokens_per_second / maxSpeed) * (chartHeight - 32);
              const isHovered = hoveredRecipeId === recipe.id;
              const color = getBarColor(recipe, isHovered);

              return (
                <div
                  key={recipe.id}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    height: '100%',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={() => setHoveredRecipeId(recipe.id)}
                  onMouseLeave={() => setHoveredRecipeId(null)}
                  onClick={() => onSelectModel(recipe)}
                >
                  <span
                    className="mono"
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      color: isHovered ? 'var(--brand-emerald)' : 'var(--text-secondary)',
                      marginBottom: '4px',
                    }}
                  >
                    {recipe.telemetry.tokens_per_second.toFixed(0)}
                  </span>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: '28px',
                      height: `${Math.max(barH, 12)}px`,
                      backgroundColor: color,
                      borderRadius: '4px 4px 1px 1px',
                      transition: 'all 0.2s ease',
                      opacity: isHovered ? 1 : 0.85,
                      transform: isHovered ? 'scaleY(1.03)' : 'scaleY(1)',
                      transformOrigin: 'bottom',
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* Labels & Provider Logos */}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '6px', paddingTop: '8px', height: '65px', overflow: 'hidden' }}>
            {speedRanked.slice(0, 9).map((recipe) => (
              <div
                key={recipe.id}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  cursor: 'pointer',
                }}
                onClick={() => onSelectModel(recipe)}
              >
                <div
                  style={{
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--bg-card-elevated)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '9px',
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    marginBottom: '4px',
                  }}
                >
                  {getProviderInitial(recipe.provider)}
                </div>
                <span
                  style={{
                    fontSize: '9px',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    transform: 'rotate(-45deg) translate(-8px, 4px)',
                    transformOrigin: 'top left',
                    display: 'inline-block',
                    width: '42px',
                    textAlign: 'left',
                  }}
                >
                  {recipe.label.split(' ')[0]}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CARD 3: Cost per 3-Round Task */}
        <div
          className="av-card"
          style={{
            padding: '20px',
            backgroundColor: 'var(--bg-card)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '10px', height: '10px', backgroundColor: 'var(--brand-orange)', borderRadius: '2px' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>Cost per 3-Round Run</h3>
              </div>
              <button
                onClick={() => onSelectTab('charts')}
                style={{ color: 'var(--text-muted)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '2px' }}
              >
                View all <ArrowUpRight size={12} />
              </button>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '24px' }}>
              Weighted inference cost (USD) · Lower is better
            </p>
          </div>

          {/* Bar Chart Container */}
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', height: `${chartHeight}px`, gap: '6px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            {costRanked.slice(0, 9).map((recipe) => {
              const costVal = recipe.telemetry.cost_usd === 'free' ? 0.005 : (recipe.telemetry.cost_usd as number);
              const barH = (costVal / maxCost) * (chartHeight - 32);
              const isHovered = hoveredRecipeId === recipe.id;
              const color = getBarColor(recipe, isHovered);

              return (
                <div
                  key={recipe.id}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    height: '100%',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={() => setHoveredRecipeId(recipe.id)}
                  onMouseLeave={() => setHoveredRecipeId(null)}
                  onClick={() => onSelectModel(recipe)}
                >
                  <span
                    className="mono"
                    style={{
                      fontSize: '9px',
                      fontWeight: 700,
                      color: isHovered ? 'var(--brand-orange)' : 'var(--text-secondary)',
                      marginBottom: '4px',
                    }}
                  >
                    {recipe.telemetry.cost_usd === 'free' ? 'Free' : `$${costVal.toFixed(2)}`}
                  </span>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: '28px',
                      height: `${Math.max(barH, 10)}px`,
                      backgroundColor: color,
                      borderRadius: '4px 4px 1px 1px',
                      transition: 'all 0.2s ease',
                      opacity: isHovered ? 1 : 0.85,
                      transform: isHovered ? 'scaleY(1.03)' : 'scaleY(1)',
                      transformOrigin: 'bottom',
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* Labels & Provider Logos */}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '6px', paddingTop: '8px', height: '65px', overflow: 'hidden' }}>
            {costRanked.slice(0, 9).map((recipe) => (
              <div
                key={recipe.id}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  cursor: 'pointer',
                }}
                onClick={() => onSelectModel(recipe)}
              >
                <div
                  style={{
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--bg-card-elevated)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '9px',
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    marginBottom: '4px',
                  }}
                >
                  {getProviderInitial(recipe.provider)}
                </div>
                <span
                  style={{
                    fontSize: '9px',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    transform: 'rotate(-45deg) translate(-8px, 4px)',
                    transformOrigin: 'top left',
                    display: 'inline-block',
                    width: '42px',
                    textAlign: 'left',
                  }}
                >
                  {recipe.label.split(' ')[0]}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
