import React, { useState } from 'react';
import { Globe, Info } from 'lucide-react';
import { BENCHMARK_RECIPES, LANGUAGE_METADATA } from '../data/benchmarkData';
import type { RecipeEntry, LanguageCode } from '../types/benchmark';

interface MultilingualMatrixProps {
  onSelectModel: (recipe: RecipeEntry) => void;
}

type RegionFilter = 'all' | 'european' | 'east_asian';

export const MultilingualMatrix: React.FC<MultilingualMatrixProps> = ({ onSelectModel }) => {
  const [regionFilter, setRegionFilter] = useState<RegionFilter>('all');
  const [hoveredLang, setHoveredLang] = useState<{ code: LanguageCode; recipe: RecipeEntry; score: number } | null>(null);

  const allLanguageCodes = Object.keys(LANGUAGE_METADATA) as LanguageCode[];
  const displayedCodes = allLanguageCodes.filter((code) => {
    if (regionFilter === 'all') return true;
    return LANGUAGE_METADATA[code].region === regionFilter;
  });

  const getHeatmapBg = (score: number) => {
    if (score >= 85) return 'rgba(16, 185, 129, 0.28)';
    if (score >= 75) return 'rgba(16, 185, 129, 0.16)';
    if (score >= 65) return 'rgba(229, 169, 60, 0.18)';
    if (score >= 50) return 'rgba(59, 130, 246, 0.15)';
    return 'rgba(244, 63, 94, 0.15)';
  };

  const getHeatmapColor = (score: number) => {
    if (score >= 85) return 'var(--brand-emerald)';
    if (score >= 75) return 'var(--brand-emerald)';
    if (score >= 65) return 'var(--brand-gold)';
    if (score >= 50) return 'var(--brand-blue)';
    return 'var(--brand-rose)';
  };

  return (
    <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)', marginBottom: '32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>
              18 Languages Multilingual Performance Matrix
            </h2>
            <span className="badge badge-purple">Issue #6 Regional Spec</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Equal-weighted European (12) and East Asian (6) regional scores across all evaluated models.
          </p>
        </div>

        {/* Region Filter Buttons */}
        <div className="tab-group">
          <button
            className={`tab-btn ${regionFilter === 'all' ? 'active' : ''}`}
            onClick={() => setRegionFilter('all')}
          >
            <Globe size={14} /> All 18 Languages
          </button>
          <button
            className={`tab-btn ${regionFilter === 'european' ? 'active' : ''}`}
            onClick={() => setRegionFilter('european')}
          >
            European Group (12)
          </button>
          <button
            className={`tab-btn ${regionFilter === 'east_asian' ? 'active' : ''}`}
            onClick={() => setRegionFilter('east_asian')}
          >
            East Asian Group (6)
          </button>
        </div>
      </div>

      {/* Matrix Table */}
      <div style={{ overflowX: 'auto', paddingBottom: '8px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'center' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-medium)' }}>
              <th style={{ textAlign: 'left', padding: '12px 14px', minWidth: '180px', color: 'var(--text-muted)' }}>
                Recipe
              </th>
              <th style={{ padding: '12px 8px', color: 'var(--brand-gold)', fontWeight: 700 }}>
                Multilingual
              </th>
              {regionFilter !== 'east_asian' && (
                <th style={{ padding: '12px 8px', color: 'var(--brand-blue)', fontWeight: 600 }}>
                  European Avg
                </th>
              )}
              {regionFilter !== 'european' && (
                <th style={{ padding: '12px 8px', color: 'var(--brand-emerald)', fontWeight: 600 }}>
                  East Asian Avg
                </th>
              )}
              {displayedCodes.map((code) => {
                const meta = LANGUAGE_METADATA[code];
                return (
                  <th
                    key={code}
                    style={{
                      padding: '10px 6px',
                      color: 'var(--text-secondary)',
                      fontWeight: 600,
                      minWidth: '46px',
                    }}
                    title={`${meta.name} (${meta.nativeName})`}
                  >
                    <div>{code}</div>
                    <div style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 400 }}>
                      {meta.name.substring(0, 3)}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {BENCHMARK_RECIPES.map((recipe) => (
              <tr
                key={recipe.id}
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                {/* Model Label */}
                <td
                  style={{ textAlign: 'left', padding: '12px 14px' }}
                  onClick={() => onSelectModel(recipe)}
                >
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="badge badge-neutral" style={{ fontSize: '9px', padding: '1px 4px' }}>#{recipe.rank}</span>
                    <span>{recipe.label}</span>
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{recipe.provider}</div>
                </td>

                {/* Multilingual Aggregate */}
                <td style={{ padding: '12px 6px' }} className="mono">
                  <span style={{ fontWeight: 800, color: 'var(--brand-gold)' }}>
                    {recipe.multilingual_score.toFixed(1)}
                  </span>
                </td>

                {/* European Average */}
                {regionFilter !== 'east_asian' && (
                  <td style={{ padding: '12px 6px' }} className="mono">
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                      {recipe.european_score.toFixed(1)}
                    </span>
                  </td>
                )}

                {/* East Asian Average */}
                {regionFilter !== 'european' && (
                  <td style={{ padding: '12px 6px' }} className="mono">
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                      {recipe.east_asian_score.toFixed(1)}
                    </span>
                  </td>
                )}

                {/* Individual Language Cells */}
                {displayedCodes.map((code) => {
                  const s = recipe.languages[code];
                  return (
                    <td
                      key={code}
                      style={{
                        padding: '8px 4px',
                      }}
                      onMouseEnter={() => setHoveredLang({ code, recipe, score: s.score })}
                      onMouseLeave={() => setHoveredLang(null)}
                      onClick={() => onSelectModel(recipe)}
                    >
                      <div
                        style={{
                          backgroundColor: getHeatmapBg(s.score),
                          color: getHeatmapColor(s.score),
                          borderRadius: 'var(--radius-sm)',
                          padding: '6px 2px',
                          fontWeight: 700,
                          fontSize: '11px',
                          border: s.status === 'measured' ? '1px solid var(--border-medium)' : '1px solid transparent',
                        }}
                        className="mono"
                      >
                        {s.score.toFixed(0)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Language Matrix Footer Info */}
      <div
        style={{
          marginTop: '16px',
          padding: '12px 16px',
          backgroundColor: 'var(--bg-card-elevated)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          fontSize: '11px',
          color: 'var(--text-secondary)',
        }}
      >
        {hoveredLang ? (
          <div>
            <strong>{LANGUAGE_METADATA[hoveredLang.code].name} ({hoveredLang.code})</strong> on{' '}
            <strong>{hoveredLang.recipe.label}</strong>: Score{' '}
            <strong className="mono">{hoveredLang.score.toFixed(1)}</strong> ({hoveredLang.recipe.languages[hoveredLang.code].status})
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Info size={13} />
            <span>Scores calculated using Issue #6 stage-specific failure policy and equal-weighted language aggregation.</span>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', backgroundColor: 'rgba(16, 185, 129, 0.4)', borderRadius: '2px' }} /> &gt; 80 (High)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', backgroundColor: 'rgba(229, 169, 60, 0.4)', borderRadius: '2px' }} /> 65 - 80 (Mid)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', backgroundColor: 'rgba(59, 130, 246, 0.4)', borderRadius: '2px' }} /> &lt; 65 (Standard)
          </span>
        </div>
      </div>
    </div>
  );
};
