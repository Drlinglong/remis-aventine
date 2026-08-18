import type { V03LeaderboardArtifact, V03Profile } from '../types/v03';

type Metric = 'cost' | 'elapsed' | 'tokens';

const METRICS: Record<Metric, { title: string; value: (profile: V03Profile) => number | null; format: (value: number) => string }> = {
  cost: {
    title: 'Intelligence vs. observed cost',
    value: (profile) => profile.telemetry.cost_usd,
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

function name(profile: V03Profile): string {
  return profile.recipe.requested_model || profile.execution_identity_sha256.slice(0, 12);
}

function score(value: number | null): string {
  return value === null ? 'Incomplete' : value.toFixed(2);
}

function FrontierScatter({ profiles, metric }: { profiles: V03Profile[]; metric: Metric }) {
  const definition = METRICS[metric];
  const points = profiles
    .map((profile) => ({
      profile,
      x: definition.value(profile),
      y: profile.scores.overall_intelligence.score,
    }))
    .filter((point): point is { profile: V03Profile; x: number; y: number } => point.x !== null && point.y !== null);

  if (points.length < 2) {
    return <div className="v03-panel" style={{ padding: 20 }}>Awaiting at least two complete, cost-observed profiles.</div>;
  }
  const minX = Math.min(...points.map((point) => point.x));
  const maxX = Math.max(...points.map((point) => point.x));
  const minY = Math.min(...points.map((point) => point.y));
  const maxY = Math.max(...points.map((point) => point.y));
  const sx = (value: number) => 38 + ((value - minX) / Math.max(maxX - minX, 1e-9)) * 304;
  const sy = (value: number) => 178 - ((value - minY) / Math.max(maxY - minY, 1e-9)) * 142;
  const frontier = [...points]
    .sort((a, b) => a.x - b.x || b.y - a.y)
    .filter((point, index, sorted) => !sorted.slice(0, index).some((other) => other.y >= point.y));

  return (
    <div className="v03-panel" style={{ padding: 16 }}>
      <strong>{definition.title}</strong>
      <svg viewBox="0 0 380 220" role="img" aria-label={definition.title} style={{ width: '100%', marginTop: 8 }}>
        <line x1="38" y1="178" x2="350" y2="178" stroke="var(--border-medium)" />
        <line x1="38" y1="28" x2="38" y2="178" stroke="var(--border-medium)" />
        {frontier.length > 1 && (
          <polyline
            fill="none"
            stroke="var(--brand-gold)"
            strokeWidth="2"
            strokeDasharray="5 4"
            points={frontier.map((point) => `${sx(point.x)},${sy(point.y)}`).join(' ')}
          />
        )}
        {points.map((point) => (
          <g key={point.profile.execution_identity_sha256}>
            <circle cx={sx(point.x)} cy={sy(point.y)} r="5" fill="var(--brand-blue)" />
            <title>{`${name(point.profile)}: ${point.y.toFixed(2)} / ${definition.format(point.x)}`}</title>
            <text x={sx(point.x) + 7} y={sy(point.y) - 6} fontSize="9" fill="var(--text-secondary)">
              {name(point.profile).split('/').pop()}
            </text>
          </g>
        ))}
        <text x="194" y="210" textAnchor="middle" fontSize="10" fill="var(--text-muted)">Lower resource use is better</text>
        <text x="10" y="104" textAnchor="middle" fontSize="10" fill="var(--text-muted)" transform="rotate(-90 10 104)">Intelligence</text>
      </svg>
    </div>
  );
}

export function V03Leaderboard({ artifact }: { artifact: V03LeaderboardArtifact }) {
  const ranked = [...artifact.profiles].sort(
    (left, right) => (right.scores.overall_intelligence.score ?? -1) - (left.scores.overall_intelligence.score ?? -1),
  );
  return (
    <section style={{ marginTop: 24, marginBottom: 40 }}>
      <div className="section-title"><span>Multilingual v0.3 · 18 directions</span></div>
      <p style={{ color: 'var(--text-secondary)', maxWidth: 900 }}>
        ZH↔EN (2), ZH/EN→JA·KO (4), and ZH/EN→DE·RU·FR·ES·PT-BR·TR (12).
        Directions are equally weighted; unresolved or missing evidence is never renormalized.
      </p>
      {artifact.status !== 'complete' && (
        <div className="v03-panel" style={{ padding: 12, marginBottom: 16, borderColor: 'var(--brand-gold)' }}>
          This artifact is incomplete. Scores remain visible only where evidence exists; it is not a final ranking.
        </div>
      )}
      <div className="v03-panel" style={{ overflowX: 'auto', marginBottom: 20 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 980 }}>
          <thead><tr>{['#', 'Recipe', 'Intelligence', 'ZH↔EN', 'East Asian', 'Continental', 'Hard format', 'Soft preference', 'Cost', 'Time', 'Total tokens'].map((label) => <th key={label} style={{ padding: 10, textAlign: 'left' }}>{label}</th>)}</tr></thead>
          <tbody>
            {ranked.map((profile, index) => (
              <tr key={profile.execution_identity_sha256} style={{ borderTop: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: 10 }}>{profile.scores.overall_intelligence.score === null ? '—' : index + 1}</td>
                <td style={{ padding: 10 }}><strong>{name(profile)}</strong><br /><small>{profile.recipe.reasoning_effort || 'unspecified'} · {profile.recipe.model_family || 'unknown family'}</small></td>
                <td style={{ padding: 10 }}>{score(profile.scores.overall_intelligence.score)}</td>
                <td style={{ padding: 10 }}>{score(profile.scores.zh_en_core.score)}</td>
                <td style={{ padding: 10 }}>{score(profile.scores.east_asian.score)}</td>
                <td style={{ padding: 10 }}>{score(profile.scores.continental.score)}</td>
                <td style={{ padding: 10 }}>{score(profile.scores.hard_format.score)}</td>
                <td style={{ padding: 10 }}>{score(profile.scores.soft_preference.score)}</td>
                <td style={{ padding: 10 }}>{profile.telemetry.cost_usd === null ? 'Unranked' : `$${profile.telemetry.cost_usd.toFixed(3)}`}</td>
                <td style={{ padding: 10 }}>{profile.telemetry.elapsed_seconds.toFixed(1)}s</td>
                <td style={{ padding: 10 }}>{profile.telemetry.tokens.total.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
        <FrontierScatter profiles={ranked} metric="cost" />
        <FrontierScatter profiles={ranked} metric="elapsed" />
        <FrontierScatter profiles={ranked} metric="tokens" />
      </div>
    </section>
  );
}
