import React from 'react';
import { ArrowRight, ArrowUpRight } from 'lucide-react';
import type { V03LeaderboardArtifact } from '../types/v03';

interface HeroSectionProps {
  onSelectTab: (tab: string) => void;
  artifact: V03LeaderboardArtifact | null;
}

function modelName(artifact: V03LeaderboardArtifact): string {
  const leader = [...artifact.profiles]
    .filter((profile) => profile.scores.overall_intelligence.score !== null)
    .sort((left, right) => (right.scores.overall_intelligence.score ?? -1) - (left.scores.overall_intelligence.score ?? -1))[0];
  return leader?.recipe.requested_model || 'Awaiting publication';
}

function modelScore(artifact: V03LeaderboardArtifact): string {
  const leader = [...artifact.profiles]
    .filter((profile) => profile.scores.overall_intelligence.score !== null)
    .sort((left, right) => (right.scores.overall_intelligence.score ?? -1) - (left.scores.overall_intelligence.score ?? -1))[0];
  return leader?.scores.overall_intelligence.score?.toFixed(2) || 'Unmeasured';
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onSelectTab, artifact }) => {
  return (
    <section className="hero-editorial">
      <div className="hero-copy-column">
        <img src="./brand/aventine-mark-gold.svg" alt="" aria-hidden="true" className="hero-mark" />
        <span className="badge badge-gold" style={{ marginBottom: 12 }}>AI-native translation benchmark</span>
        <h1 className="display-serif" style={{ fontSize: 'clamp(44px, 6vw, 72px)', lineHeight: 1.02, marginBottom: 18 }}>
          Aventine is a leaderboard for complete translation recipes.
        </h1>
        <p style={{ fontSize: 18, color: 'var(--text-secondary)', maxWidth: 700, lineHeight: 1.6, marginBottom: 12 }}>
          We benchmark model, prompt, glossary, validation, and repair together—because the goal is to make AI translate best, not to score isolated model names.
        </p>
        <p style={{ fontSize: 16, color: 'var(--text-secondary)', maxWidth: 700, lineHeight: 1.6, marginBottom: 28 }}>
          Long term, Aventine tracks the systems work needed to eliminate language barriers in the LLM era.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <button className="hero-cta hero-cta-primary" onClick={() => onSelectTab('multilingual')}>
            Explore leaderboard <ArrowRight size={16} />
          </button>
          <button className="hero-cta hero-cta-secondary" onClick={() => onSelectTab('calibration')}>
            Review evidence <ArrowUpRight size={16} />
          </button>
        </div>
      </div>

      <aside className="av-card hero-benchmark-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
            Current benchmark
          </span>
          <span className="badge badge-neutral">v0.3 public artifact</span>
        </div>
        {artifact ? (
          <>
            <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 2 }}>Status</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 14 }}>
              {artifact.status === 'complete' ? 'Complete' : 'Incomplete'}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Contestants</div>
                <div className="mono" style={{ fontSize: 16, fontWeight: 700 }}>{artifact.contestant_count}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Matches</div>
                <div className="mono" style={{ fontSize: 16, fontWeight: 700 }}>{artifact.match_count}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Top profile</div>
                <div style={{ fontSize: 13, fontWeight: 700 }}>{modelName(artifact)}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Top score</div>
                <div className="mono" style={{ fontSize: 16, fontWeight: 700 }}>{modelScore(artifact)}</div>
              </div>
            </div>
            <button className="hero-cta hero-cta-secondary" onClick={() => onSelectTab('multilingual')} style={{ width: '100%', justifyContent: 'center' }}>
              Open 18-direction table
            </button>
          </>
        ) : (
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            Waiting for a published v0.3 public result artifact.
          </p>
        )}
      </aside>
    </section>
  );
};
