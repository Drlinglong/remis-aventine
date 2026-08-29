import React, { useState } from 'react';
import { MessageSquareDot, ShieldAlert, Cpu, Award, Calendar } from 'lucide-react';
import { CHANGELOG_DATA } from '../data/changelogData';
import type { ChangelogItem } from '../types/benchmark';

export const ChangelogTimeline: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  const categories = ['All', 'Tournaments', 'Model Releases', 'Calibration', 'Infrastructure'];

  const filteredItems = CHANGELOG_DATA.filter((item) => {
    if (selectedCategory === 'All') return true;
    return item.category === selectedCategory;
  });

  const getCategoryIcon = (category: ChangelogItem['category']) => {
    switch (category) {
      case 'Tournaments':
        return <Award size={16} color="var(--brand-gold)" />;
      case 'Model Releases':
        return <MessageSquareDot size={16} color="var(--brand-blue)" />;
      case 'Calibration':
        return <ShieldAlert size={16} color="var(--brand-emerald)" />;
      case 'Infrastructure':
        return <Cpu size={16} color="var(--brand-purple)" />;
    }
  };

  const getCategoryBadge = (category: ChangelogItem['category']) => {
    switch (category) {
      case 'Tournaments':
        return 'badge-gold';
      case 'Model Releases':
        return 'badge-blue';
      case 'Calibration':
        return 'badge-emerald';
      case 'Infrastructure':
        return 'badge-purple';
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '32px', marginBottom: '40px' }}>
      {/* Left Sidebar: Filter & Info */}
      <div style={{ position: 'sticky', top: '90px', height: 'fit-content' }}>
        <h1 style={{ fontSize: '32px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Changelog
        </h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '24px' }}>
          Track the latest translation recipe benchmarks, model placements, calibration updates, and runner reliability milestones.
        </p>

        {/* Category Pill Filters */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '24px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Filter by Category
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {categories.map((cat) => {
              const isSelected = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 'var(--radius-full)',
                    fontSize: '12px',
                    fontWeight: isSelected ? 600 : 500,
                    backgroundColor: isSelected ? 'var(--bg-card-elevated)' : 'var(--bg-card)',
                    border: isSelected ? '1px solid var(--brand-gold)' : '1px solid var(--border-subtle)',
                    color: isSelected ? 'var(--brand-gold)' : 'var(--text-secondary)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {cat}
                </button>
              );
            })}
          </div>
        </div>

        {/* Info Banner Box (Artificial Analysis style) */}
        <div
          className="av-card"
          style={{
            padding: '16px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
            Evaluation Ground History
          </div>
          Aventine evaluation logs begin 14 Jul 2026 for schema contracts, moving to 9-model automated round-robin on 01 Aug 2026.
        </div>
      </div>

      {/* Right Timeline Feed */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '720px' }}>
        {filteredItems.map((item) => (
          <div key={item.id} className="av-card animate-fade-in" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
            {/* Timeline Top Meta */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: 'var(--radius-full)',
                    backgroundColor: 'var(--bg-card-elevated)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {getCategoryIcon(item.category)}
                </div>
                <span className={`badge ${getCategoryBadge(item.category)}`} style={{ fontSize: '10px' }}>
                  {item.category}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
                <Calendar size={13} />
                <span>{item.date}</span>
              </div>
            </div>

            {/* Title & Summary */}
            <h3 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
              {item.title}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '16px' }}>
              {item.summary}
            </p>

            {/* Model & Pilot Score Highlight if applicable */}
            {(item.model_tag || item.pilot_score) && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  backgroundColor: 'var(--bg-card-elevated)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '16px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Contestant Recipe: </span>
                  <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{item.model_tag}</strong>
                </div>
                {item.pilot_score && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Pilot Score:</span>
                    <span className="mono" style={{ fontSize: '15px', fontWeight: 800, color: 'var(--brand-gold)' }}>
                      {item.pilot_score.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Highlights bullet list */}
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              {item.highlights.map((h, i) => (
                <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  <span style={{ color: 'var(--brand-gold)', fontWeight: 700 }}>•</span>
                  <span>{h}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};
