import { describe, expect, it } from 'vitest';
import originalJson from '../../public/data/v03-zh-en-results.json';
import septemberJson from '../../public/data/v03-zh-en-anchors-20260925.json';
import localJson from '../../public/data/v03-zh-en-anchors-local-20261001.json';
import octoberJson from '../../public/data/v03-zh-en-anchors-20261009.json';
import { parseZhEnPreview } from './zhEnPreview';
import { buildZhEnCatalog } from './zhEnCatalog';
import { defaultModelIds, restoreSelection } from './modelSelection';
import { executionSettings } from './executionSettings';
import { zhEnSource } from './zhEnSource';

const previousSources = [originalJson, septemberJson, localJson].map(parseZhEnPreview);
const previous = buildZhEnCatalog(previousSources[0], ...previousSources.slice(1));
const october = parseZhEnPreview(octoberJson);
const catalog = buildZhEnCatalog(previousSources[0], ...previousSources.slice(1), october);

describe('October published incremental catalog', () => {
  it('adds exactly the requested recipes without changing older results', () => {
    expect(catalog.contestant_count).toBe(25);
    expect(catalog.catalog).toMatchObject({ original_count: 17, added_count: 8 });
    expect(october.profiles.map((p) => p.model_id).sort()).toEqual(['anthropic/claude-haiku-5.5', 'openai/gpt-6.1-sol']);
    for (const profile of previous.profiles) expect(catalog.profiles.find((p) => p.model_id === profile.model_id)).toEqual(profile);
    for (const profile of october.profiles) {
      expect(executionSettings(profile)?.reasoning).toBe(profile.model_id.startsWith('anthropic/') ? 'high' : 'medium');
      expect(executionSettings(profile)?.generation?.calls).toBe(44);
      expect(catalog.profiles.find((p) => p.model_id === profile.model_id)?.score_version).toBe(october.score_version);
    }
    expect(zhEnSource(october)).toEqual({ filename: 'v03-zh-en-anchors-20261009.json', date: '2026-10-09' });
  });
  it('defaults to Sol 6.1 while preserving Sol Pro and manually selected history', () => {
    const defaults = defaultModelIds(catalog.profiles);
    expect(defaults).toHaveLength(22);
    expect(defaults).toContain('openai/gpt-6.1-sol');
    expect(defaults).toContain('openai/gpt-5.6-sol-pro');
    expect(defaults).not.toContain('openai/gpt-6-sol');
    const known = previous.profiles.map((p) => p.model_id);
    expect(restoreSelection(JSON.stringify({ selected: defaultModelIds(previous.profiles), known }), catalog.profiles)).toEqual(defaults);
    expect(restoreSelection(JSON.stringify({ selected: ['openai/gpt-6-sol'], known }), catalog.profiles)).toContain('openai/gpt-6-sol');
  });
});
