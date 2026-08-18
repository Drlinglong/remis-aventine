import React from 'react';
import { Search, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenSearch: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onSelectTab,
  isDark,
  onToggleTheme,
  onOpenSearch,
}) => {
  const navItems = [
    { id: 'leaderboard', label: 'Overview' },
    { id: 'multilingual', label: '18 Directions' },
    { id: 'charts', label: 'Frontier Charts' },
    { id: 'arena', label: '9x9 Arena' },
    { id: 'calibration', label: 'Evidence' },
    { id: 'changelog', label: 'Changelog' },
    { id: 'methodology', label: 'Methodology' },
  ];

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backgroundColor: isDark ? 'rgba(12, 14, 20, 0.92)' : 'rgba(255, 255, 255, 0.92)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-subtle)',
        transition: 'background-color 0.2s ease, border-color 0.2s ease',
      }}
    >
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '64px', gap: '16px' }}>
        {/* Brand Lockup (Artificial Analysis style black pill / logo) */}
        <button
          onClick={() => onSelectTab('leaderboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            backgroundColor: isDark ? '#1a1e2b' : '#0f172a',
            color: '#ffffff',
            borderRadius: 'var(--radius-full)',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          <img
            src="./brand/aventine-mark-gold.svg"
            alt="Aventine"
            style={{ height: '18px', width: '18px' }}
            onError={(e) => {
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
          <span style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Aventine
          </span>
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
          className="hidden md:flex"
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
          {/* Pilot Spec Badge */}
          <span
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'rgba(139, 92, 246, 0.15)',
              color: 'var(--brand-purple)',
              fontSize: '12px',
              fontWeight: 700,
              display: 'none',
            }}
            className="lg:inline-flex"
          >
            Pilot v0.2
          </span>

          {/* Search Trigger */}
          <button
            onClick={onOpenSearch}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            <Search size={13} />
            <kbd
              style={{
                fontSize: '10px',
                padding: '1px 4px',
                backgroundColor: 'var(--bg-card-elevated)',
                border: '1px solid var(--border-medium)',
                borderRadius: '3px',
                color: 'var(--text-secondary)',
              }}
            >
              ⌘K
            </kbd>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={onToggleTheme}
            aria-label="Toggle theme"
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
            aria-label="GitHub Repository"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: isDark ? '#1a1e2b' : '#0f172a',
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
