import { useMemo, useState } from 'react';
import type {
  V03LeaderboardArtifact,
  V03Profile,
  V03ScoreKey,
  V03ScoreMeasure,
} from '../types/v03';
import { V03_SCORE_KEYS } from '../types/v03';

type Metric = 'cost' | 'elapsed' | 'tokens';

const SCORE_LABELS: Record<V03ScoreKey, string> = {
  overall_intelligence: 'Overall intelligence',
  zh_en_core: 'ZH↔EN core',
  east_asian: 'East Asian',
  continental: 'Continental',
  hard_format: 'Hard format',
  soft_preference: 'Soft preference',
};

const METRICS: Record<Metric, { title: string; value: (profile: V03Profile) => number | null; format: (value: number) => string }> = {
  cost: {
    title: 'Intelligence vs. observed cost',
    value: (profile) => (profile.telemetry.rank_eligible ? profile.telemetry.cost_usd : null),
    format: (value) => `$${value.toFixed(3)}`,
  },
  elapsed: {
    title: 'Intelligence vs. elapsed time',
    value: (profile) => profile.telemetry.elapsed_seconds,
    format: (value) => `${value.toFixed(1)}s`,
  },
  tokens: {
    title: 'Intelligence vs. total tokens',
    value: (profile) => profile.telemetry.tokens.total,
    format: (value) => `${Math.round(value).toLocaleString()} tok`,
  },
};

const FAMILY_COLORS: Record<string, string> = {
  gemini: 'var(--vendor-gemini)',
  openai: 'var(--vendor-openai)',
  qwen: 'var(--vendor-qwen)',
  deepseek: 'var(--vendor-deepseek)',
  nvidia: 'var(--vendor-nvidia)',
  tencent: 'var(--vendor-tencent)',
  local: 'var(--vendor-local)',
};

function modelName(profile: V03Profile): string {
  return profile.recipe.requested_model || profile.execution_identity_sha256.slice(0, 12);
}

function score(value: number | null): string {
  return value === null ? 'Unmeasured' : value.toFixed(2);
}

function percent(value: number | null): string {
  if (value === null) return 'unmeasured';
  if (value <= 1) return `${(value * 100).toFixed(0)}%`;
  return `${value.toFixed(0)}%`;
}

function colorForProfile(profile: V03Profile): string {
  const family = (profile.recipe.model_family || profile.recipe.provider || '').toLowerCase();
  const token = Object.entries(FAMILY_COLORS).find(([key]) => family.includes(key));
  return token ? token[1] : 'var(--vendor-neutral)';
}

function measureStatus(measure: V03ScoreMeasure): string {
  return `${percent(measure.coverage)} coverage · ${percent(measure.judge_agreement)} agreement · ${measure.unresolved_signals ?? 'unmeasured'} unresolved`;
}

function FrontierScatter({
  profiles,
  metric,
  activeScore,
  paretoMembers,
}: {
  profiles: V03Profile[];
  metric: Metric;
  activeScore: V03ScoreKey;
  paretoMembers: Set<string>;
}) {
  const definition = METRICS[metric];
  const points = profiles
    .map((profile) => ({
      profile,
      x: definition.value(profile),
      y: profile.scores[activeScore].score,
    }))
    .filter((point): point is { profile: V03Profile; x: number; y: number } => point.x !== null && point.y !== null);

  if (points.length < 2) {
    return <div className="v03-panel" style={{ padding: 20 }}>Awaiting at least two measured profiles for this frontier.</div>;
  }

  const minX = Math.min(...points.map((point) => point.x));
  const maxX = Math.max(...points.map((point) => point.x));
  const minY = Math.min(...points.map((point) => point.y));
  const maxY = Math.max(...points.map((point) => point.y));
  const sx = (value: number) => 38 + ((value - minX) / Math.max(maxX - minX, 1e-9)) * 304;
  const sy = (value: number) => 178 - ((value - minY) / Math.max(maxY - minY, 1e-9)) * 142;

  return (
    <div className="v03-panel" style={{ padding: 16 }}>
      <strong>{definition.title}</strong>
      <svg viewBox="0 0 380 220" role="img" aria-label={definition.title} style={{ width: '100%', marginTop: 8 }}>
        <line x1="38" y1="178" x2="350" y2="178" stroke="var(--border-medium)" />
        <line x1="38" y1="28" x2="38" y2="178" stroke="var(--border-medium)" />
        {points.map((point) => {
          const color = colorForProfile(point.profile);
          const id = point.profile.execution_identity_sha256;
          const isPareto = paretoMembers.has(id);
          return (
            <g key={id}>
              <circle cx={sx(point.x)} cy={sy(point.y)} r={isPareto ? '6' : '5'} fill={color} stroke={isPareto ? 'var(--brand-gold)' : 'transparent'} strokeWidth="1.5" />
              <title>{`${modelName(point.profile)}: ${point.y.toFixed(2)} / ${definition.format(point.x)}`}</title>
              <text x={sx(point.x) + 7} y={sy(point.y) - 6} fontSize="9" fill={color}>
                {modelName(point.profile).split('/').pop()}
              </text>
            </g>
          );
        })}
        <text x="194" y="210" textAnchor="middle" fontSize="10" fill="var(--text-muted)">Lower resource use is better</text>
        <text x="10" y="104" textAnchor="middle" fontSize="10" fill="var(--text-muted)" transform="rotate(-90 10 104)">{SCORE_LABELS[activeScore]}</text>
      </svg>
    </div>
  );
}

