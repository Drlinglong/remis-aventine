import type { ZhEnPreviewProfile } from '../types/zhEnPreview';

export type ParetoMetric = 'cost' | 'latency' | 'tokens';

export function observedThroughput(profile: ZhEnPreviewProfile): number {
  return profile.telemetry.elapsed_seconds > 0
    ? profile.telemetry.total_tokens / profile.telemetry.elapsed_seconds
    : 0;
}

export function paretoValue(profile: ZhEnPreviewProfile, metric: ParetoMetric): number | null {
  if (metric === 'cost') return profile.telemetry.cost_usd;
  if (metric === 'latency') return profile.telemetry.elapsed_seconds;
  return profile.telemetry.total_tokens;
}

export function paretoFrontier(profiles: ZhEnPreviewProfile[], metric: ParetoMetric): ZhEnPreviewProfile[] {
  const eligible = profiles
    .filter((profile) => paretoValue(profile, metric) !== null)
    .sort((left, right) => (paretoValue(left, metric) as number) - (paretoValue(right, metric) as number));

  let bestScore = -Infinity;
  return eligible.filter((profile) => {
    if (profile.zh_en_score <= bestScore) return false;
    bestScore = profile.zh_en_score;
    return true;
  });
}
