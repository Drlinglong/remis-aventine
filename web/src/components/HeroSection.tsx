import React from 'react';
import { ArrowUpRight } from 'lucide-react';

interface HeroSectionProps {
  onSelectTab: (tab: string) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onSelectTab }) => {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)',
        gap: '48px',
        alignItems: 'center',
        paddingTop: '32px',
        paddingBottom: '40px',
      }}
      className="hero-grid"
    >
      {/* Left Column: Big Editorial Serif Title */}
      <div>
        <h1
          className="display-serif"
          style={{
            fontSize: 'clamp(42px, 5.5vw, 64px)',
            color: 'var(--text-primary)',
            letterSpacing: '-0.03em',
            lineHeight: 1.05,
            marginBottom: '16px',
          }}
        >
          Independent
          <br />
          analysis of AI
          <br />
          translation
        </h1>
        <p
          style={{
            fontSize: '16px',
            color: 'var(--text-secondary)',
            maxWidth: '520px',
            lineHeight: 1.5,
          }}
        >
          Understand translation recipes, hard-reliability vetoes, and 18-direction benchmark frontiers for game localization.
        </p>
      </div>

      {/* Right Column: Update Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Card 1 */}
        <div
          className="av-card"
          style={{
            padding: '18px 20px',
            backgroundColor: 'var(--bg-card)',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onClick={() => onSelectTab('changelog')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '10px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--brand-purple)' }}>
              PILOT TOURNAMENT
            </span>
            <ArrowUpRight size={14} color="var(--text-muted)" />
          </div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
            Nine-Model Round-Robin Benchmark
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            Gemini 3.6 Flash finishes #1 with 84.21 score, 100% hard pass, and lowest latency among high reasoning contestants.
          </p>
        </div>

        {/* Card 2 */}
        <div
          className="av-card"
          style={{
            padding: '18px 20px',
            backgroundColor: 'var(--bg-card)',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onClick={() => onSelectTab('multilingual')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '10px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--brand-purple)' }}>
              SPECIFICATION
            </span>
            <ArrowUpRight size={14} color="var(--text-muted)" />
          </div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
            18 Directions & Dual-Judge Architecture
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            ZH↔EN (2), ZH/EN→JA·KO (4), and ZH/EN→six Continental targets (12), with no minor-language cross-pairs.
          </p>
        </div>
      </div>
    </div>
  );
};
