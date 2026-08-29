import React, { useState, useEffect } from 'react';
import { Search, X, Trophy, Globe, Clock, ArrowRight } from 'lucide-react';
import { BENCHMARK_RECIPES, LANGUAGE_METADATA } from '../data/benchmarkData';
import { CHANGELOG_DATA } from '../data/changelogData';
import type { RecipeEntry, LanguageCode } from '../types/benchmark';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectModel: (recipe: RecipeEntry) => void;
  onSelectTab: (tab: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectModel,
  onSelectTab,
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const normalizedQuery = query.toLowerCase().trim();

  const filteredModels = BENCHMARK_RECIPES.filter(
    (m) =>
      m.label.toLowerCase().includes(normalizedQuery) ||
      m.provider.toLowerCase().includes(normalizedQuery) ||
      m.model_id.toLowerCase().includes(normalizedQuery)
  ).slice(0, 5);

  const filteredLanguages = (Object.keys(LANGUAGE_METADATA) as LanguageCode[])
    .filter((code) => {
      const meta = LANGUAGE_METADATA[code];
      return (
        code.toLowerCase().includes(normalizedQuery) ||
        meta.name.toLowerCase().includes(normalizedQuery) ||
        meta.nativeName.toLowerCase().includes(normalizedQuery)
      );
    })
    .slice(0, 4);

  const filteredChangelog = CHANGELOG_DATA.filter(
    (c) =>
      c.title.toLowerCase().includes(normalizedQuery) ||
      c.summary.toLowerCase().includes(normalizedQuery)
  ).slice(0, 3);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '80px 16px 20px',
      }}
      onClick={onClose}
    >
      <div
        className="av-card animate-fade-in"
        style={{
          width: '100%',
          maxWidth: '620px',
          backgroundColor: 'var(--bg-card)',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-medium)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <Search size={20} color="var(--brand-gold)" />
          <input
            autoFocus
            type="text"
            placeholder="Search models, 18 languages, metrics, changelog..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              flex: 1,
              background: 'none',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '15px',
            }}
          />
          {query && (
            <button onClick={() => setQuery('')} style={{ color: 'var(--text-muted)' }}>
              <X size={16} />
            </button>
          )}
          <kbd
            style={{
              fontSize: '11px',
              padding: '2px 6px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-muted)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            ESC
          </kbd>
        </div>

        {/* Search Results List */}
        <div style={{ maxHeight: '420px', overflowY: 'auto', padding: '12px 8px' }}>
          {/* Models */}
          {filteredModels.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', padding: '4px 12px 8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Trophy size={13} color="var(--brand-gold)" /> Models & Recipes
              </div>
              {filteredModels.map((m) => (
                <div
                  key={m.id}
                  onClick={() => {
                    onSelectModel(m);
                    onClose();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    transition: 'background-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="badge badge-gold" style={{ fontSize: '10px' }}>#{m.rank}</span>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>{m.label}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{m.provider} · {m.reasoning_effort} reasoning</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span className="mono" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brand-gold)' }}>
                      {m.pilot_score.toFixed(1)}
                    </span>
                    <ArrowRight size={14} color="var(--text-muted)" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Languages */}
          {filteredLanguages.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', padding: '4px 12px 8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Globe size={13} color="var(--brand-blue)" /> 18 Directions
              </div>
              {filteredLanguages.map((code) => {
                const meta = LANGUAGE_METADATA[code];
                return (
                  <div
                    key={code}
                    onClick={() => {
                      onSelectTab('multilingual');
                      onClose();
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="badge badge-neutral" style={{ fontSize: '11px', fontWeight: 700 }}>{code}</span>
                      <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{meta.name} ({meta.nativeName})</span>
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{meta.region}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Changelog */}
          {filteredChangelog.length > 0 && (
            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', padding: '4px 12px 8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={13} color="var(--brand-emerald)" /> Changelog & Tournaments
              </div>
              {filteredChangelog.map((c) => (
                <div
                  key={c.id}
                  onClick={() => {
                    onSelectTab('changelog');
                    onClose();
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{c.title}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{c.date} · {c.category}</div>
                </div>
              ))}
            </div>
          )}

          {filteredModels.length === 0 && filteredLanguages.length === 0 && filteredChangelog.length === 0 && (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No matches found for "{query}". Try searching for Gemini, Qwen, French, or Pareto.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
