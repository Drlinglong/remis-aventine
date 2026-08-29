export type ZhEnDirection = 'zh-CN->en' | 'en->zh-CN';

export interface ZhEnMeasure {
  coverage: number;
  points: number;
  resolved: number;
  score: number;
  total: number;
}

export interface ZhEnDirectionResult {
  hard: ZhEnMeasure;
  score: number;
  soft: ZhEnMeasure;
}

export interface ZhEnPreviewProfile {
  directions: Record<ZhEnDirection, ZhEnDirectionResult>;
  execution_identity_sha256: string;
  model_family: string;
  model_id: string;
  telemetry: {
    cost_rank_eligible: boolean;
    cost_usd: number | null;
    elapsed_seconds: number;
    total_tokens: number;
  };
  zh_en_score: number;
}

export interface ZhEnPreviewArtifact {
  contestant_count: number;
  direction_count: 2;
  judge_cost_usd: number;
  profiles: ZhEnPreviewProfile[];
  protocol: string;
  schema_version: 1;
  soft_case_count: number;
  soft_resolved_count: number;
  soft_unresolved_count: number;
  status: 'complete-preview';
}
