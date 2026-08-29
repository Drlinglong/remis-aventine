export type ReasoningEffort = 'high' | 'medium' | 'low' | 'reasoning' | 'none';

export type LanguageCode =
  | 'FR'
  | 'DE'
  | 'RU'
  | 'ES'
  | 'PT'
  | 'TR'
  | 'IT'
  | 'PL'
  | 'UK'
  | 'NL'
  | 'SV'
  | 'CS'
  | 'ZH-CN'
  | 'ZH-TW'
  | 'JA'
  | 'KO'
  | 'VI'
  | 'TH';

export interface LanguageScore {
  code: LanguageCode;
  name: string;
  region: 'european' | 'east_asian';
  score: number;
  sample_count: number;
  coverage_percent: number;
  status: 'measured' | 'anchored' | 'preview_calibrated';
}

export interface ComponentScores {
  semantic_fidelity: number; // 30%
  constraint_integrity: number; // 20%
  cross_context_consistency: number; // 15%
  repair_precision: number; // 15%
  style_voice: number; // 10%
  repeatability: number; // 10%
}

export interface TelemetryData {
  elapsed_seconds: number;
  ttft_seconds: number;
  latency_p50_seconds: number;
  latency_p95_seconds: number;
  tokens_per_second: number;
  peak_vram_gib: number | null;
  peak_ram_gib: number | null;
  input_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  cost_usd: number | 'free';
}

export interface StageFailures {
  translation: {
    pass_count: number;
    recoverable_error_count: number;
    hard_failure_count: number;
    execution_failure_count: number;
    effective_multiplier: number;
  };
  proofreading: {
    pass_count: number;
    hard_failure_count: number;
    over_editing_count: number;
    execution_failure_count: number;
  };
}

export interface RemisWorkflowSignals {
  terminology_discovery_recall: number; // 0-1
  false_discovery_rate: number; // 0-1
  same_batch_cohesion: number; // 0-1
  cross_batch_drift: number; // 0-1
  reference_exact_match_rate: number; // 0-1
}

export interface RecipeEntry {
  id: string;
  rank: number;
  label: string;
  model_id: string;
  provider: string;
  provider_icon: string;
  reasoning_effort: ReasoningEffort;
  parameter_count_b?: number;
  quantization?: string;
  runtime?: string;
  recipe_sha256?: string;
  score_version: string;
  
  // Overall scores
  pilot_score: number;
  soft_preference: number; // 0-100%
  hard_reliability: number; // 0-100%
  
  // Regional scores (Issue #6)
  european_score: number;
  east_asian_score: number;
  multilingual_score: number;
  languages: Record<LanguageCode, LanguageScore>;
  
  // Capability breakdown (Issue #6 6-component)
  components: ComponentScores;
  
  // Matchup record in round robin
  wins: number;
  losses: number;
  ties: number;
  coverage_percent: number;
  
  // Telemetry & Hardware
  telemetry: TelemetryData;
  stage_failures: StageFailures;
  remis_signals: RemisWorkflowSignals;
  
  // Badges & Tagging
  badges: Array<{
    text: string;
    variant: 'gold' | 'blue' | 'emerald' | 'purple' | 'neutral';
  }>;
  is_anchor?: boolean;
  status: 'official_pilot' | 'anchored_placement' | 'community_run';
}

export interface PairwiseCell {
  left_id: string;
  right_id: string;
  left_wins: number;
  right_wins: number;
  ties: number;
  unresolved: number;
  total_cases: number;
  win_rate: number; // left win rate
  status: 'completed' | 'unresolved' | 'self';
  cases?: Array<{
    case_id: string;
    title: string;
    category: 'translation' | 'glossary_trap' | 'repair' | 'long_proclamation';
    source_text: string;
    candidate_a: string;
    candidate_b: string;
    swap_consistent: boolean;
    verdict: 'left_win' | 'right_win' | 'tie' | 'unresolved';
    reason: string;
  }>;
}

export interface CalibrationItem {
  id: string;
  name: string;
  type: 'mqm' | 'aces' | 'metricx' | 'xcomet';
  target_measure: string;
  judge_accuracy: number;
  severe_error_recall: number;
  false_good_rate: number;
  sample_size: number;
  provenance: string;
  phenomena_breakdown: Array<{
    name: string;
    samples: number;
    judge_accuracy: number;
    gold_agreement: number;
  }>;
}

export interface ChangelogItem {
  id: string;
  date: string;
  title: string;
  category: 'Tournaments' | 'Model Releases' | 'Calibration' | 'Infrastructure';
  summary: string;
  model_tag?: string;
  provider?: string;
  intelligence_index?: number;
  pilot_score?: number;
  highlights: string[];
  link?: string;
}
