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
    verified_cost?: {
      amount: number;
      currency: 'CNY';
      cny_per_usd: number;
      converted_on: string;
      observed_date: string;
      rate_date: string;
      rate_source: 'CFETS central parity';
      source: 'provider-dashboard';
    };
  };
  zh_en_score: number;
}

export interface ZhEnPreviewArtifact {
  $schema: 'https://drlinglong.github.io/remis-aventine/schemas/v03-zh-en-public-result.schema.json';
  artifact_id: 'v0.3-zh-en-results';
  contestant_count: number;
  direction_count: 2;
  judge_cost_usd: number;
  profiles: ZhEnPreviewProfile[];
  protocol: 'aventine-v0.3-zh-en-balanced-degree4-sample20-60soft-40hard';
  schema_version: 1;
  score_version: 'v0.3-zh-en-60soft-40hard';
  source_commit: string;
  soft_case_count: number;
  soft_resolved_count: number;
  soft_unresolved_count: number;
  status: 'published-partial';
}
