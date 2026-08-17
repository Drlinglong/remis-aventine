import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { HeroSection } from './components/HeroSection';
import { HighlightsBarSection } from './components/HighlightsBarSection';
import { ScatterChart } from './components/ScatterChart';
import { LeaderboardTable } from './components/LeaderboardTable';
import { MultilingualMatrix } from './components/MultilingualMatrix';
import { RadarComparison } from './components/RadarComparison';
import { PairwiseHeatmap } from './components/PairwiseHeatmap';
import { CalibrationView } from './components/CalibrationView';
import { ChangelogTimeline } from './components/ChangelogTimeline';
import { MethodologyView } from './components/MethodologyView';
import { RecipeDrawer } from './components/RecipeDrawer';
import { CommandPalette } from './components/CommandPalette';
import type { RecipeEntry } from './types/benchmark';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('leaderboard');
  const [selectedModel, setSelectedModel] = useState<RecipeEntry | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isDark, setIsDark] = useState(false); // Default clean light/dark support

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

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
            />

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
              <span className="badge badge-purple" style={{ marginBottom: '8px' }}>ISSUE #6 REGIONAL SPEC</span>
              <h1 className="display-serif" style={{ fontSize: '38px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                18 Languages Multilingual Leaderboard
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '800px', lineHeight: 1.5 }}>
                Equal-weighted aggregation across 12 European languages and 6 East Asian languages, penalizing failure modes using stage-specific multipliers.
              </p>
            </div>
            <MultilingualMatrix onSelectModel={(m) => setSelectedModel(m)} />
            <RadarComparison onSelectModel={(m) => setSelectedModel(m)} />
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
