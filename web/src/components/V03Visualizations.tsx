import { useState, type CSSProperties, type KeyboardEvent } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { modelDetailHref } from '../data/modelDetailUrl';
import { getVendorBrand } from '../data/vendorBrands';
import { observedThroughput, paretoFrontier, paretoValue, type ParetoMetric } from '../data/v03VisualMetrics';
import { zhEnProfileName } from '../data/zhEnProfileName';
import type { ZhEnMeasure, ZhEnPreviewArtifact, ZhEnPreviewProfile } from '../types/zhEnPreview';
import { VendorLogo } from './VendorLogo';
import { useI18n } from '../i18n/I18nProvider';

function aggregate(profile: ZhEnPreviewProfile, kind: 'soft' | 'hard'): ZhEnMeasure {
  const values = Object.values(profile.directions).map((direction) => direction[kind]);
  const total = values.reduce((sum, value) => sum + value.total, 0);
  const resolved = values.reduce((sum, value) => sum + value.resolved, 0);
  return { coverage: resolved / total, points: values.reduce((sum, value) => sum + value.points, 0), resolved, score: values.reduce((sum, value) => sum + value.score, 0) / values.length, total };
}

function color(profile: ZhEnPreviewProfile): string { return getVendorBrand(profile.model_family, profile.model_id).color; }

type HighlightMetric = 'score' | 'throughput' | 'cost';
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
  const { t } = useI18n();
  const ranked = profiles
    .map((profile) => ({ profile, value: highlightValue(profile, metric) }))
    .filter((item): item is { profile: ZhEnPreviewProfile; value: number } => item.value !== null)
    .sort((left, right) => (metric === 'cost' ? left.value - right.value : right.value - left.value))
    .slice(0, 9);
  const max = Math.max(...ranked.map((item) => item.value));
  const copy = {
    score: { title: t('highlight.score'), subtitle: t('highlight.scoreSub'), color: 'var(--brand-purple)' },
    throughput: { title: t('highlight.throughput'), subtitle: t('highlight.throughputSub'), color: 'var(--brand-emerald)' },
    cost: { title: t('highlight.cost'), subtitle: t('highlight.costSub'), color: 'var(--brand-orange)' },
  }[metric];
  return (
    <article className="av-card highlight-card">
      <header className="highlight-card-header">
        <div><h2><i style={{ background: copy.color }} />{copy.title}</h2><p>{copy.subtitle}</p></div>
        <span className="highlight-count">{t('common.top9')} <ArrowUpRight size={13} /></span>
      </header>
      <div className="hbar-rows" aria-label={`${copy.title}, top nine recipes`}>
        {ranked.map(({ profile, value }, index) => {
          const brand = getVendorBrand(profile.model_family, profile.model_id);
          return (
            <button
              className={`hbar-row ${index === 0 ? 'lead' : ''}`}
              key={profile.execution_identity_sha256}
              onClick={() => onOpen(profile)}
              title={`${zhEnProfileName(profile)} · ${formatHighlight(value, metric)}`}
              style={{ '--vendor-color': brand.color } as CSSProperties}
            >
              <span className="hbar-rank">{index + 1}</span>
              <span className="hbar-main">
                <span className="hbar-label">
                  <VendorLogo signals={[profile.model_family, profile.model_id]} size={16} fallback={zhEnProfileName(profile)} />
                  {zhEnProfileName(profile)}
                </span>
                <span className="hbar-track">
                  <i className="hbar-fill" style={{ width: `${Math.max(3, (value / max) * 100)}%` }} />
                </span>
              </span>
              <span className="hbar-val mono">{formatHighlight(value, metric)}</span>
            </button>
          );
        })}
      </div>
    </article>
  );
}

