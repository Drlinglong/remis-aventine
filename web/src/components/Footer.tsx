import React from 'react';
import { Shield, BookOpen, GitBranch, ExternalLink } from 'lucide-react';
import { useI18n } from '../i18n/I18nProvider';

interface FooterProps {
  onSelectTab: (tab: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onSelectTab }) => {
  const { t } = useI18n();
  const [aboutBefore, aboutAfter] = t('footer.about').split('{remis}');
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
              <span className="badge badge-gold">{t('footer.status')}</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '16px' }}>
              {aboutBefore}<a href="https://github.com/Drlinglong/Remis" target="_blank" rel="noreferrer" style={{ color: 'var(--brand-gold)', textDecoration: 'underline' }}>Remis</a>{aboutAfter}
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span className="badge badge-neutral">AGPL-3.0</span>
              <span className="badge badge-emerald">{t('footer.schema')}</span>
            </div>
          </div>

          {/* Col 2: Four Core Rules */}
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Shield size={14} color="var(--brand-gold)" /> {t('footer.principles')}
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <li>{t('footer.p1')}</li><li>{t('footer.p2')}</li><li>{t('footer.p3')}</li><li>{t('footer.p4')}</li>
            </ul>
          </div>

          {/* Col 3: Navigation & Sections */}
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BookOpen size={14} color="var(--brand-blue)" /> {t('footer.quick')}
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <li><button onClick={() => onSelectTab('leaderboard')} style={{ color: 'inherit', textAlign: 'left' }}>{t('footer.overview')}</button></li>
              <li><button onClick={() => onSelectTab('results')} style={{ color: 'inherit', textAlign: 'left' }}>{t('footer.results')}</button></li>
              <li><a href={`${import.meta.env.BASE_URL}data/v03-zh-en-results.json`} target="_blank" rel="noreferrer">{t('footer.json')}</a></li>
            </ul>
          </div>

          {/* Col 4: Repository & Artifacts */}
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <GitBranch size={14} color="var(--brand-emerald)" /> {t('footer.ecosystem')}
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <li>
                <a href="https://github.com/Drlinglong/remis-aventine" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  {t('footer.repo')} <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="https://github.com/Drlinglong/remis-aventine/issues/6" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  {t('footer.issue')} <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="https://github.com/Drlinglong/remis-aventine/tree/main/src/remis_aventine/schemas" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  {t('footer.contracts')} <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="https://artificialanalysis.ai" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)' }}>
                  {t('footer.reference')} <ExternalLink size={12} />
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
            {t('footer.copyright')}
          </div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <span>{t('footer.scorePolicy')} <code>v0.3-zh-en-60soft-40hard</code></span>
            <span>{t('footer.artifact')} <code>v0.3-zh-en-results</code></span>
          </div>
        </div>
      </div>
    </footer>
  );
};
