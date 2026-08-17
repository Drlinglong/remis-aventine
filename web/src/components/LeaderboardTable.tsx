import React, { useState, useMemo } from 'react';
import { Search, ChevronDown, ChevronUp, Filter, Sparkles, Shield, Zap, Globe, HelpCircle } from 'lucide-react';
import { BENCHMARK_RECIPES } from '../data/benchmarkData';
import type { RecipeEntry } from '../types/benchmark';

interface LeaderboardTableProps {
  onSelectModel: (recipe: RecipeEntry) => void;
}

type ViewMode = 'overall' | 'multilingual' | 'efficiency' | 'localization';
type SortField =
  | 'rank'
  | 'pilot_score'
  | 'soft_preference'
  | 'hard_reliability'
  | 'multilingual_score'
  | 'european_score'
  | 'east_asian_score'
  | 'elapsed_seconds'
  | 'tokens_per_second'
  | 'cost_usd';

export const LeaderboardTable: React.FC<LeaderboardTableProps> = ({ onSelectModel }) => {
  const [viewMode, setViewMode] = useState<ViewMode>('overall');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEffort, setSelectedEffort] = useState<string>('all');
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [onlyLocal24gb, setOnlyLocal24gb] = useState(false);
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortAsc, setSortAsc] = useState(true);

  // Available providers for filter
  const providers = useMemo(() => {
    const set = new Set<string>();
    BENCHMARK_RECIPES.forEach((r) => set.add(r.provider.split('/')[0].trim()));
    return Array.from(set);
  }, []);

  // Filtered & sorted recipes
  const filteredRecipes = useMemo(() => {
    return BENCHMARK_RECIPES.filter((recipe) => {
      const matchesSearch =
        recipe.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        recipe.provider.toLowerCase().includes(searchQuery.toLowerCase()) ||
        recipe.model_id.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesEffort =
        selectedEffort === 'all' || recipe.reasoning_effort === selectedEffort;

      const matchesProvider =
        selectedProvider === 'all' || recipe.provider.includes(selectedProvider);

      const matchesLocal =
        !onlyLocal24gb || (recipe.telemetry.peak_vram_gib !== null && recipe.telemetry.peak_vram_gib <= 24);

      return matchesSearch && matchesEffort && matchesProvider && matchesLocal;
    }).sort((a, b) => {
      let aVal: number = 0;
      let bVal: number = 0;

      switch (sortField) {
        case 'rank':
          aVal = a.rank;
          bVal = b.rank;
          break;
        case 'pilot_score':
          aVal = a.pilot_score;
          bVal = b.pilot_score;
          break;
        case 'soft_preference':
          aVal = a.soft_preference;
          bVal = b.soft_preference;
          break;
        case 'hard_reliability':
          aVal = a.hard_reliability;
          bVal = b.hard_reliability;
          break;
        case 'multilingual_score':
          aVal = a.multilingual_score;
          bVal = b.multilingual_score;
          break;
        case 'european_score':
          aVal = a.european_score;
          bVal = b.european_score;
          break;
        case 'east_asian_score':
          aVal = a.east_asian_score;
          bVal = b.east_asian_score;
          break;
        case 'elapsed_seconds':
          aVal = a.telemetry.elapsed_seconds;
          bVal = b.telemetry.elapsed_seconds;
          break;
        case 'tokens_per_second':
          aVal = a.telemetry.tokens_per_second;
          bVal = b.telemetry.tokens_per_second;
          break;
        case 'cost_usd':
          aVal = a.telemetry.cost_usd === 'free' ? 0 : (a.telemetry.cost_usd as number);
          bVal = b.telemetry.cost_usd === 'free' ? 0 : (b.telemetry.cost_usd as number);
          break;
        default:
          aVal = a.rank;
          bVal = b.rank;
      }

      if (sortAsc) {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
  }, [searchQuery, selectedEffort, selectedProvider, onlyLocal24gb, sortField, sortAsc]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      if (['rank', 'elapsed_seconds', 'cost_usd'].includes(field)) {
        setSortAsc(true);
      } else {
        setSortAsc(false);
      }
    }
  };

  return (
    <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)', marginBottom: '32px' }}>
      {/* Controls Top Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '20px' }}>
        {/* View Mode Tabs */}
        <div className="tab-group">
          <button
            className={`tab-btn ${viewMode === 'overall' ? 'active' : ''}`}
            onClick={() => setViewMode('overall')}
          >
            <Sparkles size={14} /> Overall Benchmark
          </button>
          <button
            className={`tab-btn ${viewMode === 'multilingual' ? 'active' : ''}`}
            onClick={() => setViewMode('multilingual')}
          >
            <Globe size={14} /> 18 Languages Breakdown
          </button>
          <button
            className={`tab-btn ${viewMode === 'efficiency' ? 'active' : ''}`}
            onClick={() => setViewMode('efficiency')}
          >
            <Zap size={14} /> Efficiency & Telemetry
          </button>
          <button
            className={`tab-btn ${viewMode === 'localization' ? 'active' : ''}`}
            onClick={() => setViewMode('localization')}
          >
            <Shield size={14} /> Game Localization Track
          </button>
        </div>

        {/* Search input */}
        <div style={{ position: 'relative', minWidth: '220px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Filter models or providers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 12px 6px 30px',
              fontSize: '13px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-full)',
              color: 'var(--text-primary)',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Filter Row */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 16px',
          backgroundColor: 'var(--bg-card-elevated)',
          borderRadius: 'var(--radius-md)',
          marginBottom: '16px',
          fontSize: '12px',
          color: 'var(--text-secondary)',
        }}
      >
        <span style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-primary)' }}>
          <Filter size={13} /> Filters:
        </span>

        {/* Reasoning Effort Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>Reasoning:</span>
          <select
            value={selectedEffort}
            onChange={(e) => setSelectedEffort(e.target.value)}
            style={{
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '2px 8px',
              fontSize: '12px',
            }}
          >
            <option value="all">All Efforts</option>
            <option value="high">High Reasoning</option>
            <option value="reasoning">Enabled Reasoning</option>
            <option value="none">Disabled (None)</option>
          </select>
        </div>

        {/* Provider Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>Provider:</span>
          <select
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            style={{
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '2px 8px',
              fontSize: '12px',
            }}
          >
            <option value="all">All Providers</option>
            {providers.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {/* Local <24GB VRAM Checkbox */}
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', userSelect: 'none' }}>
          <input
            type="checkbox"
            checked={onlyLocal24gb}
            onChange={(e) => setOnlyLocal24gb(e.target.checked)}
          />
          <span>Consumer GPU Capable (&lt;24GB VRAM)</span>
        </label>

        {/* Reset button */}
        {(searchQuery || selectedEffort !== 'all' || selectedProvider !== 'all' || onlyLocal24gb) && (
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedEffort('all');
              setSelectedProvider('all');
              setOnlyLocal24gb(false);
            }}
            style={{ color: 'var(--brand-gold)', fontSize: '11px', textDecoration: 'underline', marginLeft: 'auto' }}
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Table Container */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-medium)', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              <th style={{ padding: '12px 8px', cursor: 'pointer', width: '50px' }} onClick={() => handleSort('rank')}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  # {sortField === 'rank' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                </div>
              </th>
              <th style={{ padding: '12px 12px', minWidth: '220px' }}>Recipe & Provider</th>
              
              <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('pilot_score')}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  Pilot Score {sortField === 'pilot_score' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                </div>
              </th>

              {viewMode === 'overall' && (
                <>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('soft_preference')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Soft Win% {sortField === 'soft_preference' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('hard_reliability')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Hard Pass% {sortField === 'hard_reliability' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                  <th style={{ padding: '12px 12px' }}>W - L - T</th>
                  <th style={{ padding: '12px 12px' }}>Coverage</th>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('elapsed_seconds')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Time (3-Run) {sortField === 'elapsed_seconds' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('cost_usd')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Cost (USD) {sortField === 'cost_usd' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                </>
              )}

              {viewMode === 'multilingual' && (
                <>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('multilingual_score')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Multilingual {sortField === 'multilingual_score' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('european_score')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      European (12) {sortField === 'european_score' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('east_asian_score')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      East Asian (6) {sortField === 'east_asian_score' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                  <th style={{ padding: '12px 12px' }}>Top Languages</th>
                  <th style={{ padding: '12px 12px' }}>Coverage</th>
                </>
              )}

              {viewMode === 'efficiency' && (
                <>
                  <th style={{ padding: '12px 12px' }}>p50 / p95 Latency</th>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('tokens_per_second')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Throughput {sortField === 'tokens_per_second' && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                    </div>
                  </th>
                  <th style={{ padding: '12px 12px' }}>Reasoning Tokens</th>
                  <th style={{ padding: '12px 12px' }}>Total Tokens</th>
                  <th style={{ padding: '12px 12px' }}>VRAM Requirement</th>
                  <th style={{ padding: '12px 12px', cursor: 'pointer' }} onClick={() => handleSort('cost_usd')}>
                    Cost
                  </th>
                </>
              )}

              {viewMode === 'localization' && (
                <>
                  <th style={{ padding: '12px 12px' }}>Terminology Recall</th>
                  <th style={{ padding: '12px 12px' }}>Batch Cohesion</th>
                  <th style={{ padding: '12px 12px' }}>Exact Match</th>
                  <th style={{ padding: '12px 12px' }}>Hard Pass</th>
                  <th style={{ padding: '12px 12px' }}>Stage Multiplier</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {filteredRecipes.map((recipe) => (
              <tr
                key={recipe.id}
                onClick={() => onSelectModel(recipe)}
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                {/* Rank */}
                <td style={{ padding: '14px 8px' }}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '24px',
                      height: '24px',
                      borderRadius: 'var(--radius-full)',
                      backgroundColor: recipe.rank === 1 ? 'var(--brand-gold)' : recipe.rank === 2 ? 'var(--bg-card-elevated)' : 'transparent',
                      color: recipe.rank === 1 ? '#000' : 'var(--text-secondary)',
                      fontWeight: 700,
                      fontSize: '11px',
                    }}
                  >
                    {recipe.rank}
                  </span>
                </td>

                {/* Recipe & Provider */}
                <td style={{ padding: '14px 12px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{recipe.label}</span>
                      {recipe.is_anchor && (
                        <span className="badge badge-neutral" style={{ fontSize: '9px', padding: '0 4px' }}>
                          Anchor
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-muted)' }}>
                      <span>{recipe.provider}</span>
                      <span>·</span>
                      <span style={{ textTransform: 'capitalize' }}>{recipe.reasoning_effort} reasoning</span>
                    </div>
                  </div>
                </td>

                {/* Pilot Score */}
                <td style={{ padding: '14px 12px' }}>
                  <div className="mono" style={{ fontSize: '15px', fontWeight: 800, color: recipe.rank === 1 ? 'var(--brand-gold)' : 'var(--text-primary)' }}>
                    {recipe.pilot_score.toFixed(2)}
                  </div>
                </td>

                {/* Overall Mode Columns */}
                {viewMode === 'overall' && (
                  <>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: recipe.soft_preference > 60 ? 'var(--brand-blue)' : 'var(--text-secondary)', fontWeight: 600 }}>
                        {recipe.soft_preference.toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: recipe.hard_reliability === 100 ? 'var(--brand-emerald)' : 'var(--brand-gold)', fontWeight: 600 }}>
                        {recipe.hard_reliability.toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px', color: 'var(--text-secondary)' }} className="mono">
                      {recipe.wins}-{recipe.losses}-{recipe.ties}
                    </td>
                    <td style={{ padding: '14px 12px', color: 'var(--text-muted)' }} className="mono">
                      {recipe.coverage_percent.toFixed(1)}%
                    </td>
                    <td style={{ padding: '14px 12px', color: 'var(--text-secondary)' }} className="mono">
                      {recipe.telemetry.elapsed_seconds.toFixed(1)} s
                    </td>
                    <td style={{ padding: '14px 12px' }} className="mono">
                      {recipe.telemetry.cost_usd === 'free' ? (
                        <span className="badge badge-neutral" style={{ fontSize: '10px' }}>Free</span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)' }}>
                          ${(recipe.telemetry.cost_usd as number).toFixed(4)}
                        </span>
                      )}
                    </td>
                  </>
                )}

                {/* Multilingual Mode Columns */}
                {viewMode === 'multilingual' && (
                  <>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ fontWeight: 700, color: 'var(--brand-gold)' }}>
                        {recipe.multilingual_score.toFixed(1)}
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: 'var(--text-primary)' }}>
                        {recipe.european_score.toFixed(1)}
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: 'var(--text-primary)' }}>
                        {recipe.east_asian_score.toFixed(1)}
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <span className="badge badge-neutral" style={{ fontSize: '10px' }}>FR {recipe.languages.FR.score.toFixed(0)}</span>
                        <span className="badge badge-neutral" style={{ fontSize: '10px' }}>ZH {recipe.languages['ZH-CN'].score.toFixed(0)}</span>
                        <span className="badge badge-neutral" style={{ fontSize: '10px' }}>DE {recipe.languages.DE.score.toFixed(0)}</span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 12px', color: 'var(--text-muted)' }} className="mono">
                      {recipe.coverage_percent.toFixed(1)}%
                    </td>
                  </>
                )}

                {/* Efficiency Mode Columns */}
                {viewMode === 'efficiency' && (
                  <>
                    <td style={{ padding: '14px 12px', color: 'var(--text-secondary)' }} className="mono">
                      {recipe.telemetry.latency_p50_seconds}s / {recipe.telemetry.latency_p95_seconds}s
                    </td>
                    <td style={{ padding: '14px 12px' }} className="mono">
                      <span style={{ color: 'var(--brand-emerald)', fontWeight: 600 }}>
                        {recipe.telemetry.tokens_per_second.toFixed(1)} tok/s
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px', color: 'var(--brand-blue)' }} className="mono">
                      {recipe.telemetry.reasoning_tokens.toLocaleString()}
                    </td>
                    <td style={{ padding: '14px 12px', color: 'var(--text-muted)' }} className="mono">
                      {recipe.telemetry.total_tokens.toLocaleString()}
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      {recipe.telemetry.peak_vram_gib ? (
                        <span className="badge badge-blue">{recipe.telemetry.peak_vram_gib} GB VRAM</span>
                      ) : (
                        <span className="badge badge-neutral">Cloud Managed</span>
                      )}
                    </td>
                    <td style={{ padding: '14px 12px' }} className="mono">
                      {recipe.telemetry.cost_usd === 'free' ? 'Free' : `$${(recipe.telemetry.cost_usd as number).toFixed(4)}`}
                    </td>
                  </>
                )}

                {/* Game Localization Mode Columns */}
                {viewMode === 'localization' && (
                  <>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: 'var(--brand-emerald)', fontWeight: 600 }}>
                        {(recipe.remis_signals.terminology_discovery_recall * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: 'var(--brand-blue)', fontWeight: 600 }}>
                        {(recipe.remis_signals.same_batch_cohesion * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: 'var(--text-primary)' }}>
                        {(recipe.remis_signals.reference_exact_match_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: recipe.hard_reliability === 100 ? 'var(--brand-emerald)' : 'var(--brand-gold)' }}>
                        {recipe.hard_reliability.toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '14px 12px' }}>
                      <span className="mono" style={{ color: 'var(--text-secondary)' }}>
                        {recipe.stage_failures.translation.effective_multiplier.toFixed(3)}×
                      </span>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer hint */}
      <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <HelpCircle size={13} />
          <span>Click any row to open the complete recipe manifest, token usage & 6-component capability radar.</span>
        </div>
        <span>Showing {filteredRecipes.length} of {BENCHMARK_RECIPES.length} recipes</span>
      </div>
    </div>
  );
};
