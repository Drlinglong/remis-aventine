import type { ZhEnPreviewArtifact } from '../types/zhEnPreview';

/** Append previously unseen models. Rechecks never replace a published historical score. */
export function buildZhEnCatalog(historical: ZhEnPreviewArtifact, ...incrementals: ZhEnPreviewArtifact[]): ZhEnPreviewArtifact {
  const sources = [historical, ...incrementals];
  const latest = sources[sources.length - 1];
  const originalIds = new Set(historical.profiles.map((profile) => profile.model_id));
  const seen = new Set<string>();
  const profiles = sources.flatMap((source) => source.profiles.flatMap((profile) => {
    if (seen.has(profile.model_id)) return [];
    seen.add(profile.model_id);
    return [{ ...profile, score_version: source.score_version, source_commit: source.source_commit }];
  })).sort((a, b) => b.zh_en_score - a.zh_en_score);
  // Count model-side observations: historical pairwise cases can appear for both models.
  const soft = profiles.flatMap((profile) => Object.values(profile.directions).map((direction) => direction.soft));
  const total = soft.reduce((sum, measure) => sum + measure.total, 0);
  const resolved = soft.reduce((sum, measure) => sum + measure.resolved, 0);
  return {
    ...latest,
    catalog: { source_versions: sources.map((source) => source.score_version), original_count: originalIds.size, added_count: profiles.length - originalIds.size },
    profiles,
    contestant_count: profiles.length,
    soft_case_count: total,
    soft_resolved_count: resolved,
    soft_unresolved_count: total - resolved,
    judge_cost_usd: sources.reduce((sum, source) => sum + source.judge_cost_usd, 0),
    judge_cost_missing_calls: sources.reduce((sum, source) => sum + (source.judge_cost_missing_calls ?? 0), 0),
  };
}