function Highlights({ profiles, onOpen }: { profiles: ZhEnPreviewProfile[]; onOpen: (profile: ZhEnPreviewProfile) => void }) {
  return (
    <div className="highlights-grid">
      <HighlightCard metric="score" profiles={profiles} onOpen={onOpen} />
      <HighlightCard metric="throughput" profiles={profiles} onOpen={onOpen} />
      <HighlightCard metric="cost" profiles={profiles} onOpen={onOpen} />
    </div>
  );
}

function InteractivePareto({ profiles, onOpen }: { profiles: ZhEnPreviewProfile[]; onOpen: (profile: ZhEnPreviewProfile) => void }) {
  const { t } = useI18n();
  const paretoCopy: Record<ParetoMetric, { label: string; axis: string; format: (value: number) => string }> = {
    cost: { label: t('pareto.cost'), axis: t('pareto.costAxis'), format: (value) => `$${value.toFixed(value < 0.01 ? 3 : 2)}` },
    latency: { label: t('pareto.elapsed'), axis: t('pareto.elapsedAxis'), format: (value) => t('common.minutes', { value: (value / 60).toFixed(1) }) },
    tokens: { label: t('pareto.tokens'), axis: t('pareto.tokensAxis'), format: (value) => `${Math.round(value / 1000)}k` },
  };
  const [metric, setMetric] = useState<ParetoMetric>('cost');
  const [hovered, setHovered] = useState<ZhEnPreviewProfile | null>(null);
  const points = profiles.filter((profile) => paretoValue(profile, metric) !== null);
  const frontier = paretoFrontier(profiles, metric);
  const width = 940, height = 430, pad = { top: 38, right: 58, bottom: 66, left: 62 };
  const values = points.map((profile) => paretoValue(profile, metric) as number);
  const minValue = Math.min(...values), maxValue = Math.max(...values), useLog = metric === 'cost';
  const project = (value: number) => (useLog ? Math.log10(Math.max(value, 0.0001)) : value);
  const projectedMin = project(minValue), projectedMax = project(maxValue);
  const x = (value: number) => pad.left + ((project(value) - projectedMin) / Math.max(0.0001, projectedMax - projectedMin)) * (width - pad.left - pad.right);
  const yMin = Math.max(0, Math.floor(Math.min(...points.map((profile) => profile.zh_en_score)) / 10) * 10 - 5);
  const y = (value: number) => pad.top + (1 - (value - yMin) / (100 - yMin)) * (height - pad.top - pad.bottom);
  const ticks = Array.from({ length: 5 }, (_, index) => minValue + ((maxValue - minValue) * index) / 4);
  const scoreTicks = [40, 55, 70, 85, 100].filter((tick) => tick >= yMin);
  const active = hovered ?? frontier[frontier.length - 1] ?? points[0];
  const keyOpen = (event: KeyboardEvent<SVGGElement>, profile: ZhEnPreviewProfile) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(profile); }
  };
  return (
    <article className="av-card pareto-card">
      <header className="pareto-header">
        <div><span className="eyebrow">{t('pareto.eyebrow')}</span><h2>{t('pareto.title')}</h2><p>{t('pareto.subtitle')}</p></div>
        <div className="tab-group pareto-tabs" aria-label={t('pareto.title')}>
          {(Object.keys(paretoCopy) as ParetoMetric[]).map((item) => (
            <button className={`tab-btn ${metric === item ? 'active' : ''}`} key={item} onClick={() => { setMetric(item); setHovered(null); }}>
              {paretoCopy[item].label}
            </button>
          ))}
        </div>
      </header>
      <div className="pareto-chart-wrap">
        <svg viewBox={`0 0 ${width} ${height}`} className="pareto-chart" role="img" aria-label={`${t('pareto.title')} · ${paretoCopy[metric].label}`}>
          <defs>
            <linearGradient id="frontierWash" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="var(--brand-gold)" stopOpacity="0.18" />
              <stop offset="1" stopColor="var(--brand-gold)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {scoreTicks.map((tick) => (
            <g key={tick}>
              <line className="chart-gridline" x1={pad.left} y1={y(tick)} x2={width - pad.right} y2={y(tick)} />
              <text className="chart-tick" x={pad.left - 12} y={y(tick) + 4} textAnchor="end">{tick}</text>
            </g>
          ))}
          {ticks.map((tick, index) => (
            <g key={`${tick}-${index}`}>
              <line className="chart-gridline vertical" x1={x(tick)} y1={pad.top} x2={x(tick)} y2={height - pad.bottom} />
              <text className="chart-tick" x={x(tick)} y={height - pad.bottom + 24} textAnchor={index === 0 ? 'start' : index === ticks.length - 1 ? 'end' : 'middle'}>
                {paretoCopy[metric].format(tick)}
              </text>
            </g>
          ))}
          {frontier.length > 1 && (
            <>
              <polygon
                points={`${frontier.map((profile) => `${x(paretoValue(profile, metric) as number)},${y(profile.zh_en_score)}`).join(' ')} ${x(paretoValue(frontier.at(-1)!, metric) as number)},${height - pad.bottom} ${x(paretoValue(frontier[0], metric) as number)},${height - pad.bottom}`}
                fill="url(#frontierWash)"
              />
              <polyline
                className="frontier-line"
                points={frontier.map((profile) => `${x(paretoValue(profile, metric) as number)},${y(profile.zh_en_score)}`).join(' ')}
              />
            </>
          )}
          {points.map((profile) => {
            const value = paretoValue(profile, metric) as number;
            const onFrontier = frontier.includes(profile);
            const isHovered = hovered === profile;
            return (
              <g
                className="pareto-point"
                key={profile.execution_identity_sha256}
                role="button"
                tabIndex={0}
                aria-label={`${zhEnProfileName(profile)}, ${t('common.score')} ${profile.zh_en_score.toFixed(2)}, ${paretoCopy[metric].format(value)}. ${t('pareto.open')}`}
                onMouseEnter={() => setHovered(profile)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(profile)}
                onBlur={() => setHovered(null)}
                onClick={() => onOpen(profile)}
                onKeyDown={(event) => keyOpen(event, profile)}
              >
                {(isHovered || onFrontier) && (
                  <circle cx={x(value)} cy={y(profile.zh_en_score)} r={isHovered ? 14 : 10} fill={onFrontier ? 'var(--brand-gold)' : color(profile)} opacity={isHovered ? 0.2 : 0.11} />
                )}
                <circle
                  cx={x(value)}
                  cy={y(profile.zh_en_score)}
                  r={isHovered ? 7 : onFrontier ? 6 : 4.5}
                  fill={color(profile)}
                  stroke={onFrontier ? 'var(--brand-gold)' : 'var(--bg-card)'}
                  strokeWidth={onFrontier ? 3 : 2}
                />
                {(onFrontier || isHovered) && (
                  <text className="point-label" x={x(value) + (x(value) > width - 180 ? -10 : 10)} y={y(profile.zh_en_score) - 11} textAnchor={x(value) > width - 180 ? 'end' : 'start'}>
                    {zhEnProfileName(profile)}
                  </text>
                )}
              </g>
            );
          })}
          <text className="axis-title" x={width / 2} y={height - 10} textAnchor="middle">
            {paretoCopy[metric].axis}{useLog ? ` · ${t('pareto.log')}` : ''}
          </text>
          <text className="axis-title" x={18} y={height / 2} transform={`rotate(-90 18 ${height / 2})`} textAnchor="middle">
            {t('pareto.scoreAxis')}
          </text>
        </svg>
      </div>
      <footer className="pareto-inspector" aria-live="polite">
        <div className="pareto-inspector-copy">
          <span>{t('pareto.inspect')}</span><small>{t('pareto.current')}</small>
        </div>
        {active && (
          <div className="pareto-active">
            <VendorLogo signals={[active.model_family, active.model_id]} size={32} fallback={zhEnProfileName(active)} />
            <span className="pareto-active-copy">
              <strong>{zhEnProfileName(active)}</strong>
              <small>{t('common.score')} {active.zh_en_score.toFixed(2)} · {paretoCopy[metric].label} {paretoCopy[metric].format(paretoValue(active, metric) as number)}</small>
              <small>ZH→EN {active.directions['zh-CN->en'].score.toFixed(2)} · EN→ZH {active.directions['en->zh-CN'].score.toFixed(2)} · {t('manifest.soft')} {aggregate(active, 'soft').score.toFixed(1)} · {t('manifest.hard')} {aggregate(active, 'hard').score.toFixed(1)}</small>
              <small>{t('manifest.observedCost')} {active.telemetry.cost_usd === null ? t('common.notMeasured') : `$${active.telemetry.cost_usd.toFixed(3)}`} · {t('manifest.elapsed')} {t('common.minutes', { value: (active.telemetry.elapsed_seconds / 60).toFixed(1) })} · {active.telemetry.total_tokens.toLocaleString()} {t('table.tokens')}</small>
            </span>
          </div>
        )}
      </footer>
    </article>
  );
}

