import { useEffect, useMemo, useState, type CSSProperties, type KeyboardEvent } from 'react';
import { ArrowUpRight, X } from 'lucide-react';
import { getVendorBrand } from '../data/vendorBrands';
import { observedThroughput, paretoFrontier, paretoValue, type ParetoMetric } from '../data/v03VisualMetrics';
import { zhEnProfileName } from '../data/zhEnProfileName';
import type { ZhEnMeasure, ZhEnPreviewArtifact, ZhEnPreviewProfile } from '../types/zhEnPreview';
import { VendorLogo } from './VendorLogo';

function aggregate(profile: ZhEnPreviewProfile, kind: 'soft' | 'hard'): ZhEnMeasure {
  const values = Object.values(profile.directions).map((direction) => direction[kind]);
  const total = values.reduce((sum, value) => sum + value.total, 0);
  const resolved = values.reduce((sum, value) => sum + value.resolved, 0);
  return { coverage: resolved / total, points: values.reduce((sum, value) => sum + value.points, 0), resolved, score: values.reduce((sum, value) => sum + value.score, 0) / values.length, total };
}

function color(profile: ZhEnPreviewProfile): string { return getVendorBrand(profile.model_family, profile.model_id).color; }

type HighlightMetric = 'score' | 'throughput' | 'cost';
const HIGHLIGHT_COPY: Record<HighlightMetric, { title: string; subtitle: string; color: string }> = {
  score: { title: 'ZH–EN Score', subtitle: 'Published v0.3 score · Higher is better', color: 'var(--brand-purple)' },
  throughput: { title: 'Throughput Speed', subtitle: 'Observed tokens per second · Higher is better', color: 'var(--brand-emerald)' },
  cost: { title: 'Observed Recipe Cost', subtitle: 'Measured inference cost (USD) · Lower is better', color: 'var(--brand-orange)' },
};

function highlightValue(profile: ZhEnPreviewProfile, metric: HighlightMetric): number | null {
  if (metric === 'score') return profile.zh_en_score;
  if (metric === 'throughput') return observedThroughput(profile);
  return profile.telemetry.cost_usd;
}

function formatHighlight(value: number, metric: HighlightMetric): string {
  if (metric === 'score') return value.toFixed(1);
  if (metric === 'throughput') return value >= 100 ? value.toFixed(0) : value.toFixed(1);
  return value < 0.01 ? `$${value.toFixed(3)}` : `$${value.toFixed(2)}`;
}

function HighlightCard({ metric, profiles, onOpen }: { metric: HighlightMetric; profiles: ZhEnPreviewProfile[]; onOpen: (profile: ZhEnPreviewProfile) => void }) {
  const ranked = profiles.map((profile) => ({ profile, value: highlightValue(profile, metric) })).filter((item): item is { profile: ZhEnPreviewProfile; value: number } => item.value !== null).sort((left, right) => right.value - left.value).slice(0, 9);
  const max = Math.max(...ranked.map((item) => item.value));
  const copy = HIGHLIGHT_COPY[metric];
  return <article className="av-card highlight-card">
    <header className="highlight-card-header"><div><h2><i style={{ background: copy.color }} />{copy.title}</h2><p>{copy.subtitle}</p></div><span className="highlight-count">Top 9 <ArrowUpRight size={13} /></span></header>
    <div className="mini-bars" aria-label={`${copy.title}, top nine recipes`}>
      {ranked.map(({ profile, value }) => <button className="mini-bar" key={profile.execution_identity_sha256} onClick={() => onOpen(profile)} title={`${zhEnProfileName(profile)} · ${formatHighlight(value, metric)}`} style={{ '--bar-color': color(profile) } as CSSProperties}>
        <strong className="mono">{formatHighlight(value, metric)}</strong><span className="mini-bar-track"><i style={{ height: `${Math.max(5, (value / max) * 100)}%` }} /></span><span className="mini-bar-label"><VendorLogo signals={[profile.model_family, profile.model_id]} size={23} fallback={zhEnProfileName(profile)} /><small>{zhEnProfileName(profile)}</small></span>
      </button>)}
    </div>
  </article>;
}

