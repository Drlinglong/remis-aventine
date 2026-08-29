import React from 'react';
import { Shield, BookOpen, GitBranch, ExternalLink } from 'lucide-react';

interface FooterProps {
  onSelectTab: (tab: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onSelectTab }) => {
  return (
    <footer
      style={{
        marginTop: '80px',
        borderTop: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-card)',
        padding: '50px 0 30px',
        transition: 'background-color 0.2s ease, border-color 0.2s ease',
      }}
    >
      <div className="container">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '40px', marginBottom: '40px' }}>
          {/* Col 1: About Aventine */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <span style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>Aventine</span>
              <span className="badge badge-gold">ZH–EN PREVIEW v0.3</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '16px' }}>
              A reproducible evaluation ground for translation recipes, born from <a href="https://github.com/Drlinglong/Remis" target="_blank" rel="noreferrer" style={{ color: 'var(--brand-gold)', textDecoration: 'underline' }}>Remis</a>.
              Evaluating complete translation pipelines, not isolated model names.
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span className="badge badge-neutral">AGPL-3.0</span>
              <span className="badge badge-emerald">JSON Schema Bound</span>
            </div>
          </div>

          {/* Col 2: Four Core Rules */}
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Shield size={14} color="var(--brand-gold)" /> The 4 Hard Principles
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <li>1. Hard validators have veto power</li>
              <li>2. Judge evaluates soft quality</li>
              <li>3. Output is structured data</li>
              <li>4. External datasets stay external</li>
            </ul>
          </div>

          {/* Col 3: Navigation & Sections */}
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BookOpen size={14} color="var(--brand-blue)" /> Quick Links
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <li><button onClick={() => onSelectTab('leaderboard')} style={{ color: 'inherit', textAlign: 'left' }}>🏆 Comprehensive Leaderboard</button></li>
              <li><button onClick={() => onSelectTab('multilingual')} style={{ color: 'inherit', textAlign: 'left' }}>🌐 ZH–EN Results (2/18)</button></li>
              <li><button onClick={() => onSelectTab('charts')} style={{ color: 'inherit', textAlign: 'left' }}>📈 Pareto Frontier & Charts</button></li>
              <li><button onClick={() => onSelectTab('arena')} style={{ color: 'inherit', textAlign: 'left' }}>⚔️ Historical 9×9 Arena</button></li>
              <li><button onClick={() => onSelectTab('calibration')} style={{ color: 'inherit', textAlign: 'left' }}>🎯 MQM / ACES Calibration</button></li>
              <li><button onClick={() => onSelectTab('methodology')} style={{ color: 'inherit', textAlign: 'left' }}>📖 Scoring Methodology</button></li>
            </ul>
          </div>

          {/* Col 4: Repository & Artifacts */}
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <GitBranch size={14} color="var(--brand-emerald)" /> Ecosystem & Code
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <li>
                <a href="https://github.com/Drlinglong/remis-aventine" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  GitHub Repository <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="https://github.com/Drlinglong/remis-aventine/issues/6" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  Issue #6: 18-Lang Frontier Benchmark <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="https://github.com/Drlinglong/remis-aventine/tree/main/src/remis_aventine/schemas" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  JSON Schema Contracts <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="https://artificialanalysis.ai" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)' }}>
                  Aesthetics Reference: Artificial Analysis <ExternalLink size={12} />
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom copyright line */}
        <div
          style={{
            paddingTop: '24px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            fontSize: '12px',
            color: 'var(--text-muted)',
          }}
        >
          <div>
            © 2026 Aventine Project. Released under AGPL-3.0 License. All evaluation artifacts are cryptographic SHA-256 bound.
          </div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <span>Score Policy: <code>v0.3-zh-en-60soft-40hard</code></span>
            <span>Artifact: <code>zh-en-preview.v1</code></span>
          </div>
        </div>
      </div>
    </footer>
  );
};
