import { describe, expect, it } from 'vitest';
import { defaultModelIds, restoreSelection } from './modelSelection';
import fixture from '../../public/data/v03-zh-en-results.json';
import { parseZhEnPreview } from './zhEnPreview';

const old = parseZhEnPreview(fixture).profiles.find((p) => p.model_id === 'openai/gpt-5.6-luna')!;
const next = { ...old, model_id: 'openai/gpt-6-luna' };
const sol = { ...old, model_id: 'openai/gpt-6-sol' };
describe('model selection', () => {
  it('hides a predecessor while retaining other tiers from the same vendor', () => {
    expect(defaultModelIds([old, next, sol])).toEqual([next.model_id, sol.model_id]);
  });
  it('preserves explicit historical selection and intentional empty selection', () => {
    expect(restoreSelection(JSON.stringify({ selected: [old.model_id], known: [old.model_id, next.model_id] }), [old, next])).toEqual([old.model_id]);
    expect(restoreSelection(JSON.stringify({ selected: [], known: [old.model_id, next.model_id] }), [old, next])).toEqual([]);
  });
  it('handles corrupt storage and new arrivals', () => {
    expect(restoreSelection('bad json', [old, next])).toEqual([next.model_id]);
    expect(restoreSelection(JSON.stringify({ selected: [old.model_id], known: [old.model_id] }), [old, next])).toEqual([next.model_id]);
    expect(restoreSelection(JSON.stringify({ selected: [], known: [old.model_id] }), [old, next])).toEqual([next.model_id]);
  });
  it('recognizes future numeric generations without confusing version 6.10 with 6.1', () => {
    const models = ['openai/gpt-6.9-luna', 'openai/gpt-6.10-luna', 'openai/gpt-6-sol-pro', 'deepseek/deepseek-v4-flash-0731', 'deepseek/deepseek-v4.1-flash', 'xiaomi/mimo-v2.5', 'xiaomi/mimo-v2.6-pro'].map((model_id) => ({ ...old, model_id }));
    expect(defaultModelIds(models)).toEqual(['openai/gpt-6.10-luna', 'openai/gpt-6-sol-pro', 'deepseek/deepseek-v4.1-flash', 'xiaomi/mimo-v2.5', 'xiaomi/mimo-v2.6-pro']);
  });
});
