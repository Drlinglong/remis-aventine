import { useEffect, useState } from 'react';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { HeroSection } from './components/HeroSection';
import { V03Visualizations } from './components/V03Visualizations';
import { ZhEnPreviewLeaderboard } from './components/ZhEnPreviewLeaderboard';
import { loadZhEnPreview } from './data/zhEnPreview';
import type { ZhEnPreviewArtifact } from './types/zhEnPreview';
import { useI18n } from './i18n/I18nProvider';

export const App = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [isDark, setIsDark] = useState(false);
  const [result, setResult] = useState<ZhEnPreviewArtifact | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  useEffect(() => {
    const controller = new AbortController();
    loadZhEnPreview(controller.signal)
      .then(setResult)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLoadError(error instanceof Error ? error.message : String(error));
      });
    return () => controller.abort();
  }, []);

  const selectTab = (tab: string) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const resultPanel = result ? (
    <>
      <V03Visualizations artifact={result} />
      <ZhEnPreviewLeaderboard artifact={result} />
    </>
  ) : (
    <div className="v03-panel" style={{ padding: 20, marginTop: 24 }}>
      <strong>{t('results.unavailable')}</strong>
      {loadError && <p style={{ color: 'var(--text-secondary)', marginTop: 6 }}>{loadError}</p>}
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-main)' }}>
      <Header
        activeTab={activeTab}
        onSelectTab={selectTab}
        isDark={isDark}
        onToggleTheme={() => setIsDark((current) => !current)}
      />

      <main className="container" style={{ flex: 1 }}>
        {activeTab === 'leaderboard' && (
          <div className="animate-fade-in">
            <HeroSection onSelectTab={selectTab} result={result} />
            {resultPanel}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="animate-fade-in" style={{ paddingTop: 32 }}>
            <div style={{ marginBottom: 24 }}>
              <span className="badge badge-gold" style={{ marginBottom: 8 }}>{t('results.badge')}</span>
              <h1 className="display-serif" style={{ fontSize: 38, color: 'var(--text-primary)', marginBottom: 8 }}>
                {t('results.title')}
              </h1>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', maxWidth: 800, lineHeight: 1.5 }}>
                {t('results.description')}
              </p>
            </div>
            {resultPanel}
          </div>
        )}
      </main>

      <Footer onSelectTab={selectTab} />
    </div>
  );
};

export default App;