function Highlights({ profiles, onOpen }: { profiles: ZhEnPreviewProfile[]; onOpen: (profile: ZhEnPreviewProfile) => void }) {
  return <div className="highlights-grid"><HighlightCard metric="score" profiles={profiles} onOpen={onOpen} /><HighlightCard metric="throughput" profiles={profiles} onOpen={onOpen} /><HighlightCard metric="cost" profiles={profiles} onOpen={onOpen} /></div>;
}

const PARETO_COPY: Record<ParetoMetric, { label: string; axis: string; format: (value: number) => string }> = {
  cost: { label: 'Cost', axis: 'Observed recipe cost (USD)', format: (value) => `$${value.toFixed(value < 0.01 ? 3 : 2)}` },
  latency: { label: 'Elapsed time', axis: 'Elapsed benchmark time (minutes)', format: (value) => `${(value / 60).toFixed(1)}m` },
  tokens: { label: 'Token load', axis: 'Observed total tokens', format: (value) => `${Math.round(value / 1000)}k` },
};

function InteractivePareto({ profiles, onOpen }: { profiles: ZhEnPreviewProfile[]; onOpen: (profile: ZhEnPreviewProfile) => void }) {
  const [metric, setMetric] = useState<ParetoMetric>('cost');
  const [hovered, setHovered] = useState<ZhEnPreviewProfile | null>(null);
  const points = profiles.filter((profile) => paretoValue(profile, metric) !== null);
  const frontier = paretoFrontier(profiles, metric);
  const width = 940, height = 430, pad = { top: 38, right: 58, bottom: 66, left: 62 };
  const values = points.map((profile) => paretoValue(profile, metric) as number);
  const minValue = Math.min(...values), maxValue = Math.max(...values), useLog = metric === 'cost';
  const project = (value: number) => useLog ? Math.log10(Math.max(value, 0.0001)) : value;
  const projectedMin = project(minValue), projectedMax = project(maxValue);
  const x = (value: number) => pad.left + ((project(value) - projectedMin) / Math.max(0.0001, projectedMax - projectedMin)) * (width - pad.left - pad.right);
  const yMin = Math.max(0, Math.floor(Math.min(...points.map((profile) => profile.zh_en_score)) / 10) * 10 - 5);
  const y = (value: number) => pad.top + (1 - (value - yMin) / (100 - yMin)) * (height - pad.top - pad.bottom);
  const ticks = Array.from({ length: 5 }, (_, index) => minValue + ((maxValue - minValue) * index) / 4);
  const scoreTicks = [40, 55, 70, 85, 100].filter((tick) => tick >= yMin);
  const active = hovered ?? frontier[frontier.length - 1] ?? points[0];
  const keyOpen = (event: KeyboardEvent<SVGGElement>, profile: ZhEnPreviewProfile) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(profile); } };
  return <article className="av-card pareto-card">
    <header className="pareto-header"><div><span className="eyebrow">Efficiency frontier</span><h2>Quality–efficiency Pareto frontier</h2><p>Higher quality and lower resource use are better. Gold points define the current frontier.</p></div><div className="tab-group pareto-tabs" aria-label="Pareto horizontal metric">{(Object.keys(PARETO_COPY) as ParetoMetric[]).map((item) => <button className={`tab-btn ${metric === item ? 'active' : ''}`} key={item} onClick={() => { setMetric(item); setHovered(null); }}>{PARETO_COPY[item].label}</button>)}</div></header>
    <div className="pareto-chart-wrap"><svg viewBox={`0 0 ${width} ${height}`} className="pareto-chart" role="img" aria-label={`ZH-EN quality versus ${PARETO_COPY[metric].label} Pareto frontier`}>
      <defs><linearGradient id="frontierWash" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--brand-gold)" stopOpacity="0.18" /><stop offset="1" stopColor="var(--brand-gold)" stopOpacity="0" /></linearGradient></defs>
      {scoreTicks.map((tick) => <g key={tick}><line className="chart-gridline" x1={pad.left} y1={y(tick)} x2={width - pad.right} y2={y(tick)} /><text className="chart-tick" x={pad.left - 12} y={y(tick) + 4} textAnchor="end">{tick}</text></g>)}
      {ticks.map((tick, index) => <g key={`${tick}-${index}`}><line className="chart-gridline vertical" x1={x(tick)} y1={pad.top} x2={x(tick)} y2={height - pad.bottom} /><text className="chart-tick" x={x(tick)} y={height - pad.bottom + 24} textAnchor={index === 0 ? 'start' : index === ticks.length - 1 ? 'end' : 'middle'}>{PARETO_COPY[metric].format(tick)}</text></g>)}
      {frontier.length > 1 && <><polygon points={`${frontier.map((profile) => `${x(paretoValue(profile, metric) as number)},${y(profile.zh_en_score)}`).join(' ')} ${x(paretoValue(frontier.at(-1)!, metric) as number)},${height - pad.bottom} ${x(paretoValue(frontier[0], metric) as number)},${height - pad.bottom}`} fill="url(#frontierWash)" /><polyline className="frontier-line" points={frontier.map((profile) => `${x(paretoValue(profile, metric) as number)},${y(profile.zh_en_score)}`).join(' ')} /></>}
      {points.map((profile) => { const value = paretoValue(profile, metric) as number; const onFrontier = frontier.includes(profile); const isHovered = hovered === profile; return <g className="pareto-point" key={profile.execution_identity_sha256} role="button" tabIndex={0} aria-label={`${zhEnProfileName(profile)}, score ${profile.zh_en_score.toFixed(2)}, ${PARETO_COPY[metric].format(value)}. Open recipe manifest.`} onMouseEnter={() => setHovered(profile)} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered(profile)} onBlur={() => setHovered(null)} onClick={() => onOpen(profile)} onKeyDown={(event) => keyOpen(event, profile)}>
        {(isHovered || onFrontier) && <circle cx={x(value)} cy={y(profile.zh_en_score)} r={isHovered ? 14 : 10} fill={onFrontier ? 'var(--brand-gold)' : color(profile)} opacity={isHovered ? 0.2 : 0.11} />}<circle cx={x(value)} cy={y(profile.zh_en_score)} r={isHovered ? 7 : onFrontier ? 6 : 4.5} fill={color(profile)} stroke={onFrontier ? 'var(--brand-gold)' : 'var(--bg-card)'} strokeWidth={onFrontier ? 3 : 2} />{(onFrontier || isHovered) && <text className="point-label" x={x(value) + (x(value) > width - 180 ? -10 : 10)} y={y(profile.zh_en_score) - 11} textAnchor={x(value) > width - 180 ? 'end' : 'start'}>{zhEnProfileName(profile)}</text>}
      </g>; })}
      <text className="axis-title" x={width / 2} y={height - 10} textAnchor="middle">{PARETO_COPY[metric].axis}{useLog ? ' · log scale' : ''}</text><text className="axis-title" x={18} y={height / 2} transform={`rotate(-90 18 ${height / 2})`} textAnchor="middle">ZH–EN score</text>
    </svg></div>
    <footer className="pareto-inspector" aria-live="polite"><div className="pareto-inspector-copy"><span>Hover over points to inspect metrics, or click to open full recipe manifest.</span><small>All values are current published v0.3 measurements.</small></div>{active && <div className="pareto-active"><VendorLogo signals={[active.model_family, active.model_id]} size={32} fallback={zhEnProfileName(active)} /><span><strong>{zhEnProfileName(active)}</strong><small>Score {active.zh_en_score.toFixed(2)} · {PARETO_COPY[metric].format(paretoValue(active, metric) as number)}</small></span></div>}</footer>
  </article>;
}

