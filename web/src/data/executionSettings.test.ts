import { describe, expect, it } from 'vitest';
import originalJson from '../../public/data/v03-zh-en-results.json';
import septemberJson from '../../public/data/v03-zh-en-anchors-20260925.json';
import localJson from '../../public/data/v03-zh-en-anchors-local-20261001.json';
import { parseZhEnPreview } from './zhEnPreview';
import { executionSettings, reasoningLabel } from './executionSettings';
import { zhEnProfileName } from './zhEnProfileName';

const profiles = [originalJson, septemberJson, localJson].flatMap((source) => parseZhEnPreview(source).profiles);
const luna = profiles.find((p) => p.model_id === 'openai/gpt-6-luna')!;

describe('execution settings provenance', () => {
  it('covers every published identity and labels Luna as high', () => {
    for (const profile of profiles) expect(executionSettings(profile)?.max_output_tokens).toBe(32768);
    expect(zhEnProfileName(luna)).toBe('GPT-6 Luna (high)');
  });
  it('distinguishes provider defaults from explicitly disabled and enabled thinking', () => {
    expect(reasoningLabel(profiles.find((p) => p.model_id === 'minimax/minimax-m3')!, true)).toBe('默认配置');
    expect(reasoningLabel(profiles.find((p) => p.model_id.startsWith('bilibili/'))!)).toBe('thinking off');
    expect(reasoningLabel(profiles.find((p) => p.model_id.includes('distill'))!)).toBe('thinking on');
  });
  it('does not reuse a setting for an unknown execution or mismatched model', () => {
    expect(reasoningLabel({ ...luna, execution_identity_sha256: 'unknown' })).toBe('unrecorded');
    expect(executionSettings({ ...luna, model_id: 'openai/gpt-6.1-sol' })).toBeUndefined();
  });
});
