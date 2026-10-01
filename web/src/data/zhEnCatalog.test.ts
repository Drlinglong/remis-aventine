import { describe, expect, it } from 'vitest';
import originalJson from '../../public/data/v03-zh-en-results.json';
import incrementalJson from '../../public/data/v03-zh-en-anchors-20260925.json';
import { parseZhEnPreview } from './zhEnPreview';
import { buildZhEnCatalog } from './zhEnCatalog';
import { defaultModelIds } from './modelSelection';
import { modelDetailHref } from './modelDetailUrl';

const original = parseZhEnPreview(originalJson);
const incremental = parseZhEnPreview(incrementalJson);

describe('incremental model catalog', () => {
  it('appends four new models to all seventeen originals without modifying either source', () => {
    const before = JSON.stringify([original, incremental]);
    const catalog = buildZhEnCatalog(original, incremental);
    expect(catalog.contestant_count).toBe(21);
    expect(new Set(catalog.profiles.map((p) => p.model_id)).size).toBe(21);
    expect(catalog.catalog).toMatchObject({ original_count: 17, added_count: 4 });
    for (const old of original.profiles) {
      expect(catalog.profiles.find((p) => p.model_id === old.model_id)).toEqual({ ...old, score_version: original.score_version, source_commit: original.source_commit });
    }
    expect(JSON.stringify([original, incremental])).toBe(before);
  });
  it('shows nineteen models by default, retaining original predecessors for manual selection', () => {
    const catalog = buildZhEnCatalog(original, incremental);
    const defaults = defaultModelIds(catalog.profiles);
    expect(defaults).toHaveLength(19);
    expect(defaults).toEqual(expect.arrayContaining(['openai/gpt-6-luna', 'openai/gpt-6-sol', 'deepseek/deepseek-v4.1-flash', 'xiaomi/mimo-v2.6-pro', 'qwen/qwen3.8-max']));
    expect(defaults).not.toContain('openai/gpt-5.6-luna');
    expect(defaults).not.toContain('deepseek/deepseek-v4-flash-0731');
  });
  it('keeps detail URLs tied to each row source instead of the latest judge panel', () => {
    const catalog = buildZhEnCatalog(original, incremental);
    for (const profile of catalog.profiles) {
      const version = original.profiles.some((p) => p.model_id === profile.model_id) ? original.score_version : incremental.score_version;
      const href = modelDetailHref(profile.model_id, 'en', '/remis-aventine/', '/', profile.score_version);
      expect(new URL(href, 'https://example.com').searchParams.get('score_version')).toBe(version);
    }
  });
  it('counts model-side observations without adding the two rechecked models twice', () => {
    const catalog = buildZhEnCatalog(original, incremental);
    const measures = catalog.profiles.flatMap((p) => Object.values(p.directions).map((d) => d.soft));
    expect(catalog.soft_case_count).toBe(measures.reduce((n, m) => n + m.total, 0));
    expect(catalog.soft_resolved_count + catalog.soft_unresolved_count).toBe(catalog.soft_case_count);
    expect(catalog.judge_cost_usd).toBeCloseTo(original.judge_cost_usd + incremental.judge_cost_usd);
    expect(catalog.judge_cost_missing_calls).toBe(3);
  });
  it('appends another source without replacing earlier model scores or provenance', () => {
    const local = structuredClone(incremental);
    local.score_version = 'v0.3-zh-en-anchors-local-20261001-v1';
    local.profiles = [
      { ...structuredClone(incremental.profiles[0]), model_id: 'bilibili/index-translate-9b-q8_0', model_family: 'bilibili-index' },
      { ...structuredClone(incremental.profiles[0]), model_id: 'xiaomi/mimo-v2.6-distill-qwen-9b-q4_k_s', model_family: 'xiaomi-mimo' },
      { ...structuredClone(original.profiles[0]), zh_en_score: 0 },
    ];
    const before = JSON.stringify([original, incremental, local]);
    const previous = buildZhEnCatalog(original, incremental);
    const catalog = buildZhEnCatalog(original, incremental, local);
    expect(catalog.contestant_count).toBe(23);
    expect(catalog.catalog).toMatchObject({ original_count: 17, added_count: 6 });
    expect(catalog.catalog?.source_versions).toHaveLength(3);
    for (const profile of previous.profiles) expect(catalog.profiles.find((p) => p.model_id === profile.model_id)).toEqual(profile);
    expect(defaultModelIds(catalog.profiles)).toHaveLength(21);
    expect(JSON.stringify([original, incremental, local])).toBe(before);
  });
});
