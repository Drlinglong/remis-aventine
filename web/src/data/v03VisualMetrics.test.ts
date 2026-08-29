import { describe, expect, it } from 'vitest';
import { observedThroughput, paretoFrontier } from './v03VisualMetrics';
import type { ZhEnPreviewProfile } from '../types/zhEnPreview';

function profile(id: string, score: number, cost: number, tokens = 100, seconds = 10): ZhEnPreviewProfile {
  const measure = { coverage: 1, points: score, resolved: 1, score, total: 1 };
  return {
    directions: {
      'en->zh-CN': { hard: measure, score, soft: measure },
      'zh-CN->en': { hard: measure, score, soft: measure },
    },
    execution_identity_sha256: id,
    model_family: 'test',
    model_id: id,
    telemetry: { cost_rank_eligible: true, cost_usd: cost, elapsed_seconds: seconds, total_tokens: tokens },
    zh_en_score: score,
  };
}

describe('v0.3 visual metrics', () => {
  it('derives observed throughput from the published telemetry', () => {
    expect(observedThroughput(profile('fast', 80, 1, 420, 12))).toBe(35);
  });

  it('keeps only profiles that improve quality as cost rises', () => {
    const profiles = [profile('cheap', 60, 0.1), profile('dominated', 55, 0.2), profile('best', 80, 0.3)];
    expect(paretoFrontier(profiles, 'cost').map((item) => item.model_id)).toEqual(['cheap', 'best']);
  });
});