const RADAR_AXES = [['Overall', (profile: ZhEnPreviewProfile) => profile.zh_en_score], ['ZH→EN', (profile: ZhEnPreviewProfile) => profile.directions['zh-CN->en'].score], ['EN→ZH', (profile: ZhEnPreviewProfile) => profile.directions['en->zh-CN'].score], ['Soft', (profile: ZhEnPreviewProfile) => aggregate(profile, 'soft').score], ['Hard', (profile: ZhEnPreviewProfile) => aggregate(profile, 'hard').score], ['Coverage', (profile: ZhEnPreviewProfile) => aggregate(profile, 'soft').coverage * 100]] as const;

function SixAxisRadar({ profiles }: { profiles: ZhEnPreviewProfile[] }) {
  const ranked = useMemo(() => [...profiles].sort((left, right) => right.zh_en_score - left.zh_en_score), [profiles]);
  const [selected, setSelected] = useState(() => ranked.slice(0, 2).map((profile) => profile.model_id).concat('deepseek/deepseek-v4-pro-0813'));
  const chosen = selected.map((id) => profiles.find((profile) => profile.model_id === id)).filter(Boolean) as ZhEnPreviewProfile[];
  const size = 440, center = size / 2, radius = 150;
  const coordinate = (index: number, value: number) => { const angle = Math.PI * 2 * index / RADAR_AXES.length - Math.PI / 2; return { x: center + radius * value / 100 * Math.cos(angle), y: center + radius * value / 100 * Math.sin(angle) }; };
  const toggle = (id: string) => setSelected((current) => current.includes(id) ? (current.length > 1 ? current.filter((item) => item !== id) : current) : (current.length < 3 ? [...current, id] : current));
  return <article className="av-card radar-card"><h2>Six-axis measured profile</h2><p>Only published v0.3 measurements are used. Select up to three recipes.</p><div className="radar-layout"><div className="radar-options">{ranked.map((profile) => { const active = selected.includes(profile.model_id); return <button key={profile.model_id} onClick={() => toggle(profile.model_id)} style={{ '--profile-color': color(profile) } as CSSProperties} className={active ? 'active' : ''}>{zhEnProfileName(profile)}</button>; })}</div><svg viewBox={`0 0 ${size} ${size}`} className="radar-chart" aria-label="Six-axis measured recipe comparison">
    {[20, 40, 60, 80, 100].map((level) => <polygon key={level} points={RADAR_AXES.map((_, index) => { const point = coordinate(index, level); return `${point.x},${point.y}`; }).join(' ')} fill={level === 100 ? 'var(--bg-card-elevated)' : 'none'} stroke="var(--border-subtle)" />)}
    {RADAR_AXES.map(([label], index) => { const end = coordinate(index, 100), textPoint = coordinate(index, 117); return <g key={label}><line x1={center} y1={center} x2={end.x} y2={end.y} stroke="var(--border-subtle)" /><text x={textPoint.x} y={textPoint.y + 4} textAnchor={textPoint.x > center + 10 ? 'start' : textPoint.x < center - 10 ? 'end' : 'middle'} className="radar-label">{label}</text></g>; })}
    {chosen.map((profile) => <g key={profile.model_id}><polygon points={RADAR_AXES.map(([, getter], index) => { const point = coordinate(index, getter(profile)); return `${point.x},${point.y}`; }).join(' ')} fill={color(profile)} fillOpacity="0.13" stroke={color(profile)} strokeWidth="2.5" />{RADAR_AXES.map(([, getter], index) => { const point = coordinate(index, getter(profile)); return <circle key={index} cx={point.x} cy={point.y} r="3.5" fill={color(profile)} />; })}</g>)}
  </svg></div><div className="radar-legend">{chosen.map((profile) => <span key={profile.model_id}><i style={{ background: color(profile) }} />{zhEnProfileName(profile)}</span>)}</div></article>;
}