export function V03Leaderboard({ artifact }: { artifact: V03LeaderboardArtifact }) {
  const [activeScore, setActiveScore] = useState<V03ScoreKey>('overall_intelligence');

  const ranked = useMemo(() => [...artifact.profiles].sort(
    (left, right) => (right.scores[activeScore].score ?? -1) - (left.scores[activeScore].score ?? -1),
  ), [artifact.profiles, activeScore]);

  const anchorSet = useMemo(() => new Set(artifact.anchors), [artifact.anchors]);
  const watchSet = useMemo(() => new Set(artifact.watchlist), [artifact.watchlist]);

  const paretoByMetric = useMemo(() => {
    const byMetric: Record<Metric, Set<string>> = {
      cost: new Set<string>(),
      elapsed: new Set<string>(),
      tokens: new Set<string>(),
    };

    for (const [key, members] of Object.entries(artifact.pareto_frontiers)) {
      const normalized = key.toLowerCase();
      if (normalized.includes('cost')) {
        for (const id of members) {
          const profile = artifact.profiles.find((entry) => entry.execution_identity_sha256 === id);
          if (profile?.telemetry.rank_eligible !== false) byMetric.cost.add(id);
        }
      }
      if (normalized.includes('elapsed') || normalized.includes('latency') || normalized.includes('time')) {
        for (const id of members) byMetric.elapsed.add(id);
      }
      if (normalized.includes('token')) {
        for (const id of members) byMetric.tokens.add(id);
      }
    }

    return byMetric;
  }, [artifact.pareto_frontiers, artifact.profiles]);

  return (
    <section style={{ marginTop: 24, marginBottom: 40 }}>
      <div className="section-title"><span>Multilingual v0.3 · 18 directions</span></div>
      <p style={{ color: 'var(--text-secondary)', maxWidth: 960, marginBottom: 12 }}>
        ZH↔EN (2), ZH/EN→JA·KO (4), and ZH/EN→DE·RU·FR·ES·PT-BR·TR (12). Null means unmeasured, never zero.
      </p>
      {artifact.status !== 'complete' && (
        <div className="v03-panel" style={{ padding: 12, marginBottom: 16, borderColor: 'var(--brand-gold)' }}>
          This artifact is incomplete. Official ranks are hidden until status=complete.
        </div>
      )}

      <div className="tab-group" style={{ marginBottom: 14 }}>
        {V03_SCORE_KEYS.map((key) => (
          <button
            key={key}
            className={`tab-btn ${activeScore === key ? 'active' : ''}`}
            onClick={() => setActiveScore(key)}
          >
            {SCORE_LABELS[key]}
          </button>
        ))}
      </div>

      <div className="v03-panel" style={{ overflowX: 'auto', marginBottom: 20 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 1120 }}>
          <thead>
            <tr>
              {['#', 'Recipe', SCORE_LABELS[activeScore], 'Coverage / agreement / unresolved', 'Cost', 'Time', 'Total tokens', 'Signals'].map((label) => (
                <th key={label} style={{ padding: 10, textAlign: 'left' }}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ranked.map((profile) => {
              const identity = profile.execution_identity_sha256;
              const activeMeasure = profile.scores[activeScore];
              const rankVisible = artifact.status === 'complete' && profile.profile_status === 'complete';
              const color = colorForProfile(profile);
              return (
                <tr key={identity} style={{ borderTop: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: 10, fontWeight: 700, color: rankVisible ? 'var(--brand-gold)' : 'var(--text-muted)' }}>
                    {rankVisible && profile.official_rank !== null ? profile.official_rank : '—'}
                  </td>
                  <td style={{ padding: 10 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block' }} />
                      <strong>{modelName(profile)}</strong>
                    </div>
                    <small style={{ color: 'var(--text-secondary)' }}>
                      {profile.recipe.model_family || 'unknown family'} · {profile.recipe.reasoning_effort || 'unspecified'}
                    </small>
                  </td>
                  <td style={{ padding: 10 }}>
                    <span className="mono">{score(activeMeasure.score)}</span>
                  </td>
                  <td style={{ padding: 10, color: 'var(--text-secondary)', fontSize: 12 }}>{measureStatus(activeMeasure)}</td>
                  <td style={{ padding: 10 }}>
                    {profile.telemetry.cost_usd === null ? 'Unmeasured' : `$${profile.telemetry.cost_usd.toFixed(3)}`}
                    {profile.telemetry.rank_eligible ? '' : <span style={{ color: 'var(--text-muted)' }}> (ineligible)</span>}
                  </td>
                  <td style={{ padding: 10 }}>{profile.telemetry.elapsed_seconds === null ? 'Unmeasured' : `${profile.telemetry.elapsed_seconds.toFixed(1)}s`}</td>
                  <td style={{ padding: 10 }}>{profile.telemetry.tokens.total === null ? 'Unmeasured' : profile.telemetry.tokens.total.toLocaleString()}</td>
                  <td style={{ padding: 10 }}>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {anchorSet.has(identity) && <span className="badge badge-provider" style={{ borderColor: color, color }}>Anchor</span>}
                      {watchSet.has(identity) && <span className="badge badge-provider" style={{ borderColor: color, color }}>Watchlist</span>}
                      {paretoByMetric.cost.has(identity) && <span className="badge badge-neutral">Cost Pareto</span>}
                      {paretoByMetric.elapsed.has(identity) && <span className="badge badge-neutral">Time Pareto</span>}
                      {paretoByMetric.tokens.has(identity) && <span className="badge badge-neutral">Token Pareto</span>}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16, marginBottom: 16 }}>
        <FrontierScatter profiles={ranked} metric="cost" activeScore={activeScore} paretoMembers={paretoByMetric.cost} />
        <FrontierScatter profiles={ranked} metric="elapsed" activeScore={activeScore} paretoMembers={paretoByMetric.elapsed} />
        <FrontierScatter profiles={ranked} metric="tokens" activeScore={activeScore} paretoMembers={paretoByMetric.tokens} />
      </div>

      <details className="v03-panel" style={{ padding: '14px 16px' }}>
        <summary style={{ cursor: 'pointer', fontWeight: 700 }}>Technical details (fixed conditions)</summary>
        <div style={{ marginTop: 12, color: 'var(--text-secondary)', display: 'grid', gap: 8 }}>
          <div><strong style={{ color: 'var(--text-primary)' }}>Fixed recipe:</strong> {artifact.technical_details.fixed_recipe}</div>
          <div><strong style={{ color: 'var(--text-primary)' }}>Provenance:</strong> {artifact.technical_details.provenance}</div>
          <div><strong style={{ color: 'var(--text-primary)' }}>Validator:</strong> {artifact.technical_details.validator}</div>
          <div><strong style={{ color: 'var(--text-primary)' }}>Judge panel:</strong> {artifact.technical_details.judge_panel}</div>
          <div><strong style={{ color: 'var(--text-primary)' }}>Contract:</strong> {artifact.technical_details.contract}</div>
        </div>
      </details>
    </section>
  );
}
