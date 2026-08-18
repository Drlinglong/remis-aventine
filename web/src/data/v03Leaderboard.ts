import type {
  V03LeaderboardArtifact,
  V03Profile,
  V03ScoreKey,
  V03ScoreMeasure,
  V03Status,
} from '../types/v03';
import { V03_SCORE_KEYS } from '../types/v03';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function asNumberOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function asStatus(value: unknown): V03Status {
  return value === 'complete' || value === 'partial' || value === 'incomplete' ? value : 'incomplete';
}

function parseMeasure(value: unknown): V03ScoreMeasure {
  const measure = isRecord(value) ? value : {};
  return {
    score: asNumberOrNull(measure.score),
    sample_count: asNumberOrNull(measure.sample_count),
    decision_count: asNumberOrNull(measure.decision_count),
    coverage: asNumberOrNull(measure.coverage),
    judge_agreement: asNumberOrNull(measure.judge_agreement),
    unresolved_signals: asNumberOrNull(measure.unresolved_signals),
    status: asStatus(measure.status),
    missing_directions: asStringArray(measure.missing_directions),
  };
}

function parseProfile(value: unknown): V03Profile {
  if (!isRecord(value)) {
    throw new Error('v0.3 profile must be an object');
  }
  const recipe = isRecord(value.recipe) ? value.recipe : {};
  const telemetry = isRecord(value.telemetry) ? value.telemetry : {};
  const tokens = isRecord(telemetry.tokens) ? telemetry.tokens : {};
  const scores = isRecord(value.scores) ? value.scores : {};

  const parsedScores = Object.fromEntries(
    V03_SCORE_KEYS.map((key) => [key, parseMeasure(scores[key])]),
  ) as Record<V03ScoreKey, V03ScoreMeasure>;

  const rankEligible = typeof value.rank_eligible === 'boolean'
    ? value.rank_eligible
    : typeof telemetry.rank_eligible === 'boolean'
      ? telemetry.rank_eligible
      : true;

  return {
    execution_identity_sha256: asString(value.execution_identity_sha256) || 'unknown-profile',
    profile_status: asStatus(value.status),
    official_rank: asNumberOrNull(value.official_rank),
    rank_eligible: rankEligible,
    recipe: {
      requested_model: asString(recipe.requested_model) || undefined,
      model_family: asString(recipe.model_family) || undefined,
      provider: asString(recipe.provider) || undefined,
      reasoning_effort: asString(recipe.reasoning_effort) || undefined,
    },
    scores: parsedScores,
    telemetry: {
      call_count: asNumberOrNull(telemetry.call_count),
      elapsed_seconds: asNumberOrNull(telemetry.elapsed_seconds),
      throughput_output_tokens_per_second: asNumberOrNull(telemetry.throughput_output_tokens_per_second),
      tokens: {
        input: asNumberOrNull(tokens.input),
        output_including_reasoning: asNumberOrNull(tokens.output_including_reasoning),
        reasoning: asNumberOrNull(tokens.reasoning),
        total: asNumberOrNull(tokens.total),
      },
      cost_usd: asNumberOrNull(telemetry.cost_usd),
      cost_observation_count: asNumberOrNull(telemetry.cost_observation_count),
      rank_eligible: typeof telemetry.rank_eligible === 'boolean' ? telemetry.rank_eligible : rankEligible,
      judge_agreement: asNumberOrNull(telemetry.judge_agreement),
      unresolved_signals: asNumberOrNull(telemetry.unresolved_signals),
      raw_contract_pass_rate: asNumberOrNull(telemetry.raw_contract_pass_rate),
      normalization_applied_rate: asNumberOrNull(telemetry.normalization_applied_rate),
    },
  };
}

export function parseV03Leaderboard(value: unknown): V03LeaderboardArtifact {
  if (!isRecord(value)) {
    throw new Error('v0.3 public result payload must be an object');
  }

  if (!Array.isArray(value.profiles) || !isRecord(value.pareto_frontiers)) {
    throw new Error('v0.3 public result payload has an incompatible contract');
  }

  const technical = isRecord(value.technical_details) ? value.technical_details : {};
  const result: V03LeaderboardArtifact = {
    schema_version: asNumber(value.schema_version, 1),
    protocol: asString(value.protocol, 'aventine-multilingual-tournament-v0.3'),
    score_version: asString(value.score_version, 'multilingual-pilot-v0.3-60soft-40hard'),
    status: value.status === 'complete' ? 'complete' : 'incomplete',
    exam_sha256: asString(value.exam_sha256) || null,
    direction_count: asNumber(value.direction_count, 18),
    contestant_count: asNumber(value.contestant_count, value.profiles.length),
    match_count: asNumber(value.match_count, 0),
    profiles: value.profiles.map(parseProfile),
    pareto_frontiers: Object.fromEntries(
      Object.entries(value.pareto_frontiers).map(([key, ids]) => [key, asStringArray(ids)]),
    ),
    anchors: asStringArray(value.anchors),
    watchlist: asStringArray(value.watchlist),
    technical_details: {
      fixed_recipe: asString(technical.fixed_recipe, 'Not published'),
      provenance: asString(technical.provenance, 'Not published'),
      validator: asString(technical.validator, 'Not published'),
      judge_panel: asString(technical.judge_panel, 'Not published'),
      contract: asString(technical.contract, 'Not published'),
    },
  };

  if (result.direction_count !== 18) {
    throw new Error('v0.3 public result direction_count must be 18');
  }

  return result;
}

export async function loadV03Leaderboard(
  signal?: AbortSignal,
): Promise<V03LeaderboardArtifact | null> {
  const url = `${import.meta.env.BASE_URL}data/v03-public-result.json`;
  const response = await fetch(url, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`v0.3 public result request failed: ${response.status}`);
  if ((response.headers.get('content-type') || '').includes('text/html')) return null;
  return parseV03Leaderboard(await response.json());
}
