import { describe, expect, it } from 'vitest';
import { parseV03Leaderboard } from './v03Leaderboard';

function fixture() {
  const pendingMeasure = {
    score: null,
    sample_count: 0,
    decision_count: 0,
    coverage: 0,
    status: 'pending',
    missing_directions: ['en->ko'],
  };

  return {
    schema_version: 1,
    protocol: 'aventine-multilingual-tournament-v0.3',
    score_version: 'multilingual-pilot-v0.3-60soft-40hard',
    artifact_id: 'v03-public-template',
    generated_at: null,
    status: 'draft',
    publication: {
      season: '2026-Q3',
      state: 'template',
      title: 'Multilingual Tournament v0.3',
      result_visibility: 'public_sanitized',
      exam_content_included: false,
      notes: ['Template only'],
    },
    exam: {
      exam_id: 'aventine-v03-private-exam',
      sha256: null,
      direction_count: 18,
      repeat_count: 2,
      case_count: 19,
      item_occurrence_count: 598,
    },
    topology: {
      soft_preference: {
        family_exclusion: true,
        dual_judge_sample_rate: 0.2,
        swap_order_on_dual: true,
      },
      direction_weighting: 'equal',
      source_group_weighting: 'equal',
    },
    judge_panel: [
      {
        judge_id: 'judge-gemini',
        model_id: 'google/gemini-3.7-flash',
        model_family: 'gemini',
        provider: 'google',
        reasoning_effort: 'high',
        service_tier: 'batch',
        role: 'primary',
        qualification: { status: 'qualified', accuracy: 0.96, sample_count: 50, position_consistency: 0.94 },
      },
    ],
    anchors: [
      {
        anchor_id: 'high',
        level: 'high',
        status: 'pending_selection',
        profile_id: null,
        frozen_output_sha256: null,
      },
    ],
    contestant_count: 1,
    profiles: [
      {
        profile_id: 'profile-solar-pro-4',
        execution_identity_sha256: null,
        label: 'Solar Pro 4',
        model_id: 'upstage/solar-pro-4',
        model_family: 'solar',
        provider: 'upstage',
        service_tier: 'default',
        reasoning_effort: null,
        focused_capabilities: ['ko'],
        status: 'pending_smoke',
        rank: null,
        scores: {
          overall_intelligence: { ...pendingMeasure },
          zh_en_core: { ...pendingMeasure },
          east_asian: { ...pendingMeasure },
          continental: { ...pendingMeasure },
          hard_format: { ...pendingMeasure },
          soft_preference: { ...pendingMeasure },
        },
        telemetry: {
          call_count: 0,
          elapsed_seconds: null,
          throughput_output_tokens_per_second: null,
          tokens: { input: 0, output_including_reasoning: 0, reasoning: 0, total: 0 },
          cost: {
            observed_usd: null,
            observation_count: 0,
            pricing_mode: 'pending',
            rank_eligible: false,
            reproducible_paid_equivalent_usd: null,
          },
          contract: {
            raw_pass_rate: null,
            normalization_applied_rate: null,
            final_pass_rate: null,
            punctuation_warning_count: 0,
          },
        },
        evidence_summary: {
          soft: {
            wins: 0,
            losses: 0,
            ties: 0,
            unresolved: 0,
            comparison_count: 0,
            dual_judged_count: 0,
            judge_agreement: null,
          },
          hard: {
            deterministic_pass: 0,
            deterministic_fail: 0,
            structural_pass: 0,
            structural_fail: 0,
            structural_unresolved: 0,
          },
        },
      },
    ],
    rankings: {
      overall_intelligence: [],
      zh_en_core: [],
      east_asian: [],
      continental: [],
      hard_format: [],
      soft_preference: [],
    },
    pareto_frontiers: { quality_cost: [], quality_speed: [], quality_tokens: [] },
    watchlist: [
      {
        model_id: 'anthropic/claude-next',
        label: 'Claude (reserved)',
        status: 'awaiting_api',
        reason: 'Not yet entered',
        focused_capabilities: [],
      },
    ],
  };
}

describe('parseV03Leaderboard', () => {
  it('maps the canonical public v0.3 contract without turning null into zero', () => {
    const result = parseV03Leaderboard(fixture());

    expect(result.exam).toMatchObject({ direction_count: 18, repeat_count: 2, case_count: 19 });
    expect(result.profiles[0].label).toBe('Solar Pro 4');
    expect(result.profiles[0].scores.overall_intelligence.score).toBeNull();
    expect(result.profiles[0].telemetry.cost.rank_eligible).toBe(false);
    expect(result.anchors[0].profile_id).toBeNull();
    expect(result.watchlist[0].status).toBe('awaiting_api');
  });

  it('rejects a result from an incompatible protocol', () => {
    const value = fixture();
    value.protocol = 'aventine-multilingual-tournament-v0.2';

    expect(() => parseV03Leaderboard(value)).toThrow('protocol is incompatible');
  });

  it('rejects the legacy flat cost shape', () => {
    const value = fixture();
    const telemetry = value.profiles[0].telemetry as Record<string, unknown>;
    delete telemetry.cost;
    telemetry.observed_cost_usd = null;

    expect(() => parseV03Leaderboard(value)).toThrow('telemetry.cost must be an object');
  });
});