function ManifestDrawer({ profile, artifact, onClose }: { profile: ZhEnPreviewProfile | null; artifact: ZhEnPreviewArtifact; onClose: () => void }) {
  useEffect(() => {
    if (!profile) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const drawer = document.querySelector<HTMLElement>('.manifest-drawer');
    drawer?.scrollTo({ top: 0 });
    drawer?.querySelector<HTMLButtonElement>('.manifest-close')?.focus();
    const close = (event: globalThis.KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', close);
    return () => { document.removeEventListener('keydown', close); document.body.style.overflow = previousOverflow; };
  }, [profile, onClose]);
  if (!profile) return null;
  const verified = profile.telemetry.verified_cost;
  return <div className="manifest-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="manifest-drawer" role="dialog" aria-modal="true" aria-labelledby="manifest-title"><header><div><span className="eyebrow">Published recipe manifest</span><h2 id="manifest-title">{zhEnProfileName(profile)}</h2><code>{profile.model_id}</code></div><button className="manifest-close" onClick={onClose} aria-label="Close recipe manifest"><X size={20} /></button></header><div className="manifest-score"><span>ZH–EN score</span><strong>{profile.zh_en_score.toFixed(2)}</strong></div><dl className="manifest-grid">
    <div><dt>ZH→EN</dt><dd>{profile.directions['zh-CN->en'].score.toFixed(2)}</dd></div><div><dt>EN→ZH</dt><dd>{profile.directions['en->zh-CN'].score.toFixed(2)}</dd></div><div><dt>Observed cost</dt><dd>{profile.telemetry.cost_usd === null ? 'Not measured' : `$${profile.telemetry.cost_usd.toFixed(4)}`}</dd></div><div><dt>Elapsed time</dt><dd>{(profile.telemetry.elapsed_seconds / 60).toFixed(1)} min</dd></div><div><dt>Total tokens</dt><dd>{profile.telemetry.total_tokens.toLocaleString()}</dd></div><div><dt>Throughput</dt><dd>{observedThroughput(profile).toFixed(1)} tok/s</dd></div><div><dt>Soft score</dt><dd>{aggregate(profile, 'soft').score.toFixed(2)}</dd></div><div><dt>Hard score</dt><dd>{aggregate(profile, 'hard').score.toFixed(2)}</dd></div>
  </dl>{verified && <section className="manifest-note"><strong>Provider-verified cost</strong><p>¥{verified.amount.toFixed(2)} CNY, converted at {verified.cny_per_usd} CNY/USD on {verified.converted_on}. Source: provider dashboard.</p></section>}<section className="manifest-identity"><h3>Reproducibility</h3><dl><div><dt>Protocol</dt><dd>{artifact.protocol}</dd></div><div><dt>Result source</dt><dd><code>{artifact.source_commit}</code></dd></div><div><dt>Execution identity</dt><dd><code>{profile.execution_identity_sha256}</code></dd></div><div><dt>Directions</dt><dd>zh-CN→en · en→zh-CN</dd></div></dl></section><p className="manifest-disclosure">This is the complete public manifest for the published result. Sealed exam content, prompts, and candidate outputs are intentionally excluded.</p></aside></div>;
}

export function V03Visualizations({ artifact }: { artifact: ZhEnPreviewArtifact }) {
  const [openProfile, setOpenProfile] = useState<ZhEnPreviewProfile | null>(null);
  return <section className="v03-analysis"><div className="section-title"><span>Published v0.3 analysis · ZH–EN only</span></div><div className="v03-analysis-stack"><Highlights profiles={artifact.profiles} onOpen={setOpenProfile} /><InteractivePareto profiles={artifact.profiles} onOpen={setOpenProfile} /><SixAxisRadar profiles={artifact.profiles} /></div><ManifestDrawer profile={openProfile} artifact={artifact} onClose={() => setOpenProfile(null)} /></section>;
}
