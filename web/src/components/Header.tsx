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
    { id: 'arena', label: t('nav.arena') },
    { id: 'methodology', label: t('nav.methodology') },
    { id: 'changelog', label: t('nav.changelog') },
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

        {/* Center Pill Nav Bar */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '4px',
            backgroundColor: 'var(--bg-card)',
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
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-full)',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                  backgroundColor: isActive ? 'var(--bg-card-elevated)' : 'transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
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
          {/* Published scope badge */}
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
            {t('benchmark.scope')}
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
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            {isDark ? <Sun size={15} /> : <Moon size={15} />}
          </button>

          {/* GitHub Link */}
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
            <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
              <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
};
