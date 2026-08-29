export const V03_SCORE_KEYS = [
  'overall_intelligence',
  'zh_en_core',
  'east_asian',
  'continental',
  'hard_format',
  'soft_preference',
] as const;

export type V03ScoreKey = (typeof V03_SCORE_KEYS)[number];
export type V03ArtifactStatus = 'draft' | 'incomplete' | 'complete';
export type V03MeasureStatus = 'pending' | 'complete' | 'partial' | 'incomplete';
export type V03ProfileStatus = 'pending_smoke' | 'ready' | 'running' | 'complete' | 'incomplete' | 'failed' | 'withdrawn';

export interface V03ScoreMeasure {
  score: number | null;
  sample_count: number;
  decision_count: number;
  coverage: number;
  status: V03MeasureStatus;
  missing_directions: string[];
}

export interface V03Profile {
  profile_id: string;
  execution_identity_sha256: string | null;
  label: string;
  model_id: string;
  model_family: string;
  provider: string;
  service_tier: 'default';
  reasoning_effort: string | null;
  focused_capabilities: string[];
  profile_status: V03ProfileStatus;
  official_rank: number | null;
  scores: Record<V03ScoreKey, V03ScoreMeasure>;
  telemetry: {
    call_count: number;
    elapsed_seconds: number | null;
    throughput_output_tokens_per_second: number | null;
    tokens: {
      input: number;
      output_including_reasoning: number;
      reasoning: number;
      total: number;
    };
    cost: {
      observed_usd: number | null;
      observation_count: number;
      pricing_mode: 'pending' | 'metered' | 'free_tier' | 'local_unpriced' | 'unavailable';
      rank_eligible: boolean;
      reproducible_paid_equivalent_usd: number | null;
    };
    contract: {
      raw_pass_rate: number | null;
      normalization_applied_rate: number | null;
      final_pass_rate: number | null;
      punctuation_warning_count: number;
    };
  };
  evidence_summary: {
    soft: {
      wins: number;
      losses: number;
      ties: number;
      unresolved: number;
      comparison_count: number;
      dual_judged_count: number;
      judge_agreement: number | null;
    };
    hard: {
      deterministic_pass: number;
      deterministic_fail: number;
      structural_pass: number;
      structural_fail: number;
      structural_unresolved: number;
    };
  };
}

export interface V03Judge {
  judge_id: string;
  model_id: string;
  model_family: string;
  provider: string;
  reasoning_effort: string;
  service_tier: 'batch';
  role: 'primary' | 'reserve';
  qualification: {
    status: 'pending' | 'qualified' | 'rejected';
    accuracy: number | null;
    sample_count: number;
    position_consistency: number | null;
  };
}

export interface V03Anchor {
  anchor_id: string;
  level: 'high' | 'medium' | 'low';
  status: 'pending_selection' | 'frozen' | 'retired';
  profile_id: string | null;
  frozen_output_sha256: string | null;
}

export interface V03WatchlistEntry {
  model_id: string;
  label: string;
  status: 'awaiting_shared_host' | 'awaiting_api' | 'deferred' | 'retired';
  reason: string;
  focused_capabilities: string[];
}

export interface V03LeaderboardArtifact {
  schema_version: 1;
  protocol: 'aventine-multilingual-tournament-v0.3';
  score_version: 'multilingual-pilot-v0.3-60soft-40hard';
  artifact_id: string;
  generated_at: string | null;
  status: V03ArtifactStatus;
  publication: {
    season: string;
    state: 'template' | 'preview' | 'published';
    title: string;
    result_visibility: 'public_sanitized';
    exam_content_included: false;
    notes: string[];
  };
  exam: {
    exam_id: string;
    sha256: string | null;
    direction_count: 18;
    repeat_count: 2;
    case_count: number | null;
    item_occurrence_count: number | null;
  };
  topology: {
    soft_preference: {
      family_exclusion: true;
      dual_judge_sample_rate: number;
      swap_order_on_dual: boolean;
    };
    direction_weighting: string;
    source_group_weighting: string;
  };
  judge_panel: V03Judge[];
  anchors: V03Anchor[];
  contestant_count: number;
  profiles: V03Profile[];
  rankings: Record<V03ScoreKey, Array<{ rank: number; profile_id: string; score: number; coverage: number }>>;
  pareto_frontiers: {
    quality_cost: string[];
    quality_speed: string[];
    quality_tokens: string[];
  };
  watchlist: V03WatchlistEntry[];
}
