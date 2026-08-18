export interface V03Measure {
  score: number | null;
  sample_count: number;
  decision_count: number;
  coverage: number;
  status: 'complete' | 'partial' | 'incomplete';
  missing_directions: string[];
}

export interface V03Profile {
  execution_identity_sha256: string;
  recipe: {
    requested_model?: string;
    model_family?: string;
    reasoning_effort?: string;
    provider?: string;
    [key: string]: unknown;
  };
  scores: {
    overall_intelligence: V03Measure;
    zh_en_core: V03Measure;
    east_asian: V03Measure;
    continental: V03Measure;
    hard_format: V03Measure;
    soft_preference: V03Measure;
  };
  telemetry: {
    call_count: number;
    elapsed_seconds: number;
    throughput_output_tokens_per_second: number | null;
    tokens: {
      input: number;
      output_including_reasoning: number;
      reasoning: number;
      total: number;
    };
    cost_usd: number | null;
    cost_observation_count: number;
    raw_contract_pass_rate: number | null;
    normalization_applied_rate: number | null;
  };
}

export interface V03LeaderboardArtifact {
  schema_version: 1;
  protocol: 'aventine-multilingual-tournament-v0.3';
  score_version: 'multilingual-pilot-v0.3-60soft-40hard';
  status: 'complete' | 'incomplete';
  exam_sha256: string;
  direction_count: 18;
  contestant_count: number;
  match_count: number;
  profiles: V03Profile[];
}
