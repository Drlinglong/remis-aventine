import { useEffect, useMemo, useState } from 'react';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { ModelDetailPage } from './components/ModelDetailPage';
import { HeroSection, CredibilityStrip } from './components/HeroSection';
import { ResultsExplorer } from './components/ResultsExplorer';
import { MethodologyView } from './components/MethodologyView';
import { PairwiseHeatmap } from './components/PairwiseHeatmap';
import { ChangelogTimeline } from './components/ChangelogTimeline';
import { RecipeDrawer } from './components/RecipeDrawer';
import { loadZhEnPreview } from './data/zhEnPreview';
import { buildZhEnCatalog } from './data/zhEnCatalog';
import type { ZhEnPreviewArtifact } from './types/zhEnPreview';
import type { RecipeEntry } from './types/benchmark';
import { useI18n } from './i18n/I18nProvider';

export const App = () => {
  const { t, locale } = useI18n();
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [isDark, setIsDark] = useState(false);
  const [historical, setHistorical] = useState<ZhEnPreviewArtifact | null>(null);
  const [current, setCurrent] = useState<ZhEnPreviewArtifact | null>(null);
  const [showHistory, setShowHistory] = useState(() => new URLSearchParams(window.location.search).get('view') === 'history');
  const catalog = useMemo(() => historical && current ? buildZhEnCatalog(historical, current) : current ?? historical, [historical, current]);
  const result = showHistory ? historical : catalog;
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<RecipeEntry | null>(null);
  const [requestedModelId, setRequestedModelId] = useState(() => new URLSearchParams(window.location.search).get('model'));
  const requestedVersion = new URLSearchParams(window.location.search).get('score_version');
  const sources = [historical, current];
  const detailArtifact = sources.find((artifact) => artifact?.score_version === requestedVersion && artifact.profiles.some((profile) => profile.model_id === requestedModelId))
    ?? sources.find((artifact) => artifact?.profiles.some((profile) => profile.model_id === requestedModelId));
  const searchProfiles = catalog?.profiles ?? [];
  const scoreVersions = new Map<string, string>();
  for (const profile of searchProfiles) scoreVersions.set(profile.model_id, profile.score_version ?? catalog!.score_version);
  const selectCohort = (history: boolean) => {
    const url = new URL(window.location.href);
    url.searchParams.delete('score_version');
    if (history) url.searchParams.set('view', 'history');
    else url.searchParams.delete('view');
    window.history.replaceState({}, '', url);
    setShowHistory(history);
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.allSettled([loadZhEnPreview(controller.signal), loadZhEnPreview(controller.signal, 'v03-zh-en-anchors-20260925.json')])
      .then(([old, next]) => {
        if (controller.signal.aborted) return;
        if (old.status === 'fulfilled') setHistorical(old.value);
        if (next.status === 'fulfilled') setCurrent(next.value);
        const failed = [old, next].find((entry) => entry.status === 'rejected');
        if (failed?.status === 'rejected') setLoadError(String(failed.reason));
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLoadError(error instanceof Error ? error.message : String(error));
      });
    return () => controller.abort();
  }, []);

  const selectTab = (tab: string) => {
    const url = new URL(window.location.href);
    url.searchParams.delete('model');
    url.searchParams.delete('score_version');
    window.history.replaceState({}, '', url);
    setRequestedModelId(null);
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const resultPanel = result ? (
    <>
      {current && historical && <div className="tab-group cohort-tabs" aria-label={locale === 'zh-CN' ? '榜单视图' : 'Leaderboard view'}>
        <button className={`tab-btn ${!showHistory ? 'active' : ''}`} onClick={() => selectCohort(false)}>{locale === 'zh-CN' ? `完整榜单 · ${catalog?.contestant_count} 个模型` : `All models · ${catalog?.contestant_count}`}</button>
        <button className={`tab-btn ${showHistory ? 'active' : ''}`} onClick={() => selectCohort(true)}>{locale === 'zh-CN' ? '原始快照 · 2026-08' : 'Original snapshot · Aug 2026'}</button>
      </div>}
      <ResultsExplorer key={result.catalog ? 'unified-catalog' : result.score_version} artifact={result} />
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
        profiles={searchProfiles}
        scoreVersions={scoreVersions}
      />

      <main className="container" style={{ flex: 1 }}>
        {requestedModelId && detailArtifact && (
          <ModelDetailPage
            artifact={detailArtifact}
            profile={detailArtifact.profiles.find((profile) => profile.model_id === requestedModelId)!}
            versions={sources.filter((artifact): artifact is ZhEnPreviewArtifact => Boolean(artifact?.profiles.some((profile) => profile.model_id === requestedModelId)))}
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

      <Footer onSelectTab={selectTab} result={detailArtifact ?? result} />
      <RecipeDrawer recipe={selectedModel} onClose={() => setSelectedModel(null)} onSelectTab={selectTab} />
    </div>
  );
};

export default App;
