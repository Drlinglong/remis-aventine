import type {
  V03ArtifactStatus,
  V03LeaderboardArtifact,
  V03MeasureStatus,
  V03Profile,
  V03ProfileStatus,
  V03ScoreKey,
  V03ScoreMeasure,
} from '../types/v03';
import { V03_SCORE_KEYS } from '../types/v03';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`${path} must be an object`);
  return value;
}

function array(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${path} must be an array`);
  return value;
}

function string(value: unknown, path: string): string {
  if (typeof value !== 'string' || value.length === 0) throw new Error(`${path} must be a non-empty string`);
  return value;
}

function nullableString(value: unknown, path: string): string | null {
  if (value === null) return null;
  return string(value, path);
}

function number(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`${path} must be a finite number`);
  return value;
}

function nullableNumber(value: unknown, path: string): number | null {
  if (value === null) return null;
  return number(value, path);
}

function integer(value: unknown, path: string): number {
  const parsed = number(value, path);
  if (!Number.isInteger(parsed)) throw new Error(`${path} must be an integer`);
  return parsed;
}

function boolean(value: unknown, path: string): boolean {
  if (typeof value !== 'boolean') throw new Error(`${path} must be a boolean`);
  return value;
}

function strings(value: unknown, path: string): string[] {
  return array(value, path).map((item, index) => string(item, `${path}[${index}]`));
}

function enumValue<T extends string>(value: unknown, allowed: readonly T[], path: string): T {
  if (typeof value !== 'string' || !allowed.includes(value as T)) {
    throw new Error(`${path} must be one of ${allowed.join(', ')}`);
  }
  return value as T;
}

function parseMeasure(value: unknown, path: string): V03ScoreMeasure {
  const measure = record(value, path);
  return {
    score: nullableNumber(measure.score, `${path}.score`),
    sample_count: integer(measure.sample_count, `${path}.sample_count`),
    decision_count: integer(measure.decision_count, `${path}.decision_count`),
    coverage: number(measure.coverage, `${path}.coverage`),
    status: enumValue<V03MeasureStatus>(measure.status, ['pending', 'complete', 'partial', 'incomplete'], `${path}.status`),
    missing_directions: strings(measure.missing_directions, `${path}.missing_directions`),
  };
}

function parseProfile(value: unknown, index: number): V03Profile {
  const path = `profiles[${index}]`;
  const profile = record(value, path);
  const scores = record(profile.scores, `${path}.scores`);
  const telemetry = record(profile.telemetry, `${path}.telemetry`);
  const tokens = record(telemetry.tokens, `${path}.telemetry.tokens`);
  const cost = record(telemetry.cost, `${path}.telemetry.cost`);
  const contract = record(telemetry.contract, `${path}.telemetry.contract`);
  const evidence = record(profile.evidence_summary, `${path}.evidence_summary`);
  const soft = record(evidence.soft, `${path}.evidence_summary.soft`);
  const hard = record(evidence.hard, `${path}.evidence_summary.hard`);

  const parsedScores = Object.fromEntries(
    V03_SCORE_KEYS.map((key) => [key, parseMeasure(scores[key], `${path}.scores.${key}`)]),
  ) as Record<V03ScoreKey, V03ScoreMeasure>;

  return {
    profile_id: string(profile.profile_id, `${path}.profile_id`),
    execution_identity_sha256: nullableString(profile.execution_identity_sha256, `${path}.execution_identity_sha256`),
    label: string(profile.label, `${path}.label`),
    model_id: string(profile.model_id, `${path}.model_id`),
    model_family: string(profile.model_family, `${path}.model_family`),
    provider: string(profile.provider, `${path}.provider`),
    service_tier: enumValue(profile.service_tier, ['default'] as const, `${path}.service_tier`),
    reasoning_effort: nullableString(profile.reasoning_effort, `${path}.reasoning_effort`),
    focused_capabilities: strings(profile.focused_capabilities, `${path}.focused_capabilities`),
    profile_status: enumValue<V03ProfileStatus>(profile.status, ['pending_smoke', 'ready', 'running', 'complete', 'incomplete', 'failed', 'withdrawn'], `${path}.status`),
    official_rank: profile.rank === null ? null : integer(profile.rank, `${path}.rank`),
    scores: parsedScores,
    telemetry: {
      call_count: integer(telemetry.call_count, `${path}.telemetry.call_count`),
      elapsed_seconds: nullableNumber(telemetry.elapsed_seconds, `${path}.telemetry.elapsed_seconds`),
      throughput_output_tokens_per_second: nullableNumber(telemetry.throughput_output_tokens_per_second, `${path}.telemetry.throughput_output_tokens_per_second`),
      tokens: {
        input: integer(tokens.input, `${path}.telemetry.tokens.input`),
        output_including_reasoning: integer(tokens.output_including_reasoning, `${path}.telemetry.tokens.output_including_reasoning`),
        reasoning: integer(tokens.reasoning, `${path}.telemetry.tokens.reasoning`),
        total: integer(tokens.total, `${path}.telemetry.tokens.total`),
      },
      cost: {
        observed_usd: nullableNumber(cost.observed_usd, `${path}.telemetry.cost.observed_usd`),
        observation_count: integer(cost.observation_count, `${path}.telemetry.cost.observation_count`),
        pricing_mode: enumValue(cost.pricing_mode, ['pending', 'metered', 'free_tier', 'local_unpriced', 'unavailable'] as const, `${path}.telemetry.cost.pricing_mode`),
        rank_eligible: boolean(cost.rank_eligible, `${path}.telemetry.cost.rank_eligible`),
        reproducible_paid_equivalent_usd: nullableNumber(cost.reproducible_paid_equivalent_usd, `${path}.telemetry.cost.reproducible_paid_equivalent_usd`),
      },
      contract: {
        raw_pass_rate: nullableNumber(contract.raw_pass_rate, `${path}.telemetry.contract.raw_pass_rate`),
        normalization_applied_rate: nullableNumber(contract.normalization_applied_rate, `${path}.telemetry.contract.normalization_applied_rate`),
        final_pass_rate: nullableNumber(contract.final_pass_rate, `${path}.telemetry.contract.final_pass_rate`),
        punctuation_warning_count: integer(contract.punctuation_warning_count, `${path}.telemetry.contract.punctuation_warning_count`),
      },
    },
    evidence_summary: {
      soft: {
        wins: integer(soft.wins, `${path}.evidence_summary.soft.wins`),
        losses: integer(soft.losses, `${path}.evidence_summary.soft.losses`),
        ties: integer(soft.ties, `${path}.evidence_summary.soft.ties`),
        unresolved: integer(soft.unresolved, `${path}.evidence_summary.soft.unresolved`),
        comparison_count: integer(soft.comparison_count, `${path}.evidence_summary.soft.comparison_count`),
        dual_judged_count: integer(soft.dual_judged_count, `${path}.evidence_summary.soft.dual_judged_count`),
        judge_agreement: nullableNumber(soft.judge_agreement, `${path}.evidence_summary.soft.judge_agreement`),
      },
      hard: {
        deterministic_pass: integer(hard.deterministic_pass, `${path}.evidence_summary.hard.deterministic_pass`),
        deterministic_fail: integer(hard.deterministic_fail, `${path}.evidence_summary.hard.deterministic_fail`),
        structural_pass: integer(hard.structural_pass, `${path}.evidence_summary.hard.structural_pass`),
        structural_fail: integer(hard.structural_fail, `${path}.evidence_summary.hard.structural_fail`),
        structural_unresolved: integer(hard.structural_unresolved, `${path}.evidence_summary.hard.structural_unresolved`),
      },
    },
  };
}

export function parseV03Leaderboard(value: unknown): V03LeaderboardArtifact {
  const root = record(value, 'v0.3 public result');
  if (root.schema_version !== 1) throw new Error('schema_version must be 1');
  if (root.protocol !== 'aventine-multilingual-tournament-v0.3') throw new Error('protocol is incompatible with Aventine v0.3');
  if (root.score_version !== 'multilingual-pilot-v0.3-60soft-40hard') throw new Error('score_version is incompatible with Aventine v0.3');

  const publication = record(root.publication, 'publication');
  const exam = record(root.exam, 'exam');
  const topology = record(root.topology, 'topology');
  const softPreference = record(topology.soft_preference, 'topology.soft_preference');
  if (exam.direction_count !== 18 || exam.repeat_count !== 2) throw new Error('v0.3 exam must declare 18 directions and 2 repeats');
  if (softPreference.family_exclusion !== true) throw new Error('v0.3 topology must enable family exclusion');
  if (publication.exam_content_included !== false) throw new Error('public artifact must not include exam content');

  const profiles = array(root.profiles, 'profiles').map(parseProfile);
  const pareto = record(root.pareto_frontiers, 'pareto_frontiers');
  const rankings = record(root.rankings, 'rankings');

  return {
    schema_version: 1,
    protocol: 'aventine-multilingual-tournament-v0.3',
    score_version: 'multilingual-pilot-v0.3-60soft-40hard',
    artifact_id: string(root.artifact_id, 'artifact_id'),
    generated_at: nullableString(root.generated_at, 'generated_at'),
    status: enumValue<V03ArtifactStatus>(root.status, ['draft', 'incomplete', 'complete'], 'status'),
    publication: {
      season: string(publication.season, 'publication.season'),
      state: enumValue(publication.state, ['template', 'preview', 'published'] as const, 'publication.state'),
      title: string(publication.title, 'publication.title'),
      result_visibility: enumValue(publication.result_visibility, ['public_sanitized'] as const, 'publication.result_visibility'),
      exam_content_included: false,
      notes: strings(publication.notes, 'publication.notes'),
    },
    exam: {
      exam_id: string(exam.exam_id, 'exam.exam_id'),
      sha256: nullableString(exam.sha256, 'exam.sha256'),
      direction_count: 18,
      repeat_count: 2,
      case_count: nullableNumber(exam.case_count, 'exam.case_count'),
      item_occurrence_count: nullableNumber(exam.item_occurrence_count, 'exam.item_occurrence_count'),
    },
    topology: {
      soft_preference: {
        family_exclusion: true,
        dual_judge_sample_rate: number(softPreference.dual_judge_sample_rate, 'topology.soft_preference.dual_judge_sample_rate'),
        swap_order_on_dual: boolean(softPreference.swap_order_on_dual, 'topology.soft_preference.swap_order_on_dual'),
      },
      direction_weighting: string(topology.direction_weighting, 'topology.direction_weighting'),
      source_group_weighting: string(topology.source_group_weighting, 'topology.source_group_weighting'),
    },
    judge_panel: array(root.judge_panel, 'judge_panel').map((entry, index) => {
      const judge = record(entry, `judge_panel[${index}]`);
      const qualification = record(judge.qualification, `judge_panel[${index}].qualification`);
      return {
        judge_id: string(judge.judge_id, `judge_panel[${index}].judge_id`),
        model_id: string(judge.model_id, `judge_panel[${index}].model_id`),
        model_family: string(judge.model_family, `judge_panel[${index}].model_family`),
        provider: string(judge.provider, `judge_panel[${index}].provider`),
        reasoning_effort: string(judge.reasoning_effort, `judge_panel[${index}].reasoning_effort`),
        service_tier: enumValue(judge.service_tier, ['batch'] as const, `judge_panel[${index}].service_tier`),
        role: enumValue(judge.role, ['primary', 'reserve'] as const, `judge_panel[${index}].role`),
        qualification: {
          status: enumValue(qualification.status, ['pending', 'qualified', 'rejected'] as const, `judge_panel[${index}].qualification.status`),
          accuracy: nullableNumber(qualification.accuracy, `judge_panel[${index}].qualification.accuracy`),
          sample_count: integer(qualification.sample_count, `judge_panel[${index}].qualification.sample_count`),
          position_consistency: nullableNumber(qualification.position_consistency, `judge_panel[${index}].qualification.position_consistency`),
        },
      };
    }),
    anchors: array(root.anchors, 'anchors').map((entry, index) => {
      const anchor = record(entry, `anchors[${index}]`);
      return {
        anchor_id: string(anchor.anchor_id, `anchors[${index}].anchor_id`),
        level: enumValue(anchor.level, ['high', 'medium', 'low'] as const, `anchors[${index}].level`),
        status: enumValue(anchor.status, ['pending_selection', 'frozen', 'retired'] as const, `anchors[${index}].status`),
        profile_id: nullableString(anchor.profile_id, `anchors[${index}].profile_id`),
        frozen_output_sha256: nullableString(anchor.frozen_output_sha256, `anchors[${index}].frozen_output_sha256`),
      };
    }),
    contestant_count: integer(root.contestant_count, 'contestant_count'),
    profiles,
    rankings: Object.fromEntries(V03_SCORE_KEYS.map((key) => [key, array(rankings[key], `rankings.${key}`).map((entry, index) => {
      const rank = record(entry, `rankings.${key}[${index}]`);
      return {
        rank: integer(rank.rank, `rankings.${key}[${index}].rank`),
        profile_id: string(rank.profile_id, `rankings.${key}[${index}].profile_id`),
        score: number(rank.score, `rankings.${key}[${index}].score`),
        coverage: number(rank.coverage, `rankings.${key}[${index}].coverage`),
      };
    })])) as V03LeaderboardArtifact['rankings'],
    pareto_frontiers: {
      quality_cost: strings(pareto.quality_cost, 'pareto_frontiers.quality_cost'),
      quality_speed: strings(pareto.quality_speed, 'pareto_frontiers.quality_speed'),
      quality_tokens: strings(pareto.quality_tokens, 'pareto_frontiers.quality_tokens'),
    },
    watchlist: array(root.watchlist, 'watchlist').map((entry, index) => {
      const watch = record(entry, `watchlist[${index}]`);
      return {
        model_id: string(watch.model_id, `watchlist[${index}].model_id`),
        label: string(watch.label, `watchlist[${index}].label`),
        status: enumValue(watch.status, ['awaiting_shared_host', 'awaiting_api', 'deferred', 'retired'] as const, `watchlist[${index}].status`),
        reason: string(watch.reason, `watchlist[${index}].reason`),
        focused_capabilities: strings(watch.focused_capabilities, `watchlist[${index}].focused_capabilities`),
      };
    }),
  };
}

export async function loadV03Leaderboard(signal?: AbortSignal): Promise<V03LeaderboardArtifact | null> {
  const url = `${import.meta.env.BASE_URL}data/v03-public-result.json`;
  const response = await fetch(url, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`v0.3 public result request failed: ${response.status}`);
  if ((response.headers.get('content-type') || '').includes('text/html')) return null;
  return parseV03Leaderboard(await response.json());
}
