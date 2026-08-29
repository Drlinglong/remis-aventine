import type {
  ZhEnDirection,
  ZhEnDirectionResult,
  ZhEnMeasure,
  ZhEnPreviewArtifact,
  ZhEnPreviewProfile,
} from '../types/zhEnPreview';

function object(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${path} must be an object`);
  }
  return value as Record<string, unknown>;
}

function finite(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`${path} must be a finite number`);
  return value;
}

function integer(value: unknown, path: string): number {
  const result = finite(value, path);
  if (!Number.isInteger(result)) throw new Error(`${path} must be an integer`);
  return result;
}

function text(value: unknown, path: string): string {
  if (typeof value !== 'string' || value.length === 0) throw new Error(`${path} must be a non-empty string`);
  return value;
}

function measure(value: unknown, path: string): ZhEnMeasure {
  const source = object(value, path);
  return {
    coverage: finite(source.coverage, `${path}.coverage`),
    points: finite(source.points, `${path}.points`),
    resolved: integer(source.resolved, `${path}.resolved`),
    score: finite(source.score, `${path}.score`),
    total: integer(source.total, `${path}.total`),
  };
}

function direction(value: unknown, path: string): ZhEnDirectionResult {
  const source = object(value, path);
  return {
    hard: measure(source.hard, `${path}.hard`),
    score: finite(source.score, `${path}.score`),
    soft: measure(source.soft, `${path}.soft`),
  };
}

function profile(value: unknown, index: number): ZhEnPreviewProfile {
  const path = `profiles[${index}]`;
  const source = object(value, path);
  const directions = object(source.directions, `${path}.directions`);
  const telemetry = object(source.telemetry, `${path}.telemetry`);
  const cost = telemetry.cost_usd;
  if (cost !== null && (typeof cost !== 'number' || !Number.isFinite(cost))) {
    throw new Error(`${path}.telemetry.cost_usd must be a finite number or null`);
  }
  if (typeof telemetry.cost_rank_eligible !== 'boolean') {
    throw new Error(`${path}.telemetry.cost_rank_eligible must be a boolean`);
  }
  const verifiedCostSource = telemetry.verified_cost === undefined
    ? null
    : object(telemetry.verified_cost, `${path}.telemetry.verified_cost`);
  const verifiedCost = verifiedCostSource
    ? {
        amount: finite(verifiedCostSource.amount, `${path}.telemetry.verified_cost.amount`),
        currency: text(verifiedCostSource.currency, `${path}.telemetry.verified_cost.currency`),
        cny_per_usd: finite(verifiedCostSource.cny_per_usd, `${path}.telemetry.verified_cost.cny_per_usd`),
        converted_on: text(verifiedCostSource.converted_on, `${path}.telemetry.verified_cost.converted_on`),
        observed_date: text(verifiedCostSource.observed_date, `${path}.telemetry.verified_cost.observed_date`),
        rate_date: text(verifiedCostSource.rate_date, `${path}.telemetry.verified_cost.rate_date`),
        rate_source: text(verifiedCostSource.rate_source, `${path}.telemetry.verified_cost.rate_source`),
        source: text(verifiedCostSource.source, `${path}.telemetry.verified_cost.source`),
      }
    : undefined;
  if (verifiedCost && (verifiedCost.currency !== 'CNY' || verifiedCost.rate_source !== 'CFETS central parity' || verifiedCost.source !== 'provider-dashboard')) {
    throw new Error(`${path}.telemetry.verified_cost has an unsupported currency or source`);
  }

  return {
    directions: Object.fromEntries((['zh-CN->en', 'en->zh-CN'] as ZhEnDirection[]).map((key) => [
      key,
      direction(directions[key], `${path}.directions.${key}`),
    ])) as Record<ZhEnDirection, ZhEnDirectionResult>,
    execution_identity_sha256: text(source.execution_identity_sha256, `${path}.execution_identity_sha256`),
    model_family: text(source.model_family, `${path}.model_family`),
    model_id: text(source.model_id, `${path}.model_id`),
    telemetry: {
      cost_rank_eligible: telemetry.cost_rank_eligible,
      cost_usd: cost,
      elapsed_seconds: finite(telemetry.elapsed_seconds, `${path}.telemetry.elapsed_seconds`),
      total_tokens: integer(telemetry.total_tokens, `${path}.telemetry.total_tokens`),
      verified_cost: verifiedCost as ZhEnPreviewProfile['telemetry']['verified_cost'],
    },
    zh_en_score: finite(source.zh_en_score, `${path}.zh_en_score`),
  };
}

export function parseZhEnPreview(value: unknown): ZhEnPreviewArtifact {
  const source = object(value, 'ZH-EN results');
  if (source.schema_version !== 1) throw new Error('ZH-EN results schema_version must be 1');
  if (source.status !== 'published-partial') throw new Error('ZH-EN results must have status published-partial');
  if (source.direction_count !== 2) throw new Error('ZH-EN results must contain exactly two directions');
  if (!Array.isArray(source.profiles)) throw new Error('ZH-EN results profiles must be an array');
  const profiles = source.profiles.map(profile);
  const contestantCount = integer(source.contestant_count, 'contestant_count');
  if (profiles.length !== contestantCount) throw new Error('contestant_count does not match profiles length');

  return {
    contestant_count: contestantCount,
    direction_count: 2,
    judge_cost_usd: finite(source.judge_cost_usd, 'judge_cost_usd'),
    profiles,
    protocol: text(source.protocol, 'protocol'),
    schema_version: 1,
    source_commit: text(source.source_commit, 'source_commit'),
    soft_case_count: integer(source.soft_case_count, 'soft_case_count'),
    soft_resolved_count: integer(source.soft_resolved_count, 'soft_resolved_count'),
    soft_unresolved_count: integer(source.soft_unresolved_count, 'soft_unresolved_count'),
    status: 'published-partial',
  };
}

export async function loadZhEnPreview(signal?: AbortSignal): Promise<ZhEnPreviewArtifact | null> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/v03-zh-en-results.json`, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`ZH-EN results request failed: ${response.status}`);
  if ((response.headers.get('content-type') || '').includes('text/html')) return null;
  return parseZhEnPreview(await response.json());
}
