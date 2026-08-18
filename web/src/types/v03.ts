export const V03_SCORE_KEYS = [
  'overall_intelligence',
  'zh_en_core',
  'east_asian',
  'continental',
  'hard_format',
  'soft_preference',
] as const;

export type V03ScoreKey = (typeof V03_SCORE_KEYS)[number];
export type V03Status = 'complete' | 'partial' | 'incomplete';

export interface V03ScoreMeasure {
  score: number | null;
  sample_count: number | null;
  decision_count: number | null;
  coverage: number | null;
  judge_agreement: number | null;
  unresolved_signals: number | null;
  status: V03Status;
  missing_directions: string[];
}

export interface V03Profile {
  execution_identity_sha256: string;
  profile_status: V03Status;
  official_rank: number | null;
  rank_eligible: boolean;
  recipe: {
    requested_model?: string;
    model_family?: string;
    provider?: string;
    reasoning_effort?: string;
    [key: string]: unknown;
  };
  scores: Record<V03ScoreKey, V03ScoreMeasure>;
  telemetry: {
    call_count: number | null;
    elapsed_seconds: number | null;
    throughput_output_tokens_per_second: number | null;
    tokens: {
      input: number | null;
      output_including_reasoning: number | null;
      reasoning: number | null;
      total: number | null;
    };
    cost_usd: number | null;
    cost_observation_count: number | null;
    rank_eligible: boolean;
    judge_agreement: number | null;
    unresolved_signals: number | null;
    raw_contract_pass_rate: number | null;
    normalization_applied_rate: number | null;
  };
}

export interface V03TechnicalDetails {
  fixed_recipe: string;
  provenance: string;
  validator: string;
  judge_panel: string;
  contract: string;
}

export interface V03LeaderboardArtifact {
  schema_version: number;
  protocol: string;
  score_version: string;
  status: 'complete' | 'incomplete';
  exam_sha256: string | null;
  direction_count: number;
  contestant_count: number;
  match_count: number;
  profiles: V03Profile[];
  pareto_frontiers: Record<string, string[]>;
  anchors: string[];
  watchlist: string[];
  technical_details: V03TechnicalDetails;
}