function SoftHardScatter({ profiles, onOpen }: { profiles: ZhEnPreviewProfile[]; onOpen: (profile: ZhEnPreviewProfile) => void }) {
  const { t } = useI18n();
  const [hovered, setHovered] = useState<ZhEnPreviewProfile | null>(null);
  const width = 940, height = 430, pad = { top: 30, right: 40, bottom: 56, left: 56 };
  const points = profiles.map((profile) => ({
    profile,
    hard: aggregate(profile, 'hard').score,
    soft: aggregate(profile, 'soft').score,
  }));
  const xMin = Math.floor(Math.min(...points.map((point) => point.hard)) / 10) * 10;
  const x = (value: number) => pad.left + ((value - xMin) / (100 - xMin)) * (width - pad.left - pad.right);
  const y = (value: number) => pad.top + (1 - value / 100) * (height - pad.top - pad.bottom);
  const xTicks = Array.from({ length: 5 }, (_, index) => xMin + ((100 - xMin) * index) / 4);
  const yTicks = [0, 25, 50, 75, 100];
  const isoLines = [45, 60, 75, 90];
  const active = hovered ?? points[0].profile;
  const activeSoft = aggregate(active, 'soft').score;
  const activeHard = aggregate(active, 'hard').score;
  const keyOpen = (event: KeyboardEvent<SVGGElement>, profile: ZhEnPreviewProfile) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(profile); }
  };
  return (
    <article className="av-card soft-hard-scatter">
      <h2>{t('softhard.title')}</h2>
      <p>{t('softhard.subtitle')}</p>
      <svg viewBox={`0 0 ${width} ${height}`} className="soft-hard-chart" role="img" aria-label={t('softhard.title')}>
        {yTicks.map((tick) => (
          <g key={tick}>
            <line className="chart-gridline" x1={pad.left} y1={y(tick)} x2={width - pad.right} y2={y(tick)} />
            <text className="chart-tick" x={pad.left - 12} y={y(tick) + 4} textAnchor="end">{tick}</text>
          </g>
        ))}
        {xTicks.map((tick) => (
          <g key={tick}>
            <line className="chart-gridline vertical" x1={x(tick)} y1={pad.top} x2={x(tick)} y2={height - pad.bottom} />
            <text className="chart-tick" x={x(tick)} y={height - pad.bottom + 24} textAnchor="middle">{Math.round(tick)}</text>
          </g>
        ))}
        {isoLines.map((k) => {
          // 0.6·S + 0.4·H = k → S = (k - 0.4·H)/0.6; clip to [0,100]×[0,100]
          const candidates: Array<[number, number]> = [
            [xMin, (k - 0.4 * xMin) / 0.6],
            [100, (k - 40) / 0.6],
            [k / 0.4, 0],
            [(k - 60) / 0.4, 100],
          ].filter(([h, s]) => h >= 0 && h <= 100 && s >= 0 && s <= 100) as Array<[number, number]>;
          if (candidates.length < 2) return null;
          const [a, b] = candidates;
          return (
            <g key={k}>
              <line
                x1={x(a[0])} y1={y(a[1])} x2={x(b[0])} y2={y(b[1])}
                stroke="var(--brand-gold)" strokeWidth="1" strokeDasharray="4 4" opacity="0.35"
              />
              <text
                x={x(b[0]) - 4} y={y(b[1]) - 4}
                textAnchor="end" fontSize="9" fill="var(--brand-gold)" opacity="0.7"
              >
                {k}
              </text>
            </g>
          );
        })}
        {points.map(({ profile, hard, soft }) => {
          const isHovered = hovered === profile;
          return (
            <g
              key={profile.execution_identity_sha256}
              role="button"
              tabIndex={0}
              aria-label={`${zhEnProfileName(profile)}, ${t('softhard.xAxis')} ${hard.toFixed(1)}, ${t('softhard.yAxis')} ${soft.toFixed(1)}`}
              onMouseEnter={() => setHovered(profile)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(profile)}
              onBlur={() => setHovered(null)}
              onClick={() => onOpen(profile)}
              onKeyDown={(event) => keyOpen(event, profile)}
              style={{ cursor: 'pointer' }}
            >
              {isHovered && <circle cx={x(hard)} cy={y(soft)} r={12} fill={color(profile)} opacity="0.15" />}
              <circle cx={x(hard)} cy={y(soft)} r={isHovered ? 6 : 4.5} fill={color(profile)} stroke="var(--bg-card)" strokeWidth="1.5" />
              {(isHovered || profile.zh_en_score === Math.max(...points.map((p) => p.profile.zh_en_score))) && (
                <text className="point-label" x={x(hard) + 8} y={y(soft) - 6}>
                  {zhEnProfileName(profile)}
                </text>
              )}
            </g>
          );
        })}
        <text className="axis-title" x={width / 2} y={height - 10} textAnchor="middle">
          {t('softhard.xAxis')}
        </text>
        <text className="axis-title" x={18} y={height / 2} transform={`rotate(-90 18 ${height / 2})`} textAnchor="middle">
          {t('softhard.yAxis')}
        </text>
        <text className="chart-direction chart-direction-x" x={width - pad.right} y={height - pad.bottom + 42} textAnchor="end">{t('softhard.reliable')}</text>
        <text className="chart-direction" x={pad.left + 6} y={pad.top + 14}>{t('softhard.better')}</text>
      </svg>
      <footer className="soft-hard-inspector" aria-live="polite">
        <div>
          <span>{t('softhard.inspect')}</span>
          <small>{t('softhard.isoFormula')}</small>
        </div>
        <div className="soft-hard-active">
          <VendorLogo signals={[active.model_family, active.model_id]} size={32} fallback={zhEnProfileName(active)} />
          <span>
            <strong>{zhEnProfileName(active)}</strong>
            <small>{t('common.score')} {active.zh_en_score.toFixed(2)} · {t('manifest.soft')} {activeSoft.toFixed(1)} · {t('manifest.hard')} {activeHard.toFixed(1)}</small>
          </span>
        </div>
      </footer>
    </article>
  );
}

export function V03Visualizations({ artifact }: { artifact: ZhEnPreviewArtifact }) {
  const { locale, t } = useI18n();
  const openDetails = (profile: ZhEnPreviewProfile) => {
    window.open(modelDetailHref(profile.model_id, locale), '_blank', 'noopener,noreferrer');
  };
  return (
    <section className="v03-analysis">
      <div className="section-title"><span>{t('analysis.title')}</span></div>
      <div className="v03-analysis-stack">
        <Highlights profiles={artifact.profiles} onOpen={openDetails} />
        <InteractivePareto profiles={artifact.profiles} onOpen={openDetails} />
        <SoftHardScatter profiles={artifact.profiles} onOpen={openDetails} />
      </div>
    </section>
  );
}
