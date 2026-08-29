import { useEffect, useState } from 'react';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { ModelDetailPage } from './components/ModelDetailPage';
import { HeroSection, CredibilityStrip } from './components/HeroSection';
import { V03Visualizations } from './components/V03Visualizations';
import { ZhEnPreviewLeaderboard } from './components/ZhEnPreviewLeaderboard';
import { MethodologyView } from './components/MethodologyView';
import { PairwiseHeatmap } from './components/PairwiseHeatmap';
import { ChangelogTimeline } from './components/ChangelogTimeline';
import { RecipeDrawer } from './components/RecipeDrawer';
import { loadZhEnPreview } from './data/zhEnPreview';
import type { ZhEnPreviewArtifact } from './types/zhEnPreview';
import type { RecipeEntry } from './types/benchmark';
import { useI18n } from './i18n/I18nProvider';

export const App = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [isDark, setIsDark] = useState(false);
  const [result, setResult] = useState<ZhEnPreviewArtifact | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<RecipeEntry | null>(null);
  const requestedModelId = new URLSearchParams(window.location.search).get('model');

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
    const url = new URL(window.location.href);
    url.searchParams.delete('model');
    window.history.replaceState({}, '', url);
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
        {requestedModelId && result?.profiles.find((profile) => profile.model_id === requestedModelId) && (
          <ModelDetailPage
            artifact={result}
            profile={result.profiles.find((profile) => profile.model_id === requestedModelId)!}
            onBack={() => selectTab('leaderboard')}
          />
        )}
        {!requestedModelId && <>
        {activeTab === 'leaderboard' && (
          <div className="animate-fade-in">
            <HeroSection onSelectTab={selectTab} result={result} />
            <CredibilityStrip />
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

        {activeTab === 'arena' && (
          <div className="animate-fade-in" style={{ paddingTop: 32 }}>
            <div style={{ marginBottom: 24 }}>
              <span className="badge badge-gold" style={{ marginBottom: 8 }}>{t('arena.badge')}</span>
              <h1 className="display-serif" style={{ fontSize: 38, color: 'var(--text-primary)', marginBottom: 8 }}>
                {t('arena.title')}
              </h1>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', maxWidth: 800, lineHeight: 1.5 }}>
                {t('arena.description')}
              </p>
            </div>
            <PairwiseHeatmap onSelectModel={setSelectedModel} />
          </div>
        )}

        {activeTab === 'methodology' && (
          <div className="animate-fade-in" style={{ paddingTop: 32 }}>
            <MethodologyView />
          </div>
        )}

        {activeTab === 'changelog' && (
          <div className="animate-fade-in" style={{ paddingTop: 32 }}>
            <ChangelogTimeline />
          </div>
        )}
        </>}
      </main>

      <Footer onSelectTab={selectTab} />
      <RecipeDrawer recipe={selectedModel} onClose={() => setSelectedModel(null)} onSelectTab={selectTab} />
    </div>
  );
};

export default App;
