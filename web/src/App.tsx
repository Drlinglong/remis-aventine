import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { HeroSection } from './components/HeroSection';
import { HighlightsBarSection } from './components/HighlightsBarSection';
import { ScatterChart } from './components/ScatterChart';
import { LeaderboardTable } from './components/LeaderboardTable';
import { RadarComparison } from './components/RadarComparison';
import { PairwiseHeatmap } from './components/PairwiseHeatmap';
import { CalibrationView } from './components/CalibrationView';
import { ChangelogTimeline } from './components/ChangelogTimeline';
import { MethodologyView } from './components/MethodologyView';
import { RecipeDrawer } from './components/RecipeDrawer';
import { CommandPalette } from './components/CommandPalette';
import { V03Leaderboard } from './components/V03Leaderboard';
import { ZhEnPreviewLeaderboard } from './components/ZhEnPreviewLeaderboard';
import { loadV03Leaderboard } from './data/v03Leaderboard';
import { loadZhEnPreview } from './data/zhEnPreview';
import type { RecipeEntry } from './types/benchmark';
import type { V03LeaderboardArtifact } from './types/v03';
import type { ZhEnPreviewArtifact } from './types/zhEnPreview';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('leaderboard');
  const [selectedModel, setSelectedModel] = useState<RecipeEntry | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isDark, setIsDark] = useState(false); // Default clean light/dark support
  const [v03Artifact, setV03Artifact] = useState<V03LeaderboardArtifact | null>(null);
  const [v03LoadError, setV03LoadError] = useState<string | null>(null);
  const [zhEnPreview, setZhEnPreview] = useState<ZhEnPreviewArtifact | null>(null);
  const [zhEnLoadError, setZhEnLoadError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  useEffect(() => {
    const controller = new AbortController();
    loadV03Leaderboard(controller.signal)
      .then(setV03Artifact)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setV03LoadError(error instanceof Error ? error.message : String(error));
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadZhEnPreview(controller.signal)
      .then(setZhEnPreview)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setZhEnLoadError(error instanceof Error ? error.message : String(error));
      });
    return () => controller.abort();
  }, []);

  const handleToggleTheme = () => {
    setIsDark(!isDark);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-main)' }}>
      {/* Global Header */}
      <Header
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        isDark={isDark}
        onToggleTheme={handleToggleTheme}
        onOpenSearch={() => setIsSearchOpen(true)}
      />

      {/* Main Container */}
      <main className="container" style={{ flex: 1 }}>
        {/* VIEW 1: OVERVIEW / LEADERBOARD (Artificial Analysis 1:1 Flow) */}
        {activeTab === 'leaderboard' && (
          <div className="animate-fade-in">
            {/* 1. Hero Section (Editorial Serif + Updates) */}
            <HeroSection
              onSelectTab={(tab) => {
                setActiveTab(tab);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              artifact={v03Artifact}
              preview={zhEnPreview}
            />

            {zhEnPreview ? (
              <ZhEnPreviewLeaderboard artifact={zhEnPreview} />
            ) : v03Artifact ? (
              <V03Leaderboard artifact={v03Artifact} />
            ) : (
              <div className="v03-panel" style={{ padding: '14px 16px', marginTop: 20, marginBottom: 24 }}>
                <strong>Multilingual v0.3 · awaiting public artifact</strong>
                <p style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
                  No public result artifact was found.
                  {zhEnLoadError || v03LoadError ? ` (${zhEnLoadError || v03LoadError})` : ''}
                </p>
              </div>
            )}

            <div className="section-title" style={{ marginTop: 28 }}>
              <span>Historical pilot · v0.1 + anchored v0.2</span>
            </div>

            {/* 2. Highlights Visual Vertical Bar Cards (Pilot Score / Speed / Cost) */}
            <HighlightsBarSection
              onSelectModel={(m) => setSelectedModel(m)}
              onSelectTab={(tab) => {
                setActiveTab(tab);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />

            {/* 3. Interactive Pareto Frontier Scatter Plot */}
            <div style={{ marginTop: '16px', marginBottom: '40px' }}>
              <div className="section-title">
                <span>Frontier Trade-offs</span>
              </div>
              <ScatterChart onSelectModel={(m) => setSelectedModel(m)} />
            </div>

            {/* 4. Complete Leaderboard Table */}
            <div style={{ marginTop: '16px', marginBottom: '40px' }}>
              <div className="section-title">
                <span>Full Benchmark Leaderboard</span>
              </div>
              <LeaderboardTable onSelectModel={(m) => setSelectedModel(m)} />
            </div>

            {/* 5. 6-Dimension Capability Radar */}
            <div style={{ marginTop: '16px', marginBottom: '40px' }}>
              <div className="section-title">
                <span>Capability Dimensions</span>
              </div>
              <RadarComparison onSelectModel={(m) => setSelectedModel(m)} />
            </div>
          </div>
        )}

        {/* VIEW 2: 18 LANGUAGES MATRIX */}
        {activeTab === 'multilingual' && (
          <div className="animate-fade-in" style={{ paddingTop: '32px' }}>
            <div style={{ marginBottom: '24px' }}>
              <span className="badge badge-purple" style={{ marginBottom: '8px' }}>2 OF 18 DIRECTIONS COMPLETE</span>
              <h1 className="display-serif" style={{ fontSize: '38px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                ZH–EN Core Preview
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '800px', lineHeight: 1.5 }}>
                The two highest-priority directions are measured now: zh-CN→en and en→zh-CN. The remaining 16 directions stay unmeasured and are never estimated or renormalized into this preview.
              </p>
            </div>
            {zhEnPreview ? (
              <ZhEnPreviewLeaderboard artifact={zhEnPreview} />
            ) : v03Artifact ? (
              <V03Leaderboard artifact={v03Artifact} />
            ) : (
              <div className="v03-panel" style={{ padding: 20 }}>
                The v0.3 exam is frozen and ready, but no 18-direction result has been published.
                Historical v0.2 language estimates are intentionally excluded from this view.
              </div>
            )}
          </div>
        )}

        {/* VIEW 3: FRONTIER CHARTS */}
        {activeTab === 'charts' && (
          <div className="animate-fade-in" style={{ paddingTop: '32px' }}>
            <div style={{ marginBottom: '24px' }}>
              <span className="badge badge-gold" style={{ marginBottom: '8px' }}>PARETO EFFICIENCY</span>
              <h1 className="display-serif" style={{ fontSize: '38px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                Frontier Scatter Plots & Trade-offs
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '800px', lineHeight: 1.5 }}>
                Examine intelligence vs. latency, token efficiency, and per-task pricing frontiers inspired by Artificial Analysis.
              </p>
            </div>
            <ScatterChart onSelectModel={(m) => setSelectedModel(m)} />
            <RadarComparison onSelectModel={(m) => setSelectedModel(m)} />
          </div>
        )}

        {/* VIEW 4: 9x9 ARENA */}
        {activeTab === 'arena' && (
          <div className="animate-fade-in" style={{ paddingTop: '32px' }}>
            <div style={{ marginBottom: '24px' }}>
              <span className="badge badge-gold" style={{ marginBottom: '8px' }}>ROUND-ROBIN TOURNAMENT</span>
              <h1 className="display-serif" style={{ fontSize: '38px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                9x9 Head-to-Head Arena Matrix
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '800px', lineHeight: 1.5 }}>
                Inspect every pairwise matchup across all 36 candidate pairs. Double-order swap consistency ensures robust, position-unbiased decisions.
              </p>
            </div>
            <PairwiseHeatmap onSelectModel={(m) => setSelectedModel(m)} />
          </div>
        )}

        {/* VIEW 5: EVIDENCE & CALIBRATION */}
        {activeTab === 'calibration' && (
          <div className="animate-fade-in" style={{ paddingTop: '32px' }}>
            <div style={{ marginBottom: '24px' }}>
              <span className="badge badge-emerald" style={{ marginBottom: '8px' }}>GROUND TRUTH EVIDENCE</span>
              <h1 className="display-serif" style={{ fontSize: '38px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                Judge Calibration & Baseline Alignment
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '800px', lineHeight: 1.5 }}>
                Empirical verification of judge recall on severe errors against professional MQM annotations and ACES contrastive challenge sets.
              </p>
            </div>
            <CalibrationView />
          </div>
        )}

        {/* VIEW 6: CHANGELOG */}
        {activeTab === 'changelog' && (
          <div className="animate-fade-in" style={{ paddingTop: '32px' }}>
            <ChangelogTimeline />
          </div>
        )}

        {/* VIEW 7: METHODOLOGY */}
        {activeTab === 'methodology' && (
          <div className="animate-fade-in" style={{ paddingTop: '32px' }}>
            <MethodologyView />
          </div>
        )}
      </main>

      {/* Global Footer */}
      <Footer
        onSelectTab={(tab) => {
          setActiveTab(tab);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />

      {/* Recipe Detail Slide-out Drawer */}
      <RecipeDrawer
        recipe={selectedModel}
        onClose={() => setSelectedModel(null)}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          setSelectedModel(null);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />

      {/* Command Palette Modal */}
      <CommandPalette
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectModel={(m) => setSelectedModel(m)}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />
    </div>
  );
};

export default App;
