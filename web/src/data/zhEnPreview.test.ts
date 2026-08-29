import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { parseZhEnPreview } from './zhEnPreview';

const fixture = JSON.parse(readFileSync(new URL('../../public/data/v03-zh-en-preview.json', import.meta.url), 'utf8')) as unknown;

describe('ZH-EN public preview artifact', () => {
  it('loads the committed 17-contestant, two-direction result', () => {
    const result = parseZhEnPreview(fixture);
    const ranked = [...result.profiles].sort((left, right) => right.zh_en_score - left.zh_en_score);

    expect(result).toMatchObject({
      contestant_count: 17,
      direction_count: 2,
      soft_case_count: 677,
      soft_resolved_count: 640,
      soft_unresolved_count: 37,
      status: 'complete-preview',
    });
    expect(ranked[0]).toMatchObject({ model_id: 'openai/gpt-5.6-sol-pro', zh_en_score: 91.1842 });
  });

  it('contains no exam text, source text, candidate output, or judge rationale', () => {
    const serialized = JSON.stringify(fixture).toLowerCase();
    for (const forbidden of ['source_text', 'candidate_a', 'candidate_b', 'candidate_output', 'rationale', 'exam_items']) {
      expect(serialized).not.toContain(`"${forbidden}"`);
    }
  });
});
