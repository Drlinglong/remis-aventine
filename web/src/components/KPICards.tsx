import React from 'react';
import { Trophy, Zap, ShieldCheck, Globe2 } from 'lucide-react';
import { BENCHMARK_RECIPES } from '../data/benchmarkData';
import type { RecipeEntry } from '../types/benchmark';

interface KPICardsProps {
  onSelectModel: (recipe: RecipeEntry) => void;
  onSelectTab: (tab: string) => void;
}

export const KPICards: React.FC<KPICardsProps> = ({ onSelectModel, onSelectTab }) => {
  const leader = BENCHMARK_RECIPES[0]; // Gemini 3.6 Flash
  const speedChampion = BENCHMARK_RECIPES[3]; // Luna
  const zeroBreachModels = BENCHMARK_RECIPES.filter((m) => m.hard_reliability === 100).length;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', margin: '28px 0' }}>
      {/* KPI 1: Leader */}
      <div
        className="av-card"
        style={{
          padding: '20px',
          background: 'linear-gradient(145deg, var(--bg-card) 0%, var(--bg-card-elevated) 100%)',
          border: '1px solid rgba(229, 169, 60, 0.25)',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
        }}
        onClick={() => onSelectModel(leader)}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(229, 169, 60, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--brand-gold)',
              }}
            >
              <Trophy size={18} />
            </div>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-gold)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              #1 Overall Pilot Leader
            </span>
          </div>
          <span className="badge badge-gold" style={{ fontSize: '10px' }}>Rank 1</span>
        </div>

        <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
          {leader.label}
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          {leader.provider} · 73.7% soft win rate · 100% hard pass
        </p>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span className="mono" style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-primary)' }}>
            {leader.pilot_score.toFixed(2)}
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>/ 100 Pilot Score</span>
        </div>
      </div>

      {/* KPI 2: Speed & Reasoning Efficiency */}
      <div
        className="av-card"
        style={{
          padding: '20px',
          background: 'linear-gradient(145deg, var(--bg-card) 0%, var(--bg-card-elevated) 100%)',
          cursor: 'pointer',
        }}
        onClick={() => onSelectModel(speedChampion)}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--brand-blue)',
              }}
            >
              <Zap size={18} />
            </div>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-blue)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              High-Tier Speed Frontier
            </span>
          </div>
          <span className="badge badge-blue" style={{ fontSize: '10px' }}>174.3 s</span>
        </div>

        <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
          {speedChampion.label}
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          Only 10.9k reasoning tokens vs. 98.9k in heavy models
        </p>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span className="mono" style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-primary)' }}>
            {speedChampion.pilot_score.toFixed(2)}
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Score · $0.0107 / run</span>
        </div>
      </div>

      {/* KPI 3: Hard Reliability Zero Breach */}
      <div
        className="av-card"
        style={{
          padding: '20px',
          background: 'linear-gradient(145deg, var(--bg-card) 0%, var(--bg-card-elevated) 100%)',
          cursor: 'pointer',
        }}
        onClick={() => onSelectTab('leaderboard')}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--brand-emerald)',
              }}
            >
              <ShieldCheck size={18} />
            </div>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-emerald)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Hard Reliability (21/21)
            </span>
          </div>
          <span className="badge badge-emerald" style={{ fontSize: '10px' }}>Zero Breach</span>
        </div>

        <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
          {zeroBreachModels} Models at 100.0%
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          Gemini 3.6, Gemma 4 31B, Nemotron 3 Ultra passed all tags & placeholders
        </p>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span className="mono" style={{ fontSize: '28px', fontWeight: 800, color: 'var(--brand-emerald)' }}>
            100%
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Veto-safe pass rate</span>
        </div>
      </div>

      {/* KPI 4: 18-Language Multilingual Scope */}
      <div
        className="av-card"
        style={{
          padding: '20px',
          background: 'linear-gradient(145deg, var(--bg-card) 0%, var(--bg-card-elevated) 100%)',
          cursor: 'pointer',
        }}
        onClick={() => onSelectTab('multilingual')}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(139, 92, 246, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--brand-purple)',
              }}
            >
              <Globe2 size={18} />
            </div>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-purple)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Issue #6 Multilingual
            </span>
          </div>
          <span className="badge badge-purple" style={{ fontSize: '10px' }}>18 Languages</span>
        </div>

        <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
          European & East Asian
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          12 European (FR, DE, RU...) + 6 East Asian (ZH, JA, KO, VI...)
        </p>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span className="mono" style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-primary)' }}>
            18
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Target languages matrix</span>
        </div>
      </div>
    </div>
  );
};
