import { useMemo, useState } from 'react';
import { getVendorBrand } from '../data/vendorBrands';
import { zhEnProfileName } from '../data/zhEnProfileName';
import type { ZhEnMeasure, ZhEnPreviewArtifact, ZhEnPreviewProfile } from '../types/zhEnPreview';

function aggregate(profile: ZhEnPreviewProfile, kind: 'soft' | 'hard'): ZhEnMeasure {
  const values = Object.values(profile.directions).map((direction) => direction[kind]);
  const total = values.reduce((sum, value) => sum + value.total, 0);
  const resolved = values.reduce((sum, value) => sum + value.resolved, 0);
  return {
    coverage: resolved / total,
    points: values.reduce((sum, value) => sum + value.points, 0),
    resolved,
    score: values.reduce((sum, value) => sum + value.score, 0) / values.length,
    total,
  };
}

function color(profile: ZhEnPreviewProfile): string {
  return getVendorBrand(profile.model_family, profile.model_id).color;
}

function ScoreBars({ profiles }: { profiles: ZhEnPreviewProfile[] }) {
  const ranked = [...profiles].sort((left, right) => right.zh_en_score - left.zh_en_score);
  return (
    <div className="av-card" style={{ padding: 24, backgroundColor: 'var(--bg-card)' }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>Current score distribution</h2>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>All 17 recipes, ranked on the published ZH–EN v0.3 score.</p>
      <div style={{ overflowX: 'auto', marginTop: 24 }}>
        <div style={{ minWidth: 780, height: 270, display: 'flex', alignItems: 'flex-end', gap: 8, borderBottom: '1px solid var(--border-medium)', padding: '0 8px 8px' }}>
          {ranked.map((profile, index) => (
            <div key={profile.execution_identity_sha256} title={`${zhEnProfileName(profile)}: ${profile.zh_en_score.toFixed(2)}`} style={{ flex: 1, height: '100%', minWidth: 32, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center' }}>
              <strong className="mono" style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 5 }}>{profile.zh_en_score.toFixed(1)}</strong>
              <div style={{ width: '72%', maxWidth: 38, height: `${Math.max(8, profile.zh_en_score * 1.9)}px`, backgroundColor: color(profile), borderRadius: '4px 4px 1px 1px', opacity: 0.9 }} />
              <span style={{ height: 48, width: 50, marginTop: 8, fontSize: 9, lineHeight: 1.15, color: 'var(--text-muted)', textAlign: 'center', overflow: 'hidden' }}>
                {index + 1}. {zhEnProfileName(profile)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ParetoFrontier({ profiles }: { profiles: ZhEnPreviewProfile[] }) {
  const points = profiles
    .filter((profile) => profile.telemetry.cost_usd !== null)
    .map((profile) => ({ profile, cost: profile.telemetry.cost_usd as number, score: profile.zh_en_score }));
  const frontier = [...points]
    .sort((left, right) => left.cost - right.cost)
    .filter((point, index, sorted) => point.score > sorted.slice(0, index).reduce((best, prior) => Math.max(best, prior.score), -Infinity));
  const width = 900;
  const height = 430;
  const pad = { top: 36, right: 34, bottom: 62, left: 60 };
  const logMin = Math.log10(0.003);
  const logMax = Math.log10(3.2);
  const x = (value: number) => pad.left + ((Math.log10(value) - logMin) / (logMax - logMin)) * (width - pad.left - pad.right);
  const y = (value: number) => pad.top + (1 - value / 100) * (height - pad.top - pad.bottom);
  const costTicks = [0.003, 0.01, 0.03, 0.1, 0.3, 1, 3];
  const scoreTicks = [20, 40, 60, 80, 100];

  return (
    <div className="av-card" style={{ padding: 24, backgroundColor: 'var(--bg-card)' }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>Quality–cost Pareto frontier</h2>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>Higher quality and lower observed cost are better. Cost uses a logarithmic USD axis.</p>
      <div style={{ overflowX: 'auto', marginTop: 14 }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', minWidth: 720, height: 'auto' }} aria-label="ZH-EN quality-cost Pareto frontier">
          {scoreTicks.map((tick) => <g key={tick}><line x1={pad.left} y1={y(tick)} x2={width - pad.right} y2={y(tick)} stroke="var(--border-subtle)" strokeDasharray="4 5" /><text x={pad.left - 10} y={y(tick) + 4} textAnchor="end" fontSize="11" fill="var(--text-muted)">{tick}</text></g>)}
          {costTicks.map((tick) => <g key={tick}><line x1={x(tick)} y1={pad.top} x2={x(tick)} y2={height - pad.bottom} stroke="var(--border-subtle)" strokeDasharray="4 5" /><text x={x(tick)} y={height - pad.bottom + 22} textAnchor="middle" fontSize="11" fill="var(--text-muted)">${tick}</text></g>)}
          <polyline points={frontier.map((point) => `${x(point.cost)},${y(point.score)}`).join(' ')} fill="none" stroke="var(--brand-gold)" strokeWidth="3" strokeDasharray="7 5" />
          {points.map((point) => {
            const onFrontier = frontier.includes(point);
            return <g key={point.profile.execution_identity_sha256}><circle cx={x(point.cost)} cy={y(point.score)} r={onFrontier ? 7 : 5} fill={color(point.profile)} stroke="var(--bg-card)" strokeWidth="2"><title>{`${zhEnProfileName(point.profile)} · ${point.score.toFixed(2)} · $${point.cost.toFixed(3)}`}</title></circle>{onFrontier && <text x={x(point.cost) + 9} y={y(point.score) - 8} fontSize="10" fontWeight="700" fill="var(--text-secondary)">{zhEnProfileName(point.profile)}</text>}</g>;
          })}
          <text x={width / 2} y={height - 12} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--text-secondary)">Observed recipe cost (USD, log scale)</text>
          <text x={16} y={height / 2} transform={`rotate(-90 16 ${height / 2})`} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--text-secondary)">ZH–EN score</text>
        </svg>
      </div>
    </div>
  );
}

const RADAR_AXES = [
  ['Overall', (profile: ZhEnPreviewProfile) => profile.zh_en_score],
  ['ZH→EN', (profile: ZhEnPreviewProfile) => profile.directions['zh-CN->en'].score],
  ['EN→ZH', (profile: ZhEnPreviewProfile) => profile.directions['en->zh-CN'].score],
  ['Soft', (profile: ZhEnPreviewProfile) => aggregate(profile, 'soft').score],
  ['Hard', (profile: ZhEnPreviewProfile) => aggregate(profile, 'hard').score],
  ['Coverage', (profile: ZhEnPreviewProfile) => aggregate(profile, 'soft').coverage * 100],
] as const;

function SixAxisRadar({ profiles }: { profiles: ZhEnPreviewProfile[] }) {
  const ranked = useMemo(() => [...profiles].sort((left, right) => right.zh_en_score - left.zh_en_score), [profiles]);
  const [selected, setSelected] = useState(() => ranked.slice(0, 2).map((profile) => profile.model_id).concat('deepseek/deepseek-v4-pro-0813'));
  const chosen = selected.map((id) => profiles.find((profile) => profile.model_id === id)).filter(Boolean) as ZhEnPreviewProfile[];
  const size = 440;
  const center = size / 2;
  const radius = 150;
  const coordinate = (index: number, value: number) => {
    const angle = Math.PI * 2 * index / RADAR_AXES.length - Math.PI / 2;
    return { x: center + radius * value / 100 * Math.cos(angle), y: center + radius * value / 100 * Math.sin(angle) };
  };
  const toggle = (id: string) => setSelected((current) => current.includes(id) ? (current.length > 1 ? current.filter((item) => item !== id) : current) : (current.length < 3 ? [...current, id] : current));

  return (
    <div className="av-card" style={{ padding: 24, backgroundColor: 'var(--bg-card)' }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>Six-axis measured profile</h2>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>Only published v0.3 measurements are used: both directions, soft preference, hard reliability, and coverage. Select up to three recipes.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24, alignItems: 'center', marginTop: 18 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
          {ranked.map((profile) => {
            const active = selected.includes(profile.model_id);
            return <button key={profile.model_id} onClick={() => toggle(profile.model_id)} style={{ padding: '7px 10px', borderRadius: 999, border: `1px solid ${active ? color(profile) : 'var(--border-subtle)'}`, background: active ? 'var(--bg-card-elevated)' : 'transparent', color: 'var(--text-secondary)', fontSize: 11, cursor: 'pointer' }}>{zhEnProfileName(profile)}</button>;
          })}
        </div>
        <svg viewBox={`0 0 ${size} ${size}`} style={{ width: '100%', maxWidth: 440, justifySelf: 'center' }} aria-label="Six-axis measured recipe comparison">
          {[20, 40, 60, 80, 100].map((level) => <polygon key={level} points={RADAR_AXES.map((_, index) => { const point = coordinate(index, level); return `${point.x},${point.y}`; }).join(' ')} fill={level === 100 ? 'var(--bg-card-elevated)' : 'none'} stroke="var(--border-subtle)" />)}
          {RADAR_AXES.map(([label], index) => { const end = coordinate(index, 100); const textPoint = coordinate(index, 117); return <g key={label}><line x1={center} y1={center} x2={end.x} y2={end.y} stroke="var(--border-subtle)" /><text x={textPoint.x} y={textPoint.y + 4} textAnchor={textPoint.x > center + 10 ? 'start' : textPoint.x < center - 10 ? 'end' : 'middle'} fontSize="11" fontWeight="700" fill="var(--text-secondary)">{label}</text></g>; })}
          {chosen.map((profile) => <g key={profile.model_id}><polygon points={RADAR_AXES.map(([, getter], index) => { const point = coordinate(index, getter(profile)); return `${point.x},${point.y}`; }).join(' ')} fill={color(profile)} fillOpacity="0.13" stroke={color(profile)} strokeWidth="2.5" />{RADAR_AXES.map(([, getter], index) => { const point = coordinate(index, getter(profile)); return <circle key={index} cx={point.x} cy={point.y} r="3.5" fill={color(profile)} />; })}</g>)}
        </svg>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, justifyContent: 'center' }}>{chosen.map((profile) => <span key={profile.model_id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-secondary)' }}><i style={{ width: 10, height: 10, borderRadius: 99, background: color(profile) }} />{zhEnProfileName(profile)}</span>)}</div>
    </div>
  );
}

export function V03Visualizations({ artifact }: { artifact: ZhEnPreviewArtifact }) {
  return (
    <section style={{ marginBottom: 56 }}>
      <div className="section-title"><span>Published v0.3 analysis · ZH–EN only</span></div>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 22, minWidth: 0 }}>
        <ScoreBars profiles={artifact.profiles} />
        <ParetoFrontier profiles={artifact.profiles} />
        <SixAxisRadar profiles={artifact.profiles} />
      </div>
    </section>
  );
}
