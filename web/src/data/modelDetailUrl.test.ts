import { describe, expect, it } from 'vitest';
import { modelDetailHref } from './modelDetailUrl';

describe('model detail URL', () => {
  it('keeps the locale and safely encodes the model identifier', () => {
    expect(modelDetailHref('qwen/qwen3.8-max', 'zh-CN', '/remis-aventine/'))
      .toBe('/remis-aventine/?lang=zh-CN&model=qwen%2Fqwen3.8-max');
  });

  it('preserves the GitHub Pages directory when Vite uses a relative base', () => {
    expect(modelDetailHref('tencent/hy3', 'en', './', '/remis-aventine/'))
      .toBe('/remis-aventine/?lang=en&model=tencent%2Fhy3');
  });
});
