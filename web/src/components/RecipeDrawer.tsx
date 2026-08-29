import React, { useState } from 'react';
import { X, Layers, Copy, Check } from 'lucide-react';
import type { RecipeEntry, LanguageCode } from '../types/benchmark';

interface RecipeDrawerProps {
  recipe: RecipeEntry | null;
  onClose: () => void;
  onSelectTab: (tab: string) => void;
}

export const RecipeDrawer: React.FC<RecipeDrawerProps> = ({
  recipe,
  onClose,
  onSelectTab: _onSelectTab,
}) => {
  const [copiedSha, setCopiedSha] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<'overview' | 'languages' | 'telemetry' | 'manifest'>('overview');

  if (!recipe) return null;

  const handleCopySha = () => {
    navigator.clipboard.writeText(recipe.recipe_sha256 || '');
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  const getLanguageColor = (score: number) => {
    if (score >= 80) return 'var(--brand-emerald)';
    if (score >= 65) return 'var(--brand-gold)';
    return 'var(--brand-blue)';
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(8px)',
        zIndex: 999,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        className="animate-slide-in"
        style={{
          width: '100%',
          maxWidth: '680px',
          height: '100%',
          backgroundColor: 'var(--bg-card)',
          borderLeft: '1px solid var(--border-medium)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-xl)',
          overflowY: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '24px 28px',
            borderBottom: '1px solid var(--border-subtle)',
            position: 'sticky',
            top: 0,
            backgroundColor: 'var(--bg-card)',
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span className="badge badge-gold">Rank #{recipe.rank}</span>
                <span className="badge badge-neutral">{recipe.provider}</span>
                {recipe.is_anchor && <span className="badge badge-purple">Anchor Model</span>}
              </div>
              <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                {recipe.label}
              </h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Model ID: <code>{recipe.model_id}</code>
              </div>
            </div>

            <button
              onClick={onClose}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-full)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'var(--bg-card-elevated)',
                color: 'var(--text-secondary)',
              }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Sub Navigation Tabs */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '20px' }}>
            {(['overview', 'languages', 'telemetry', 'manifest'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveSubTab(tab)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '12px',
                  fontWeight: activeSubTab === tab ? 600 : 500,
                  backgroundColor: activeSubTab === tab ? 'var(--bg-card-elevated)' : 'transparent',
                  color: activeSubTab === tab ? 'var(--brand-gold)' : 'var(--text-secondary)',
                  border: activeSubTab === tab ? '1px solid var(--brand-gold)' : '1px solid transparent',
                  textTransform: 'capitalize',
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Drawer Body Content */}
        <div style={{ padding: '24px 28px', flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* TAB 1: OVERVIEW */}
          {activeSubTab === 'overview' && (
            <>
              {/* Primary Score Hero Box */}
              <div
                style={{
                  padding: '20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'linear-gradient(135deg, var(--bg-card-elevated) 0%, var(--bg-card) 100%)',
                  border: '1px solid var(--border-medium)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '12px',
                  textAlign: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Pilot Score (0-100)</div>
                  <div className="mono" style={{ fontSize: '26px', fontWeight: 800, color: 'var(--brand-gold)' }}>
                    {recipe.pilot_score.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Soft Win Rate</div>
                  <div className="mono" style={{ fontSize: '26px', fontWeight: 800, color: 'var(--brand-blue)' }}>
                    {recipe.soft_preference.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Hard Reliability</div>
                  <div className="mono" style={{ fontSize: '26px', fontWeight: 800, color: 'var(--brand-emerald)' }}>
                    {recipe.hard_reliability.toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* 6 Capability Tracks Breakdown */}
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Layers size={15} color="var(--brand-gold)" />
                  <span>Issue #6 Capability Score Distribution</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {Object.entries(recipe.components).map(([key, score]) => {
                    const formattedName = key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
                    return (
                      <div key={key}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>{formattedName}</span>
                          <span className="mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{score.toFixed(1)} / 100</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--bg-muted)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${score}%`,
                              height: '100%',
                              backgroundColor: score >= 80 ? 'var(--brand-emerald)' : score >= 65 ? 'var(--brand-gold)' : 'var(--brand-blue)',
                              borderRadius: '3px',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Stage Failure Multipliers Breakdown */}
              <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
                  Stage-Specific Failure Policy
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px' }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Translation Phase:</div>
                    <div style={{ fontWeight: 600, color: 'var(--brand-emerald)' }}>
                      Pass: {recipe.stage_failures.translation.pass_count} / Recoverable: {recipe.stage_failures.translation.recoverable_error_count}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Effective Multiplier:</div>
                    <div className="mono" style={{ fontWeight: 700, color: 'var(--brand-gold)' }}>
                      {recipe.stage_failures.translation.effective_multiplier.toFixed(3)}×
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* TAB 2: 18 LANGUAGES */}
          {activeSubTab === 'languages' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
                  18 Target Language Scores
                </span>
                <span className="badge badge-purple">
                  Multilingual: {recipe.multilingual_score.toFixed(1)}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '8px' }}>
                {(Object.keys(recipe.languages) as LanguageCode[]).map((code) => {
                  const lang = recipe.languages[code];
                  return (
                    <div
                      key={code}
                      style={{
                        padding: '10px',
                        backgroundColor: 'var(--bg-card-elevated)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                        {code} · {lang.region === 'european' ? 'EU' : 'ASIA'}
                      </div>
                      <div className="mono" style={{ fontSize: '18px', fontWeight: 800, color: getLanguageColor(lang.score), margin: '4px 0' }}>
                        {lang.score.toFixed(1)}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                        {lang.name}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: TELEMETRY & HARDWARE */}
          {activeSubTab === 'telemetry' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ padding: '14px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Elapsed Execution Time</div>
                  <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {recipe.telemetry.elapsed_seconds.toFixed(1)} s
                  </div>
                </div>
                <div style={{ padding: '14px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Inference Cost (3 Runs)</div>
                  <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--brand-emerald)' }}>
                    {recipe.telemetry.cost_usd === 'free' ? 'Free Tier' : `$${(recipe.telemetry.cost_usd as number).toFixed(4)}`}
                  </div>
                </div>
                <div style={{ padding: '14px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Reasoning Tokens</div>
                  <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--brand-blue)' }}>
                    {recipe.telemetry.reasoning_tokens.toLocaleString()}
                  </div>
                </div>
                <div style={{ padding: '14px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Generation Throughput</div>
                  <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {recipe.telemetry.tokens_per_second.toFixed(1)} tok/s
                  </div>
                </div>
              </div>

              {/* Hardware / Runtime Spec */}
              <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)', fontSize: '12px' }}>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
                  Execution Environment & Precision
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)' }}>
                  <div><strong>Runtime:</strong> {recipe.runtime}</div>
                  <div><strong>Quantization:</strong> {recipe.quantization}</div>
                  <div><strong>VRAM Footprint:</strong> {recipe.telemetry.peak_vram_gib ? `${recipe.telemetry.peak_vram_gib} GiB VRAM` : 'Managed Serverless API'}</div>
                  <div><strong>Score Policy:</strong> <code>{recipe.score_version}</code></div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: RECIPE MANIFEST & REPRODUCIBILITY */}
          {activeSubTab === 'manifest' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  CRYPTOGRAPHIC RECIPE SHA-256
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    backgroundColor: 'var(--bg-input)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <code style={{ fontSize: '11px', wordBreak: 'break-all', color: 'var(--brand-gold)' }}>
                    {recipe.recipe_sha256}
                  </code>
                  <button
                    onClick={handleCopySha}
                    style={{
                      padding: '4px 8px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--bg-card-elevated)',
                      color: copiedSha ? 'var(--brand-emerald)' : 'var(--text-secondary)',
                      fontSize: '11px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      marginLeft: '8px',
                    }}
                  >
                    {copiedSha ? <Check size={12} /> : <Copy size={12} />}
                    <span>{copiedSha ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              {/* CLI command to reproduce */}
              <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
                  Reproduce Locally via Remis Aventine CLI
                </div>
                <pre style={{ margin: 0, padding: '10px', backgroundColor: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', fontSize: '11px', color: 'var(--text-secondary)', overflowX: 'auto' }}>
                  <code>remis-aventine run --recipe {recipe.id} --tournament nine-model-pilot-2026-08-01</code>
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
