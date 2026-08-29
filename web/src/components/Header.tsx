import React from 'react';
import { Sun, Moon, Languages } from 'lucide-react';
import { LOCALES, useI18n, type Locale } from '../i18n/I18nProvider';

interface HeaderProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onSelectTab,
  isDark,
  onToggleTheme,
}) => {
  const { locale, setLocale, t } = useI18n();
  const navItems = [
    { id: 'leaderboard', label: t('nav.overview') },
    { id: 'results', label: t('nav.results') },
  ];

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backgroundColor: isDark ? 'rgba(22, 28, 36, 0.92)' : 'rgba(247, 241, 230, 0.92)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-subtle)',
        transition: 'background-color 0.2s ease, border-color 0.2s ease',
      }}
    >
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '64px', gap: '16px' }}>
        {/* Canonical Aventine brand lockup */}
        <button
          className="header-brand"
          onClick={() => onSelectTab('leaderboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: 0,
            backgroundColor: 'transparent',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          <img
            src={isDark ? './brand/aventine-lockup-on-dark.svg' : './brand/aventine-lockup-on-light.svg'}
            alt="Aventine"
            className="header-brand-logo"
            onError={(e) => {
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
        </button>

        {/* Center Pill Nav Bar (Artificial Analysis style) */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2px',
            backgroundColor: 'var(--bg-input)',
            padding: '4px 6px',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--border-subtle)',
          }}
          className="header-nav hidden md:flex"
        >
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  backgroundColor: isActive ? 'var(--bg-card-elevated)' : 'transparent',
                  border: 'none',
                  boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap',
                }}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label className="language-picker" title={t('nav.language')}>
            <Languages size={14} aria-hidden="true" />
            <select aria-label={t('nav.language')} value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
              {LOCALES.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
            </select>
          </label>
          {/* Pilot Spec Badge */}
          <span
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'color-mix(in srgb, var(--brand-purple) 18%, transparent)',
              color: 'var(--brand-purple)',
              fontSize: '12px',
              fontWeight: 700,
              display: 'none',
            }}
            className="lg:inline-flex"
          >
            ZH–EN v0.3
          </span>

          {/* Theme Toggle */}
          <button
            onClick={onToggleTheme}
            aria-label={t('a11y.theme')}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            {isDark ? <Sun size={15} /> : <Moon size={15} />}
          </button>

          {/* GitHub Repo */}
          <a
            href="https://github.com/Drlinglong/remis-aventine"
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t('a11y.github')}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: isDark ? '#2a2e35' : '#161c24',
              color: '#ffffff',
              border: 'none',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
};
