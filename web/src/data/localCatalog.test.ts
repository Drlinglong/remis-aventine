import { describe, expect, it } from 'vitest';
import originalJson from '../../public/data/v03-zh-en-results.json';
import septemberJson from '../../public/data/v03-zh-en-anchors-20260925.json';
import localJson from '../../public/data/v03-zh-en-anchors-local-20261001.json';
import { parseZhEnPreview } from './zhEnPreview';
import { buildZhEnCatalog } from './zhEnCatalog';
import { defaultModelIds, restoreSelection } from './modelSelection';
import { zhEnSource } from './zhEnSource';

const original = parseZhEnPreview(originalJson);
const september = parseZhEnPreview(septemberJson);
const local = parseZhEnPreview(localJson);
const previous = buildZhEnCatalog(original, september);
const catalog = buildZhEnCatalog(original, september, local);
const localIds = ['bilibili/index-translate-9b-q8_0', 'xiaomi/mimo-v2.6-distill-qwen-9b-q4_k_s'];

describe('published local model catalog', () => {
  it('adds the two actual recipes to every unchanged historical row', () => {
    expect(catalog.contestant_count).toBe(23);
    expect(catalog.catalog).toMatchObject({ original_count: 17, added_count: 6 });
    expect(local.profiles.map((p) => p.model_id).sort()).toEqual([...localIds].sort());
    for (const profile of previous.profiles) {
      expect(catalog.profiles.find((p) => p.model_id === profile.model_id)).toEqual(profile);
    }
    expect(defaultModelIds(catalog.profiles)).toHaveLength(21);
  });

  it('preserves a saved selection while making both new recipes available', () => {
    const selected = [previous.profiles[0].model_id];
    const saved = JSON.stringify({ selected, known: previous.profiles.map((p) => p.model_id) });
    expect(restoreSelection(saved, catalog.profiles).sort()).toEqual([...selected, ...localIds].sort());
  });

  it('keeps local compute unranked and each source download tied to its version', () => {
    for (const profile of local.profiles) {
      expect(profile.telemetry.cost_usd).toBeNull();
      expect(profile.telemetry.cost_rank_eligible).toBe(false);
      expect(catalog.profiles.find((p) => p.model_id === profile.model_id)?.score_version).toBe(local.score_version);
    }
    expect(zhEnSource(local)).toEqual({ filename: 'v03-zh-en-anchors-local-20261001.json', date: '2026-10-01' });
    expect(zhEnSource(september).filename).toBe('v03-zh-en-anchors-20260925.json');
    expect(zhEnSource(original).filename).toBe('v03-zh-en-results.json');
  });
});
