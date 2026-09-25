import type { ZhEnPreviewArtifact } from '../types/zhEnPreview';

/** Append previously unseen models. Rechecks never replace a published historical score. */
export function buildZhEnCatalog(historical: ZhEnPreviewArtifact, incremental: ZhEnPreviewArtifact): ZhEnPreviewArtifact {
  const originalIds = new Set(historical.profiles.map((profile) => profile.model_id));
  const additions = incremental.profiles.filter((profile) => !originalIds.has(profile.model_id));
  const profiles = [
    ...historical.profiles.map((profile) => ({ ...profile, score_version: historical.score_version, source_commit: historical.source_commit })),
    ...additions.map((profile) => ({ ...profile, score_version: incremental.score_version, source_commit: incremental.source_commit })),
  ].sort((a, b) => b.zh_en_score - a.zh_en_score);
  // Count model-side observations: historical pairwise cases can appear for both models.
  const soft = profiles.flatMap((profile) => Object.values(profile.directions).map((direction) => direction.soft));
  const total = soft.reduce((sum, measure) => sum + measure.total, 0);
  const resolved = soft.reduce((sum, measure) => sum + measure.resolved, 0);
  return {
    ...incremental,
    catalog: { source_versions: [historical.score_version, incremental.score_version], original_count: originalIds.size, added_count: additions.length },
    profiles,
    contestant_count: profiles.length,
    soft_case_count: total,
    soft_resolved_count: resolved,
    soft_unresolved_count: total - resolved,
    judge_cost_usd: historical.judge_cost_usd + incremental.judge_cost_usd,
    judge_cost_missing_calls: (historical.judge_cost_missing_calls ?? 0) + (incremental.judge_cost_missing_calls ?? 0),
  };
}
